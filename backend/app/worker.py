from arq import cron
from arq.connections import RedisSettings

from .catalog import cleanup_expired, prune_stale_locations, refill_catalog
from .config import get_settings


class WorkerSettings:
    functions = [cleanup_expired, prune_stale_locations, refill_catalog]
    cron_jobs = [
        cron(cleanup_expired, hour=3, minute=10),
        cron(prune_stale_locations, weekday=0, hour=4),
        cron(refill_catalog, hour={0, 6, 12, 18}, minute=20),
    ]
    on_startup = refill_catalog
    max_jobs = 3
    job_timeout = 300
    redis_settings = RedisSettings.from_dsn(get_settings().redis_url)
