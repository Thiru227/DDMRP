## ADDED Requirements

### Requirement: Create order recommendation draft
The planner SHALL be able to create an order recommendation draft for any MSKU from the Alert Dashboard. Clicking "Create Order Rec" opens the Order Recommendation Draft screen pre-populated with DDMRP buffer data (OH, OO, NFP, TOR, TOG, calculated qty = TOG − NFP rounded up to MOQ).

#### Scenario: Create order rec from alert row
- **WHEN** planner clicks "Create Order Rec" on an MSKU row in the Alert Dashboard
- **THEN** `POST /api/order-recs/` is called with `msku_code`, system computes recommended qty and creates a draft; the Draft screen loads with pre-filled PO Details and DDMRP Buffer Reference panel

#### Scenario: Draft qty calculation
- **WHEN** the draft is created
- **THEN** `total_qty` = max(TOG − NFP, 0) rounded up to the nearest MOQ; if result <= 0, MOQ floor is applied and shown as a demo override

#### Scenario: Open Hub Allocation
- **WHEN** planner clicks "Open Hub Allocation →" on the draft screen
- **THEN** the 4-step hub allocation wizard opens for that order rec

### Requirement: 4-step hub allocation wizard
The system SHALL guide the planner through four sequential steps to split the total order quantity: (1) Supplier, (2) MRP Split, (3) Colour × Size, (4) Design. The system SHALL validate that quantities balance at each step before allowing progression.

#### Scenario: Step 1 — Supplier split
- **WHEN** planner is on the Supplier step
- **THEN** `GET /api/suppliers/?active=1` populates the supplier cards; planner enters qty per supplier; total must equal `total_qty` to proceed

#### Scenario: Step 2 — MRP Split
- **WHEN** planner proceeds to MRP Split
- **THEN** for each selected supplier the planner distributes that supplier's qty across MRP price bands (e.g., ₹131, ₹147, ₹167) as % or direct qty; sum must equal supplier qty

#### Scenario: Step 3 — Colour × Size matrix
- **WHEN** planner proceeds to Colour × Size
- **THEN** for each supplier+MRP-band combination, planner fills a colour × size matrix; each row total must match the MRP band qty

#### Scenario: Step 4 — Design split
- **WHEN** planner proceeds to Design
- **THEN** planner distributes total qty across design codes (DES01, DES02…) as % or direct qty; sum must equal total_qty

#### Scenario: Send to Executor
- **WHEN** design totals are balanced and planner clicks "Send to Execution →"
- **THEN** `POST /api/order-recs/<id>/submit` is called; the order rec status changes to `sent_to_executor`; a Requirement Slip is auto-created and appears in the Executor inbox

### Requirement: Order rec status display
The order recommendation status SHALL be displayed in the top-right corner of the draft screen as a badge.

#### Scenario: Status badge reflects state
- **WHEN** an order rec is in draft state
- **THEN** the badge shows "Draft — Not Submitted" in amber; after submission it shows "Sent to Executor" in teal
