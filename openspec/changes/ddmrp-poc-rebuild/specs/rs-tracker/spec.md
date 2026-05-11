## ADDED Requirements

### Requirement: Admin RS tracker shows all requirement slips
The system SHALL serve `GET /api/rs` returning all requirement slips with their linked order rec slip number, MSKU display name, line count, status, and timestamps. The Admin role SHALL see this as a read-only tracker table on the admin dashboard. Planners and executors SHALL NOT access this endpoint (HTTP 403).

#### Scenario: Admin views RS tracker with data
- **WHEN** admin navigates to the RS tracker tab
- **THEN** a table renders one row per RS with columns: RS slip_no, linked OR slip_no, MSKU display name, line count, status badge, created_at, released_at

#### Scenario: Status badge on RS tracker
- **WHEN** an RS has `status='pending'`
- **THEN** its row shows an amber "Pending" badge
- **WHEN** an RS has `status='released'`
- **THEN** its row shows a teal "Released" badge

#### Scenario: Empty RS tracker
- **WHEN** no requirement slips exist
- **THEN** tracker shows empty state: "No requirement slips yet"

#### Scenario: Tracker refreshes from DB on every load
- **WHEN** admin opens or revisits the RS tracker tab
- **THEN** `GET /api/rs` is called fresh — no client-side cache; new RSes created since last load are visible

#### Scenario: Non-admin access blocked
- **WHEN** a planner or executor calls `GET /api/rs`
- **THEN** system returns HTTP 403

### Requirement: Admin can view RS line detail
The system SHALL serve `GET /api/rs/<id>` returning the full RS record including `lines_json`. The admin tracker SHALL link each RS row to a read-only detail view showing the line breakdown.

#### Scenario: Admin views RS line detail
- **WHEN** admin clicks on an RS row in the tracker
- **THEN** a detail panel or modal shows lines_json rendered as a table: MRP band, size, colour, design, qty; with a grand total row
