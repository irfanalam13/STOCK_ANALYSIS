"""Time-series OHLCV market data ORM model.

A composite index on ``(stock_id, timestamp)`` backs the dominant query
pattern — "latest / recent rows for one symbol, newest first".
"""
from datetime import datetime, timezone

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class MarketData(Base):
    __tablename__ = "market_data"
    __table_args__ = (
        Index("ix_market_data_stock_ts", "stock_id", "timestamp"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    stock_id: Mapped[int] = mapped_column(
        ForeignKey("stocks.id", ondelete="CASCADE"), nullable=False, index=True
    )
    open_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    high_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    low_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    close_price: Mapped[float] = mapped_column(Numeric(14, 2), nullable=False)
    volume: Mapped[int] = mapped_column(BigInteger, nullable=False, default=0)
    timestamp: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        nullable=False,
    )

    stock = relationship("Stock", back_populates="market_data")
