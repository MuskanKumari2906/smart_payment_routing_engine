import pytest

from app import routing
from app.config import settings
from app.gateways import GatewayError


@pytest.fixture
def calls(monkeypatch):
    """Replace the gateway call with a fake that fails only on the very first call."""
    called = []

    async def fake_call(gateway, amount):
        called.append(gateway.name)
        if len(called) == 1:
            raise GatewayError("first gateway down")

    monkeypatch.setattr(routing, "call_gateway", fake_call)
    monkeypatch.setattr(settings, "explore_rate", 0.0)
    return called


async def test_failover_to_next_gateway(session, calls):
    txn = await routing.process_payment(session, 100.0, "key-1")

    assert txn.status == "succeeded"
    assert txn.attempts_count == 2
    assert [a.success for a in txn.attempts] == [False, True]
    assert calls[0] != calls[1]
    assert txn.final_gateway_id == txn.attempts[1].gateway_id


async def test_same_key_returns_same_transaction(session, calls):
    first = await routing.process_payment(session, 100.0, "key-2")
    second = await routing.process_payment(session, 999.0, "key-2")

    assert second.id == first.id
    assert second.amount == 100.0
    assert len(calls) == 2  # the second request made no gateway calls
