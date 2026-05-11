## 1. Database — New Migrations

- [x] 1.1 Add migration `008_msku_display_name.sql`: ALTER TABLE msku_master ADD COLUMN display_name TEXT; ADD COLUMN short_code TEXT
- [x] 1.2 Add migration `009_suppliers.sql`: CREATE TABLE suppliers with all fields from design; seed POOMEX-001 and POOMEX-002
- [x] 1.3 Add migration `010_order_recommendations.sql`: CREATE TABLE order_recommendations (id, msku_code, hub_code, total_qty, status, allocation_json, notes, created_by, created_at)
- [x] 1.4 Add migration `011_requirement_slips.sql`: CREATE TABLE requirement_slips (id RS-YYYY-NNN, order_rec_id, msku_code, total_qty, status, sent_at, released_by, released_at); CREATE TABLE rs_sequence (year INT, last_num INT)

## 2. MSKU Display Name Parser

- [x] 2.1 In `legacy_parser.py`: add `_extract_display_name(msku_code)` function — regex between SOLID and (CLASSIC|POOMEX), title-case result, append PRM if PREMIUM in code
- [x] 2.2 Add `_derive_short_code(display_name, mode)` — words joined by `-`, uppercased, include ECO/PRM suffix for disambiguation
- [x] 2.3 Update `_upsert_msku()` in `uploads.py` to write `display_name` and `short_code`
- [x] 2.4 Update `GET /api/alerts/` to JOIN msku_master and include `display_name`, `short_code` in response
- [x] 2.5 Update `GET /api/planning/` (if exists) similarly

## 3. Auth Blueprint

- [x] 3.1 Create `app/routes/auth.py` with `POST /api/auth/login` — validate against hardcoded USERS dict, set Flask session `{user, role, name, initials, color}`
- [x] 3.2 Add `POST /api/auth/logout` — clears session, returns 200
- [x] 3.3 Add `GET /api/auth/me` — returns current session user or 401
- [x] 3.4 Register `auth_bp` in `app.py`
- [x] 3.5 Add `@login_required(role=None)` decorator that checks session; returns 401 JSON if not authenticated; accepts optional `role` list to gate by role

## 4. Suppliers Blueprint

- [x] 4.1 Create `app/routes/suppliers.py` with `GET /api/suppliers/` — list all, optional `?active=1` filter
- [x] 4.2 Add `POST /api/suppliers/` — create supplier
- [x] 4.3 Add `PATCH /api/suppliers/<code>` — update supplier fields
- [x] 4.4 Register `suppliers_bp` in `app.py`

## 5. Order Recommendations Blueprint

- [x] 5.1 Create `app/routes/order_recs.py` with `POST /api/order-recs/` — create draft, compute recommended qty from latest planning_snapshot (TOG−NFP, round up to MOQ)
- [x] 5.2 Add `GET /api/order-recs/` — list order recs (optional status filter)
- [x] 5.3 Add `GET /api/order-recs/<id>` — single order rec with full DDMRP buffer data joined from planning_snapshots
- [x] 5.4 Add `PATCH /api/order-recs/<id>` — update notes, total_qty, allocation_json
- [x] 5.5 Add `POST /api/order-recs/<id>/submit` — validate allocation_json is complete, change status to `sent_to_executor`, create a Requirement Slip record
- [x] 5.6 Register `order_recs_bp` in `app.py`

## 6. Requirement Slips Blueprint

- [x] 6.1 Create `app/routes/requirement_slips.py` with `GET /api/requirement-slips/` — list slips, optional `?status=` filter
- [x] 6.2 Add `GET /api/requirement-slips/<id>` — full slip detail including validation checks, supplier split, MRP band breakdown, SKU line items (derived from allocation_json)
- [x] 6.3 Add `POST /api/requirement-slips/<id>/release` — set status=released, record released_by and released_at from session
- [x] 6.4 Add `POST /api/requirement-slips/<id>/return` — set status back to draft on order_rec, delete slip
- [x] 6.5 Add `PATCH /api/requirement-slips/<id>` — for manual status updates (in_transit, received)
- [x] 6.6 Add `_next_rs_id(year)` helper that reads rs_sequence table and returns next RS-YYYY-NNN
- [x] 6.7 Register `requirement_slips_bp` in `app.py`

## 7. PO Tracking Blueprint

- [x] 7.1 Create `app/routes/po_tracking.py` with `GET /api/po-tracking/` — returns all slips grouped by status column, joined with order_recs for MSKU and qty

## 8. Sales Upload Parser

