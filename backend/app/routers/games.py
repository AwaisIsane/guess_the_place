import uuid
from datetime import UTC, datetime

from fastapi import APIRouter, Depends, Header, HTTPException, Request, Response
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from ..config import get_settings
from ..db import get_db
from ..models import Game, GameStatus, Round
from ..schemas import (
    ErrorResponse,
    GameSummary,
    GameView,
    GuessIn,
    GuessResult,
    PublicConfig,
)
from ..security import session_id
from ..services import ROUNDS_PER_GAME, assert_playable, calculate_score, create_game, haversine_km

router = APIRouter(prefix="/api/v1", tags=["game"])
ERRORS = {
    404: {"model": ErrorResponse},
    409: {"model": ErrorResponse},
    410: {"model": ErrorResponse},
}


def owned_game(game_id: uuid.UUID, sid: str, db: Session, *, lock: bool = False) -> Game:
    stmt = (
        select(Game)
        .options(selectinload(Game.rounds).selectinload(Round.location))
        .where(Game.id == game_id)
    )
    if lock:
        stmt = stmt.with_for_update()
    game = db.scalar(stmt)
    if not game or game.session_id != sid:
        raise HTTPException(404, "Game not found")
    try:
        assert_playable(game)
    except ValueError as exc:
        db.commit()
        raise HTTPException(410, str(exc)) from exc
    return game


def round_public(game: Game) -> dict:
    current = game.rounds[game.current_round - 1] if game.current_round <= 5 else None
    return {
        "game_id": game.id,
        "status": game.status.value,
        "current_round": game.current_round,
        "total_score": game.total_score,
        "round": None
        if current is None
        else {
            "number": current.number,
            "image_id": current.location.image_id,
            "sequence_id": current.location.sequence_id,
            "compass_angle": current.location.compass_angle,
        },
    }


def saved_result(game: Game, item: Round) -> dict:
    location = item.location
    return {
        "round": item.number,
        "distance_km": round(item.distance_km or 0, 3),
        "score": item.score or 0,
        "total_score": sum(
            (round_item.score or 0)
            for round_item in game.rounds
            if round_item.number <= item.number
        ),
        "guess": {"latitude": item.guess_latitude, "longitude": item.guess_longitude},
        "actual": {"latitude": location.latitude, "longitude": location.longitude},
        "game_complete": item.number == ROUNDS_PER_GAME,
    }


@router.get("/config", response_model=PublicConfig)
def config():
    settings = get_settings()
    return PublicConfig(
        mapillary_client_token=settings.mapillary_client_token,
        map_style_url=settings.map_style_url,
        map_attribution=settings.map_attribution,
    )


@router.post(
    "/games",
    response_model=GameView,
    status_code=201,
    responses={503: {"model": ErrorResponse}},
)
def new_game(request: Request, response: Response, db: Session = Depends(get_db)):
    try:
        return round_public(create_game(db, session_id(request, response)))
    except LookupError as exc:
        raise HTTPException(503, str(exc)) from exc


@router.get("/games/{game_id}", response_model=GameView, responses=ERRORS)
def get_game(
    game_id: uuid.UUID, request: Request, response: Response, db: Session = Depends(get_db)
):
    return round_public(owned_game(game_id, session_id(request, response), db))


@router.post("/games/{game_id}/rounds/{number}/guess", response_model=GuessResult, responses=ERRORS)
def guess(
    game_id: uuid.UUID,
    number: int,
    body: GuessIn,
    request: Request,
    response: Response,
    idempotency_key: uuid.UUID = Header(alias="Idempotency-Key"),
    db: Session = Depends(get_db),
):
    game = owned_game(game_id, session_id(request, response), db, lock=True)
    if not 1 <= number <= 5:
        raise HTTPException(409, "This round is not active")
    item = game.rounds[number - 1]
    if item.guessed:
        if item.idempotency_key == idempotency_key:
            return saved_result(game, item)
        raise HTTPException(409, "Round already completed with another idempotency key")
    if game.status != GameStatus.active or number != game.current_round:
        raise HTTPException(409, "This round is not active")
    location = item.location
    distance = haversine_km(body.latitude, body.longitude, location.latitude, location.longitude)
    item.guessed, item.idempotency_key = True, idempotency_key
    item.guess_latitude, item.guess_longitude = body.latitude, body.longitude
    item.distance_km = distance
    item.score = calculate_score(distance)
    item.guessed_at = datetime.now(UTC)
    location.last_selected_at = datetime.now(UTC)
    game.total_score += item.score
    game.current_round += 1
    if number == 5:
        game.status = GameStatus.complete
    db.commit()
    return saved_result(game, item)


@router.get("/games/{game_id}/summary", response_model=GameSummary, responses=ERRORS)
def summary(
    game_id: uuid.UUID, request: Request, response: Response, db: Session = Depends(get_db)
):
    game = owned_game(game_id, session_id(request, response), db)
    if game.status != GameStatus.complete:
        raise HTTPException(409, "Game is not complete")
    return {
        "game_id": game.id,
        "total_score": game.total_score,
        "maximum_score": 25_000,
        "rounds": [
            {
                "round": item.number,
                "score": item.score,
                "distance_km": item.distance_km,
                "guess": {
                    "latitude": item.guess_latitude,
                    "longitude": item.guess_longitude,
                },
                "actual": {
                    "latitude": item.location.latitude,
                    "longitude": item.location.longitude,
                },
            }
            for item in game.rounds
        ],
    }
