import time

from fastapi import APIRouter, Depends, Response
from redis import Redis
from sqlalchemy import text
from sqlalchemy.orm import Session

from ..config import get_settings
from ..db import get_db
from ..schemas import Readiness
from ..telemetry import render_metrics

router = APIRouter(tags=["operations"])


@router.get("/health/live")
def live():
    return {"status": "ok"}


@router.get("/health/ready", response_model=Readiness)
def ready(response: Response, db: Session = Depends(get_db)):
    dependencies = {}
    for name, check in (
        ("postgresql", lambda: db.execute(text("SELECT 1"))),
        ("redis", lambda: Redis.from_url(get_settings().redis_url, socket_timeout=0.5).ping()),
    ):
        started = time.monotonic()
        try:
            check()
            dependencies[name] = {
                "status": "up",
                "latency_ms": round((time.monotonic() - started) * 1000, 2),
            }
        except Exception as exc:
            dependencies[name] = {"status": "down", "detail": type(exc).__name__}
    status = "ready" if all(x["status"] == "up" for x in dependencies.values()) else "degraded"
    if status == "degraded":
        response.status_code = 503
    return {"status": status, "dependencies": dependencies}


@router.get("/metrics", response_class=Response)
def metrics():
    return Response(render_metrics(), media_type="text/plain; version=0.0.4")
