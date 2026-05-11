"""
DDMRP planning engine — pure functions, no I/O.

This is the system of record for planning math. All formulas are derived from
the source Excel workbook and validated against it by the calibration test.
"""
from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any, Mapping


@dataclass(frozen=True)
class EngineInputs:
    sales_90d: float = 0.0
    adu_days: float = 0.0
    on_hand_qty: float = 0.0
    on_order_qty: float = 0.0
    qualified_demand_qty: float = 0.0
    moq: float = 0.0
    lead_time: float = 0.0
    dlt: float = 0.0
    ltf: float = 0.0
    vf: float = 0.0
    doc: float = 0.0


@dataclass(frozen=True)
class EngineOutputs:
    adu: float
    red_base: float
    red_safety: float
    red_zone: float
    yellow_zone: float
    green_zone: float
    tor: float
    toy: float
    tog: float
    net_flow: float
    planning_priority: float
    order_recommendation: float
    alert_level: str

    def as_dict(self) -> dict[str, Any]:
        return asdict(self)


def compute_alert_level(net_flow: float, red_zone: float, toy: float) -> str:
    if net_flow < red_zone:
        return "red"
    if net_flow < toy:
        return "yellow"
    return "healthy"


def compute(inputs: EngineInputs) -> EngineOutputs:
    sales = float(inputs.sales_90d or 0.0)
    days = float(inputs.adu_days or 0.0)
    adu = sales / days if days > 0 else 0.0

    dlt = float(inputs.dlt or 0.0)
    ltf = float(inputs.ltf or 0.0)
    vf = float(inputs.vf or 0.0)
    doc = float(inputs.doc or 0.0)
    moq = float(inputs.moq or 0.0)

    red_base = adu * dlt * ltf
    red_safety = red_base * vf
    red_zone = red_base + red_safety
    yellow_zone = adu * dlt
    green_zone = max(red_base, adu * doc, moq)

    tor = red_zone
    toy = red_zone + yellow_zone
    tog = red_zone + yellow_zone + green_zone

    on_hand = float(inputs.on_hand_qty or 0.0)
    on_order = float(inputs.on_order_qty or 0.0)
    qd = float(inputs.qualified_demand_qty or 0.0)
    net_flow = (on_hand + on_order) - qd

    planning_priority = (net_flow / tog) if tog > 0 else 0.0

    if net_flow <= toy and tog > net_flow:
        order_recommendation = max(0.0, tog - net_flow)
    else:
        order_recommendation = 0.0

    alert_level = compute_alert_level(net_flow, red_zone, toy)

    return EngineOutputs(
        adu=adu,
        red_base=red_base,
        red_safety=red_safety,
        red_zone=red_zone,
        yellow_zone=yellow_zone,
        green_zone=green_zone,
        tor=tor,
        toy=toy,
        tog=tog,
        net_flow=net_flow,
        planning_priority=planning_priority,
        order_recommendation=order_recommendation,
        alert_level=alert_level,
    )


_DIFF_FIELD_TOLERANCES = {
    "adu": 0.05,
    "red": 0.05,
    "yellow": 0.05,
    "green": 0.5,
    "tog": 0.5,
    "net_flow": 0.5,
    "order_recommendation": 0.5,
}


def compute_diffs(
    outputs: EngineOutputs,
    source: Mapping[str, float | None],
) -> dict[str, Any]:
    """Return engine_minus_source_* deltas plus a flagged_diff bool.

    `source` is a mapping that may contain any of the keys:
        source_adu, source_red, source_yellow, source_green,
        source_tog, source_net_flow, source_order_recommendation
    """
    pairs = {
        "adu": ("source_adu", outputs.adu),
        "red": ("source_red", outputs.red_zone),
        "yellow": ("source_yellow", outputs.yellow_zone),
        "green": ("source_green", outputs.green_zone),
        "tog": ("source_tog", outputs.tog),
        "net_flow": ("source_net_flow", outputs.net_flow),
        "order_recommendation": ("source_order_recommendation", outputs.order_recommendation),
    }

    deltas: dict[str, Any] = {}
    flagged = False
    for key, (source_key, engine_value) in pairs.items():
        src = source.get(source_key)
        if src is None:
            deltas[f"engine_minus_source_{key}"] = None
            continue
        delta = float(engine_value) - float(src)
        deltas[f"engine_minus_source_{key}"] = delta
        if abs(delta) > _DIFF_FIELD_TOLERANCES[key]:
            flagged = True

    deltas["flagged_diff"] = flagged
    return deltas
