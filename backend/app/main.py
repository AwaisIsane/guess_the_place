import logging
import time
import uuid
from collections import defaultdict, deque
from datetime import UTC, datetime

from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.responses import JSONResponse
from sqlalchemy import select, text
from sqlalchemy.orm import Session, selectinload

from .config import get_settings
from .db import get_db
from .models import Game, GameStatus, Round
from .schemas import GuessIn, PublicConfig
from .security import enforce_same_origin, session_id
from .services import assert_playable, calculate_score, create_game, haversine_km

app = FastAPI(title="WorldGuessr API", version="1.0.0")
log = logging.getLogger("worldguessr")
requests_by_key: dict[str, deque[float]] = defaultdict(deque)


@app.middleware("http")
async def request_controls(request: Request, call_next):
    started = time.monotonic()
    if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
        enforce_same_origin(request)
    key = request.client.host if request.client else "unknown"
    now = time.monotonic()
    bucket = requests_by_key[key]
    while bucket and bucket[0] < now - 60:
        bucket.popleft()
    if len(bucket) >= get_settings().rate_limit_per_minute:
        return JSONResponse({"detail": "Rate limit exceeded"}, 429)
    bucket.append(now)
    response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    log.info(
        "request",
        extra={"method": request.method, "path": request.url.path, "status": response.status_code,
               "duration_ms": round((time.monotonic() - started) * 1000)},
    )
    return response


def owned_game(game_id: uuid.UUID, sid: str, db: Session) -> Game:
    game = db.scalar(
        select(Game)
        .options(selectinload(Game.rounds).selectinload(Round.location))
        .where(Game.id == game_id)
    )
    if not game:
        raise HTTPException(404, "Game not found")
    if game.session_id != sid:
        raise HTTPException(404, "Game not found")
    try:
        assert_playable(game)
    except ValueError as exc:
        db.commit()
        raise HTTPException(410, str(exc)) from exc
    return game


def round_public(game: Game):
    current = game.rounds[game.current_round - 1] if game.current_round <= 5 else None
    return {
        "game_id": str(game.id),
        "status": game.status.value,
        "current_round": game.current_round,
        "total_score": game.total_score,
        "round": None if current is None else {
            "number": current.number,
            "image_id": current.location.image_id,
            "sequence_id": current.location.sequence_id,
            "compass_angle": current.location.compass_angle,
        },
    }


@app.get("/api/v1/config", response_model=PublicConfig)
def config():
    settings = get_settings()
    return PublicConfig(
        mapillary_client_token=settings.mapillary_client_token,
        map_style_url=settings.map_style_url,
        map_attribution=settings.map_attribution,
    )


@app.post("/api/v1/games", status_code=201)
def new_game(request: Request, response: Response, db: Session = Depends(get_db)):
    sid = session_id(request, response)
    try:
        return round_public(create_game(db, sid))
    except LookupError as exc:
        raise HTTPException(503, str(exc)) from exc


@app.get("/api/v1/games/{game_id}")
def get_game(
    game_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    sid = session_id(request, response)
    return round_public(owned_game(game_id, sid, db))


@app.post("/api/v1/games/{game_id}/rounds/{number}/guess")
def guess(
    game_id: uuid.UUID,
    number: int,
    body: GuessIn,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    sid = session_id(request, response)
    game = owned_game(game_id, sid, db)
    if game.status != GameStatus.active or number != game.current_round or not 1 <= number <= 5:
        raise HTTPException(409, "This round is not active")
    game_round = game.rounds[number - 1]
    if game_round.guessed:
        raise HTTPException(409, "Guess already submitted")
    location = game_round.location
    distance = haversine_km(body.latitude, body.longitude, location.latitude, location.longitude)
    score = calculate_score(distance)
    game_round.guessed = True
    game_round.guess_latitude = body.latitude
    game_round.guess_longitude = body.longitude
    game_round.distance_km = distance
    game_round.score = score
    game_round.guessed_at = datetime.now(UTC)
    location.last_selected_at = datetime.now(UTC)
    game.total_score += score
    game.current_round += 1
    if number == 5:
        game.status = GameStatus.complete
    db.commit()
    return {
        "round": number,
        "distance_km": round(distance, 3),
        "score": score,
        "total_score": game.total_score,
        "guess": {"latitude": body.latitude, "longitude": body.longitude},
        "actual": {"latitude": location.latitude, "longitude": location.longitude},
        "game_complete": game.status == GameStatus.complete,
    }


@app.get("/api/v1/games/{game_id}/summary")
def summary(
    game_id: uuid.UUID,
    request: Request,
    response: Response,
    db: Session = Depends(get_db),
):
    sid = session_id(request, response)
    game = owned_game(game_id, sid, db)
    if game.status != GameStatus.complete:
        raise HTTPException(409, "Game is not complete")
    return {
        "game_id": str(game.id),
        "total_score": game.total_score,
        "maximum_score": 25000,
        "rounds": [
            {
                "round": item.number,
                "score": item.score,
                "distance_km": item.distance_km,
                "guess": {"latitude": item.guess_latitude, "longitude": item.guess_longitude},
                "actual": {
                    "latitude": item.location.latitude,
                    "longitude": item.location.longitude,
                },
            }
            for item in game.rounds
        ],
    }


@app.get("/health/live")
def live():
    return {"status": "ok"}


@app.get("/health/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        raise HTTPException(503, "database unavailable") from exc
    return {"status": "ready"}
