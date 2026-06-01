from datetime import date, datetime
from uuid import UUID

from pydantic import BaseModel, EmailStr, Field


class NominalOption(BaseModel):
    id: int
    variant: str
    nominal_rub: int
    price_rub: int
    available_count: int
    can_buy: bool


class CatalogResponse(BaseModel):
    spa_nominals: list[NominalOption]
    ar_nominals: list[NominalOption]


class CreateOrderRequest(BaseModel):
    denomination_id: int
    buyer_name: str = Field(min_length=2, max_length=200)
    buyer_email: EmailStr
    buyer_phone: str = Field(min_length=10, max_length=32)
    consent_pd: bool
    consent_privacy: bool


class CreateOrderResponse(BaseModel):
    order_id: UUID
    public_token: str
    redirect_url: str


class OrderStatusResponse(BaseModel):
    public_token: str
    status: str
    amount_rub: int
    nominal_rub: int
    variant: str
    buyer_email: str
    certificate_delivered: bool
    can_download_certificate: bool = False


class StockRow(BaseModel):
    denomination_id: int
    variant: str
    nominal_rub: int
    available: int
    reserved: int
    sold: int


class ImportResult(BaseModel):
    imported: int
    skipped: int
    errors: list[str]
