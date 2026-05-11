## Why

The DDMRP platform has a complete, high-fidelity HTML prototype and a solid Flask backend (upload, engine, alerts), but they are disconnected: the demo shows hardcoded data and the backend has no frontend. Stakeholders need an end-to-end working POC — real CSV data flowing through alerts, planning, order creation, hub allocation, and executor release — to validate the DDMRP concept before scaling.

## What Changes

- Replace hardcoded demo JS data with live Flask API calls across all screens
- Add Flask session-based auth with three pre-configured roles (admin, planner, executor)
- Add `display_name` extraction to the MSKU parser so product names show as "RN Vest", "Gym Vest" etc. instead of raw concatenated codes
- Add `suppliers` master table (seeded with POOMEX-001 / POOMEX-002) with admin CRUD UI
- Add `order_recommendations` table and API covering the full draft → hub-allocation → submit lifecycle
- Add `requirement_slips` table and API with RS-YYYY-NNN auto-numbering; executor inbox and release flow
- Add inline editing for Branch Master, Supplier Master, and MSKU Master in the admin UI
- Add CSV revoke capability surfaced in the admin upload history UI (already exists in backend, needs frontend wire-up)
- Add sales CSV upload (separate from stock/MSKU upload) wired to the `sales-upload` admin page

## Capabilities

### New Capabilities

- `auth`: Session-based login with three hardcoded roles — admin (admin/admin), planner (planning/planning), executor (executer/executer). Role gates which nav items and pages are visible.
- `msku-display-name`: Parser extracts human-readable product name and a short hyphenated MSKU code from the raw concatenated classification string. Stored as `display_name` and `short_code` on `msku_master`.
- `supplier-master`: Suppliers CRUD table in the admin area. Fields: supplier_code, name, unit, location, contact, credit_days, is_msme, stock_clearance_rule, moq, active. Seeded with two Poomex units.
- `order-recommendation`: Planner creates a draft PO for an MSKU, progresses through 4-step hub allocation (Supplier → MRP Split → Colour × Size → Design), then submits. Submitted orders land in the executor inbox as Requirement Slips.
- `requirement-slip`: Auto-numbered (RS-YYYY-NNN) document generated from a submitted order recommendation. Executor reviews validation checks and supplier split, then releases. Released slips move to PO Tracking.
- `po-tracking`: Kanban board showing all requirement slips across lifecycle stages: Pending Placement → Pending Executor → PO Released → In Transit → Received. Status transitions are manual for the POC.
- `sales-upload`: Admin uploads a separate sales/stock CSV (`sales&stocks.csv` format). Parsed and committed to inventory_snapshots alongside the existing MSKU working file upload.

### Modified Capabilities

- `csv-upload`: Revoke button added to upload history UI (DELETE endpoint already exists, needs frontend).

## Impact

- `app/uploads/legacy_parser.py` — add display_name / short_code extraction
- `app/migrations/` — new migrations for suppliers, order_recommendations, requirement_slips; alter msku_master to add display_name, short_code
- `app/routes/` — new blueprints: auth, suppliers, order_recs, requirement_slips, po_tracking
- `poc_quick_demo.html` — replace all static JS data blocks with fetch() calls; add session guard at page load; remove hardcoded `const USERS`
- `requirements.txt` — no new dependencies (Flask sessions are built-in)
