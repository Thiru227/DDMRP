## 1. Project skeleton and tooling

- [x] 1.1 Create folder structure: `app/{routes,services,calculations,validators,repositories,uploads,templates}`, `static/{css,js,uploads}`, `tests/`
- [x] 1.2 Add `requirements.txt` with `flask`, `supabase`, `pandas`, `openpyxl`, `python-dotenv`, `pytest`, `pytest-asyncio`
- [x] 1.3 Add `.env.example` documenting `SUPABASE_URL`, `SUPABASE_ANON_KEY`, `SUPABASE_SERVICE_ROLE_KEY`, `FLASK_ENV`
- [x] 1.4 Create `app.py` with Flask app factory, config loader, blueprint registration, and `/healthz` returning `{"ok": true}`
- [x] 1.5 Wire static asset serving for `/static/*`

## 2. Supabase schema

- [ ] 2.1 Create migration `001_branches.sql` for `branches` table (`branch_code` PK, `display_name`, `active`) with check constraint `branch_code <> 'TOT'`
- [ ] 2.2 Create migration `002_msku_master.sql` for `msku_master` (descriptive + parameter columns; range checks for `ltf`, `vf`, `doc`, `moq`, `lead_time`, `dlt`)
- [ ] 2.3 Create migration `003_inventory_snapshots.sql` keyed `(msku_code, branch_code, snapshot_date)`, FK to `msku_master` and `branches`, with `source_*` nullable columns
- [ ] 2.4 Create migration `004_planning_snapshots.sql` keyed `(msku_code, branch_code, snapshot_date)` with engine fields and `engine_minus_source_*` deltas + `flagged_diff` boolean
- [ ] 2.5 Create migration `005_upload_jobs.sql` (id, filename, format, uploaded_at, totals, committed_at, status enum)
- [ ] 2.6 Create migration `006_alerts.sql` (id, msku_code, branch_code, alert_type, severity, message, created_at, resolved, resolved_at)
- [ ] 2.7 Add seed script `seed_branches.py` inserting the twelve canonical codes
- [ ] 2.8 Add indexes: `inventory_snapshots(msku_code, branch_code)`, `planning_snapshots(alert_level)`, `alerts(msku_code, branch_code, resolved)`, `upload_jobs(uploaded_at desc)`

## 3. Calculation engine

- [ ] 3.1 Implement `app/calculations/ddmrp_engine.py` with `EngineInputs` and `EngineOutputs` dataclasses and a single `compute(inputs) -> outputs` function covering all formulas in the planning-engine spec
- [ ] 3.2 Add `compute_alert_level(net_flow, red_zone, toy)` returning `"red" | "yellow" | "healthy"` per the alert thresholds
- [ ] 3.3 Add `compute_diffs(engine_outputs, source_values)` returning per-field deltas and a `flagged_diff` boolean using the documented tolerances
- [ ] 3.4 Write unit tests for boundary cases: zeros, division-by-zero guards, negative net flow, `adu_days != 90`
- [ ] 3.5 Write a calibration test that loads `01 MENS INNER - PILOT - CURRENT WORKING FILE 1(MSK_WORKING).csv`, runs the engine on every operational row, and asserts diffs are within tolerance for `adu, red, yellow, green, tog, net_flow, order_recommendation`

## 4. Repositories (Supabase access)

- [ ] 4.1 `repositories/branches.py`: `list_active()`, `exists(code)`
- [ ] 4.2 `repositories/msku_master.py`: `get(code)`, `upsert(record)`, `list_all()`, `update_parameters(code, **fields)`
- [ ] 4.3 `repositories/inventory_snapshots.py`: `upsert_many(rows)`, `latest_per_pair()`, `get(msku, branch, date)`, `update_quantities(msku, branch, date, **fields)`
- [ ] 4.4 `repositories/planning_snapshots.py`: `upsert(row)`, `latest_per_pair()`, `latest_for_pair(msku, branch)`
- [ ] 4.5 `repositories/upload_jobs.py`: `create(...)`, `mark_committed(id, ...)`, `mark_rejected(id)`, `recent(limit)`
- [ ] 4.6 `repositories/alerts.py`: `open_alerts_for_pair(msku, branch)`, `resolve_open_for_pair(msku, branch, ts)`, `insert(...)`, `list(filters)`, `summary()`

## 5. Upload pipeline

