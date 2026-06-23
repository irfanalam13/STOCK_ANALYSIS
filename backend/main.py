"""FastAPI application entrypoint for the NEPSE trading backend.

Wires together auth, users, stocks, market data, and the WebSocket layer.
On startup it creates tables (dev), seeds the stock catalog, and launches the
Redis pub/sub subscriber that powers real-time broadcasts.

Run with:
    uvicorn main:app --reload
"""
import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from alerts.routes import router as alerts_router
from analytics.routes import router as analytics_router
from auth.routes import router as auth_router
from core.config import settings
from core.database import AsyncSessionLocal, init_models
from core.redis_client import close_redis
from market_data.routes import router as market_router
from mobile.routes import router as mobile_router
from monitoring.routes import router as monitoring_router
from portfolio.routes import router as portfolio_router
from security.audit import AuditMiddleware
from security.headers import SecurityHeadersMiddleware
from security.ratelimit import RateLimitMiddleware
from security.routes import router as security_router
from stocks.routes import router as stocks_router
from users.routes import router as users_router
from utils.helpers import seed_stocks
from websocket.broadcaster import broadcaster
from websocket.routes import router as ws_router

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # --- startup ---
    await init_models()
    async with AsyncSessionLocal() as db:
        created = await seed_stocks(db)
        if created:
            logger.info("Seeded %d stocks", created)
    await broadcaster.start()
    logger.info("%s started in %s mode", settings.APP_NAME, settings.ENVIRONMENT)
    yield
    # --- shutdown ---
    await broadcaster.stop()
    await close_redis()


app = FastAPI(
    title=settings.APP_NAME,
    version="1.0.0",
    debug=settings.DEBUG,
    lifespan=lifespan,
)

# Middleware stack (Phase 8). add_middleware registers outermost-last, so the
# resulting request order is: CORS -> SecurityHeaders -> RateLimit -> Audit ->
# routes. Audit is innermost so it records the real route status; SecurityHeaders
# wraps everything so even rate-limit 429s carry the hardened headers.
app.add_middleware(AuditMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_middleware(SecurityHeadersMiddleware)

_cors_origins = (
    ["*"] if settings.CORS_ORIGINS.strip() == "*"
    else [o.strip() for o in settings.CORS_ORIGINS.split(",") if o.strip()]
)
app.add_middleware(
    CORSMiddleware,
    allow_origins=_cors_origins,
    allow_credentials=settings.CORS_ORIGINS.strip() != "*",
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "app": settings.APP_NAME}


# REST routers (versioned)
api = settings.API_V1_PREFIX
app.include_router(auth_router, prefix=api)
app.include_router(users_router, prefix=api)
app.include_router(stocks_router, prefix=api)
app.include_router(market_router, prefix=api)
app.include_router(portfolio_router, prefix=api)
app.include_router(alerts_router, prefix=api)
app.include_router(analytics_router, prefix=api)
app.include_router(security_router, prefix=api)
app.include_router(mobile_router, prefix=api)

# Monitoring (unversioned, internal scrape target)
app.include_router(monitoring_router)

# WebSocket router (not under the REST version prefix by convention)
app.include_router(ws_router)
