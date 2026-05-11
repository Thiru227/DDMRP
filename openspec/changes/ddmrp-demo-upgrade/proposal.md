## Why

The DDMRP demo needs to be stakeholder-ready: uploads are ambiguous (one zone for two CSVs), the planner table is read-only, the action workflow mixes planner/executor terminology, and PO tracking cards lack detail. These gaps make the demo feel unfinished during live presentations.

## What Changes

- Split admin upload into two explicit cards — MSKU (branch-level CSV) and Sales & Stocks (hub-level CSV) — so the upload intent is always unambiguous
- Derive and store a short product code (e.g. `MI-ECO-ACT-GV`) from the MSKU string during upload; show it everywhere as a monospace badge
- Make the planner table inline-editable for independent DDMRP variables only (OH, OO, DLT, LTF, VF, DOC, MOQ); all derived fields (ADU, zones, TOG, NFP, priority, order rec) auto-recalculate on change
- Replace the single action button with a 4-state planner workflow: Create Draft → Continue Draft → Sent to Executor (green, no-op) → RS Created ✓ (green, no-op)
- Change OR slip codes from random hex (`OR-2025-A3B4C5`) to sequential (`OR-2025-001`)
- Add a full-detail side panel when clicking a PO tracking card (RS lines, sizes, MRP, colors, design, quantities)
- Add tooltip/label on the allocation panel explaining why size/color splits must total 100%
- Show `product_code` in the Admin RS Tracker table

## Capabilities

### New Capabilities

- `dual-upload`: Two distinct upload sections (MSKU CSV + Sales & Stocks CSV) with separate upload zones, format labels, and success feedback
- `product-code`: Systematic code derivation from MSKU string at upload time; stored in DB; displayed throughout the app
- `planner-inline-edit`: Inline editing of independent planning variables with live DDMRP recompute on save
- `planner-action-states`: 4-state action column on planner rows reflecting OR/RS lifecycle without executor terminology
- `po-tracking-detail`: Click-to-expand detail panel on PO tracking kanban cards showing full RS line breakdown

### Modified Capabilities

*(none — all new)*

## Impact

- `app.py`: add `product_code` column to `mskus` table via migration; add `PATCH /api/mskus/<id>` endpoint with recompute logic; fix `_next_slip()` for OR sequential codes; add `product_code` derivation to `_parse_branch` and `_parse_hub`
- `demo.html`: admin upload page, planner table (columns + edit handlers), action button states, PO tracking cards + side panel, allocation panel label
- `ddmrp_v2.db`: schema migration (ALTER TABLE mskus ADD COLUMN product_code TEXT)
- No new dependencies; no breaking API changes; existing uploads remain valid (product_code nullable until re-upload)
