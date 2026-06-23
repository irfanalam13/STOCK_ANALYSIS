"""Pydantic schemas for the alerts API.

Validation here is the server-side guard required by the spec: thresholds must
be positive, EQUAL needs a tolerance, and conditions must be sane for the
chosen alert type.
"""
from datetime import datetime

from pydantic import BaseModel, ConfigDict, Field, model_validator

from alerts.models import (
    AlertCondition,
    AlertType,
    NotificationChannel,
    NotificationStatus,
)


class AlertCreate(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    alert_type: AlertType
    condition: AlertCondition
    threshold_value: float = Field(..., gt=0)
    tolerance: float = Field(default=0.0, ge=0)
    channel: NotificationChannel = NotificationChannel.EMAIL
    label: str | None = Field(default=None, max_length=120)
    cooldown_seconds: int = Field(default=300, ge=0, le=86_400)

    @model_validator(mode="after")
    def _check_semantics(self) -> "AlertCreate":
        if self.condition == AlertCondition.EQUAL and self.tolerance <= 0:
            raise ValueError("EQUAL alerts require a positive tolerance band")
        # A volume spike is only meaningful as an "above N× average" trigger.
        if self.alert_type == AlertType.VOLUME and self.condition != AlertCondition.ABOVE:
            raise ValueError("VOLUME alerts only support the ABOVE condition")
        return self


class AlertUpdate(BaseModel):
    threshold_value: float | None = Field(default=None, gt=0)
    tolerance: float | None = Field(default=None, ge=0)
    condition: AlertCondition | None = None
    channel: NotificationChannel | None = None
    label: str | None = Field(default=None, max_length=120)
    cooldown_seconds: int | None = Field(default=None, ge=0, le=86_400)
    is_active: bool | None = None


class AlertOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    stock_symbol: str
    alert_type: AlertType
    condition: AlertCondition
    threshold_value: float
    tolerance: float
    channel: NotificationChannel
    label: str | None
    cooldown_seconds: int
    is_active: bool
    trigger_count: int
    last_triggered_at: datetime | None
    created_at: datetime


class NotificationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    alert_id: int | None
    stock_symbol: str | None
    channel: NotificationChannel
    subject: str | None
    message: str
    status: NotificationStatus
    error: str | None
    attempts: int
    timestamp: datetime
