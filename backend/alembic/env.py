"""Alembic environment.

The migration target metadata is the project's shared declarative ``Base``, with
every model imported so ``--autogenerate`` sees the full schema. The connection
URL comes from ``core.config.settings`` (the synchronous psycopg2 URL — Alembic
runs sync), keeping config in one place and out of version control.
"""
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

from core.config import settings
from core.database import Base

# Import models so they register on Base.metadata before autogenerate runs.
import alerts.models  # noqa: F401
import auth.models  # noqa: F401
import market_data.models  # noqa: F401
import portfolio.models  # noqa: F401
import stocks.models  # noqa: F401
import users.models  # noqa: F401

config = context.config
# Inject the runtime DB URL (kept out of alembic.ini on purpose). An explicit
# ``-x db_url=...`` wins, so a different env can be targeted without editing
# config (e.g. `alembic -x db_url=sqlite:///./x.db upgrade head`).
_db_url = context.get_x_argument(as_dictionary=True).get("db_url")
config.set_main_option("sqlalchemy.url", _db_url or settings.DATABASE_URL_SYNC)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Emit SQL to stdout without a DBAPI connection (`alembic upgrade --sql`)."""
    context.configure(
        url=config.get_main_option("sqlalchemy.url"),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations against a live connection."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
