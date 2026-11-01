import asyncio
import random
import time

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.gateways import GatewayError, call_gateway
from app.models import Attempt, Gateway, Transaction
from app.scoring import NEUTRAL_SUCCESS_RATE, GatewayMetrics, score_gateways


async def load_metrics(session: AsyncSession, gateway: Gateway) -> GatewayMetrics:
    """Build metrics from the gateway's last N attempts, or neutral defaults with no history."""
    rows = (
        await session.execute(
            select(Attempt.success, Attempt.latency_ms)
            .where(Attempt.gateway_id == gateway.id)
            .order_by(Attempt.id.desc())
            .limit(settings.history_size)
        )
    ).all()
    if not rows:
        return GatewayMetrics(gateway.id, gateway.fee_pct, gateway.base_latency_ms, NEUTRAL_SUCCESS_RATE)
    success_rate = sum(r.success for r in rows) / len(rows)
    avg_latency = sum(r.latency_ms for r in rows) / len(rows)
    return GatewayMetrics(gateway.id, gateway.fee_pct, avg_latency, success_rate)


async def scored_gateways(session: AsyncSession) -> list[tuple[Gateway, GatewayMetrics, float]]:
    """Return (gateway, metrics, score) for every gateway, best score first."""
    gateways = (await session.scalars(select(Gateway).order_by(Gateway.id))).all()
    metrics = [await load_metrics(session, g) for g in gateways]
    scores = score_gateways(
        metrics, settings.weight_cost, settings.weight_latency, settings.weight_reliability
    )
    rows = [(g, m, scores[g.id]) for g, m in zip(gateways, metrics)]
    return sorted(rows, key=lambda row: row[2], reverse=True)


async def rank_gateways(session: AsyncSession) -> list[Gateway]:
    """Rank by score; with probability explore_rate swap the top two (epsilon-greedy)."""
    ranked = [g for g, _, _ in await scored_gateways(session)]
    if len(ranked) > 1 and random.random() < settings.explore_rate:
        ranked[0], ranked[1] = ranked[1], ranked[0]
    return ranked


async def find_transaction(session: AsyncSession, key: str) -> Transaction | None:
    return await session.scalar(
        select(Transaction)
        .where(Transaction.idempotency_key == key)
        .options(selectinload(Transaction.attempts).selectinload(Attempt.gateway))
    )


async def process_payment(session: AsyncSession, amount: float, key: str) -> Transaction:
    """Route a payment through ranked gateways with failover; idempotent per key."""
    if existing := await find_transaction(session, key):
        return existing

    txn = Transaction(idempotency_key=key, amount=amount, attempts=[])
    session.add(txn)
    try:
        await session.commit()
    except IntegrityError:  # another request with the same key won the race
        await session.rollback()
        return await find_transaction(session, key)

    for gateway in (await rank_gateways(session))[: settings.max_attempts]:
        start = time.perf_counter()
        try:
            await asyncio.wait_for(call_gateway(gateway, amount), settings.gateway_timeout_s)
            success = True
        except (GatewayError, asyncio.TimeoutError):
            # Caveat: a timeout does not prove the payment failed - the gateway may still
            # charge the customer. A real system must query the first gateway's status before
            # retrying and pass the idempotency key to every gateway so it cannot charge twice.
            success = False
        latency_ms = int((time.perf_counter() - start) * 1000)
        txn.attempts.append(Attempt(gateway=gateway, success=success, latency_ms=latency_ms))
        txn.attempts_count += 1
        if success:
            txn.status, txn.final_gateway_id = "succeeded", gateway.id
            break
    else:
        txn.status = "failed"

    await session.commit()
    return txn
