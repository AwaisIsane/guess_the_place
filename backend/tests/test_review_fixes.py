from types import SimpleNamespace

import pytest
from redis.exceptions import RedisError

from app.main import app
from app.rate_limit import check_rate_limit
from app.routers.games import saved_result


def completed_round(number: int, score: int):
    return SimpleNamespace(
        number=number,
        score=score,
        distance_km=12.3456,
        guess_latitude=1.0,
        guess_longitude=2.0,
        location=SimpleNamespace(latitude=3.0, longitude=4.0),
    )


def test_replayed_result_preserves_fields_from_the_original_round():
    first = completed_round(1, 4_000)
    later = completed_round(2, 3_000)
    game = SimpleNamespace(rounds=[first, later], total_score=7_000, status="complete")

    result = saved_result(game, first)

    assert result["total_score"] == 4_000
    assert result["game_complete"] is False


def test_replayed_final_round_remains_complete():
    rounds = [completed_round(number, number * 100) for number in range(1, 6)]
    game = SimpleNamespace(rounds=rounds, total_score=1_500, status="complete")

    result = saved_result(game, rounds[-1])

    assert result["total_score"] == 1_500
    assert result["game_complete"] is True


def test_openapi_publishes_fastapi_validation_error_schema():
    response = app.openapi()["paths"]["/api/v1/games/{game_id}"]["get"]["responses"]["422"]

    assert response["content"]["application/json"]["schema"] == {
        "$ref": "#/components/schemas/HTTPValidationError"
    }


class RedisClient:
    def __init__(self, result=None, error=None):
        self.result = result
        self.error = error
        self.call = None

    def eval(self, *args):
        self.call = args
        if self.error:
            raise self.error
        return self.result


def rate_limit_settings(*, fail_open: bool):
    return SimpleNamespace(
        rate_limit_window_seconds=60,
        rate_limit_per_minute=120,
        rate_limit_fail_open=fail_open,
        redis_url="redis://example/0",
    )


def test_rate_limit_bucket_expires_at_the_aligned_boundary(monkeypatch):
    redis = RedisClient(result=(121, 1))
    monkeypatch.setattr("app.rate_limit.get_settings", lambda: rate_limit_settings(fail_open=False))
    monkeypatch.setattr("app.rate_limit.time.time", lambda: 119.9)
    monkeypatch.setattr("app.rate_limit.Redis.from_url", lambda *args, **kwargs: redis)

    allowed, retry_after = check_rate_limit("client")

    assert allowed is False
    assert retry_after == 1
    assert redis.call[2:] == ("rate:client:1", 1)


@pytest.mark.parametrize(
    ("fail_open", "expected"),
    [(True, (True, 0)), (False, (False, 1))],
)
def test_rate_limit_redis_failure_uses_boundary_retry(
    monkeypatch, fail_open: bool, expected: tuple[bool, int]
):
    redis = RedisClient(error=RedisError("unavailable"))
    monkeypatch.setattr(
        "app.rate_limit.get_settings", lambda: rate_limit_settings(fail_open=fail_open)
    )
    monkeypatch.setattr("app.rate_limit.time.time", lambda: 119.9)
    monkeypatch.setattr("app.rate_limit.Redis.from_url", lambda *args, **kwargs: redis)

    assert check_rate_limit("client") == expected
