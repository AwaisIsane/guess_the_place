import asyncio
import logging
import random
from datetime import UTC, datetime, timedelta

import httpx
from sqlalchemy import delete, func, select

from .config import get_settings
from .db import SessionLocal
from .models import CountryCatalog, LocationStatus, PlayableLocation

log = logging.getLogger("worldguessr.catalog")

# Compact regions around well-covered cities. Keeping the boxes small avoids
# Mapillary's "reduce the amount of data" response in dense areas.
DISCOVERY_CENTERS = {
    "AU": (-33.8688, 151.2093),
    "BR": (-23.5505, -46.6333),
    "DE": (52.5200, 13.4050),
    "FR": (48.8566, 2.3522),
    "IN": (28.6139, 77.2090),
    "JP": (35.6762, 139.6503),
    "MX": (19.4326, -99.1332),
    "NZ": (-36.8509, 174.7645),
    "US": (40.7128, -74.0060),
    "ZA": (-33.9249, 18.4241),
}


async def fetch_images(bbox: str, after: str | None = None) -> dict:
    settings = get_settings()
    params = {
        "access_token": settings.mapillary_graph_token,
        "bbox": bbox,
        "fields": "id,sequence,geometry,compass_angle,captured_at",
        "limit": 100,
    }
    if after:
        params["after"] = after
    delay = 1.0
    async with httpx.AsyncClient(timeout=20) as client:
        for attempt in range(5):
            try:
                response = await client.get("https://graph.mapillary.com/images", params=params)
                response.raise_for_status()
                return response.json()
            except httpx.HTTPStatusError as exc:
                if (
                    exc.response.status_code == 500
                    and "reduce the amount of data" in exc.response.text.lower()
                ):
                    raise
                if attempt == 4:
                    raise
                await asyncio.sleep(delay + random.random())
                delay *= 2
            except (httpx.HTTPError, ValueError):
                if attempt == 4:
                    raise
                await asyncio.sleep(delay + random.random())
                delay *= 2
    return {}


def _bbox(latitude: float, longitude: float, radius: float = 0.001) -> str:
    return f"{longitude - radius},{latitude - radius},{longitude + radius},{latitude + radius}"


async def discover_country(country: str, latitude: float, longitude: float) -> list[dict]:
    try:
        return (await fetch_images(_bbox(latitude, longitude))).get("data", [])
    except httpx.HTTPStatusError as exc:
        # Dense regions can exceed Mapillary's internal query limit even when
        # the requested result limit is small. Four smaller cells avoid it.
        if exc.response.status_code != 500:
            raise
        cells = [
            _bbox(latitude + dy, longitude + dx, 0.00045)
            for dy in (-0.0005, 0.0005)
            for dx in (-0.0005, 0.0005)
        ]
        pages = await asyncio.gather(*(fetch_images(cell) for cell in cells))
        return [image for page in pages for image in page.get("data", [])]


async def refill_catalog(ctx=None) -> int:
    settings = get_settings()
    if not settings.mapillary_graph_token:
        log.info("Mapillary catalog discovery skipped: MAPILLARY_GRAPH_TOKEN is not set")
        return 0

    results = await asyncio.gather(
        *(
            discover_country(country, latitude, longitude)
            for country, (latitude, longitude) in DISCOVERY_CENTERS.items()
        ),
        return_exceptions=True,
    )
    inserted = 0
    with SessionLocal() as db:
        for (country, _), result in zip(DISCOVERY_CENTERS.items(), results, strict=True):
            if isinstance(result, Exception):
                log.warning("Mapillary discovery failed for %s: %s", country, result)
                continue
            seen: set[str] = set()
            for image in result:
                image_id = str(image.get("id", ""))
                geometry = image.get("geometry") or {}
                coordinates = geometry.get("coordinates") or []
                if not image_id or image_id in seen or len(coordinates) < 2:
                    continue
                seen.add(image_id)
                location = db.scalar(
                    select(PlayableLocation).where(PlayableLocation.image_id == image_id)
                )
                if location is None:
                    location = PlayableLocation(image_id=image_id)
                    db.add(location)
                    inserted += 1
                sequence = image.get("sequence")
                location.sequence_id = (
                    str(sequence.get("id") if isinstance(sequence, dict) else sequence or "")
                    or None
                )
                location.country_code = country
                location.longitude = coordinates[0]
                location.latitude = coordinates[1]
                location.compass_angle = image.get("compass_angle")
                location.quality = 1.0
                location.status = LocationStatus.active
                captured_at = image.get("captured_at")
                if captured_at:
                    location.captured_at = datetime.fromtimestamp(captured_at / 1000, UTC)
                location.metadata_fetched_at = datetime.now(UTC)
                if len(seen) >= settings.country_pool_target:
                    break
        db.commit()
        rebuild_catalog_counts(db)

        eligible = db.scalar(
            select(func.count()).select_from(
                select(PlayableLocation.country_code)
                .where(
                    PlayableLocation.status == LocationStatus.active,
                    ~PlayableLocation.image_id.like("demo-%"),
                )
                .group_by(PlayableLocation.country_code)
                .having(func.count() >= settings.country_pool_minimum)
                .subquery()
            )
        )
        if eligible >= settings.eligible_country_minimum:
            demos = db.scalars(
                select(PlayableLocation).where(PlayableLocation.image_id.like("demo-%"))
            )
            for location in demos:
                location.status = LocationStatus.stale
            db.commit()
            rebuild_catalog_counts(db)
        elif settings.allow_demo_catalog:
            demos = db.scalars(
                select(PlayableLocation).where(PlayableLocation.image_id.like("demo-%"))
            )
            for location in demos:
                location.status = LocationStatus.active
            db.commit()
            rebuild_catalog_counts(db)
    log.info("Mapillary catalog discovery added %d images", inserted)
    return inserted


async def cleanup_expired(ctx):
    with SessionLocal() as db:
        from .models import Game

        result = db.execute(delete(Game).where(Game.expires_at < datetime.now(UTC)))
        db.commit()
        return result.rowcount


async def prune_stale_locations(ctx):
    cutoff = datetime.now(UTC) - timedelta(days=90)
    with SessionLocal() as db:
        result = db.execute(
            delete(PlayableLocation).where(
                PlayableLocation.status != LocationStatus.active,
                PlayableLocation.metadata_fetched_at < cutoff,
            )
        )
        db.commit()
        return result.rowcount


def rebuild_catalog_counts(db):
    counts = db.execute(
        select(PlayableLocation.country_code, func.count())
        .where(PlayableLocation.status == LocationStatus.active)
        .group_by(PlayableLocation.country_code)
    )
    for country, count in counts:
        state = db.get(CountryCatalog, country) or CountryCatalog(country_code=country)
        state.active_count = count
        state.last_refilled_at = datetime.now(UTC)
        db.add(state)
    db.commit()
