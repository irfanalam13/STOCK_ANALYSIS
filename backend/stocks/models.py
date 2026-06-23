"""Stock (security) ORM model."""
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from core.database import Base


class Stock(Base):
    __tablename__ = "stocks"

    id: Mapped[int] = mapped_column(primary_key=True)
    symbol: Mapped[str] = mapped_column(
        String(20), unique=True, index=True, nullable=False
    )
    company_name: Mapped[str] = mapped_column(String(255), nullable=False)
    sector: Mapped[str | None] = mapped_column(String(100), index=True)

    market_data = relationship(
        "MarketData", back_populates="stock", cascade="all, delete-orphan"
    )
