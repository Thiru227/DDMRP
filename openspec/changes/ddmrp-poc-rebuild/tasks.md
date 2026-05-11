## Implementation Tasks

### Phase 1: Backend — app.py

- [x] **1.1** Create `/Users/designer/Desktop/DDMRP/app.py` (replace existing): import flask, sqlite3, csv, io, json, re, os, datetime; define `DB = "ddmrp_v2.db"`, `_ABBREVS`, `display_name()`, `pnum()`, `pp_status()` helpers
- [x] **1.2** Write `init_db()`: executescript to create 4 tables (`mskus`, `upload_logs`, `order_recs`, `requirement_slips`) with all columns per design.md D2; call on app startup
- [x] **1.3** Implement auth routes: `GET /` → serve `demo.html`; `POST /api/auth/login` (validate role/username/password, set session); `POST /api/auth/logout`; `_require(role)` decorator
- [x] **1.4** Implement CSV upload routes: `POST /api/upload` — read file bytes, detect format via `_auto_fmt()`, branch to `_parse_hub()` or `_parse_branch()`, upsert `mskus`, insert `upload_logs`; `GET /api/uploads` (admin only); `POST /api/uploads/<id>/revoke` (admin only)
- [x] **1.5** Implement `_parse_hub(rows)`: map hub CSV columns to msku fields per design.md column mapping; return list of dicts
- [x] **1.6** Implement `_parse_branch(rows)`: skip header rows until S.NO found, group by MSKU code, sum 90-day sales + OH across branches, take TOR/TOY/TOG from first row where TOR > 0, compute ADU/NFP/plan_priority/order_rec; return list of dicts
- [x] **1.7** Implement MSKU routes: `GET /api/mskus` (planner only) — query all mskus, add `status` via `pp_status()`, return JSON array; `GET /api/mskus/<id>` — single MSKU with all fields
- [x] **1.8** Implement order rec routes: `POST /api/order-recs` (planner only) — insert draft OR, auto-generate slip_no `OR-YYYY-NNN`; `GET /api/order-recs/<id>`; `PATCH /api/order-recs/<id>` (draft only, 400 if non-draft); `POST /api/order-recs/<id>/send` (planner only, 403 for others)
- [x] **1.9** Implement `_gen_rs_lines(msku, order_qty, alloc)`: if alloc empty → equal split across mrp_bands; else multiply mrp_split × size_color matrix × design_split percentages to produce `[{mrp, size, colour, design, qty}]` list; round to integers with remainder on last item
- [x] **1.10** Implement executor routes: `GET /api/executor/inbox` (executor only); `POST /api/executor/order-recs/<id>/create-rs` — fetch OR + MSKU, call `_gen_rs_lines()`, insert RS, update OR status to `rs_created`; `POST /api/rs/<id>/release`
- [x] **1.11** Implement RS/tracking routes: `GET /api/rs` (admin only) — all RSes joined with OR and MSKU display name; `GET /api/rs/<id>`; `GET /api/po-tracking` (executor only)
- [x] **1.12** Run `python3 app.py` and verify server starts, `ddmrp_v2.db` is created with correct schema

### Phase 2: Frontend — demo.html

- [x] **2.1** Create `/Users/designer/Desktop/DDMRP/app/templates/demo.html`: copy `<style>` block verbatim from prototype lines 7–708; set up base HTML structure with `<div id="app">` container
- [x] **2.2** Build login screen (`#page-login`): three role cards (Admin/Planner/Executor) using prototype's `#rc-admin`/`#rc-placement`/`#rc-executer` style; `pickRole()` pre-fills username/password inputs; `doLogin()` POSTs to `/api/auth/login` then calls `goPage()` based on role
- [x] **2.3** Implement `goPage(id)` SPA router: hide all `.page` divs, show target, call page-specific `load*()` function
- [x] **2.4** Build admin upload page (`#page-admin-upload`): file input + upload button → POST to `/api/upload` with FormData; show result toast; render upload log table via `GET /api/uploads`; revoke button per row
- [x] **2.5** Build admin RS tracker tab (`#page-admin-rs`): `loadRsTracker()` fetches `GET /api/rs`; renders table with slip_no, OR slip_no, MSKU name, line count, status badge, timestamps; click row → show line detail modal/panel
- [x] **2.6** Build planner alert dashboard (`#page-planner-alerts`): `loadAlerts()` fetches `GET /api/mskus`; renders `.atbl` table with one row per MSKU; status badges; filter bar dropdowns populated from data; client-side filter logic; "Create Order Rec" / "Continue Draft" / "Track" / "View" action buttons per row
- [x] **2.7** Build order rec detail page (`#page-order-rec`): two-column layout — left: editable qty + notes + buffer reference display (DDMRP zone bar with TOR/TOY/TOG markers, NFP position); right: hub allocation wizard tabs
- [x] **2.8** Build hub allocation wizard (embedded in order rec page): step indicator (3 steps); Step 1 MRP split — render one row per `mrp_bands` entry with % input, live total, warn + disable Next if ≠ 100; Step 2 Size×Colour matrix — columns from `msku.sizes`, rows = White/Black/Navy/Grey, integer inputs, live column + row totals; Step 3 Design split — DES01 Solid Plain (60%) + DES02 Pattern (40%) % inputs
- [x] **2.9** Wire "Send to Execution" CTA: visible only after Step 3 completed; onClick → `PATCH /api/order-recs/<id>` with allocation JSON then `POST /api/order-recs/<id>/send`; on success show confirmation toast and return to alerts page
- [x] **2.10** Build executor inbox (`#page-executor-inbox`): `loadInbox()` fetches `GET /api/executor/inbox`; render one card per OR with slip_no, MSKU name, qty, sent_at, "Create Requirement Slip" button; onClick → POST create-rs, show success, refresh inbox
- [x] **2.11** Build executor PO tracking (`#page-po-tracking`): `loadPoTracking()` fetches `GET /api/po-tracking`; render two-column kanban (Pending / Released); each card shows RS slip_no, OR slip_no, MSKU name, line count; "Release" button on pending cards
- [x] **2.12** Implement global error handling: `apiFetch(url, opts)` wrapper that checks `res.ok`, shows toast on 4xx/5xx, handles 403 by redirecting to login

### Phase 3: Validation

- [x] **3.1** Upload `sales&stocks.csv` as admin → verify 8 MSKU rows appear in planner dashboard with correct plan_priority and status badges
- [x] **3.2** Upload `01 MENS INNER…csv` → verify sizes and mrp_bands populated on existing MSKUs, DDMRP fields preserved from hub upload
- [x] **3.3** Complete full planner flow: create OR → fill wizard all 3 steps → send to execution → OR disappears from draft list
- [x] **3.4** Complete executor flow: create RS from sent OR → verify RS lines generated → check OR status is `rs_created`; release RS → card moves to Released column
- [x] **3.5** Verify admin RS tracker shows all RSes with correct status badges and line detail is accessible
- [x] **3.6** Verify empty states: planner dashboard with empty DB shows "No data yet" message; executor inbox with no sent ORs shows waiting message
- [x] **3.7** Verify role gating: planner cannot access `/api/uploads` (403); executor cannot access `/api/order-recs/<id>/send` (403); admin cannot access `/api/executor/inbox` (403)
