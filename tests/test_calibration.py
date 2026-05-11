"""Calibration test — engine output must match the seed Excel within tolerance.

Failures here mean the Python engine has drifted from the spreadsheet that the
domain experts trust. This test gates the demo: a green run is the public
claim that "engine matches Excel."
"""
from __future__ import annotations

from pathlib import Path

import pytest

from app.calculations.ddmrp_engine import EngineInputs, compute, compute_diffs
from app.uploads.legacy_parser import iter_engine_inputs, parse_legacy

SEED_PATH = Path(__file__).resolve().parent.parent / "static" / "uploads" / "sample" / "seed.csv"

# Tolerances per field. Decimals: 0.05; integer-ish quantities: 0.5; the source
# rounds aggressively (e.g. ADU shown as 0.48 when actual is 0.4778).
FIELD_TOLERANCES = {
    "engine_minus_source_adu":                  0.05,
    "engine_minus_source_red":                  0.6,   # source rounds RED to 1 d.p.
    "engine_minus_source_yellow":               1.0,   # YELLOW shown as int in seed
    "engine_minus_source_green":                1.0,
    "engine_minus_source_tog":                  1.5,
    "engine_minus_source_net_flow":             1.5,
    "engine_minus_source_order_recommendation": 1.5,
}


def _load_seed_rows():
    parsed = parse_legacy(SEED_PATH)
    assert parsed["header_row_index"] >= 0, "Seed CSV must have an S.NO header row"
    assert not parsed["missing_fields"], (
        f"Seed CSV missing canonical fields: {parsed['missing_fields']}"
    )
    return parsed


def test_seed_file_parses_with_operational_rows():
    parsed = _load_seed_rows()
    assert len(parsed["data"]) > 0, "Seed CSV produced zero data rows"
    for row in parsed["data"]:
        assert row["msku_code"], "Empty msku_code should have been filtered"
        assert row["branch_code"] != "TOT", "TOT rows should be dropped"


@pytest.mark.parametrize("field,tol", list(FIELD_TOLERANCES.items()))
def test_engine_matches_excel_within_tolerance(field, tol):
    parsed = _load_seed_rows()
    breaches: list[str] = []
    for msku, branch, kwargs, source in iter_engine_inputs(parsed):
        out = compute(EngineInputs(**kwargs))
        deltas = compute_diffs(out, source)
        delta = deltas.get(field)
        if delta is None:
            continue
        if abs(delta) > tol:
            breaches.append(
                f"  {msku[:30]}@{branch}: {field}={delta:+.3f} (>|{tol}|) "
                f"engine={_engine_value_for(field, out):.3f} source={_source_value_for(field, source)}"
            )
    assert not breaches, (
        f"Engine vs source diffs out of tolerance for {field} (tol={tol}):\n"
        + "\n".join(breaches[:20])
        + (f"\n  ... and {len(breaches) - 20} more" if len(breaches) > 20 else "")
    )


def _engine_value_for(diff_field: str, out) -> float:
    mapping = {
        "engine_minus_source_adu": out.adu,
        "engine_minus_source_red": out.red_zone,
        "engine_minus_source_yellow": out.yellow_zone,
        "engine_minus_source_green": out.green_zone,
        "engine_minus_source_tog": out.tog,
        "engine_minus_source_net_flow": out.net_flow,
        "engine_minus_source_order_recommendation": out.order_recommendation,
    }
    return mapping[diff_field]


def _source_value_for(diff_field: str, source: dict):
    mapping = {
        "engine_minus_source_adu": "source_adu",
        "engine_minus_source_red": "source_red",
        "engine_minus_source_yellow": "source_yellow",
        "engine_minus_source_green": "source_green",
        "engine_minus_source_tog": "source_tog",
        "engine_minus_source_net_flow": "source_net_flow",
        "engine_minus_source_order_recommendation": "source_order_recommendation",
    }
    return source.get(mapping[diff_field])
