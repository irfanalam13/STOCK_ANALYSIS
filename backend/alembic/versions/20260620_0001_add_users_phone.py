"""add users.phone column

Adds the nullable ``phone`` column to ``users`` for SMS notifications (Phase 6).

This is the first Alembic revision. The baseline schema is currently created by
``core.database.init_models`` (``create_all``); this migration brings an
existing database up to date with the new column. For a fresh, fully
Alembic-managed database, generate a baseline first
(``alembic revision --autogenerate``) and set it as this revision's parent.

Revision ID: 0001_add_users_phone
Revises:
Create Date: 2026-06-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001_add_users_phone"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("phone", sa.String(length=20), nullable=True))


def downgrade() -> None:
    op.drop_column("users", "phone")
