## ADDED Requirements

### Requirement: Real-time MSKU alert table
The system SHALL serve the planner alert dashboard from `GET /api/mskus`, returning all MSKUs sorted by `plan_priority` ascending (most urgent first). The response SHALL include a computed `status` field: `red` (pp < 0), `yellow` (0 ≤ pp < 50), `green` (50 ≤ pp < 100), `blue` (pp ≥ 100). The UI SHALL contain zero hardcoded MSKU data — if the table is empty, it SHALL show an empty state prompting admin to upload data.

#### Scenario: Planner loads alert dashboard with data
- **WHEN** planner navigates to the alert dashboard and MSKUs exist in the DB
- **THEN** the table renders one row per MSKU with columns: MSKU display name, OH, OO, NFP, TOR, TOG, Plan Priority %, Order Rec qty, Status badge, and an action button

#### Scenario: Empty state when no data uploaded
- **WHEN** planner loads the dashboard and `mskus` table is empty
- **THEN** the table shows an empty-state message: "No data yet — ask Admin to upload MSKUs"

#### Scenario: Status badge reflects plan priority
- **WHEN** an MSKU has plan_priority < 0
- **THEN** its row has a red "🔴 Order Now" badge and `row-red` CSS class
- **WHEN** an MSKU has 0 ≤ plan_priority < 50
- **THEN** its row has an amber "🟡 Order Soon" badge and `row-yellow` CSS class
- **WHEN** an MSKU has plan_priority ≥ 100
- **THEN** its row has a blue "🔵 Overstock" badge and `row-blue` CSS class

### Requirement: Filter bar narrows table
The planner dashboard SHALL include a filter bar with dropdowns populated from actual MSKU data (no hardcoded options). Selecting a filter value SHALL narrow the visible table rows client-side without a server round-trip. A "Reset filters" control SHALL restore all rows.

#### Scenario: Filter by product keyword
- **WHEN** planner selects a value in any filter dropdown
- **THEN** only MSKU rows matching that filter are visible; the count badge updates accordingly

#### Scenario: Reset filters
- **WHEN** planner clicks "Reset filters"
- **THEN** all rows are shown and all dropdowns return to "All"

### Requirement: Action buttons per MSKU status
Each MSKU row SHALL show context-appropriate action buttons:
- If MSKU has `order_rec > 0` and no existing draft order rec: show "Create Order Rec" button (ruby/red)
- If a draft order rec exists for this MSKU: show "Continue Draft" button
- If order rec sent to execution: show "Track" button
- Otherwise: show "View" button

#### Scenario: Create Order Rec from alert row
- **WHEN** planner clicks "Create Order Rec" on a red/yellow MSKU
- **THEN** an order rec is created via `POST /api/order-recs` and planner is navigated to the order rec detail page
