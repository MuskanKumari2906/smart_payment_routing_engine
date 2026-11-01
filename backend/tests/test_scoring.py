from pytest import approx

from app.scoring import GatewayMetrics, normalize, score_gateways


def test_normalize_scales_to_zero_one():
    assert normalize([10, 20, 30]) == [0.0, 0.5, 1.0]


def test_normalize_invert_makes_lowest_best():
    assert normalize([10, 20, 30], invert=True) == [1.0, 0.5, 0.0]


def test_normalize_equal_values_all_get_one():
    assert normalize([5, 5, 5]) == [1.0, 1.0, 1.0]


def test_score_applies_weights():
    metrics = [
        GatewayMetrics(1, fee_pct=1.0, avg_latency_ms=900, success_rate=0.5),  # cheapest
        GatewayMetrics(2, fee_pct=3.0, avg_latency_ms=100, success_rate=1.0),  # fastest, most reliable
    ]
    scores = score_gateways(metrics, w_cost=0.3, w_latency=0.2, w_reliability=0.5)
    assert scores[1] == approx(0.3)
    assert scores[2] == approx(0.7)


def test_score_equal_metric_does_not_separate_gateways():
    metrics = [GatewayMetrics(1, 2.0, 100, 0.9), GatewayMetrics(2, 2.0, 100, 0.9)]
    assert score_gateways(metrics, 0.3, 0.2, 0.5) == {1: approx(1.0), 2: approx(1.0)}
