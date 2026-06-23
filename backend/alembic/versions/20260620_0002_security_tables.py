"""security: audit_logs + account_flags tables, analyst role

Phase 8. Adds the audit-log and fraud-flag tables and the new ``analyst`` value
to the ``user_role`` enum.

Revision ID: 0002_security_audit_fraud
Revises: 0001_add_users_phone
Create Date: 2026-06-20
"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002_security_audit_fraud"
down_revision: Union[str, None] = "0001_add_users_phone"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()

    # New RBAC role (Postgres enum). Safe on PG 12+; harmless elsewhere.
    if bind.dialect.name == "postgresql":
        op.execute("ALTER TYPE user_role ADD VALUE IF NOT EXISTS 'analyst'")

    op.create_table(
        "audit_logs",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="SET NULL"), nullable=True),
        sa.Column("action", sa.String(length=120), nullable=False),
        sa.Column("method", sa.String(length=10), nullable=True),
        sa.Column("path", sa.String(length=255), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("ip_address", sa.String(length=64), nullable=True),
        sa.Column("user_agent", sa.String(length=255), nullable=True),
        sa.Column("meta", sa.JSON(), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_audit_logs_user_id", "audit_logs", ["user_id"])
    op.create_index("ix_audit_logs_timestamp", "audit_logs", ["timestamp"])
    op.create_index("ix_audit_user_ts", "audit_logs", ["user_id", "timestamp"])
    op.create_index("ix_audit_action_ts", "audit_logs", ["action", "timestamp"])

    op.create_table(
        "account_flags",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(),
                  sa.ForeignKey("users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("reason", sa.String(length=60), nullable=False),
        sa.Column("severity", sa.String(length=20), nullable=False),
        sa.Column("details", sa.JSON(), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_account_flags_user_id", "account_flags", ["user_id"])
    op.create_index("ix_account_flags_created_at", "account_flags", ["created_at"])
    op.create_index("ix_account_flags_user", "account_flags", ["user_id", "resolved"])


def downgrade() -> None:
    op.drop_table("account_flags")
    op.drop_table("audit_logs")
    # Note: Postgres cannot drop an enum value; 'analyst' is left in place.
