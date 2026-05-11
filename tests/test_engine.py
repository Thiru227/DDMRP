"""Boundary tests for the DDMRP engine."""
from app.calculations.ddmrp_engine import (
    EngineInputs,
    compute,
    compute_alert_level,
    compute_diffs,
)


def test_all_zeros_does_not_raise_and_is_healthy():
    out = compute(EngineInputs())
    assert out.adu == 0
    assert out.red_zone == 0
    assert out.yellow_zone == 0
    assert out.green_zone == 0
    assert out.tog == 0
    assert out.net_flow == 0
    assert out.planning_priority == 0
    assert out.order_recommendation == 0
    assert out.alert_level == "healthy"


def test_division_by_zero_guards_when_adu_days_zero():
    out = compute(EngineInputs(sales_90d=100, adu_days=0))
    assert out.adu == 0


def test_adu_honours_per_row_adu_days():
    out = compute(EngineInputs(sales_90d=89, adu_days=89))
    assert out.adu == 1.0


def test_alert_level_thresholds():
    assert compute_alert_level(net_flow=5, red_zone=10, toy=15) == "red"
    assert compute_alert_level(net_flow=10, red_zone=10, toy=15) == "yellow"
    assert compute_alert_level(net_flow=12, red_zone=10, toy=15) == "yellow"
    assert compute_alert_level(net_flow=15, red_zone=10, toy=15) == "healthy"


def test_negative_net_flow_triggers_red():
    out = compute(
        EngineInputs(
            sales_90d=900, adu_days=90, on_hand_qty=0, on_order_qty=0,
            qualified_demand_qty=50, dlt=10, ltf=0.75, vf=0.25, doc=7, moq=10,
        )
    )
    assert out.net_flow < 0
    assert out.alert_level == "red"


def test_order_recommendation_zero_when_healthy():
    out = compute(
        EngineInputs(
            sales_90d=43, adu_days=90, on_hand_qty=45, on_order_qty=0,
            qualified_demand_qty=1.43, dlt=10, ltf=0.75, vf=0.25, doc=7, moq=120,
        )
    )
    assert out.alert_level == "healthy"
    assert out.order_recommendation == 0


def test_order_recommendation_fills_to_tog_when_yellow():
    out = compute(
        EngineInputs(
            sales_90d=151, adu_days=89, on_hand_qty=16, on_order_qty=20,
            qualified_demand_qty=5.09, dlt=10, ltf=0.75, vf=0.25, doc=7, moq=120,
        )
    )
    assert out.alert_level in ("red", "yellow")
    assert abs(out.order_recommendation - (out.tog - out.net_flow)) < 0.01


def test_compute_diffs_returns_none_when_source_missing():
    out = compute(EngineInputs(sales_90d=90, adu_days=90))
    deltas = compute_diffs(out, source={})
    assert deltas["engine_minus_source_adu"] is None
    assert deltas["flagged_diff"] is False


def test_compute_diffs_flags_above_tolerance():
    out = compute(EngineInputs(sales_90d=90, adu_days=90, dlt=10, ltf=0.5, vf=0.5, doc=7, moq=10))
    deltas = compute_diffs(
        out,
        source={"source_order_recommendation": out.order_recommendation - 5.0},
    )
    assert deltas["flagged_diff"] is True
