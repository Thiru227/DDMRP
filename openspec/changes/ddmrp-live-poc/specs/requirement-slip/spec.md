## ADDED Requirements

### Requirement: Requirement Slip auto-creation and numbering
The system SHALL auto-create a Requirement Slip when an order recommendation is submitted. The slip ID SHALL follow the format `RS-{YYYY}-{NNN}` where YYYY is the current calendar year and NNN is a zero-padded 3-digit sequence that increments per year, resetting to 001 each new year.

#### Scenario: RS number increments correctly
- **WHEN** the first order rec of 2026 is submitted
- **THEN** the created slip ID is `RS-2026-001`

#### Scenario: RS number increments on next submission
- **WHEN** a second order rec is submitted in the same year
- **THEN** the created slip ID is `RS-2026-002`

#### Scenario: Year rollover resets counter
- **WHEN** the first order rec of 2027 is submitted
- **THEN** the created slip ID is `RS-2027-001`

### Requirement: Executor inbox lists pending slips
The Executor inbox SHALL display all Requirement Slips with status `pending_release`, showing supplier name, MSKU display name, total qty, and submission date.

#### Scenario: Inbox populated from API
- **WHEN** executor navigates to Inbox
- **THEN** `GET /api/requirement-slips/?status=pending_release` is called and results render as inbox cards

#### Scenario: Empty inbox
- **WHEN** no pending slips exist
- **THEN** the inbox shows "No pending requirement slips" message

### Requirement: Executor reviews and releases requirement slip
The executor SHALL review a Requirement Slip showing: validation checks (MOQ, lead time, SKU balance, design split, budget, hub destination), supplier split summary, MRP band breakdown, and full SKU line items table with qty and value.

#### Scenario: Slip detail loads from API
- **WHEN** executor clicks a slip in the inbox
- **THEN** `GET /api/requirement-slips/<id>` is called and all sections populate

#### Scenario: Release requirement slip
- **WHEN** executor clicks "Release Requirement Slip" and confirms
- **THEN** `POST /api/requirement-slips/<id>/release` is called; slip status changes to `released`; slip moves out of inbox into the Released view; a success screen is shown

#### Scenario: Return to planner
- **WHEN** executor clicks "Return to Placement"
- **THEN** `POST /api/requirement-slips/<id>/return` is called; slip status reverts to `draft` on the planner side; the order rec is re-opened for editing

### Requirement: Released slips visible in Released tab
All released slips SHALL appear in the Executor's "Released" tab with their RS number, MSKU, supplier, qty, release date and time.

#### Scenario: Released list loads from API
- **WHEN** executor navigates to Released
- **THEN** `GET /api/requirement-slips/?status=released` is called and results render
