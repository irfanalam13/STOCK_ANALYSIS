"""Authentication for the ML service.

Accepts EITHER a JWT access token (signed with the shared backend SECRET_KEY,
so a logged-in user's token works directly) OR an ``X-API-Key`` header for
service-to-service calls.
"""
from fastapi import Depends, Header, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError, jwt

from config import settings

bearer = HTTPBearer(auto_error=False)


async def require_auth(
    creds: HTTPAuthorizationCredentials | None = Depends(bearer),
    x_api_key: str | None = Header(default=None),
) -> dict:
    if x_api_key and x_api_key in settings.api_keys:
        return {"sub": f"apikey:{x_api_key[:6]}", "via": "api_key"}

    if creds is not None:
        try:
            payload = jwt.decode(
                creds.credentials,
                settings.SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM],
            )
            if payload.get("type", "access") != "access":
                raise JWTError("not an access token")
            payload["via"] = "jwt"
            return payload
        except JWTError:
            pass

    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Missing or invalid credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
