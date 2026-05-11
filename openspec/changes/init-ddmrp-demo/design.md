## Context

The team currently runs Demand-Driven MRP (DDMRP) inventory planning in an Excel workbook. The provided seed file (`01 MENS INNER - PILOT - CURRENT WORKING FILE 1(MSK_WORKING).csv`, 141 rows) is the workbook's flattened export. Inspection shows three facts that materially shape the design and were not captured in the input PRD:

1. **The data is per-(MSKU × Branch).** Each Master SKU (e.g. `MENSINNER WEARECONOMICACTIVE WEAR INNER WEAR TOPSOLIDGYM VESTCLASSICPOOMEX`) appears once per branch code. There are 12 real branches (`TUP, CBE, ERD, CB2, TNV, SLM, MDU, VPM, TUT, DGL, PDY, NGL`) plus a synthetic `TOT` aggregate row. Modelling MSKU alone would collapse 12× the actual planning state.
2. **The export already contains every computed field** — `90 DAY SAL`, `ADU`, `RED`, `YELLOW`, `GREEN`, `TOG`, `NET FLOW`, `ORDER RECOM`, etc. The "upload" is an Excel output dump, not a raw input file.
3. **The CSV's first ~26 rows are merged-cell formula annotations** (`"ADU * DLT * LTF"`, `"RED + YELLOW + GREEN"`, …). The actual header row sits around line 32 and uses pseudo-multi-row column names. Any naive `pandas.read_csv` will fail.

The PRD also specifies a 5-column daily upload schema (`MSKU_CODE, OH_QTY, DATE, OO_QTY, QD_QTY`) which does not match the seed file. Rather than choosing one or the other, this design supports both via a single ingestion pipeline.

Stakeholders: a planning manager who runs the workbook today (will demo the result); a small dev team building the demo over a few days; reviewers who will verify numbers against the original Excel.

Constraints (from PRD §33 and §9): Flask + Supabase + vanilla JS only. No microservices, no message bus, no AI layer, no WebSockets. Polling at ~5 s is sufficient.

## Goals / Non-Goals

**Goals:**
- A planner can open the app, click "Load sample data," and see the seed CSV's planning state populated end-to-end (dashboard KPIs, planning table with color-coded rows, alerts, upload history) within seconds.
- A planner can edit any of `MOQ, VF, LTF, DOC, Lead Time, On Hand, On Order, Qualified Demand` inline; the affected `(msku, branch)` recomputes within the same request and the next poll reflects new zones, net flow, alert level, and recommendation.
- A planner can upload a CSV/XLSX in either the documented "clean template" format or the legacy Excel-export format; rejected rows are previewed before commit.
- The Python DDMRP engine is the single source of truth for planning math; per-row diffs vs. the source CSV are surfaced as a confidence signal but never override the engine's output.
- The HTML structure of the supplied prototype is preserved; only data-binding and interactivity are added.

**Non-Goals:**
- Multi-tenant authorisation, RLS policies, or organisation-scoped data.
- Background workers, queues, or asynchronous recompute. Recompute is in-request, scoped to affected `(msku, branch)` rows.
- WebSockets, server-sent events, or push notifications.
- Forecasting, ML-driven ADU smoothing, or anything beyond rolling 90-day sales / day count.
- Historical reporting, trend charts, or audit logs beyond what `upload_jobs` and `alerts` already give us.
- Mobile-specific layouts.
- Internationalisation.

## Decisions

### Decision 1 — Carry a `branch` column on every operational table

The natural key for inventory and planning is `(msku_code, branch_code)`, with a daily snapshot date layered on top. `inventory_snapshots` and `planning_snapshots` are keyed `(msku_code, branch_code, snapshot_date)`. Alerts reference `(msku_code, branch_code)`.

A `branches` lookup table holds the 12 real codes; rows uploaded with an unknown branch code are rejected unless the row's branch is `TOT` (handled below).

