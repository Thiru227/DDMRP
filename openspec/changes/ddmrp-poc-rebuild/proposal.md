## Why

The existing DDMRP Flask POC has accumulated static/hardcoded data scattered across `demo.html`, making it misleading during stakeholder demos and preventing real data flow. The prototype HTML (`DDMRP Prototype.html`) defines the correct UX and visual language; we now need a real-data version built on top of it — scrapping the old blueprint approach and replacing it with a single-file, zero-static-data app wired to live CSV uploads.

## What Changes

- **BREAKING** Replace all existing Flask blueprints (`alerts`, `auth`, `dashboard`, `order_recs`, `planning`, `po_tracking`, `requirement_slips`, `suppliers`, `uploads`) with a single flat `app.py` containing all routes
- **BREAKING** Replace `app/templates/demo.html` with a fully API-driven SPA that shares the prototype's design system (CSS tokens, component classes) but fetches all data from the Flask backend — zero hardcoded MSKU arrays, demo toggles, or fake numbers
- Add CSV upload flow for two file formats: hub-level (`sales&stocks.csv`) and branch-level (`01 MENS INNER…csv`) — auto-detected on upload
- Add 3-role quick-login: Admin, Planning, Executor — pre-filled credentials, single click
- Admin: uploads (MSKU master + stock/sales), revoke, RS tracker (view-only)
- Planner: live alert dashboard with real DDMRP numbers + filter bar; Order Rec creation → Hub Allocation wizard (MRP % split → Size×Colour matrix → Design split) → "Send to Execution" CTA
- Executor: inbox (pending order recs), create Requirement Slip (one button), PO tracking kanban
- New SQLite schema (`ddmrp_v2.db`) — 4 tables: `mskus`, `upload_logs`, `order_recs`, `requirement_slips`
- Single branch (Madurai Hub), single supplier (Poomex) scope for this demo

## Capabilities

### New Capabilities

- `csv-upload`: Admin uploads MSKU master or stock+sales CSV; system auto-detects format, parses and upserts into `mskus` table; upload log with revoke option
- `msku-alert-dashboard`: Real-time MSKU table driven by DB with filter bar (division/segment/mode/collection/product/style); status badges (red/yellow/green/blue) from plan priority; no static fallback
- `order-rec-flow`: Planner creates order recommendation from MSKU detail; stores qty + notes; status lifecycle: `draft` → `sent_to_execution` → `rs_created`
- `hub-allocation-wizard`: 3-step wizard embedded in order rec: (1) MRP % split per band, (2) Size × Colour quantity matrix, (3) Design % split; allocation saved as JSON on order rec record
- `executor-rs-creation`: Executor sees sent order recs in inbox; one-click "Create Requirement Slip" generates RS lines from allocation JSON; RS slip number auto-assigned (RS-YYYY-NNN)
- `rs-tracker`: Admin and executor can view all requirement slips with stage, MSKU, qty, dates — fully live from DB, no static rows

### Modified Capabilities

- (none — this is a clean rebuild, not a delta on existing specs)

## Impact

- `app.py` — complete rewrite; old blueprint imports removed
- `app/templates/demo.html` — complete rewrite; retains CSS design tokens from prototype
- `app/data/ddmrp_v2.db` — new DB file (old `ddmrp.db` left intact, not migrated)
- `app/routes/` — all files become dead code (can be deleted after rebuild)
- `app/migrations/` — no longer used; schema is inline in `app.py`
- `requirements.txt` — Flask + no new dependencies needed
