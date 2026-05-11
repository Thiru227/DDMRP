## ADDED Requirements

### Requirement: Admin upload page has two distinct upload zones
The admin upload page SHALL present two separate upload cards — one for MSKU (branch-level) CSV and one for Sales & Stocks (hub-level) CSV — each with its own file input, upload button, format label, and success/error feedback.

#### Scenario: Admin uploads MSKU CSV successfully
- **WHEN** admin selects the branch-level CSV ("01 MENS INNER…") in the MSKU upload card and clicks Upload
- **THEN** the system calls `POST /api/upload` with `type=msku`, parses using `_parse_branch()`, stores rows in `mskus`, and shows a success toast with the row count

#### Scenario: Admin uploads Sales & Stocks CSV successfully
- **WHEN** admin selects the hub-level CSV ("sales&stocks.csv") in the Sales & Stocks card and clicks Upload
- **THEN** the system calls `POST /api/upload` with `type=sales`, parses using `_parse_hub()`, stores rows in `mskus`, and shows a success toast with the row count

#### Scenario: Wrong CSV uploaded to wrong zone
- **WHEN** admin uploads a hub-format CSV into the MSKU upload zone
- **THEN** if `_auto_fmt()` detects the mismatch, the system SHALL show an error; otherwise the `type` hint forces the correct parser

#### Scenario: Upload history shows format label
- **WHEN** admin views the upload history table
- **THEN** each row SHALL display a format badge ("MSKU" or "Sales & Stocks") not the raw internal format key
