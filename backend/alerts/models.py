"""Alert & notification ORM models.

* ``UserAlert`` is one user-defined trigger condition against a symbol.
* ``NotificationLog`` is the immutable audit trail of every delivery attempt.

``stock_symbol`` is stored denormalized (uppercased) and indexed so the
evaluation engine can look up "all active alerts for these symbols" without a
join — the dominant hot-path query each market tick.
"""
import enum
from datetime import datetime, timezone

from sqlalchemy import (
    Boolean,
    DateTime,
    Enum,
    Float,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class AlertType(str, enum.Enum):
    PRICE = "price"      # absolute price threshold
    PERCENT = "percent"  # intraday % change threshold
    VOLUME = "volume"    # volume vs. average-volume multiplier


class AlertCondition(str, enum.Enum):
    ABOVE = "above"  # value >  threshold
    BELOW = "below"  # value <  threshold
    EQUAL = "equal"  # |value - threshold| <= tolerance (near match)


class NotificationChannel(str, enum.Enum):
    EMAIL = "email"
    SMS = "sms"
    PUSH = "push"


class NotificationStatus(str, enum.Enum):
    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


class UserAlert(Base):
    __tablename__ = "user_alerts"
    __table_args__ = (
        # Hot path: WHERE is_active AND stock_symbol IN (...). Composite index
        # keeps the per-tick evaluation lookup off a full table scan.
        Index("ix_user_alerts_active_symbol", "is_active", "stock_symbol"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    stock_symbol: Mapped[str] = mapped_column(String(20), index=True, nullable=False)
    alert_type: Mapped[AlertType] = mapped_column(
        Enum(AlertType, name="alert_type"), nullable=False
    )
    condition: Mapped[AlertCondition] = mapped_column(
        Enum(AlertCondition, name="alert_condition"), nullable=False
    )
    # Meaning depends on alert_type: NPR price / percent / volume-multiplier.
    threshold_value: Mapped[float] = mapped_column(Float, nullable=False)
    # Tolerance band for EQUAL/near matches (absolute units of the metric).
    tolerance: Mapped[float] = mapped_column(Float, default=0.0, nullable=False)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"),
        default=NotificationChannel.EMAIL,
        nullable=False,
    )
    label: Mapped[str | None] = mapped_column(String(120), nullable=True)
    cooldown_seconds: Mapped[int] = mapped_column(Integer, default=300, nullable=False)

    is_active: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    trigger_count: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    last_triggered_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), nullable=True
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    notifications = relationship(
        "NotificationLog", back_populates="alert", cascade="all, delete-orphan"
    )


class NotificationLog(Base):
    __tablename__ = "notification_logs"
    __table_args__ = (
        Index("ix_notification_logs_user_ts", "user_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True, nullable=False
    )
    alert_id: Mapped[int | None] = mapped_column(
        ForeignKey("user_alerts.id", ondelete="SET NULL"), nullable=True
    )
    stock_symbol: Mapped[str | None] = mapped_column(String(20), nullable=True)
    channel: Mapped[NotificationChannel] = mapped_column(
        Enum(NotificationChannel, name="notification_channel"), nullable=False
    )
    subject: Mapped[str | None] = mapped_column(String(255), nullable=True)
    message: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(NotificationStatus, name="notification_status"),
        default=NotificationStatus.PENDING,
        nullable=False,
    )
    error: Mapped[str | None] = mapped_column(Text, nullable=True)
    attempts: Mapped[int] = mapped_column(Integer, default=0, nullable=False)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
        nullable=False,
    )

    alert = relationship("UserAlert", back_populates="notifications")
