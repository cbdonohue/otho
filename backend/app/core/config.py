from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    app_name: str = "Otho"
    database_url: str = "sqlite+aiosqlite:///./otho.db"
    redis_url: str = ""
    cors_origins: str = "http://localhost:5173,http://localhost:3000,http://127.0.0.1:5173"
    sleeper_base_url: str = "https://api.sleeper.app/v1"
    default_league_id: str = ""
    openai_api_key: str = ""
    openai_base_url: str = "https://api.openai.com/v1"
    openai_model: str = "gpt-4o-mini"
    enable_scheduler: bool = True
    log_level: str = "INFO"

    # Adaptive polling (seconds)
    poll_players_s: int = 24 * 3600
    poll_league_settings_s: int = 6 * 3600
    poll_rosters_s: int = 90
    poll_transactions_s: int = 90
    poll_matchups_live_s: int = 20
    poll_matchups_gameday_s: int = 120
    poll_matchups_off_s: int = 600
    poll_trending_s: int = 420

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    @property
    def is_sqlite(self) -> bool:
        return self.database_url.startswith("sqlite")

    @property
    def has_redis(self) -> bool:
        return bool(self.redis_url)

    @property
    def has_openai(self) -> bool:
        return bool(self.openai_api_key)


@lru_cache
def get_settings() -> Settings:
    return Settings()
