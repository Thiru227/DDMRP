## ADDED Requirements

### Requirement: Planner action column reflects OR/RS lifecycle with 4 states
The planner alert table action column SHALL show one of four states per MSKU row based on the current Order Recommendation status. No "Requirement Slip" or executor-side terminology SHALL appear in the planner UI.

| OR state | Action column content |
|---|---|
| No OR exists | Button: "Create Order Recommendation Draft" |
| OR = `draft` | Button: "Continue Draft" |
| OR = `sent_to_execution` | Green badge: "Sent to Executor" (no button, no action) |
| OR = `rs_created` | Green badge: "RS Created ✓" (no button, no action) |

#### Scenario: No OR exists — Create Draft button shown
- **WHEN** the planner views a MSKU row that has no associated Order Recommendation
- **THEN** the action column SHALL show a "Create Order Recommendation Draft" button

#### Scenario: OR in draft — Continue Draft button shown
- **WHEN** the planner views a MSKU row whose OR has status `draft`
- **THEN** the action column SHALL show a "Continue Draft" button that opens the same OR detail panel

#### Scenario: OR sent to executor — informational badge shown
- **WHEN** an OR has been sent to the executor (status `sent_to_execution`)
- **THEN** the action column SHALL show a non-interactive amber/neutral badge "Sent to Executor" with no button

#### Scenario: RS created by executor — green notification badge shown
- **WHEN** the executor has created the Requirement Slip (OR status `rs_created`)
- **THEN** the action column SHALL show a green badge "RS Created ✓" with no button; this is informational only

### Requirement: OR slip codes are sequential
Order Recommendation slip codes SHALL follow the format `OR-{YYYY}-{NNN}` (zero-padded 3 digits) matching the RS slip code convention.

#### Scenario: First OR of the year
- **WHEN** the first Order Recommendation of 2025 is created
- **THEN** its `slip_no` SHALL be `OR-2025-001`

#### Scenario: Subsequent ORs increment
- **WHEN** three ORs exist and a fourth is created
- **THEN** the new `slip_no` SHALL be `OR-2025-004`
