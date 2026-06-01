import enum
import uuid
from datetime import date, datetime

from sqlalchemy import (
    Date,
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db import Base


class CodeStatus(str, enum.Enum):
    available = "available"
    reserved = "reserved"
    sold = "sold"


class OrderStatus(str, enum.Enum):
    pending_payment = "pending_payment"
    paid = "paid"
    paid_pending_delivery = "paid_pending_delivery"
    failed = "failed"
    cancelled = "cancelled"


class Denomination(Base):
    __tablename__ = "denominations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    variant: Mapped[str] = mapped_column(String(16), default="spa")  # spa | ar
    nominal_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    price_rub: Mapped[int] = mapped_column(Integer, nullable=False)
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    codes: Mapped[list["CertificateCode"]] = relationship(back_populates="denomination")

    __table_args__ = (UniqueConstraint("variant", "nominal_rub", name="uq_denom_variant_nominal"),)


class CertificateCode(Base):
    __tablename__ = "certificate_codes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    denomination_id: Mapped[int] = mapped_column(ForeignKey("denominations.id"), index=True)
    code: Mapped[str] = mapped_column(String(128), unique=True, nullable=False)
    pin: Mapped[str | None] = mapped_column(String(32), nullable=True)
    valid_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    batch_id: Mapped[str | None] = mapped_column(String(64), nullable=True)
    status: Mapped[CodeStatus] = mapped_column(Enum(CodeStatus), default=CodeStatus.available, index=True)
    reserved_until: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("orders.id"), nullable=True)
    sold_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    denomination: Mapped["Denomination"] = relationship(back_populates="codes")
    order: Mapped["Order | None"] = relationship(back_populates="certificate_code")


class Order(Base):
    __tablename__ = "orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    public_token: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    denomination_id: Mapped[int] = mapped_column(ForeignKey("denominations.id"))
    variant: Mapped[str] = mapped_column(String(16))
    nominal_rub: Mapped[int] = mapped_column(Integer)
    amount_rub: Mapped[int] = mapped_column(Integer)
    buyer_name: Mapped[str] = mapped_column(String(200))
    buyer_email: Mapped[str] = mapped_column(String(320), index=True)
    buyer_phone: Mapped[str] = mapped_column(String(32))
    consent_pd: Mapped[bool] = mapped_column(default=False)
    consent_privacy: Mapped[bool] = mapped_column(default=False)
    status: Mapped[OrderStatus] = mapped_column(Enum(OrderStatus), default=OrderStatus.pending_payment)
    payment_provider: Mapped[str] = mapped_column(String(32))
    payment_external_id: Mapped[str | None] = mapped_column(String(128), nullable=True, index=True)
    payment_idempotency_key: Mapped[str | None] = mapped_column(String(128), unique=True, nullable=True)
    redirect_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    email_sent_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now()
    )

    certificate_code: Mapped["CertificateCode | None"] = relationship(
        back_populates="order", uselist=False
    )


class AuditLog(Base):
    __tablename__ = "audit_log"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    action: Mapped[str] = mapped_column(String(64), index=True)
    actor: Mapped[str] = mapped_column(String(128), default="system")
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), nullable=True, index=True)
    details: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())
