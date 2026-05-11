## ADDED Requirements

### Requirement: Independent DDMRP variables are inline-editable in the planner table
The planner table SHALL allow inline editing of exactly these fields: `on_hand` (OH), `on_order` (OO), `dlt`, `ltf`, `vf`, `doc`, `moq`. All other fields are display-only.

#### Scenario: Planner edits On Hand value
- **WHEN** planner clicks an OH cell, changes the value, and presses Enter or tabs away
- **THEN** the system calls `PATCH /api/mskus/<id>` with `{on_hand: <value>}` and the row updates with recalculated derived fields

#### Scenario: Planner edits DLT (Decoupling Lead Time)
- **WHEN** planner changes the DLT cell value
- **THEN** the system recalculates Red zone, TOG, Plan Priority %, and Order Rec and flashes the updated cells in the same row

#### Scenario: Derived fields are not editable
- **WHEN** planner attempts to click ADU, NFP, Red, Yellow, Green, TOG, Plan Priority, or Order Rec cells
- **THEN** those cells SHALL not become inputs; they display the current computed value only

### Requirement: PATCH /api/mskus/<id> recalculates all derived DDMRP fields
The endpoint SHALL accept any subset of `{on_hand, on_order, dlt, ltf, vf, doc, moq}`, persist the changes, recompute all derived fields server-side, and return the full updated MSKU row.

Derived field formulas:
- `adu = sales_90d / 90`
- `red = adu * dlt * ltf`
- `yellow = adu * doc`
- `green = max(moq, yellow)`
- `tor = red + yellow`
- `toy = tor + yellow`
- `tog = tor + green`
- `nfp = on_hand + on_order`
- `plan_priority = (nfp / tog * 100) if tog > 0 else 0`
- `order_rec = ceil((tog - nfp) / moq) * moq if nfp < tor else 0`
- `status = pp_status(plan_priority)`

#### Scenario: Server returns full recalculated row
- **WHEN** `PATCH /api/mskus/3` is called with `{dlt: 12}`
- **THEN** the response SHALL include the updated `dlt` value AND recalculated `red`, `toy`, `tog`, `plan_priority`, `order_rec`, and `status`

#### Scenario: Invalid field values are rejected
- **WHEN** `PATCH /api/mskus/<id>` is called with a negative `moq` or `dlt`
- **THEN** the server SHALL return 400 with a descriptive error message

### Requirement: Allocation panel explains 100% constraint
The size/color allocation panel SHALL display a label: "Distribute 100% so all ordered units are assigned to variants" with a tooltip showing the formula: `variant % × total qty = units for that variant`.

#### Scenario: Allocation label is visible
- **WHEN** planner opens the order detail / allocation panel
- **THEN** the 100% label SHALL be visible above or adjacent to the size/color grid

#### Scenario: Tooltip explains the math
- **WHEN** planner hovers over the 100% label or its info icon
- **THEN** a tooltip SHALL appear explaining: "Example: 25% of 480 units = 120 pcs for that size"
