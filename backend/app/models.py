from datetime import UTC, datetime

from sqlalchemy import DateTime, ForeignKey
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class Gateway(Base):
    __tablename__ = "gateways"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(unique=True)
    fee_pct: Mapped[float]
    base_latency_ms: Mapped[int]
    failure_rate: Mapped[float]
    degraded: Mapped[bool] = mapped_column(default=False)


class Transaction(Base):
    __tablename__ = "transactions"

    id: Mapped[int] = mapped_column(primary_key=True)
    idempotency_key: Mapped[str] = mapped_column(unique=True)
    amount: Mapped[float]
    status: Mapped[str] = mapped_column(default="pending")
    final_gateway_id: Mapped[int | None] = mapped_column(ForeignKey("gateways.id"))
    attempts_count: Mapped[int] = mapped_column(default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    attempts: Mapped[list["Attempt"]] = relationship(order_by="Attempt.id")


class Attempt(Base):
    __tablename__ = "attempts"

    id: Mapped[int] = mapped_column(primary_key=True)
    transaction_id: Mapped[int] = mapped_column(ForeignKey("transactions.id"))
    gateway_id: Mapped[int] = mapped_column(ForeignKey("gateways.id"))
    success: Mapped[bool]
    latency_ms: Mapped[int]
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=lambda: datetime.now(UTC))

    gateway: Mapped[Gateway] = relationship()
