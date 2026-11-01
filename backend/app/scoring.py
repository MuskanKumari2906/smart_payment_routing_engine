from dataclasses import dataclass

NEUTRAL_SUCCESS_RATE = 0.9  # assumed when a gateway has no history yet


@dataclass
class GatewayMetrics:
    gateway_id: int
    fee_pct: float
    avg_latency_ms: float
    success_rate: float


def normalize(values: list[float], invert: bool = False) -> list[float]:
    """Min-max scale to 0..1; if invert, the lowest value gets 1.0. Equal values all get 1.0."""
    low, high = min(values), max(values)
    if high == low:
        return [1.0] * len(values)
    scaled = [(v - low) / (high - low) for v in values]
    return [1.0 - s for s in scaled] if invert else scaled


def score_gateways(
    metrics: list[GatewayMetrics], w_cost: float, w_latency: float, w_reliability: float
) -> dict[int, float]:
    """Return a weighted score per gateway id; higher is better."""
    cost = normalize([m.fee_pct for m in metrics], invert=True)
    latency = normalize([m.avg_latency_ms for m in metrics], invert=True)
    reliability = normalize([m.success_rate for m in metrics])
    return {
        m.gateway_id: w_cost * c + w_latency * l + w_reliability * r
        for m, c, l, r in zip(metrics, cost, latency, reliability)
    }
