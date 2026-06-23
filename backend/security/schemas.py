"""Pydantic schemas for the security admin API."""
from datetime import datetime

from pydantic import BaseModel, ConfigDict


class AuditLogOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int | None
    action: str
    method: str | None
    path: str | None
    status_code: int | None
    ip_address: str | None
    user_agent: str | None
    meta: dict | None
    timestamp: datetime


class AccountFlagOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    user_id: int
    reason: str
    severity: str
    details: dict | None
    resolved: bool
    created_at: datetime


class PermissionsOut(BaseModel):
    role: str
    permissions: list[str]
    rate_limit_per_minute: int
