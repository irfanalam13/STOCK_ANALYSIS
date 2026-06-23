"""Stock schemas."""
from pydantic import BaseModel, ConfigDict


class StockBase(BaseModel):
    symbol: str
    company_name: str
    sector: str | None = None


class StockCreate(StockBase):
    pass


class StockOut(StockBase):
    model_config = ConfigDict(from_attributes=True)

    id: int
