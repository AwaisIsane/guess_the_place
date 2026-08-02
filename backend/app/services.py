import math
import random
from datetime import UTC, datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from .config import get_settings
from .models import Game, GameStatus, LocationStatus, PlayableLocation, Round

ROUNDS_PER_GAME = 5


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    radius = 6371.0088
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lon2 - lon1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return radius * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def calculate_score(distance_km: float) -> int:
    return min(5000, max(0, round(5000 * math.exp(-distance_km / 2000))))


def eligible_countries(db: Session) -> list[str]:
    settings = get_settings()
    minimum = settings.country_pool_minimum
    real_only = bool(settings.mapillary_graph_token) or not settings.allow_demo_catalog
    stmt = (
        select(PlayableLocation.country_code)
        .where(PlayableLocation.status == LocationStatus.active)
        .group_by(PlayableLocation.country_code)
        .having(func.count() >= minimum)
    )
    if real_only:
        stmt = stmt.where(~PlayableLocation.image_id.like("demo-%"))
    return list(db.scalars(stmt))


def select_locations(db: Session, session_id: str, count: int = ROUNDS_PER_GAME):
    countries = eligible_countries(db)
    settings = get_settings()
    real_provider_ready = bool(settings.mapillary_graph_token)
    real_only = real_provider_ready or not settings.allow_demo_catalog
    required = (
        1
        if settings.allow_demo_catalog or real_provider_ready
        else settings.eligible_country_minimum
    )
    if len(countries) < required:
        raise LookupError("The location catalog is still warming up")

    recent = set(
        db.scalars(
            select(Round.location_id)
            .join(Game)
            .where(Game.session_id == session_id)
            .order_by(Game.created_at.desc())
            .limit(settings.recent_location_limit)
        )
    )
    chosen: list[PlayableLocation] = []
    available_countries = countries[:]
    random.shuffle(available_countries)
    for index in range(count):
        country = available_countries[index % len(available_countries)]
        candidate_filters = [
            PlayableLocation.country_code == country,
            PlayableLocation.status == LocationStatus.active,
        ]
        if real_only:
            candidate_filters.append(~PlayableLocation.image_id.like("demo-%"))
        candidates = list(
            db.scalars(
                select(PlayableLocation).where(
                    *candidate_filters,
                    PlayableLocation.id.not_in(recent | {x.id for x in chosen}),
                )
            )
        )
        if not candidates:
            candidates = list(
                db.scalars(select(PlayableLocation).where(*candidate_filters))
            )
        if not candidates:
            raise LookupError("No playable locations available")
        weights = [max(location.quality, 0.01) for location in candidates]
        chosen.append(random.choices(candidates, weights=weights)[0])
    return chosen


def create_game(db: Session, session_id: str) -> Game:
    locations = select_locations(db, session_id)
    game = Game(
        session_id=session_id,
        expires_at=datetime.now(UTC) + timedelta(days=get_settings().game_ttl_days),
    )
    game.rounds = [Round(number=i + 1, location=location) for i, location in enumerate(locations)]
    db.add(game)
    db.commit()
    db.refresh(game)
    return game


def assert_playable(game: Game) -> None:
    expires = game.expires_at
    if expires.tzinfo is None:
        expires = expires.replace(tzinfo=UTC)
    if expires <= datetime.now(UTC):
        game.status = GameStatus.expired
        raise ValueError("Game has expired")
