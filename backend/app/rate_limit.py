import time

from redis import Redis
from redis.exceptions import RedisError

from .config import get_settings

SCRIPT = """
local current = redis.call('INCR', KEYS[1])
if current == 1 then redis.call('EXPIRE', KEYS[1], ARGV[1]) end
local ttl = redis.call('TTL', KEYS[1])
return {current, ttl}
"""


def check_rate_limit(identity: str) -> tuple[bool, int]:
    settings = get_settings()
    window = settings.rate_limit_window_seconds
    now = int(time.time())
    bucket = now // window
    expires_in = window - (now % window)
    try:
        redis = Redis.from_url(
            settings.redis_url,
            socket_connect_timeout=0.15,
            socket_timeout=0.15,
            decode_responses=True,
        )
        count, ttl = redis.eval(SCRIPT, 1, f"rate:{identity}:{bucket}", expires_in)
        return int(count) <= settings.rate_limit_per_minute, max(1, int(ttl))
    except RedisError:
        if settings.rate_limit_fail_open:
            return True, 0
        return False, expires_in
