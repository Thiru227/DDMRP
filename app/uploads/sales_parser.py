"""Sales & stock CSV parser — simpler format than the MSKU working file.

The sales&stocks.csv has branch-level 90-day sales and branch stock per MSKU,
but no planning parameters. Missing parameters are filled from msku_master.
"""
from __future__ import annotations

import csv
import re
from io import StringIO
from typing import Any

from app.uploads.legacy_parser import _extract_display_name, _derive_short_code


_SALES_COLUMN_MAP: dict[str, list[str]] = {
    "msku_code":  ["MASTER SKU", "SKU", "MSK"],
    "branch_code": ["BRANCH"],
    "sales_90d":  ["90 DAY SAL", "90 DAYS SALES", "90 DAY SALES"],
    "on_hand_qty": ["BRANCH STOCK", "SHOP STK", "ON HAND"],
    "on_order_qty": ["IN TRANSIST", "IN TRANSIT", "ON ORDER"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ").strip()).upper()


def _to_float(v: Any) -> float:
    if v is None:
        return 0.0
    s = str(v).strip().replace(",", "").replace("%", "")
    try:
        return max(0.0, float(s))
    except ValueError:
        return 0.0


def _find_header(rows: list[list[str]]) -> int | None:
    for idx, row in enumerate(rows):
        normed = [_norm(c) for c in row]
        if "BRANCH" in normed and any(
            n in normed for n in ("90 DAY SAL", "90 DAYS SALES", "90 DAY SALES")
        ):
            return idx
    return None


def _build_index(header: list[str]) -> dict[str, int]:
    norm_header = [_norm(h) for h in header]
    indexed: dict[str, int] = {}
    for canonical, spellings in _SALES_COLUMN_MAP.items():
        norm_spellings = [_norm(s) for s in spellings]
        for idx, nh in enumerate(norm_header):
            if nh in norm_spellings and canonical not in indexed:
                indexed[canonical] = idx
    return indexed


def parse_sales(file_or_path) -> dict[str, Any]:
    """Parse a sales&stocks CSV.

    Returns same shape as parse_legacy:
        {data: [...], warnings: [...], missing_fields: [...]}
    """
    if hasattr(file_or_path, "read"):
        raw = file_or_path.read()
        text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else raw
    else:
        text = str(file_or_path)

    rows = list(csv.reader(StringIO(text)))
    header_idx = _find_header(rows)
    if header_idx is None:
        return {"data": [], "warnings": [],
                "missing_fields": ["BRANCH and 90-day sales columns not found"]}

    header = rows[header_idx]
    index = _build_index(header)

    required = ["msku_code", "branch_code", "sales_90d", "on_hand_qty"]
    missing = [r for r in required if r not in index]

    # Try to find MSKU code from an earlier column if not on the same header row
    msku_col_idx = index.get("msku_code")

    data: list[dict] = []
    warnings: list[str] = []
    last_msku = None

    for raw in rows[header_idx + 1:]:
        if all((cell or "").strip() == "" for cell in raw):
            continue

        msku_val = (raw[msku_col_idx].strip() if msku_col_idx is not None and msku_col_idx < len(raw) else "")
        if msku_val:
            last_msku = msku_val

        branch = (raw[index["branch_code"]].strip().upper()
                  if "branch_code" in index and index["branch_code"] < len(raw) else "")
        if not branch or branch == "TOT":
            continue

        msku = msku_val or last_msku
        if not msku:
            continue

        row: dict[str, Any] = {
            "msku_code":   msku,
            "branch_code": branch,
            "sales_90d":   _to_float(raw[index["sales_90d"]]  if "sales_90d"   in index and index["sales_90d"]   < len(raw) else 0),
            "on_hand_qty": _to_float(raw[index["on_hand_qty"]] if "on_hand_qty" in index and index["on_hand_qty"] < len(raw) else 0),
            "on_order_qty":_to_float(raw[index["on_order_qty"]] if "on_order_qty" in index and index["on_order_qty"] < len(raw) else 0),
            "display_name": _extract_display_name(msku),
            "short_code":   _derive_short_code(msku),
        }
        data.append(row)

    return {"data": data, "warnings": warnings, "missing_fields": missing}
