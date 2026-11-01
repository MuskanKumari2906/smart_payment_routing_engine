from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Gateway

GATEWAYS = [
    dict(name="FastPay", fee_pct=1.8, base_latency_ms=1500, failure_rate=0.05),
    dict(name="QuickPay", fee_pct=2.9, base_latency_ms=200, failure_rate=0.02),
    dict(name="BudgetPay", fee_pct=1.2, base_latency_ms=500, failure_rate=0.25),
]


async def seed_gateways(session: AsyncSession) -> None:
    """Insert the three simulated gateways if the table is empty."""
    if await session.scalar(select(Gateway.id).limit(1)) is None:
        session.add_all(Gateway(**g) for g in GATEWAYS)
        await session.commit()
