"""Legacy Excel-export parser. Skips the multi-row preamble, fuzzy-matches columns."""
from __future__ import annotations

import csv
import re
from io import StringIO
from pathlib import Path
from typing import Any, Iterator


# Map of canonical fields → list of acceptable source-label spellings (uppercased,
# whitespace-collapsed, internal whitespace replaced with single space).
COLUMN_MAP: dict[str, list[str]] = {
    "msku_code":             ["MASTER SKU"],
    "branch_code":           ["BRANCH"],
    "sales_90d":             ["90 DAY SAL", "90 DAYS SALES", "90 DAY SALES"],
    "adu_days":              ["ADU DAYS"],
    "on_hand_qty":           ["ON HAND"],
    "on_order_qty":          ["ON ORDER"],
    "qualified_demand_qty":  ["QUALIFIED DEMAND"],
    # master parameters
    "moq":                   ["MOQ"],
    "lead_time":             ["LEAD TIME"],
    "ltf":                   ["LTF"],
    "vf":                    ["VF"],
    "doc":                   ["DOC"],
    "dlt":                   ["DLT"],
    # source-calculated (preserved for diffing)
    "source_adu":            ["ADU"],
    "source_red":            ["RED"],
    "source_yellow":         ["YELLOW"],
    "source_green":          ["GREEN"],
    "source_tog":            ["TOG"],
    "source_net_flow":       ["NET FLOW"],
    "source_order_recommendation": ["ORDER RECOM", "ORDER RECOMMENDATION"],
}

# Descriptive master fields we also pull when present
DESCRIPTIVE_FIELDS = {
    "product_classification": ["PRODUCT CLASSIFICATION"],
    "price_range":            ["PRICE RANGE"],
    "size":                   ["SIZE"],
    "mrp":                    ["MRP"],
    "season":                 ["SEASON"],
}


def _norm(s: str) -> str:
    return re.sub(r"\s+", " ", (s or "").replace("\n", " ").strip()).upper()


# ── MSKU display-name extraction ─────────────────────────────────────────────

_GARMENT_TERMS = re.compile(
    r"(INNER|OUTER|VEST|BRIEFS|TRUNK|BOXER|SHORT|BRIEF|BOTTOM|TOP|RIB|PANTS|SHORTS)"
)


def _extract_display_name(msku_code: str) -> str:
    """Pull the human-readable product name from a raw concatenated MSKU code.

    The code packs classification attributes as one long string:
      MENSINNER WEARECONOMICACTIVE WEAR INNER WEAR TOPSOLIDGYM VESTCLASSICPOOMEX
    The product name sits between the token SOLID and the next CLASSIC or POOMEX.
    Returns title-cased name, with 'PRM' appended when PREMIUM is present.
    Falls back to the raw code if pattern not matched.
    """
    upper = re.sub(r"\s+", " ", msku_code.strip()).upper()
    m = re.search(r"SOLID(.+?)(?:CLASSIC|POOMEX)", upper)
    if not m:
        return msku_code
    raw = m.group(1).strip()
    # Insert spaces before known garment terms when they're run together
    spaced = _GARMENT_TERMS.sub(r" \1", raw).strip()
    spaced = re.sub(r"\s+", " ", spaced)
    _ABBREVS = {"RN", "RNS", "LT", "OTB"}
    words = [w if w in _ABBREVS else w.title() for w in spaced.split()]
    name = " ".join(words)
    if "PREMIUM" in upper:
        name = name + " PRM"
    return name


def _derive_short_code(msku_code: str) -> str:
    """Build a short hyphenated code like GYM-VEST-ECO from the raw msku_code."""
    display = _extract_display_name(msku_code)
    # If extraction failed (no SOLID token) use initials of raw words
    if display == msku_code:
        words = re.sub(r"\s+", " ", msku_code.strip()).split()
        return "-".join(w[:3].upper() for w in words[:4])
    upper = msku_code.upper()
    suffix = "PRM" if "PREMIUM" in upper else "ECO"
    # Use words of the display name (strip PRM — we re-add the suffix)
    base_words = display.replace(" PRM", "").split()
    code = "-".join(w.upper() for w in base_words) + "-" + suffix
    return code


def _build_index(header: list[str]) -> dict[str, int]:
    """Walk the header row and return a map of canonical_field → column index.

    For DOC, the source file has *two* columns named "DOC" (a parameter and an
    inferred value mid-formula chain). We always take the *last* DOC seen before
    the YELLOW column, because that one matches the planning parameter.
    """
    norm_header = [_norm(h) for h in header]
    indexed: dict[str, int] = {}

    # First pass: pick canonical fields by direct match
    all_maps = {**COLUMN_MAP, **DESCRIPTIVE_FIELDS}
    for canonical, spellings in all_maps.items():
        norm_spellings = [_norm(s) for s in spellings]
        for idx, norm_h in enumerate(norm_header):
            if norm_h in norm_spellings:
                if canonical == "doc":
                    indexed[canonical] = idx  # last wins
                elif canonical not in indexed:
                    indexed[canonical] = idx
    return indexed


