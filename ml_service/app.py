"""NEPSE AI — ML serving API (standalone FastAPI microservice).

Endpoints (all require a valid JWT access token or X-API-Key, and are rate
limited + Redis-cached):

    GET  /health
    GET  /models                 — registry info (versions + metrics)
    POST /models/reload          — hot-reload latest models after retrain
    POST /predict/price          — next-bar price + confidence
    POST /predict/trend          — up / sideways / down
    POST /predict/volatility     — low / medium / high
    POST /signal/stock           — fused BUY / SELL / HOLD signal
    POST /predict/batch          — price predictions for many symbols
"""
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import settings
from core.cache import cache_get, cache_set, close_redis, rate_limited
from models.service import ModelService
from schemas import (
    BatchRequest,
    PredictRequest,
    PricePrediction,
    RiskBatchRequest,
    RiskItem,
    TradingSignal,
    TrendPrediction,
    VolatilityPrediction,
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("ml_service")

_state: dict[str, ModelService] = {}


def get_service() -> ModelService:
    return _state["service"]


@asynccontextmanager
async def lifespan(app: FastAPI):
    _state["service"] = ModelService()
    info = _state["service"].registry.info()
    logger.info("ML models loaded: %s", info or "none (fallback mode)")
    yield
    await close_redis()


app = FastAPI(title=settings.APP_NAME, version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"]
)


@app.get("/health", tags=["health"])
async def health() -> dict:
    return {"status": "ok", "service": settings.APP_NAME}


@app.get("/models", tags=["models"])
async def models(_: dict = Depends(rate_limited)) -> dict:
    return get_service().registry.info()


@app.post("/models/reload", tags=["models"])
async def reload_models(_: dict = Depends(rate_limited)) -> dict:
    get_service().reload()
    return {"reloaded": True, "registry": get_service().registry.info()}


async def _cached(kind: str, symbol: str, key_close: float, compute):
    cache_key = f"pred:{kind}:{symbol.upper()}:{round(key_close, 2)}"
    hit = await cache_get(cache_key)
    if hit is not None:
        return hit
    result = compute()
    await cache_set(cache_key, result)
    return result


def _key_close(req: PredictRequest, svc: ModelService) -> float:
    if req.features is not None:
        return req.features.close
    from data import loader

    return float(loader.recent_bars(req.symbol, 30)["close"].iloc[-1])


@app.post("/predict/price", response_model=PricePrediction, tags=["predict"])
async def predict_price(req: PredictRequest, _: dict = Depends(rate_limited)):
    svc = get_service()
    return await _cached(
        "price", req.symbol, _key_close(req, svc),
        lambda: svc.predict_price(req.symbol, req.features, req.history),
    )


@app.post("/predict/trend", response_model=TrendPrediction, tags=["predict"])
async def predict_trend(req: PredictRequest, _: dict = Depends(rate_limited)):
    svc = get_service()
    return await _cached(
        "trend", req.symbol, _key_close(req, svc),
        lambda: svc.predict_trend(req.symbol, req.features, req.history),
    )


@app.post("/predict/volatility", response_model=VolatilityPrediction, tags=["predict"])
async def predict_volatility(req: PredictRequest, _: dict = Depends(rate_limited)):
    svc = get_service()
    return await _cached(
        "vol", req.symbol, _key_close(req, svc),
        lambda: svc.predict_volatility(req.symbol, req.features, req.history),
    )


@app.post("/signal/stock", response_model=TradingSignal, tags=["signal"])
async def signal_stock(req: PredictRequest, _: dict = Depends(rate_limited)):
    svc = get_service()
    return await _cached(
        "signal", req.symbol, _key_close(req, svc),
        lambda: svc.signal(req.symbol, req.features, req.history),
    )


@app.post("/predict/batch", response_model=list[PricePrediction], tags=["predict"])
async def predict_batch(req: BatchRequest, _: dict = Depends(rate_limited)):
    svc = get_service()
    return [
        svc.predict_price(item.symbol, item.features, item.history)
        for item in req.items
    ]


@app.post("/risk/batch", response_model=list[RiskItem], tags=["signal"])
async def risk_batch(req: RiskBatchRequest, _: dict = Depends(rate_limited)):
    """Combined volatility + signal per symbol — one call for portfolio risk."""
    svc = get_service()
    return [svc.risk(symbol, None, None) for symbol in req.symbols]
