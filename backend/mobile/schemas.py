"""Pydantic schemas for the mobile API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field


class WatchlistSyncItem(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    updated_at: int = Field(..., ge=0)  # epoch milliseconds
    deleted: bool = False


class WatchlistSyncRequest(BaseModel):
    items: list[WatchlistSyncItem] = Field(default_factory=list)


class WatchlistItemOut(BaseModel):
    symbol: str
    updated_at: int
    deleted: bool


class WatchlistSyncResponse(BaseModel):
    items: list[WatchlistItemOut]   # full merged state incl. tombstones
    symbols: list[str]              # active (non-deleted) symbols


class DeviceTokenIn(BaseModel):
    token: str = Field(..., min_length=8, max_length=255)
    platform: str = Field(default="web", max_length=20)


class DeviceTokenOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    token: str  # masked for display
    platform: str
    created_at: datetime
    last_seen: datetime


class NotificationPreferenceSchema(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    push_enabled: bool = True
    email_enabled: bool = True
    sms_enabled: bool = False
    price_alerts: bool = True
    portfolio_alerts: bool = True
    news_alerts: bool = True


class MobileHome(BaseModel):
    overview: dict
    watchlist: list[dict]
    portfolio: dict
    preferences: NotificationPreferenceSchema
