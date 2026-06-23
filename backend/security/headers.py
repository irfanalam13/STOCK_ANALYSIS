"""Security-headers middleware.

Adds defensive HTTP response headers (clickjacking, MIME-sniffing, referrer
leakage, etc.). HSTS is opt-in via ``HSTS_ENABLED`` because it must only be sent
when the API is genuinely served over HTTPS.
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from core.config import settings

_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
    "X-XSS-Protection": "0",  # modern browsers: rely on CSP, disable legacy auditor
    "Permissions-Policy": "geolocation=(), microphone=(), camera=()",
    "Cross-Origin-Opener-Policy": "same-origin",
}


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        if settings.SECURITY_HEADERS_ENABLED:
            for header, value in _HEADERS.items():
                response.headers.setdefault(header, value)
            if settings.HSTS_ENABLED:
                response.headers.setdefault(
                    "Strict-Transport-Security",
                    "max-age=31536000; includeSubDomains",
                )
        return response