- [ ] 5.1 Implement `uploads/clean_parser.py` reading CSV/XLSX with strict single-row header against the documented column list
- [ ] 5.2 Implement `uploads/legacy_parser.py` skipping rows until the first cell equals `S.NO`, fuzzy-mapping columns per the daily-upload spec, dropping `BRANCH = TOT` and blank-MSKU rows
- [ ] 5.3 Implement `validators/upload_validator.py` enforcing required-field, non-negative, `adu_days > 0`, in-file uniqueness, and FK existence rules
- [ ] 5.4 Implement `services/upload_service.py.parse_and_preview(file, format)` returning the staged `upload_jobs` row plus an in-memory list of accepted rows keyed by job id (or persisted to a transient `upload_staging` table)
- [ ] 5.5 Implement `services/upload_service.py.commit(job_id)` upserting accepted rows into `inventory_snapshots`, upserting master records (legacy path only), invoking the recompute service, and marking the job committed
- [ ] 5.6 Implement `routes/uploads.py` with `POST /api/uploads/stock`, `POST /api/uploads/{job_id}/commit`, `GET /api/uploads/template`, `GET /api/uploads/history`
- [ ] 5.7 Wire a background-free expiry helper that marks `status = expired` for `upload_jobs` older than 24 h with `status = preview` (invoked at the top of upload routes; no scheduler required)

## 6. Recompute service

- [ ] 6.1 Implement `services/recompute_service.py.recompute_pairs(pairs: Iterable[(msku, branch)])` that loads each pair's latest inventory + master, runs the engine, computes diffs, upserts the planning snapshot
- [ ] 6.2 Inside `recompute_pairs`, after each upsert call `services/alert_service.py.reconcile(msku, branch, new_alert_level, planning_snapshot)` to handle insert/resolve transitions per the alerts spec
- [ ] 6.3 Implement `services/recompute_service.py.recompute_msku_all_branches(msku)` for parameter edits (looks up branches via `inventory_snapshots`)
- [ ] 6.4 Add unit test simulating a healthy → red → healthy cycle and asserting the alerts table reflects open/resolve correctly

## 7. Planning + alerts + dashboard APIs

- [ ] 7.1 Implement `routes/planning.py` with `GET /api/planning` returning latest pair-level rows joined to master + diffs
- [ ] 7.2 Implement `PUT /api/planning/{msku}/{branch}` accepting any subset of `moq, ltf, vf, doc, lead_time, dlt, on_hand_qty, on_order_qty, qualified_demand_qty`, dispatching to the right repos and the right recompute scope
- [ ] 7.3 Implement `routes/alerts.py` with `GET /api/alerts?status=&severity=` and `GET /api/alerts/summary`
- [ ] 7.4 Implement `routes/dashboard.py` with `GET /api/dashboard` aggregating KPIs and recent uploads, with a 1-second per-process cache
- [ ] 7.5 Add a small response cache helper (`functools.lru_cache` with TTL or a hand-rolled dict + monotonic clock) used only by the dashboard route

## 8. Frontend integration (preserve uploaded HTML)

- [ ] 8.1 Drop the supplied prototype HTML into `app/templates/` (one file per page: `dashboard.html`, `planning.html`, `stock_upload.html`, `master_upload.html`, `alerts.html`, `upload_history.html`)
- [ ] 8.2 Add `static/js/api.js` exposing `getJSON`, `postJSON`, `putJSON`, `postFile` helpers with consistent error handling
- [ ] 8.3 Add `static/js/dashboard.js` implementing 5-second polling, KPI binding, recent uploads list, the failure-banner state machine, and 15-second backoff after three consecutive failures
- [ ] 8.4 Add `static/js/planning.js` rendering rows from `/api/planning`, applying `alert_level` colour cues, supporting inline edits with debounce, and re-rendering after the PUT response
- [ ] 8.5 Add `static/js/upload.js` implementing drag-and-drop, format selector (`clean | legacy`), preview rendering of accepted/rejected rows, and the explicit "Commit" button
- [ ] 8.6 Add a "Load sample data" button on the upload page that POSTs the bundled seed CSV to `/api/uploads/stock?format=legacy` and auto-commits the resulting job
- [ ] 8.7 Add `static/js/alerts.js` filtered listing with status + severity dropdowns
- [ ] 8.8 Add `static/css/app.css` (or extend the prototype CSS) for the red/yellow/green row colour cues, the diff-flag indicator, and the polling-paused banner

## 9. Demo readiness

- [ ] 9.1 Verify end-to-end on a fresh Supabase: bring-up steps from design.md migration plan succeed without manual intervention
- [ ] 9.2 Ship the seed CSV at a stable path under `app/uploads/sample/` so the "Load sample data" button is reproducible
- [ ] 9.3 Add a Postman/Bruno collection (or `.http` file) covering every endpoint
- [ ] 9.4 Run the calibration test in CI; fail the build if engine-vs-Excel diffs exceed tolerance for any seed row
- [ ] 9.5 Walk through every Demo Success Criterion from PRD §29 and confirm each one passes by visible UI behaviour