- [x] 8.1 Create `app/uploads/sales_parser.py` — parses `sales&stocks.csv` format (simpler headers: branch, 90d sales, stock only); missing planning params taken from existing msku_master row
- [x] 8.2 Add `POST /api/uploads/sales` route in `uploads.py` — parse, stage, return preview
- [x] 8.3 Ensure `commit_upload` handles sales format jobs (fills missing params from msku_master)

## 9. Wire the Demo HTML — Session & Login

- [x] 9.1 Copy `poc_quick_demo.html` → `app/templates/demo.html`
- [x] 9.2 Add Flask route `GET /` that checks session: if no session, serve demo.html (login screen visible); inject `<script>window.__SESSION__ = {{ session_json | tojson | safe }};</script>` into `<head>`
- [x] 9.3 In `demo.html` JS: replace `const USERS = {...}` and `doLogin()` with a `fetch('POST /api/auth/login')` call; on success store role in JS and call existing `applyRole()` / `goPage()` logic
- [x] 9.4 Add session guard at app init: if `window.__SESSION__.role` is falsy, show `#login-screen` and hide `#app-shell`

## 10. Wire the Demo HTML — Admin Data

- [x] 10.1 MSKU Master page: replace static JS MSKU array with `fetch('/api/dashboard/msku')` — endpoint returns msku_master rows with display_name
- [x] 10.2 Branch Master page: replace static branch array with `fetch('/api/dashboard/branches')`; wire Edit → `PATCH /api/dashboard/branches/<code>`
- [x] 10.3 Supplier Master page: replace static supplier HTML with `fetch('/api/suppliers/')` render; wire Edit → `PATCH /api/suppliers/<code>`
- [x] 10.4 Upload History page: replace static history rows with `fetch('/api/uploads/history')`; add Revoke button per committed row → `DELETE /api/uploads/<job_id>` with confirmation dialog
- [x] 10.5 Stock Upload page: wire the file input → `POST /api/uploads/stock`; show preview table from response; wire Confirm → `POST /api/uploads/<job_id>/commit`
- [x] 10.6 Sales Upload page: wire file input → `POST /api/uploads/sales`; preview + commit flow same as stock upload

## 11. Wire the Demo HTML — Planner Data

- [x] 11.1 Alert Dashboard: replace static MSKU rows with `fetch('/api/alerts/')` render; map alert_level + planning_priority to status badge and priority bar; wire "Create Order Rec" button → `POST /api/order-recs/`
- [x] 11.2 Order Recommendation Draft screen: load DDMRP buffer panel from order rec data; wire total_qty input
- [ ] 11.3 Hub Allocation — Supplier step: load suppliers from `fetch('/api/suppliers/?active=1')`; POST supplier qty split into `PATCH /api/order-recs/<id>` allocation_json
- [ ] 11.4 Hub Allocation — MRP Split, Colour×Size, Design steps: save each step's data to allocation_json via `PATCH /api/order-recs/<id>`
- [x] 11.5 "Send to Execution →" button: call `POST /api/order-recs/<id>/submit` with auto-built allocation_json; on success show alert and return to planner-alerts

## 12. Wire the Demo HTML — Executor Data

- [x] 12.1 Executor Inbox: replace static inbox card with `fetch('/api/requirement-slips/?status=pending_release')` render; wire card click → load slip review
- [x] 12.2 Requirement Slip Review page: populate RS number, MSKU name, hub, qty, validation checks, supplier split from API response
- [x] 12.3 "Release Requirement Slip" button: call `POST /api/requirement-slips/<id>/release`; on success navigate to executer-success page
- [ ] 12.4 Released tab: load from `fetch('/api/requirement-slips/?status=released')`
- [x] 12.5 PO Tracking kanban: load from `fetch('/api/po-tracking/')`; wire "Mark In Transit" and "Mark Received" buttons → `PATCH /api/requirement-slips/<id>`

## 13. Wire the Demo HTML — Admin Dashboard

- [x] 13.1 Admin Dashboard KPI cards: replace static counts with `fetch('/api/dashboard/')` — total_skus, red, yellow, pending_slips, released_slips, snapshot_date
- [x] 13.2 Recent Requirement Slips table on admin dashboard: load from `/api/requirement-slips/?limit=5`

## 14. Final Polish & Verification

- [ ] 14.1 Test full end-to-end flow: upload MSKU CSV → alert appears → create order rec → hub allocation → send to executor → executor reviews → release → PO Tracking shows released
- [ ] 14.2 Test revoke: commit upload → revoke → alerts disappear
- [ ] 14.3 Test all three role logins: verify correct nav items appear/hide for each role
- [ ] 14.4 Verify RS auto-numbering: two submissions in same year produce RS-YYYY-001 and RS-YYYY-002
- [ ] 14.5 Verify MSKU display names render correctly (not raw concatenated codes) across Alert Dashboard, Order Rec, Requirement Slip, PO Tracking
