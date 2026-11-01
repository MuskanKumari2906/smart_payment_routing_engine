import asyncio
import random
import uuid
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.db import SessionLocal, engine
from app.models import Attempt, Base, Gateway, Transaction
from app.routing import process_payment, scored_gateways
from app.seed import seed_gateways


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with SessionLocal() as session:
        await seed_gateways(session)
    yield


app = FastAPI(title="Smart Payment Routing Engine", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["http://localhost:5173"], allow_methods=["*"], allow_headers=["*"])


async def get_session():
    async with SessionLocal() as session:
        yield session


class PaymentRequest(BaseModel):
    amount: float = Field(gt=0)
    idempotency_key: str


def transaction_out(txn: Transaction) -> dict:
    return {
        "id": txn.id,
        "idempotency_key": txn.idempotency_key,
        "amount": txn.amount,
        "status": txn.status,
        "final_gateway_id": txn.final_gateway_id,
        "attempts_count": txn.attempts_count,
        "created_at": txn.created_at,
        "attempts": [
            {"gateway": a.gateway.name, "success": a.success, "latency_ms": a.latency_ms}
            for a in txn.attempts
        ],
    }


@app.post("/payments")
async def create_payment(req: PaymentRequest, session: AsyncSession = Depends(get_session)):
    return transaction_out(await process_payment(session, req.amount, req.idempotency_key))


@app.get("/gateways")
async def list_gateways(session: AsyncSession = Depends(get_session)):
    return [
        {
            "id": g.id,
            "name": g.name,
            "fee_pct": g.fee_pct,
            "base_latency_ms": g.base_latency_ms,
            "degraded": g.degraded,
            "score": round(score, 3),
            "success_rate": round(m.success_rate, 3),
            "avg_latency_ms": round(m.avg_latency_ms),
        }
        for g, m, score in await scored_gateways(session)
    ]


@app.post("/gateways/{gateway_id}/degrade")
async def toggle_degraded(gateway_id: int, session: AsyncSession = Depends(get_session)):
    gateway = await session.get(Gateway, gateway_id)
    if gateway is None:
        raise HTTPException(404, "Gateway not found")
    gateway.degraded = not gateway.degraded
    await session.commit()
    return {"id": gateway.id, "name": gateway.name, "degraded": gateway.degraded}


@app.get("/transactions")
async def list_transactions(session: AsyncSession = Depends(get_session)):
    txns = await session.scalars(
        select(Transaction)
        .order_by(Transaction.id.desc())
        .limit(50)
        .options(selectinload(Transaction.attempts).selectinload(Attempt.gateway))
    )
    return [transaction_out(t) for t in txns]


@app.get("/stats")
async def stats(session: AsyncSession = Depends(get_session)):
    total, succeeded, avg_attempts = (
        await session.execute(
            select(
                func.count(Transaction.id),
                func.count(Transaction.id).filter(Transaction.status == "succeeded"),
                func.avg(Transaction.attempts_count),
            )
        )
    ).one()
    per_gateway = (
        await session.execute(
            select(Gateway.name, func.count(Attempt.id))
            .outerjoin(Attempt, Attempt.gateway_id == Gateway.id)
            .group_by(Gateway.name)
        )
    ).all()
    total_attempts = sum(count for _, count in per_gateway)
    return {
        "total_transactions": total,
        "success_rate": round(succeeded / total, 3) if total else 0.0,
        "avg_attempts": round(float(avg_attempts or 0), 2),
        "traffic_share": {name: round(count / total_attempts, 3) if total_attempts else 0.0 for name, count in per_gateway},
    }


async def simulated_payment() -> str:
    async with SessionLocal() as session:
        txn = await process_payment(session, round(random.uniform(10, 1000), 2), str(uuid.uuid4()))
        return txn.status


@app.post("/simulate")
async def simulate(count: int = 100):
    """Fire `count` payments concurrently, each with its own DB session."""
    statuses = await asyncio.gather(*(simulated_payment() for _ in range(count)))
    return {"count": count, "succeeded": statuses.count("succeeded"), "failed": statuses.count("failed")}
