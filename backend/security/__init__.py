"""Security & scalability hardening (Phase 8).

Production-grade protections layered onto the platform:

* Redis-backed API rate limiting (per-IP + per-user, tier-based).
* Security-headers + strict CORS middleware.
* RBAC permission matrix (Admin / Analyst / Trader / Free) + ``require_permission``.
* Audit logging of critical actions and API access.
* Field-level AES encryption (Fernet) for sensitive data.
* API-key auth for external/service callers.
* WebSocket hardening (per-socket message rate limit + idle disconnect).
* Rule-based fraud detection (rapid trades / request spikes).

Hashing vs. encryption: passwords are *hashed* (bcrypt, irreversible);
sensitive-but-recoverable fields (API keys, etc.) are *encrypted* (reversible).
"""
