"""ML service configuration (env-driven, single source of truth)."""
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    APP_NAME: str = "NEPSE AI ML Service"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True

    # Auth — shares the core backend's SECRET_KEY so its access tokens work here.
    SECRET_KEY: str = "change-me"
    JWT_ALGORITHM: str = "HS256"
    ML_API_KEYS: str = ""

    # Redis
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 1
    REDIS_PASSWORD: str = ""
    PREDICTION_CACHE_TTL: int = 30
    RATE_LIMIT_PER_MIN: int = 120

    # Data
    USE_DB: bool = False
    POSTGRES_USER: str = "nepse"
    POSTGRES_PASSWORD: str = "nepse_secret"
    POSTGRES_DB: str = "nepse_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # Models
    MODEL_DIR: str = "model_store"
    LOOKBACK: int = 150

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @property
    def api_keys(self) -> set[str]:
        return {k.strip() for k in self.ML_API_KEYS.split(",") if k.strip()}


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
