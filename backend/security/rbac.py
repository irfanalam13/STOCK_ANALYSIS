"""Role-based access control: a permission matrix + dependency.

Roles (Phase 8): Admin, Analyst, Trader, Free (viewer). Each role maps to a set
of fine-grained permissions; ``require_permission`` is a FastAPI dependency
factory that enforces them. ADMIN implicitly holds every permission.

Also defines the rate-limit *tier* per role, used by the rate-limiter.
"""
from fastapi import Depends, HTTPException, status

from auth.dependencies import get_current_user
from core.config import settings
from users.models import User, UserRole

# ---- Permission catalog ---------------------------------------------------- #
P_MARKET_READ = "market:read"
P_ANALYTICS_READ = "analytics:read"
P_PORTFOLIO_READ = "portfolio:read"
P_PORTFOLIO_TRADE = "portfolio:trade"
P_ALERTS_WRITE = "alerts:write"
P_ADMIN_AUDIT = "admin:audit"
P_ADMIN_USERS = "admin:users"
P_ADMIN_FRAUD = "admin:fraud"

_ALL = "*"

# ---- Role -> permissions matrix ------------------------------------------- #
ROLE_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ADMIN: {_ALL},
    UserRole.ANALYST: {
        P_MARKET_READ, P_ANALYTICS_READ, P_PORTFOLIO_READ, P_ALERTS_WRITE,
    },
    UserRole.TRADER: {
        P_MARKET_READ, P_ANALYTICS_READ, P_PORTFOLIO_READ, P_PORTFOLIO_TRADE,
        P_ALERTS_WRITE,
    },
    UserRole.VIEWER: {
        P_MARKET_READ, P_ANALYTICS_READ, P_PORTFOLIO_READ,
    },
}


def has_permission(role: UserRole, permission: str) -> bool:
    perms = ROLE_PERMISSIONS.get(role, set())
    return _ALL in perms or permission in perms


def require_permission(permission: str):
    """Dependency factory: allow only users whose role grants ``permission``."""

    async def _checker(user: User = Depends(get_current_user)) -> User:
        if not has_permission(user.role, permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Missing permission: {permission}",
            )
        return user

    return _checker


# ---- Rate-limit tiers ------------------------------------------------------ #
def rate_limit_for_role(role: str | None) -> int:
    """Per-window request budget for a role (tier-based limits)."""
    if role == UserRole.ADMIN.value:
        return settings.RATE_LIMIT_ADMIN
    if role in (UserRole.ANALYST.value, UserRole.TRADER.value):
        return settings.RATE_LIMIT_PREMIUM
    if role == UserRole.VIEWER.value:
        return settings.RATE_LIMIT_FREE
    return settings.RATE_LIMIT_ANON  # unknown/anonymous
