## ADDED Requirements

### Requirement: Order recommendation creation
The system SHALL allow the Planning role to create an order recommendation for an MSKU via `POST /api/order-recs`. The order rec SHALL be assigned a slip number in format `OR-YYYY-NNN` (auto-incrementing). Initial status SHALL be `draft`. The order rec detail page SHALL display the MSKU's DDMRP buffer reference (TOR, TOY, TOG, NFP, plan_priority, OH, OO) alongside an editable quantity field.

#### Scenario: Create order rec
- **WHEN** planner posts `{msku_id, order_qty, notes}` to `POST /api/order-recs`
- **THEN** system creates a record with `status='draft'`, returns `{ok: true, id, slip_no}`

#### Scenario: Quantity validation
- **WHEN** planner enters a quantity below the MSKU's MOQ
- **THEN** the UI shows a warning hint "⚠ Below MOQ (N pcs)" but does NOT block saving

#### Scenario: Buffer reference visible on order rec page
- **WHEN** planner opens an order rec detail page
- **THEN** the right column shows the DDMRP zone bar with TOR/TOY/TOG markers and current NFP position

### Requirement: Order rec status lifecycle
An order rec SHALL move through statuses: `draft` → `sent_to_execution` → `rs_created`. Only the Planning role can transition `draft → sent_to_execution` via `POST /api/order-recs/<id>/send`. Only the Executor role can transition `sent_to_execution → rs_created` (when creating the RS). Once sent, the order rec SHALL be immutable (PATCH returns 400).

#### Scenario: Send to execution
- **WHEN** planner calls `POST /api/order-recs/<id>/send` on a draft order rec
- **THEN** status changes to `sent_to_execution`, `sent_at` is recorded, and the record becomes read-only

#### Scenario: Cannot edit after sending
- **WHEN** planner calls `PATCH /api/order-recs/<id>` on a non-draft order rec
- **THEN** system returns HTTP 400 with `{error: "Cannot edit after sending"}`

#### Scenario: Wrong role cannot send
- **WHEN** an executor or admin calls `POST /api/order-recs/<id>/send`
- **THEN** system returns HTTP 403
