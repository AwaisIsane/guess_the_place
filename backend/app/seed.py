import argparse
import random

from sqlalchemy import select

from .catalog import rebuild_catalog_counts
from .db import SessionLocal
from .models import PlayableLocation

CENTERS = {
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


def seed_demo(per_country: int = 25) -> int:
    inserted = 0
    with SessionLocal() as db:
        for country, (lat, lng) in CENTERS.items():
            for index in range(per_country):
                image_id = f"demo-{country.lower()}-{index}"
                existing = select(PlayableLocation.id).where(PlayableLocation.image_id == image_id)
                if db.scalar(existing):
                    continue
                db.add(
                    PlayableLocation(
                        image_id=image_id,
                        sequence_id=f"demo-{country.lower()}",
                        country_code=country,
                        latitude=lat + random.uniform(-0.15, 0.15),
                        longitude=lng + random.uniform(-0.15, 0.15),
                        quality=0.8,
                    )
                )
                inserted += 1
        db.commit()
        rebuild_catalog_counts(db)
    return inserted


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--demo", action="store_true", help="Seed non-production demo locations")
    parser.add_argument("--per-country", type=int, default=25)
    args = parser.parse_args()
    if not args.demo:
        parser.error(
            "Provider seed requires deployment-specific country boundary inputs; use --demo"
        )
    print(f"Inserted {seed_demo(args.per_country)} demo locations")
