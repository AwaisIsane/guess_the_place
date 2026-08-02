from functools import lru_cache

from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    environment: str = "development"
    database_url: str = "postgresql+psycopg://worldguessr:worldguessr@postgres/worldguessr"
    redis_url: str = "redis://redis:6379/0"
    signing_secret: str = "development-only-change-me"
    public_origin: str = "http://localhost"
    mapillary_client_token: str = ""
    mapillary_graph_token: str = ""
    map_style_url: str = "https://tiles.openfreemap.org/styles/liberty"
    map_attribution: str = "© OpenStreetMap contributors"
    game_ttl_days: int = 30
    eligible_country_minimum: int = 10
    country_pool_minimum: int = 25
    country_pool_target: int = 200
    recent_location_limit: int = 25
    rate_limit_per_minute: int = 120
    rate_limit_window_seconds: int = 60
    rate_limit_fail_open: bool = True
    telemetry_enabled: bool = True
    allow_demo_catalog: bool = False


@lru_cache
def get_settings() -> Settings:
    return Settings()
