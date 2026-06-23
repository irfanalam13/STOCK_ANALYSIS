"""Pydantic request/response models for the ML API."""
from pydantic import BaseModel, Field


class OHLCV(BaseModel):
    open: float = Field(gt=0)
    high: float = Field(gt=0)
    low: float = Field(gt=0)
    close: float = Field(gt=0)
    volume: float = Field(ge=0)


class PredictRequest(BaseModel):
    """Shared request. `features` (current bar) and `history` are optional —
    when omitted the service loads recent history for the symbol itself."""
    symbol: str
    features: OHLCV | None = None
    history: list[OHLCV] | None = None


class BatchRequest(BaseModel):
    items: list[PredictRequest]


class RiskBatchRequest(BaseModel):
    symbols: list[str]


class RiskItem(BaseModel):
    symbol: str
    volatility: str
    volatility_score: float
    signal: str
    signal_strength: str
    confidence: float
    predicted_return: float
    fallback: bool = False


class PricePrediction(BaseModel):
    symbol: str
    predicted_price: float
    predicted_return: float
    confidence: float
    model_version: str | None = None
    fallback: bool = False


class TrendPrediction(BaseModel):
    symbol: str
    trend: str
    confidence: float
    probabilities: dict[str, float] = {}
    model_version: str | None = None
    fallback: bool = False


class VolatilityPrediction(BaseModel):
    symbol: str
    volatility: str
    confidence: float
    probabilities: dict[str, float] = {}
    model_version: str | None = None
    fallback: bool = False


class TradingSignal(BaseModel):
    symbol: str
    signal: str
    strength: str
    confidence: float
    reason: list[str]
    details: dict
