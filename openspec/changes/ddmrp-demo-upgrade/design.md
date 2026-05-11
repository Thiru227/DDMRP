## Context

The app is a single-file Flask SPA (`app.py` + `demo.html`). All business logic, DB access, and HTML live in these two files. The DB is SQLite (`ddmrp_v2.db`) with four tables: `mskus`, `upload_logs`, `order_recs`, `requirement_slips`. There is a separate `app/` module in the project but it is **not running** — all changes target `app.py` + `demo.html` only.

Current gaps:
- Single upload zone; format is auto-detected silently — confusing for stakeholders
- `mskus` table has no `product_code` column
- No `PATCH /api/mskus/<id>` endpoint; planner table is read-only
- Action column has one button that doesn't reflect OR/RS lifecycle states
- OR codes use random hex: `_next_slip()` exists for RS but OR uses `uuid4().hex[:6]`
- PO tracking cards show summary only; no detail drill-down

## Goals / Non-Goals

**Goals:**
- Stakeholder demo is fully self-contained from two CSV uploads with no manual data entry
- Planner can adjust inventory position (OH/OO) and planning parameters inline; derived DDMRP values update immediately
- Planner action column clearly communicates state without exposing executor-side terminology
- PO tracking cards show enough detail to be meaningful during a demo walk-through
- All codes (MSKU product code, OR slip, RS slip) look systematic, not machine-generated

**Non-Goals:**
- Rewriting the `app/` module or migrating to its architecture
- Multi-user conflict resolution on inline edits
- Audit trail / change history
- Real supplier API integration

## Decisions

### D1 — One upload endpoint, two UI zones

**Decision:** Keep the single `POST /api/upload` endpoint. Add a `type` form field (`msku` or `sales`) that overrides `_auto_fmt()`, ensuring the right parser runs even if format detection is ambiguous.

**Alternative considered:** Two separate endpoints (`/api/upload/msku`, `/api/upload/sales`). Rejected because it duplicates 80% of upload logic for zero functional gain. The type hint on the form field is sufficient.

### D2 — Product code derivation

**Decision:** Derive `product_code` inside `_parse_branch()` and `_parse_hub()` at upload time using a pure-string function `_derive_product_code(msku_code)`. Store in a new `product_code TEXT` column (nullable). Use the pattern: `{CAT}-{TIER}-{OCC}-{STYLE}` e.g. `MI-ECO-ACT-GV`.

Derivation rules (all from MSKU string, no external lookup):
- **CAT**: `MENS INNER WEAR` → `MI`; default → `GEN`
- **TIER**: `ECONOMIC` → `ECO`; `PREMIUM` → `PRM`; default → `STD`
- **OCC**: `ACTIVE WEAR` → `ACT`; `DAILY WEAR` → `DAI`; default → `GEN`
- **STYLE**: extract same way as `display_name()` — between `SOLID` and `CLASSIC/POOMEX`, take first two words, uppercase abbrev e.g. `GYM VEST` → `GV`, `BRIEFS` → `BR`, `TRUNK` → `TR`

**Alternative considered:** Manual code assignment via admin UI. Rejected — defeats the "zero hardcoded data" principle.

### D3 — PATCH /api/mskus/<id> with recompute

**Decision:** Accept a JSON body with any subset of `{on_hand, on_order, dlt, ltf, vf, doc, moq}`. After updating the row, recalculate all derived DDMRP fields server-side and return the full updated row. The client replaces the row in-place and flashes the updated cells.

Derived field formulas (matching existing CSV import logic):
```
adu         = sales_90d / 90
red         = adu * dlt * ltf
yellow      = adu * doc
green       = max(moq, yellow)
tor         = red + yellow          (TOR = top of red)
toy         = tor + yellow          (TOY = top of yellow)
tog         = tor + green           (TOG = top of green)
nfp         = on_hand + on_order
plan_priority = (nfp / tog * 100) if tog > 0 else 0
order_rec   = ceil((tog - nfp) / moq) * moq  if nfp < tor else 0
status      = pp_status(plan_priority)   (existing function)
```

**Why only independent fields editable:** If a field can be derived from another editable field (e.g. `red` is derived from `adu`, `dlt`, `ltf`), making it directly editable would create inconsistency. Keeping derived fields display-only preserves DDMRP integrity and matches how the spreadsheet model works.

### D4 — 4-state planner action column

**Decision:** The planner table fetches active ORs once on load (`GET /api/order-recs`) and builds a lookup map `{msku_id → or}`. Each row checks this map:

| OR state | Render |
|---|---|
| no OR | `<button>Create Order Recommendation Draft</button>` |
| `draft` | `<button>Continue Draft</button>` |
| `sent_to_execution` | `<span class="badge b-amber">Sent to Executor</span>` |
| `rs_created` | `<span class="badge b-green">RS Created ✓</span>` |

"Continue Draft" re-opens the existing OR detail panel (same panel as "Create"). No new page needed.

**Why not per-row API call:** Would cause N+1 requests. One prefetch on load is sufficient.

### D5 — Sequential OR codes

**Decision:** Replace `uuid4().hex[:6].upper()` in `create_order_rec()` with the same `_next_slip(db, "OR")` pattern already used for RS codes. Result: `OR-2025-001`.

**Risk:** Two concurrent POSTs could read the same COUNT before either commits. Acceptable for a single-user POC demo.

### D6 — PO Tracking detail panel

**Decision:** Add a slide-in side panel (right-side drawer, 380px wide) populated by `GET /api/rs/<id>`. Panel shows: RS code, OR code, product name + product code, hub, total qty, and a table of all RS lines (MRP | Size | Colour | Design | Qty). The Release button remains on the kanban card (not in the panel) to keep the release action visible at a glance.

**Alternative considered:** Modal dialog. Rejected — side panel keeps the kanban context visible while reviewing detail, which is better for demo flow.

## Risks / Trade-offs

- **Schema migration at startup** — `ALTER TABLE mskus ADD COLUMN product_code TEXT` runs in `init_db()` inside a `try/except` (column already exists = no-op). Existing rows get `NULL`; repopulated on next upload.
- **product_code for hub-format CSV** — `_parse_hub()` reads the MSKU code from column 0 of `sales&stocks.csv`. If that CSV doesn't contain the full concatenated MSKU string, derivation may fall back to `GEN-STD-GEN-XX`. Acceptable for demo — branch CSV is the primary MSKU source.
- **Inline edit concurrency** — No optimistic locking. If two planners edit the same row simultaneously, last write wins. Single-user POC: acceptable.
- **N+1 on OR prefetch** — One extra `GET /api/order-recs` on planner page load. Negligible for demo data volumes (<50 MSKUs).

## Migration Plan

1. `init_db()` runs `ALTER TABLE mskus ADD COLUMN product_code TEXT` (idempotent via try/except)
2. On next CSV upload, `product_code` is derived and stored for all rows
3. Existing rows without `product_code` display `—` until re-uploaded
4. No data loss; no rollback needed (column is additive and nullable)

## Open Questions

*(none — all decisions made)*
