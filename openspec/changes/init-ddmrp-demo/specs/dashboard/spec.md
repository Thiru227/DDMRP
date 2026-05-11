## ADDED Requirements

### Requirement: Dashboard endpoint returns aggregated planning state

`GET /api/dashboard` SHALL return a JSON object containing at minimum:

- `kpi.total_msku_branch_pairs`: total count of `(msku, branch)` pairs with at least one planning snapshot.
- `kpi.red_count`, `kpi.yellow_count`, `kpi.healthy_count`: counts based on the latest planning snapshot per pair.
- `kpi.total_order_recommendation`: sum of `order_recommendation` across the latest planning snapshot per pair.
- `recent_uploads`: the five most recent `upload_jobs` rows ordered by `uploaded_at` descending, each with `id`, `filename`, `format`, `uploaded_at`, `status`, `valid_rows`, `invalid_rows`.
- `latest_calculated_at`: the maximum `calculated_at` across all planning snapshots, or `null` if none.

The response MUST be served from a per-process cache with TTL of one second to avoid hammering Supabase under 5 s polling.

#### Scenario: Empty system returns zeroed KPIs
- **GIVEN** no inventory or planning data has been ingested
- **WHEN** a client calls `GET /api/dashboard`
- **THEN** every KPI count is `0`, `recent_uploads = []`, `latest_calculated_at = null`

#### Scenario: KPIs reflect current state after seed load
- **GIVEN** the legacy seed CSV has been committed
- **WHEN** a client calls `GET /api/dashboard`
- **THEN** `kpi.total_msku_branch_pairs == count of distinct (msku, branch) pairs in the seed`
- **AND** `kpi.red_count + kpi.yellow_count + kpi.healthy_count == kpi.total_msku_branch_pairs`

### Requirement: Frontend dashboard polls and updates without full reload

The dashboard HTML page SHALL fetch `/api/dashboard` on initial render and every five seconds thereafter using `setInterval`. The page MUST update the KPI cards, the recent uploads list, and the alert counts in place without reloading the document.

If the fetch fails for three consecutive attempts, the page SHALL display a non-blocking banner reading `"Live updates paused — retrying"` and continue polling at a 15-second interval until a successful response, after which it returns to 5-second polling.

#### Scenario: Polling continues after a transient failure
- **GIVEN** the dashboard page is open and `/api/dashboard` is reachable
- **WHEN** the API returns 500 once
- **THEN** the page continues polling and updates on the next successful response

#### Scenario: Three failures degrade polling and show banner
- **GIVEN** the dashboard page is open
- **WHEN** `/api/dashboard` returns 5xx three times in a row
- **THEN** the page shows the `"Live updates paused — retrying"` banner
- **AND** the polling interval is 15 seconds until the next success

### Requirement: Planning table renders inline-editable rows from `/api/planning`

`GET /api/planning` SHALL return the latest `planning_snapshots` joined with their `inventory_snapshots` and `msku_master` rows, with one entry per `(msku, branch)` pair. The response SHALL include `flagged_diff` (boolean) and the per-field engine-vs-source deltas described in the planning-engine spec.

The Planning page SHALL render every row with a colour cue corresponding to `alert_level` (red, yellow, green) and SHALL allow inline edits to: `moq, ltf, vf, doc, lead_time, dlt` (which PUT to `msku_master`) and `on_hand_qty, on_order_qty, qualified_demand_qty` (which PUT to the underlying `inventory_snapshots` row).

`PUT /api/planning/{msku_code}/{branch_code}` SHALL accept any subset of those nine fields, dispatch the writes to the correct underlying tables, trigger the appropriate scoped recompute (per Decision 5), and return the updated planning snapshot(s).

#### Scenario: Editing on-hand updates one row
- **WHEN** a planner submits `PUT /api/planning/ABC/TUP` with `{ "on_hand_qty": 50 }`
- **THEN** the response contains a single updated planning snapshot for `(ABC, TUP)` with recomputed zones, net flow, and alert level

#### Scenario: Editing a master parameter updates all branches of that MSKU
- **GIVEN** `(ABC, TUP)`, `(ABC, CBE)`, `(ABC, ERD)` exist
- **WHEN** a planner submits `PUT /api/planning/ABC/TUP` with `{ "ltf": 0.80 }`
- **THEN** the response contains three updated planning snapshots — one per branch of `ABC`
- **AND** the corresponding `msku_master` row reflects `ltf = 0.80`
