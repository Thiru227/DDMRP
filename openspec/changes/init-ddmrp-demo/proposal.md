## Why

A textile-inventory team currently runs DDMRP planning in a multi-tab Excel workbook (`01 MENS INNER - PILOT - CURRENT WORKING FILE 1(MSK_WORKING).csv` is its export). The spreadsheet computes Average Daily Usage (ADU), Red/Yellow/Green buffer zones, Net Flow, and order recommendations per SKU per branch — but it is not interactive, not auditable, and not shareable in real time.

We need a small, demoable Flask + Supabase web application that reproduces the spreadsheet's planning math, accepts daily uploads, lets planners edit values inline, and surfaces alerts and order recommendations live. The bar is "feels like an operational prototype," not "enterprise SCM."

## What Changes

- Stand up a Flask backend with Supabase (Postgres) persistence and a static HTML/CSS/vanilla-JS frontend that polls every 5 s.
- Introduce a **per-branch** dimension throughout the data model — every MSKU is tracked across ~12 branch codes (TUP, CBE, ERD, CB2, TNV, SLM, MDU, VPM, TUT, DGL, PDY, NGL). The PRD did not anticipate this; the source CSV requires it.
- Define **two upload paths** to the same ingestion pipeline:
  1. **Clean CSV/XLSX template** — single header row, only the columns the system needs. Documented and downloadable from the upload page.
  2. **Legacy Excel importer** — accepts the existing messy `MSK_WORKING.csv` as-is (skips the ~26-row formula-annotation preamble, fuzzy-matches column names, exposed via a "Load sample data" button on the upload page for instant demo payoff).
- Implement the DDMRP calculation engine in Python as the **system of record** for planning math (`calculate_adu`, `calculate_red_zone`, `calculate_yellow_zone`, `calculate_green_zone`, `calculate_tog`, `calculate_net_flow`, `calculate_order_recommendation`, `calculate_alert_level`).
- Use a **hybrid ingest strategy**: when a file already contains pre-computed planning fields (as the legacy export does), store them in `source_calculated_*` columns AND recompute everything in Python; surface per-row diffs on the planning view as a confidence signal ("engine matches Excel to 0.01"). Recomputed values are authoritative.
- Treat aggregate rows like `TOT` as system-computed roll-ups, not stored input.
- Trigger recomputation on every upload, inline edit, and parameter change. For the demo, recompute the affected `(msku, branch)` rows synchronously inside the request.
- Provide HTML-driven pages for: Dashboard, Planning Table (inline-editable, color-coded, sortable, filterable), Stock Upload, SKU/Master Upload, Alerts, Upload History.
- Provide REST APIs: `POST /api/uploads/stock`, `POST /api/uploads/master`, `GET /api/dashboard`, `GET /api/planning`, `PUT /api/planning/{msku}/{branch}`, `GET /api/alerts`, `GET /api/uploads/history`.

## Capabilities

### New Capabilities

- `master-data`: MSKU master records, branch directory, and per-MSKU planning parameters (MOQ, DLT, LTF, VF, DOC, lead time). Loaded via a separate "master upload" path; required to exist before daily snapshots can be ingested for an MSKU.
- `daily-upload`: Ingest path for daily inventory snapshots. Supports both the clean template format and the legacy Excel-export format. Validates rows, previews acceptance/rejection counts, commits accepted rows to `inventory_snapshots`, and triggers downstream recompute.
- `planning-engine`: Pure-Python implementation of the DDMRP formulas. Computes ADU, Red/Yellow/Green zones, TOR, TOG, Net Flow, planning priority, and order recommendation per `(msku, branch)`. Persists results to `planning_snapshots`. When the source upload includes pre-computed fields, also surfaces a delta vs. the engine output.
- `alerts`: Derives Red / Yellow / Healthy alert levels from each planning snapshot, persists transitions as alert events, and exposes counts and listings to the dashboard and alerts page.
- `dashboard`: Aggregates KPIs (counts of red/yellow/healthy SKU-branch pairs, recent uploads, total order-recommendation value) for the homepage; consumed by the polling frontend.

### Modified Capabilities

<!-- None — this is a greenfield change; no existing specs to amend. -->

## Impact

- **New code**: Flask app skeleton (`app/`), Supabase schema migrations, DDMRP calculation engine (`app/calculations/ddmrp_engine.py`), upload validators and parsers (clean + legacy), repositories per table, REST routes, templated HTML pages and vanilla-JS clients.
- **New dependencies**: `flask`, `supabase`, `pandas`, `openpyxl`, `python-dotenv`. No microservices, no message bus, no ML.
- **External services**: a Supabase project (free tier is sufficient for the demo); auth is Supabase Auth in single-tenant demo mode.
- **Data**: the existing `01 MENS INNER - PILOT - CURRENT WORKING FILE 1(MSK_WORKING).csv` becomes the canonical demo seed loaded by the legacy importer.
- **Out of scope for this change**: multi-tenant RLS, role-based permissions, background workers, WebSockets, mobile views, historical reporting beyond the latest snapshot, sales-forecast modelling.
