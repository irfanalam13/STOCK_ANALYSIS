"""Auth module re-exports the shared User model.

Authentication is stateless (JWT), so there is no separate auth table. This
module exists to keep the ``import auth.models`` registration path in
``core.database.init_models`` explicit and future-proof (e.g. for a token
blacklist table later).
"""
from users.models import User, UserRole  # noqa: F401
