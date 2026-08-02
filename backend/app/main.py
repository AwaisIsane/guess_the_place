import logging
import time
import uuid
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from .config import get_settings
from .rate_limit import check_rate_limit
from .routers import games, health
from .security import enforce_same_origin
from .telemetry import observe


@asynccontextmanager
async def lifespan(_: FastAPI):
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    yield


def create_app() -> FastAPI:
    application = FastAPI(
        title="WorldGuessr API",
        version="1.1.0",
        description="Five-round guest geography game API.",
        lifespan=lifespan,
    )

    @application.middleware("http")
    async def request_controls(request: Request, call_next):
        started = time.monotonic()
        request_id = request.headers.get("X-Request-ID") or str(uuid.uuid4())
        request.state.request_id = request_id
        if request.method in {"POST", "PUT", "PATCH", "DELETE"}:
            enforce_same_origin(request)
        identity = request.client.host if request.client else "unknown"
        allowed, retry_after = check_rate_limit(identity)
        if not allowed:
            response = JSONResponse(
                {"detail": "Rate limit exceeded", "request_id": request_id},
                status_code=429,
                headers={"Retry-After": str(retry_after)},
            )
        else:
            response = await call_next(request)
        response.headers.update(
            {
                "X-Request-ID": request_id,
                "X-Content-Type-Options": "nosniff",
                "Referrer-Policy": "strict-origin-when-cross-origin",
            }
        )
        if get_settings().telemetry_enabled:
            observe(
                request.method,
                request.url.path,
                response.status_code,
                time.monotonic() - started,
                request_id,
            )
        return response

    application.include_router(games.router)
    application.include_router(health.router)
    return application


app = create_app()
