## ADDED Requirements

### Requirement: Engine implements DDMRP formulas exactly as specified

The system SHALL implement the following formulas as pure functions in `app/calculations/ddmrp_engine.py`. The functions MUST take primitive inputs (numbers and dicts/dataclasses) and return primitive outputs; they MUST NOT perform any I/O.

| Output | Formula |
|---|---|
| `adu` | `sales_90d / adu_days` (where `adu_days > 0`) |
| `red_base` | `adu * dlt * ltf` |
| `red_safety` | `red_base * vf` |
| `red_zone` | `red_base + red_safety` |
| `yellow_zone` | `adu * dlt` (matches the source workbook; the PRD's `adu * doc` formula does not match the Excel TOY values and is overridden) |
| `green_zone` | `max(adu * dlt * ltf, adu * doc, moq)` (Excel uses these three — `adu * dlt` is shown as a step but is excluded from the GREEN max) |
| `tor` | `red_zone` |
| `toy` | `red_zone + yellow_zone` |
| `tog` | `red_zone + yellow_zone + green_zone` |
| `net_flow` | `(on_hand_qty + on_order_qty) - qualified_demand_qty` |
| `planning_priority` | `net_flow / tog` (zero if `tog == 0`) |
| `order_recommendation` | `(tog - net_flow)` when `net_flow <= toy`, else `0`. Always clamped to `>= 0`. |

When `adu_days == 0` or `tog == 0`, the engine MUST return `adu = 0` (or proceed with `tog = 0`) and produce zero zones, zero recommendation, `planning_priority = 0`, and `alert_level = "healthy"` rather than raising. Division-by-zero MUST never escape the engine.

#### Scenario: ADU computed from sales over actual day count
- **GIVEN** inputs `sales_90d = 90, adu_days = 90`
- **WHEN** the engine runs
- **THEN** `adu == 1.0`

#### Scenario: ADU honours per-row adu_days when not equal to 90
- **GIVEN** inputs `sales_90d = 89, adu_days = 89`
- **WHEN** the engine runs
- **THEN** `adu == 1.0` (not `89/90`)

#### Scenario: All zeros do not raise
- **GIVEN** inputs `sales_90d = 0, adu_days = 0, on_hand_qty = 0, on_order_qty = 0, qualified_demand_qty = 0`
- **WHEN** the engine runs
- **THEN** every output is `0` and `alert_level == "healthy"`

#### Scenario: Order recommendation is zero when net flow is healthy
- **GIVEN** inputs producing `net_flow > toy`
- **WHEN** the engine runs
- **THEN** `order_recommendation == 0`

#### Scenario: Order recommendation fills the gap to TOG when in yellow or red
- **GIVEN** inputs producing `net_flow <= toy` and `tog > net_flow`
- **WHEN** the engine runs
- **THEN** `order_recommendation == tog - net_flow`

### Requirement: Alert level is derived from net flow versus zone thresholds

The system SHALL derive `alert_level` per `(msku, branch)` according to:

- `alert_level == "red"` when `net_flow < red_zone`
- `alert_level == "yellow"` when `red_zone <= net_flow < toy`
- `alert_level == "healthy"` when `net_flow >= toy`

#### Scenario: Below red triggers red
- **GIVEN** `net_flow = 5, red_zone = 10, yellow_zone = 5`
- **THEN** `alert_level == "red"`

#### Scenario: Inside yellow band triggers yellow
- **GIVEN** `net_flow = 12, red_zone = 10, yellow_zone = 5` (toy = 15)
- **THEN** `alert_level == "yellow"`

#### Scenario: At or above toy is healthy
- **GIVEN** `net_flow = 15, red_zone = 10, yellow_zone = 5`
- **THEN** `alert_level == "healthy"`

### Requirement: Engine output is persisted to `planning_snapshots`

The system SHALL persist every engine result to `planning_snapshots` keyed `(msku_code, branch_code, snapshot_date)`. Each row carries: `adu`, `red_zone`, `yellow_zone`, `green_zone`, `tog`, `net_flow`, `planning_priority`, `order_recommendation`, `alert_level`, `calculated_at`.

The persistence layer MUST upsert on conflict by `(msku_code, branch_code, snapshot_date)`.

#### Scenario: Recompute replaces an existing snapshot
- **GIVEN** a `planning_snapshots` row exists for `(ABC, TUP, 2026-05-06)` with `alert_level = "yellow"`
- **WHEN** a parameter edit causes a recompute that produces `alert_level = "red"` for the same pair and date
- **THEN** the row is updated in place; no duplicate is created

### Requirement: Engine vs. source diff is computed and exposed when source values are present

When an `inventory_snapshots` row carries any `source_*` columns (populated by the legacy upload path), the system SHALL compute and persist `engine_minus_source_*` deltas alongside the planning snapshot. The deltas SHALL be exposed via `GET /api/planning` for use as a UI confidence indicator.

The system SHALL flag a planning row whose absolute delta on any of `adu, red, yellow, green, tog, net_flow, order_recommendation` exceeds tolerance: `0.5` for integer-typed fields (`order_recommendation`), `0.05` for decimal-typed fields (`adu`, others). The flag is purely informational; the engine value remains authoritative for downstream alerts and recommendations.

#### Scenario: Diff within tolerance is not flagged
- **GIVEN** engine `adu = 1.23` and source `source_adu = 1.23`
- **THEN** the planning row's `engine_minus_source_adu = 0.0` and the row is not flagged

#### Scenario: Diff above tolerance is flagged
- **GIVEN** engine `order_recommendation = 50` and source `source_order_recommendation = 60`
- **THEN** the planning row is flagged with reason `engine vs source order_recommendation diff = -10`

### Requirement: Recompute is scoped to affected `(msku, branch)` pairs

When a single `(msku, branch)` row's input changes (inline edit of OH / OO / QD), the system SHALL recompute only that pair. When a master parameter changes for an MSKU, the system SHALL recompute every `(msku, branch)` pair belonging to that MSKU. When an upload commits N pairs, the system SHALL recompute exactly those N pairs.

The system SHALL NOT recompute the entire dataset on any single user action.

#### Scenario: Editing one row recomputes one row
- **GIVEN** 30 `(msku, branch)` pairs exist
- **WHEN** a planner edits the `on_hand_qty` of one row
- **THEN** exactly one `planning_snapshots` row is recomputed
