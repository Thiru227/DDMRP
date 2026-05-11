## ADDED Requirements

### Requirement: PO Tracking kanban board
The system SHALL display a kanban board visible to all roles showing all Requirement Slips across five lifecycle columns: Pending Placement, Pending Executor, PO Released, In Transit, Received.

Column mapping to slip status:
- `draft` → Pending Placement
- `pending_release` → Pending Executor
- `released` → PO Released
- `in_transit` → In Transit
- `received` → Received

#### Scenario: Kanban loads from API
- **WHEN** any user navigates to PO Tracking
- **THEN** `GET /api/po-tracking/` is called and slips render in their respective columns

#### Scenario: Kanban card shows key info
- **WHEN** a slip card renders
- **THEN** it shows: RS number, MSKU display name, total qty, supplier name, and days since release (or ETA if in-transit)

### Requirement: Manual status progression for In Transit and Received
The executor SHALL be able to manually advance a released slip to "In Transit" or "Received" for the POC demo.

#### Scenario: Mark as In Transit
- **WHEN** executor clicks "Mark In Transit" on a PO Released card
- **THEN** `PATCH /api/requirement-slips/<id>` with `{status: "in_transit"}` is called and card moves column

#### Scenario: Mark as Received
- **WHEN** executor clicks "Mark Received" on an In Transit card
- **THEN** `PATCH /api/requirement-slips/<id>` with `{status: "received"}` is called and card moves column with "GRN done" badge

### Requirement: Calendar view toggle
The PO Tracking board SHALL offer a calendar view showing expected delivery dates.

#### Scenario: Switch to calendar view
- **WHEN** user clicks the Calendar toggle
- **THEN** the board switches to a month calendar; slips with ETAs appear as date events
