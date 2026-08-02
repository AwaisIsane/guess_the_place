import json
import logging
import threading
import time
from collections import Counter

log = logging.getLogger("worldguessr.http")
_lock = threading.Lock()
_requests: Counter[tuple[str, str, int]] = Counter()
_durations: Counter[tuple[str, str]] = Counter()


def observe(method: str, path: str, status: int, duration: float, request_id: str) -> None:
    route = path if not path.startswith("/api/v1/games/") else "/api/v1/games/{id}"
    with _lock:
        _requests[(method, route, status)] += 1
        _durations[(method, route)] += duration
    log.info(
        json.dumps(
            {
                "event": "request",
                "request_id": request_id,
                "method": method,
                "path": path,
                "status": status,
                "duration_ms": round(duration * 1000, 2),
            }
        )
    )


def render_metrics() -> str:
    lines = [
        "# HELP worldguessr_http_requests_total HTTP requests.",
        "# TYPE worldguessr_http_requests_total counter",
    ]
    with _lock:
        for (method, route, status), value in sorted(_requests.items()):
            labels = f'method="{method}",route="{route}",status="{status}"'
            lines.append(f"worldguessr_http_requests_total{{{labels}}} {value}")
        lines += [
            "# HELP worldguessr_http_request_duration_seconds_sum Request duration.",
            "# TYPE worldguessr_http_request_duration_seconds_sum counter",
        ]
        for (method, route), value in sorted(_durations.items()):
            labels = f'method="{method}",route="{route}"'
            lines.append(f"worldguessr_http_request_duration_seconds_sum{{{labels}}} {value}")
    return "\n".join(lines) + "\n"


class Timer:
    def __enter__(self):
        self.started = time.monotonic()
        return self

    def __exit__(self, *_):
        self.elapsed = time.monotonic() - self.started
