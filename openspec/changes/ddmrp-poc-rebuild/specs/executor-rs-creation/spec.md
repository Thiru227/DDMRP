## ADDED Requirements

### Requirement: Executor inbox shows sent order recs
The system SHALL serve `GET /api/executor/inbox` returning all order recs with `status='sent_to_execution'`, including the MSKU display name, slip number, order quantity, and sent timestamp. Only the Executor role SHALL access this endpoint.

#### Scenario: Inbox populated after planner sends
- **WHEN** executor navigates to the inbox
- **THEN** one card per sent order rec is shown with: slip number, MSKU display name, order qty, sent_at timestamp, and a "Create Requirement Slip" button

#### Scenario: Empty inbox
- **WHEN** no order recs are in `sent_to_execution` status
- **THEN** inbox shows empty state: "No pending order recs — waiting for planner"

#### Scenario: Wrong role blocked
- **WHEN** a planner or admin calls `GET /api/executor/inbox`
- **THEN** system returns HTTP 403

### Requirement: Executor creates a requirement slip from an order rec
The system SHALL allow the Executor role to create a Requirement Slip (RS) by calling `POST /api/executor/order-recs/<id>/create-rs`. The RS SHALL be assigned a slip number in format `RS-YYYY-NNN` (auto-incrementing). RS lines SHALL be auto-generated server-side from `allocation_json` via `_gen_rs_lines()`. On success the order rec status transitions to `rs_created`.

#### Scenario: RS created with full allocation
- **WHEN** executor calls `POST /api/executor/order-recs/<id>/create-rs` and `allocation_json` is non-empty
- **THEN** system generates RS lines from `mrp_split × size_color × design_split`, inserts into `requirement_slips`, sets order rec `status='rs_created'`, and returns `{ok: true, rs_id, slip_no}`

#### Scenario: RS created with empty allocation (fallback)
- **WHEN** executor calls `POST /api/executor/order-recs/<id>/create-rs` and `allocation_json` is `{}`
- **THEN** system splits `order_qty` equally across all MRP bands from the MSKU's `mrp_bands` field and generates one RS line per band; remaining qty from integer rounding goes to the last band

#### Scenario: RS line structure
- **WHEN** an RS is created
- **THEN** `lines_json` is an array of objects: `[{mrp, size, colour, design, qty}, ...]`

#### Scenario: Cannot create RS for wrong status
- **WHEN** executor calls `POST /api/executor/order-recs/<id>/create-rs` on an order rec that is not `sent_to_execution`
- **THEN** system returns HTTP 400 with `{error: "Order rec not in sent_to_execution status"}`

#### Scenario: Executor views RS detail
- **WHEN** executor navigates to an RS detail page
- **THEN** lines_json is rendered as a table grouped by MRP band showing: size, colour, design, qty columns with subtotals per band

### Requirement: PO tracking view for executor
The system SHALL serve `GET /api/po-tracking` returning all requirement slips with their current status (`pending` or `released`). The executor UI SHALL render this as a kanban with two columns: "Pending" and "Released".

#### Scenario: Kanban renders all RS cards
- **WHEN** executor opens PO tracking
- **THEN** each RS appears as a card in the appropriate column showing: slip_no, linked order rec slip_no, MSKU display name, and line count

#### Scenario: Release RS
- **WHEN** executor calls `POST /api/rs/<id>/release`
- **THEN** RS status changes to `released` and `released_at` is recorded; card moves to Released column on next load
