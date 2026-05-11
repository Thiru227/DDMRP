## ADDED Requirements

### Requirement: Sales CSV upload
The system SHALL allow admin to upload a sales/stock CSV (`sales&stocks.csv` format) via the Sales Upload page. The file SHALL be parsed, previewed, and committed to `inventory_snapshots` as a separate upload job from the MSKU working file.

The sales CSV format has simpler headers than the MSKU working file: it contains branch-level 90-day sales and stock figures but not the full planning parameters. Missing planning parameters SHALL be taken from the existing `msku_master` record.

#### Scenario: Upload and preview sales CSV
- **WHEN** admin selects a sales CSV file and clicks Upload
- **THEN** `POST /api/uploads/sales` is called; a preview table shows parsed rows with MSKU display names and branch stocks; warnings are shown for unrecognised MSKUs

#### Scenario: Commit sales upload
- **WHEN** admin clicks Confirm after preview
- **THEN** `POST /api/uploads/<job_id>/commit` is called; inventory_snapshots are updated; planning_snapshots are recomputed for affected MSKU/branch combinations

#### Scenario: Sales upload in history
- **WHEN** admin navigates to upload history
- **THEN** the sales upload job appears with type `sales` in the format column

### Requirement: Inline data editing via upload replace
The system SHALL allow admin to "revoke" a prior upload from the history page and upload a replacement CSV, providing an inline data correction workflow.

#### Scenario: Revoke upload from history
- **WHEN** admin clicks the Revoke button on a committed upload job in history
- **THEN** `DELETE /api/uploads/<job_id>` is called; the job and its snapshots are deleted; the history row is removed; a success toast is shown
