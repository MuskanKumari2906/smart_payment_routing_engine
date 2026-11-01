import asyncio
import random

from app.models import Gateway

DEGRADED_FAILURE_RATE = 0.9


class GatewayError(Exception):
    pass


async def call_gateway(gateway: Gateway, amount: float) -> None:
    """Simulate a payment call: sleep for a jittered latency, then maybe fail."""
    await asyncio.sleep(gateway.base_latency_ms * random.uniform(0.6, 1.4) / 1000)
    failure_rate = DEGRADED_FAILURE_RATE if gateway.degraded else gateway.failure_rate
    if random.random() < failure_rate:
        raise GatewayError(f"{gateway.name} declined {amount:.2f}")
