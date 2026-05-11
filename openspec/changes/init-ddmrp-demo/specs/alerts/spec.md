## ADDED Requirements

### Requirement: Alerts table records transitions between alert levels

The system SHALL maintain an `alerts` table containing one row per `(msku_code, branch_code)` transition into a non-healthy state (`red` or `yellow`). Each row carries: `id`, `msku_code`, `branch_code`, `alert_type` (= `alert_level` at transition), `severity` (`high` for red, `medium` for yellow), `message` (human-readable summary), `created_at`, `resolved` (boolean), `resolved_at` (nullable).

A new alert row SHALL be inserted ONLY when a recompute changes a pair's `alert_level` from `healthy` to `red` or `yellow`, OR from `yellow` to `red`. Returning to `healthy` SHALL mark all open (`resolved = false`) alerts for that `(msku, branch)` as `resolved = true` with `resolved_at` set, but SHALL NOT insert a new row.

A transition from `red` directly to `yellow` (improvement) SHALL resolve the open red alert and insert a new yellow alert.

#### Scenario: Healthy → red inserts an alert
- **GIVEN** the latest planning snapshot for `(ABC, TUP)` is healthy with no open alerts
- **WHEN** a recompute produces `alert_level = "red"` for that pair
- **THEN** a new `alerts` row is inserted with `alert_type = "red"`, `severity = "high"`, `resolved = false`

#### Scenario: Red → healthy resolves the alert
- **GIVEN** an open red alert exists for `(ABC, TUP)`
- **WHEN** a recompute produces `alert_level = "healthy"` for that pair
- **THEN** the existing alert row's `resolved` is `true` and `resolved_at` is set
- **AND** no new alert row is inserted

#### Scenario: Yellow → red resolves yellow and opens red
- **GIVEN** an open yellow alert exists for `(ABC, TUP)`
- **WHEN** a recompute produces `alert_level = "red"` for that pair
- **THEN** the yellow alert is resolved
- **AND** a new red alert is inserted

#### Scenario: Repeat at same level does not duplicate
- **GIVEN** an open red alert exists for `(ABC, TUP)`
- **WHEN** a recompute again produces `alert_level = "red"` for that pair
- **THEN** no new `alerts` row is inserted
- **AND** the existing alert remains open

### Requirement: Alert message text describes the operational state

Alert messages SHALL be deterministic strings with the following templates:

- Red: `"Net flow {net_flow:.1f} below red zone {red_zone:.1f} — order {order_recommendation:.0f}"`
- Yellow: `"Net flow {net_flow:.1f} in yellow band (red {red_zone:.1f}, toy {toy:.1f})"`

The message SHALL be written at the moment of transition using the current planning snapshot values.

#### Scenario: Red alert message includes recommendation
- **WHEN** a red alert is opened with `net_flow = 5, red_zone = 10.5, order_recommendation = 50`
- **THEN** `message == "Net flow 5.0 below red zone 10.5 — order 50"`

### Requirement: Alerts API exposes current and historical views

`GET /api/alerts` SHALL accept query params `status` (`open | resolved | all`, default `open`) and `severity` (`high | medium | all`, default `all`) and return a JSON array of alerts ordered by `created_at` descending.

`GET /api/alerts/summary` SHALL return aggregate counts for the dashboard: `red_count`, `yellow_count`, `healthy_count`. Counts MUST reflect the latest `planning_snapshots` per `(msku, branch)`, not the historical alerts table — i.e. a pair is counted once based on its current state.

#### Scenario: Default listing returns only open alerts
- **WHEN** a client calls `GET /api/alerts`
- **THEN** the response contains only rows with `resolved = false`

#### Scenario: Summary counts current state, not history
- **GIVEN** a pair `(ABC, TUP)` has had 3 historical red alerts and is currently healthy
- **WHEN** a client calls `GET /api/alerts/summary`
- **THEN** the pair contributes 1 to `healthy_count` and 0 to `red_count`
