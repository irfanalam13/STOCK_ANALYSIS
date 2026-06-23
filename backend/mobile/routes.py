"""Mobile API: watchlist + offline sync, device tokens, preferences, home."""
from fastapi import APIRouter, Body, Depends, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_access_token, get_current_user
from core.database import get_db
from mobile import service
from mobile.schemas import (
    DeviceTokenIn,
    DeviceTokenOut,
    MobileHome,
    NotificationPreferenceSchema,
    WatchlistItemOut,
    WatchlistSyncRequest,
    WatchlistSyncResponse,
)
from security.encryption import mask
from users.models import User

router = APIRouter(prefix="/mobile", tags=["mobile"])


# ---- Watchlist ----
@router.get("/watchlist", response_model=list[str])
async def get_watchlist(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.active_symbols(db, user.id)


@router.post("/watchlist", response_model=list[str], status_code=status.HTTP_201_CREATED)
async def add_watchlist(
    symbol: str = Body(..., embed=True),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.add_symbol(db, user.id, symbol)
    return await service.active_symbols(db, user.id)


@router.delete("/watchlist/{symbol}", status_code=status.HTTP_204_NO_CONTENT)
async def remove_watchlist(
    symbol: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.remove_symbol(db, user.id, symbol)


@router.post("/watchlist/sync", response_model=WatchlistSyncResponse)
async def sync_watchlist(
    payload: WatchlistSyncRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    merged = await service.sync_watchlist(db, user.id, payload.items)
    return {
        "items": [
            WatchlistItemOut(symbol=m.symbol, updated_at=m.updated_at, deleted=m.deleted)
            for m in merged
        ],
        "symbols": [m.symbol for m in merged if not m.deleted],
    }


# ---- Device tokens ----
def _device_out(d) -> DeviceTokenOut:
    return DeviceTokenOut(id=d.id, token=mask(d.token), platform=d.platform,
                          created_at=d.created_at, last_seen=d.last_seen)


@router.post("/devices", response_model=DeviceTokenOut, status_code=status.HTTP_201_CREATED)
async def register_device(
    payload: DeviceTokenIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    device = await service.register_device(db, user.id, payload.token, payload.platform)
    return _device_out(device)


@router.get("/devices", response_model=list[DeviceTokenOut])
async def list_devices(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return [_device_out(d) for d in await service.list_devices(db, user.id)]


@router.delete("/devices", status_code=status.HTTP_204_NO_CONTENT)
async def delete_device(
    token: str = Query(...),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    await service.delete_device(db, user.id, token)


# ---- Notification preferences ----
@router.get("/preferences", response_model=NotificationPreferenceSchema)
async def get_preferences(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.get_preferences(db, user.id)


@router.put("/preferences", response_model=NotificationPreferenceSchema)
async def update_preferences(
    payload: NotificationPreferenceSchema,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await service.update_preferences(db, user.id, payload.model_dump())


# ---- Aggregated home (one round-trip for mobile) ----
@router.get("/home", response_model=MobileHome)
async def mobile_home(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
    token: str = Depends(get_access_token),
):
    return await service.home(db, user.id, token)
