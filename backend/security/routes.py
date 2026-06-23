"""Security admin API: audit logs, fraud flags, and RBAC introspection.

Audit/fraud routes are admin-only via the RBAC permission matrix. ``/me/permissions``
lets any authenticated user see their own effective permissions and rate tier.
"""
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.ext.asyncio import AsyncSession

from auth.dependencies import get_current_user
from core.database import get_db
from security import audit, fraud
from security.models import AccountFlag
from security.rbac import (
    P_ADMIN_AUDIT,
    P_ADMIN_FRAUD,
    ROLE_PERMISSIONS,
    rate_limit_for_role,
    require_permission,
)
from security.schemas import AccountFlagOut, AuditLogOut, PermissionsOut
from users.models import User

router = APIRouter(prefix="/security", tags=["security"])


@router.get("/me/permissions", response_model=PermissionsOut)
async def my_permissions(user: User = Depends(get_current_user)):
    perms = ROLE_PERMISSIONS.get(user.role, set())
    return {
        "role": user.role.value,
        "permissions": sorted(perms),
        "rate_limit_per_minute": rate_limit_for_role(user.role.value),
    }


@router.get("/audit", response_model=list[AuditLogOut])
async def audit_logs(
    user_id: int | None = Query(None),
    action: str | None = Query(None),
    limit: int = Query(100, ge=1, le=1000),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(P_ADMIN_AUDIT)),
):
    return await audit.list_audit(db, user_id=user_id, action=action, limit=limit)


@router.get("/fraud/flags", response_model=list[AccountFlagOut])
async def fraud_flags(
    resolved: bool | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(P_ADMIN_FRAUD)),
):
    return await fraud.list_flags(db, resolved=resolved, limit=limit)


@router.post("/fraud/scan")
async def run_fraud_scan(
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(P_ADMIN_FRAUD)),
):
    flagged = await fraud.scan_recent(db)
    return {"flags_raised": flagged}


@router.patch("/fraud/flags/{flag_id}/resolve", response_model=AccountFlagOut)
async def resolve_flag(
    flag_id: int,
    db: AsyncSession = Depends(get_db),
    _: User = Depends(require_permission(P_ADMIN_FRAUD)),
):
    flag = await db.get(AccountFlag, flag_id)
    if flag is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Flag not found")
    flag.resolved = True
    await db.flush()
    return flag
