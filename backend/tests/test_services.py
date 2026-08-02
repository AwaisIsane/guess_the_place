import math
from types import SimpleNamespace

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session

from app.db import Base
from app.models import PlayableLocation
from app.services import calculate_score, haversine_km, select_locations


@pytest.fixture
def db():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    Base.metadata.create_all(engine)
    with Session(engine) as session:
        yield session


def location(image_id: str) -> PlayableLocation:
    return PlayableLocation(
        image_id=image_id,
        country_code="AU",
        latitude=-33.8688,
        longitude=151.2093,
        quality=1.0,
    )


def settings(*, graph_token: str, allow_demo: bool):
    return SimpleNamespace(
        allow_demo_catalog=allow_demo,
        country_pool_minimum=1,
        eligible_country_minimum=1,
        mapillary_graph_token=graph_token,
        recent_location_limit=25,
    )


def test_scoring_boundaries():
    assert calculate_score(0) == 5000
    assert calculate_score(2000) == round(5000 / math.e)
    assert calculate_score(100_000) == 0


def test_haversine_known_distance():
    distance = haversine_km(51.5074, -0.1278, 48.8566, 2.3522)
    assert 342 < distance < 345


def test_haversine_symmetry():
    a = haversine_km(-33.86, 151.2, 35.67, 139.65)
    b = haversine_km(35.67, 139.65, -33.86, 151.2)
    assert a == b


def test_real_catalog_excludes_demo_locations_from_primary_and_fallback_queries(
    db, monkeypatch
):
    db.add_all([location("real-image"), location("demo-au-1")])
    db.commit()
    monkeypatch.setattr(
        "app.services.get_settings",
        lambda: settings(graph_token="graph-token", allow_demo=True),
    )

    selected = select_locations(db, "session", count=2)

    assert [item.image_id for item in selected] == ["real-image", "real-image"]


def test_demo_catalog_is_available_only_when_explicitly_enabled(db, monkeypatch):
    db.add(location("demo-au-1"))
    db.commit()
    monkeypatch.setattr(
        "app.services.get_settings",
        lambda: settings(graph_token="", allow_demo=True),
    )

    selected = select_locations(db, "session", count=1)

    assert [item.image_id for item in selected] == ["demo-au-1"]


def test_demo_catalog_is_rejected_when_disabled(db, monkeypatch):
    db.add(location("demo-au-1"))
    db.commit()
    monkeypatch.setattr(
        "app.services.get_settings",
        lambda: settings(graph_token="", allow_demo=False),
    )

    with pytest.raises(LookupError, match="catalog is still warming up"):
        select_locations(db, "session", count=1)
