## ADDED Requirements

### Requirement: 3-step hub allocation wizard
The order rec detail page SHALL include an embedded 3-step wizard for allocating the order quantity. Steps: (1) MRP Split, (2) Size × Colour Matrix, (3) Design Split. The wizard SHALL be accessible from the order rec page via a tab or section, and completing it SHALL save `allocation_json` to the order rec via `PATCH /api/order-recs/<id>`. The "Send to Execution" CTA SHALL only appear after Step 3.

#### Scenario: Wizard renders MRP bands from MSKU data
- **WHEN** planner opens the hub allocation wizard for an MSKU with mrp_bands `["131", "147", "167"]`
- **THEN** Step 1 shows three rows — one per MRP value — each with a percentage input; the total percentage is shown live

#### Scenario: MRP split percentage validation
- **WHEN** planner enters MRP percentages that do not sum to 100
- **THEN** a warning is shown and the "Next" button is disabled

#### Scenario: Size × Colour matrix renders actual MSKU sizes
- **WHEN** planner advances to Step 2
- **THEN** a matrix is rendered with MSKU sizes (e.g., 80, 85, 90, 95) as columns and standard colours (White, Black, Navy, Grey) as rows; each cell is an editable integer quantity input

#### Scenario: Matrix column totals update live
- **WHEN** planner edits any cell in the size × colour matrix
- **THEN** column totals and row totals update immediately without server round-trip

#### Scenario: Design split in Step 3
- **WHEN** planner advances to Step 3
- **THEN** two design rows are shown (DES01 — Solid Plain, DES02 — Pattern) each with a percentage input defaulting to 60% and 40%

#### Scenario: Allocation saved on completing wizard
- **WHEN** planner completes all three steps and clicks "Send to Execution"
- **THEN** `PATCH /api/order-recs/<id>` is called with `{allocation: {mrp_split, size_color, design_split}}` followed by `POST /api/order-recs/<id>/send`; on success, planner sees a confirmation and the order rec disappears from the draft list

### Requirement: Allocation is optional for demo flow
If the planner skips the wizard and sends without completing allocation, the system SHALL still accept the send. The executor's RS creation SHALL fall back to equal MRP band split if `allocation_json` is empty `{}`.

#### Scenario: Skip wizard, send directly
- **WHEN** planner calls `POST /api/order-recs/<id>/send` without setting allocation
- **THEN** order rec transitions to `sent_to_execution` with `allocation_json = '{}'`

#### Scenario: RS fallback with no allocation
- **WHEN** executor creates RS for an order rec with empty allocation
- **THEN** RS lines are generated as equal split across all MRP bands from the MSKU's `mrp_bands` field
