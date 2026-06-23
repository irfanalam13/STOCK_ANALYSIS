"""Centralized application configuration.

All settings are read from environment variables (or a local ``.env`` file).
This is the single source of truth for connection strings and tunables so the
rest of the codebase never reads ``os.environ`` directly.
"""
from functools import lru_cache

from pydantic import computed_field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env", env_file_encoding="utf-8", extra="ignore"
    )

    # ---- Application ----
    APP_NAME: str = "NEPSE Trading Backend"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # ---- PostgreSQL ----
    POSTGRES_USER: str = "nepse"
    POSTGRES_PASSWORD: str = "nepse_secret"
    POSTGRES_DB: str = "nepse_db"
    POSTGRES_HOST: str = "localhost"
    POSTGRES_PORT: int = 5432

    # ---- Redis ----
    REDIS_HOST: str = "localhost"
    REDIS_PORT: int = 6379
    REDIS_DB: int = 0
    REDIS_PASSWORD: str = ""

    # ---- Security ----
    SECRET_KEY: str = "change-me"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    REFRESH_TOKEN_EXPIRE_DAYS: int = 7
    JWT_ALGORITHM: str = "HS256"

    # ---- Market data ----
    MARKET_FETCH_INTERVAL: int = 15
    NEPSE_API_URL: str = ""
    CACHE_TTL_SECONDS: int = 10

    # ---- Portfolio (paper trading) ----
    PORTFOLIO_INITIAL_BALANCE: float = 1_000_000.0  # NPR virtual cash
    PORTFOLIO_FEE_RATE: float = 0.004  # 0.4% simulated broker commission

    # ---- ML risk integration ----
    ML_SERVICE_URL: str = "http://localhost:8100"
    ML_API_KEY: str = ""  # optional; if unset, the user's JWT is forwarded
    RISK_CACHE_TTL: int = 45  # seconds to cache per-symbol risk in Redis

    # ---- Alerts & notifications (Phase 6) ----
    ALERT_MAX_PER_USER: int = 100          # hard cap on active alerts per user
    ALERT_DEFAULT_COOLDOWN: int = 300      # seconds an alert is silenced after firing
    ALERT_RATE_LIMIT: int = 30             # max notifications per user per window
    ALERT_RATE_WINDOW: int = 3600          # rate-limit window in seconds (1h)
    VOLUME_AVG_LOOKBACK: int = 30          # rows used for the volume-average baseline
    VOLUME_AVG_CACHE_TTL: int = 300        # seconds to cache a symbol's avg volume

    # ---- Security & scalability hardening (Phase 8) ----
    # CORS: comma-separated allowed origins (use "*" only in dev).
    CORS_ORIGINS: str = "*"
    SECURITY_HEADERS_ENABLED: bool = True
    HSTS_ENABLED: bool = False  # enable only when served over HTTPS

    # API rate limiting (Redis-backed; fail-open if Redis is down).
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_WINDOW: int = 60            # seconds per window
    RATE_LIMIT_ANON: int = 30             # per-IP, unauthenticated
    RATE_LIMIT_FREE: int = 100            # per-user, free tier (viewer)
    RATE_LIMIT_PREMIUM: int = 1000        # per-user, premium tier (trader/analyst)
    RATE_LIMIT_ADMIN: int = 5000          # per-user, admin

    # API keys for external/service-to-service callers (comma-separated).
    API_KEYS: str = ""

    # WebSocket hardening.
    WS_MSG_RATE_LIMIT: int = 30           # max client frames per window
    WS_MSG_WINDOW: int = 10               # seconds
    WS_IDLE_TIMEOUT: int = 120            # disconnect after N seconds idle

    # Field-level encryption (AES/Fernet). If empty, derived from SECRET_KEY.
    DATA_ENCRYPTION_KEY: str = ""

    # Rule-based fraud detection thresholds.
    FRAUD_TRADE_WINDOW: int = 60          # seconds
    FRAUD_MAX_TRADES: int = 20            # trades per window before flagging
    FRAUD_REQUEST_WINDOW: int = 60
    FRAUD_MAX_REQUESTS: int = 600         # API calls per window before flagging

    # ---- Analytics dashboard (Phase 7) ----
    ANALYTICS_CACHE_TTL: int = 8          # seconds to cache live aggregations
    ANALYTICS_INDICATOR_TTL: int = 60     # seconds to cache computed indicators
    ANALYTICS_INDEX_BASE: float = 2000.0  # synthetic NEPSE index base level
    ANALYTICS_MIN_HISTORY: int = 35       # min OHLCV rows to compute indicators

    # ---- Email delivery (SMTP) ----
    EMAIL_ENABLED: bool = False            # when False, emails are logged, not sent
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 587
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_USE_TLS: bool = True
    EMAIL_FROM: str = "alerts@nepse-ai.local"
    EMAIL_FROM_NAME: str = "NEPSE AI Alerts"
    EMAIL_MAX_RETRIES: int = 3
    EMAIL_RETRY_DELAY: int = 10            # seconds between delivery retries

    # ---- Push notifications / mobile (Phase 10) ----
    FCM_ENABLED: bool = False              # when False, pushes are logged, not sent
    FCM_SERVER_KEY: str = ""              # legacy FCM HTTP API server key
    FCM_API_URL: str = "https://fcm.googleapis.com/fcm/send"
    MOBILE_SNAPSHOT_TTL: int = 5          # seconds to cache the mobile home payload

    # ---- SMS delivery (optional, Twilio-ready) ----
    SMS_ENABLED: bool = False
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    TWILIO_FROM_NUMBER: str = ""

    # ---- Derived connection strings ----
    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_ASYNC(self) -> str:
        return (
            f"postgresql+asyncpg://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def DATABASE_URL_SYNC(self) -> str:
        """Sync driver — used by Celery workers (Celery is not async-native)."""
        return (
            f"postgresql+psycopg2://{self.POSTGRES_USER}:{self.POSTGRES_PASSWORD}"
            f"@{self.POSTGRES_HOST}:{self.POSTGRES_PORT}/{self.POSTGRES_DB}"
        )

    @computed_field  # type: ignore[prop-decorator]
    @property
    def REDIS_URL(self) -> str:
        auth = f":{self.REDIS_PASSWORD}@" if self.REDIS_PASSWORD else ""
        return f"redis://{auth}{self.REDIS_HOST}:{self.REDIS_PORT}/{self.REDIS_DB}"


@lru_cache
def get_settings() -> Settings:
    """Cached accessor so the .env file is parsed only once per process."""
    return Settings()


settings = get_settings()
