from typing import Literal
from uuid import UUID

from pydantic import BaseModel, Field


class GuessIn(BaseModel):
    latitude: float = Field(ge=-90, le=90)
    longitude: float = Field(ge=-180, le=180)


class PublicConfig(BaseModel):
    mapillary_client_token: str
    map_style_url: str
    map_attribution: str
    rounds_per_game: int = 5


class Coordinate(BaseModel):
    latitude: float
    longitude: float


class RoundView(BaseModel):
    number: int
    image_id: str
    sequence_id: str | None = None
    compass_angle: float | None = None


class GameView(BaseModel):
    game_id: UUID
    status: Literal["active", "complete", "expired"]
    current_round: int
    total_score: int
    round: RoundView | None


class GuessResult(BaseModel):
    round: int
    distance_km: float
    score: int
    total_score: int
    guess: Coordinate
    actual: Coordinate
    game_complete: bool


class SummaryRound(BaseModel):
    round: int
    score: int
    distance_km: float
    guess: Coordinate
    actual: Coordinate


class GameSummary(BaseModel):
    game_id: UUID
    total_score: int
    maximum_score: int = 25_000
    rounds: list[SummaryRound]


class ErrorResponse(BaseModel):
    detail: str
    request_id: str | None = None


class DependencyStatus(BaseModel):
    status: Literal["up", "down"]
    latency_ms: float | None = None
    detail: str | None = None


class Readiness(BaseModel):
    status: Literal["ready", "degraded"]
    dependencies: dict[str, DependencyStatus]