*Alternatives considered.* (a) Modelling branches as a separate per-MSKU "warehouse" relation — overkill, branches are global. (b) Stuffing the branch into the MSKU primary key as a compound text field — fragile, breaks joins. (c) Ignoring branch entirely (PRD's implicit choice) — collapses 12× the data and makes the seed file unusable.

### Decision 2 — Treat `TOT` rows as system-computed aggregates, never stored input

The `TOT` row in the seed file is the per-MSKU sum across branches. The ingestion path drops these rows. The dashboard computes equivalent aggregates from stored `(msku, branch)` snapshots when needed. This avoids a class of bug where editing one branch leaves a stale `TOT` row.

*Alternative considered.* Store `TOT` as a synthetic branch_code. Rejected because every recompute would need to re-emit a `TOT` row in lockstep, and any UI that filters by branch would have to special-case it.

### Decision 3 — Hybrid ingest: store source-calculated fields, recompute everything

Each `inventory_snapshots` row carries the raw input fields (`on_hand_qty, on_order_qty, qualified_demand_qty, sales_90d, adu_days`). It also carries a small set of `source_calculated_*` columns (`source_adu, source_red, source_yellow, source_green, source_tog, source_net_flow, source_order_recommendation`) populated only when the source file already had them.

`planning_snapshots` always holds the engine's output. The planning view exposes a per-row diff (`engine_value − source_value`) for the columns where both exist. A row whose engine-vs-source diff exceeds a small tolerance (e.g. ≥ 0.5 for integers, ≥ 0.05 for rates) is flagged in the UI but the engine's number still drives alerts and recommendations.

*Why this matters for the demo:* reviewers will check our numbers against Excel. A built-in "engine matches Excel" indicator is easier to defend than asking them to spot-check by hand.

*Alternatives considered.* (A) trust the source file and store-only — fails PRD §30 ("Python engine is SSOT"); engine never gets exercised. (B) ignore source values — loses the validation hook and the demo confidence signal.

### Decision 4 — Two upload paths, one ingestion pipeline

Both upload paths land in the same `parse → validate → preview → commit → recompute` flow. They differ only in the parser:

- **Clean template parser** — single-row header. Required columns: `msku_code, branch_code, snapshot_date, on_hand_qty, on_order_qty, qualified_demand_qty, sales_90d, adu_days`. Optional: `source_adu, source_red, source_yellow, source_green, source_tog, source_net_flow, source_order_recommendation`.
- **Legacy parser** — skips lines until it finds a row whose first cell is `S.NO` (the seed file's real header is around line 32). Fuzzy-maps Excel labels: `MASTER SKU → msku_code`, `BRANCH → branch_code`, `90 DAY SAL → sales_90d`, `ADU DAYS → adu_days`, `ON HAND → on_hand_qty`, `ON ORDER → on_order_qty`, `QUALIFIED DEMAND → qualified_demand_qty`, parameter columns `LTF, VF, DOC, DLT, MOQ, LEAD TIME → msku_master upserts`, computed columns into `source_*`. Rows where `branch_code = "TOT"` or `msku_code` is blank are dropped.

The legacy path also upserts `msku_master` rows on the fly, because the seed file is the only source of master data we have for the demo. This is intentional for the demo and explicitly disallowed for the clean template path (master records must be loaded via `POST /api/uploads/master` first).

*Alternative considered.* Build only the legacy parser ("just make the existing file work"). Rejected because a clean template is the long-term contract; supporting only the legacy format would calcify around one team's Excel layout.

### Decision 5 — In-request synchronous recompute, scoped per `(msku, branch)`

For the demo's data volume (140 rows of seed × small daily uploads), a full recompute completes in milliseconds. Any state-changing endpoint (upload commit, planning row PUT) recomputes the affected `(msku, branch)` rows synchronously and returns the new state. The frontend's 5-second poll picks up changes for other rows.

*Alternative considered.* Background recompute via threading or Celery. Rejected as over-engineering for the demo's scale and explicitly prohibited by the PRD's "no microservices, no event streaming" rule.

### Decision 6 — Engine implemented in pure Python with no Supabase dependency

`app/calculations/ddmrp_engine.py` accepts plain dataclasses or dicts and returns plain dataclasses or dicts. It has no Supabase client, no Flask import, and no I/O. This makes it directly unit-testable against the seed CSV and trivially callable from any other context. Ports to/from Supabase live in `app/repositories/`.

### Decision 7 — Naming sticks to the PRD's ubiquitous language

Database columns, Python variables, JSON keys, and HTML data attributes all use the PRD §3 terms (`adu`, `red_zone`, `yellow_zone`, `green_zone`, `tog`, `net_flow`, `order_recommendation`, `alert_level`). The seed CSV's idiosyncratic labels (`STEP 1`, `RBASE`, `RSAFETY`, `TOY`) are mapped at the parser boundary and not propagated.

## Risks / Trade-offs

- **Risk: engine output diverges from Excel by more than rounding.** → Mitigation: ship a small calibration test that loads the seed CSV, runs the engine, and asserts each row's diffs are within tolerance for the seven shared columns. Failing rows print the input + expected + actual.
- **Risk: legacy parser silently drops rows when the Excel layout shifts (e.g. a new column inserted between `BRANCH` and `90 DAY SAL`).** → Mitigation: parser is column-name driven, not column-index driven. If a required name is missing, the upload is rejected with the missing column listed.
- **Risk: Supabase free tier rate limits during a live demo.** → Mitigation: a single-process Flask app with a connection pool; the polling endpoint returns cached aggregates with a short (~1 s) TTL.
- **Trade-off: no auth → anyone with the URL can edit data.** Acceptable for the demo. Production deploy would need to enable Supabase Auth + RLS, which is intentionally deferred.
- **Trade-off: synchronous recompute during commit means uploading a 100k-row file blocks the request.** Acceptable for the demo's scale (~140 rows). If the file is genuinely large, the API returns 413 before parsing.
- **Trade-off: editing a parameter (e.g. `LTF`) on `msku_master` triggers recompute across all branches for that MSKU. For a 12-branch SKU this is 12 row recomputes per edit.** Still milliseconds at this scale.

## Migration Plan

There is no existing system to migrate from — this is a greenfield demo. Bring-up steps:

1. Create the Supabase project, run schema migrations (one SQL file per table from the specs), seed the `branches` lookup with the 12 codes from the seed CSV.
2. Stand up the Flask app with `/healthz` returning 200.
3. Implement the engine and run the calibration test against the seed CSV; do not proceed past this step until diffs are within tolerance.
4. Implement the legacy parser and the "Load sample data" button; verify the dashboard, planning table, and alerts populate correctly from the seed.
5. Implement the clean-template parser and the master-upload path; verify a synthetic clean upload over the seed data produces the same planning state.
6. Implement inline edit + recompute.
7. Wire frontend polling.

Rollback: drop the Supabase project (or `TRUNCATE` the four operational tables); the app has no other persistence.

## Open Questions

- **What tolerance, exactly, is acceptable for the engine-vs-source diff?** Best resolved by running the calibration once and looking at the natural distribution of diffs in the seed file. If most rows agree to ≤ 0.05 and a few are off by ≥ 1 because of Excel rounding, we'll set the tolerance at that gap.
- **Should the Alerts page show only currently-Red/Yellow `(msku, branch)` rows, or a transition log?** Default for the demo: a live "currently in this state" listing with the latest transition timestamp, sourced from `planning_snapshots`. A full event log can come later if needed.
- **`ADU DAYS` is sometimes 89 or 52 in the seed file rather than 90.** The engine should respect the per-row value rather than hard-coding 90. Confirmed in the spec.
- **Multiple snapshots per day for the same `(msku, branch)` — keep all or upsert latest?** Default for the demo: upsert by `(msku, branch, snapshot_date)`, latest wins. The spec encodes this; revisit if the team needs intra-day history.