def _to_float(v: Any, default: float | None = 0.0) -> float | None:
    if v is None:
        return default
    if isinstance(v, (int, float)):
        return float(v)
    s = str(v).strip()
    if not s or s == "-":
        return default
    s = s.replace(",", "").replace("%", "").strip()
    try:
        return float(s)
    except ValueError:
        return default


def _read_rows(content: str) -> list[list[str]]:
    return list(csv.reader(StringIO(content)))


def parse_legacy(file_or_path) -> dict[str, Any]:
    """Parse a legacy Excel-export CSV.

    Accepts a file path, a file-like object, or raw text. Returns:
        {
            "header_row_index": int,
            "data": [ {canonical_field: value, ...}, ... ],
            "warnings": [str, ...],
            "missing_fields": [str, ...],     # required canonical fields not in header
        }

    Rows where BRANCH == "TOT" or MSKU is empty are dropped silently.
    """
    text = _load_text(file_or_path)
    rows = _read_rows(text)

    header_idx = _find_header_row(rows)
    if header_idx is None:
        return {
            "header_row_index": -1,
            "data": [],
            "warnings": [],
            "missing_fields": ["S.NO header row not found"],
        }

    header = rows[header_idx]
    index = _build_index(header)

    required = ["msku_code", "branch_code", "on_hand_qty", "on_order_qty",
                "sales_90d", "adu_days"]
    missing = [r for r in required if r not in index]

    data: list[dict[str, Any]] = []
    warnings: list[str] = []
    for raw in rows[header_idx + 1:]:
        if all((cell or "").strip() == "" for cell in raw):
            continue

        row = _project_row(raw, index)
        msku = (row.get("msku_code") or "").strip()
        branch = (row.get("branch_code") or "").strip().upper()

        if not msku:
            continue
        if branch == "TOT":
            continue

        row["msku_code"] = msku
        row["branch_code"] = branch
        data.append(row)

    return {
        "header_row_index": header_idx,
        "data": data,
        "warnings": warnings,
        "missing_fields": missing,
    }


def _find_header_row(rows: list[list[str]]) -> int | None:
    for idx, r in enumerate(rows):
        if r and _norm(r[0]) == "S.NO":
            return idx
    return None


def _project_row(raw: list[str], index: dict[str, int]) -> dict[str, Any]:
    out: dict[str, Any] = {}
    for canonical, col_idx in index.items():
        value = raw[col_idx] if col_idx < len(raw) else ""
        if canonical in ("msku_code", "branch_code") | DESCRIPTIVE_FIELDS.keys():
            out[canonical] = (value or "").strip()
        else:
            out[canonical] = _to_float(value, default=None)
    return out


def _load_text(file_or_path) -> str:
    if isinstance(file_or_path, (str, Path)):
        return Path(file_or_path).read_text(encoding="utf-8-sig", errors="replace")
    if hasattr(file_or_path, "read"):
        data = file_or_path.read()
        if isinstance(data, bytes):
            return data.decode("utf-8-sig", errors="replace")
        return data
    return str(file_or_path)


def iter_engine_inputs(parsed: dict[str, Any]) -> Iterator[tuple[str, str, dict, dict]]:
    """Yield `(msku, branch, engine_input_kwargs, source_values)` per data row."""
    for row in parsed["data"]:
        engine_kwargs = {
            "sales_90d": row.get("sales_90d") or 0.0,
            "adu_days": row.get("adu_days") or 0.0,
            "on_hand_qty": row.get("on_hand_qty") or 0.0,
            "on_order_qty": row.get("on_order_qty") or 0.0,
            "qualified_demand_qty": row.get("qualified_demand_qty") or 0.0,
            "moq": row.get("moq") or 0.0,
            "lead_time": row.get("lead_time") or 0.0,
            "dlt": row.get("dlt") or 0.0,
            "ltf": row.get("ltf") or 0.0,
            "vf": row.get("vf") or 0.0,
            "doc": row.get("doc") or 0.0,
        }
        source = {
            k: row.get(k)
            for k in (
                "source_adu", "source_red", "source_yellow", "source_green",
                "source_tog", "source_net_flow", "source_order_recommendation",
            )
        }
        yield row["msku_code"], row["branch_code"], engine_kwargs, source
