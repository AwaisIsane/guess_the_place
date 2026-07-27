import math

from app.services import calculate_score, haversine_km


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
