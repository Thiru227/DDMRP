## MODIFIED Requirements

### Requirement: Upload history shows revoke action
The upload history page SHALL display a Revoke button for each committed upload job. Clicking Revoke SHALL call `DELETE /api/uploads/<job_id>` and remove the job and its snapshots. The backend DELETE endpoint already exists; this requirement covers the frontend wire-up.

#### Scenario: Revoke button visible on committed jobs
- **WHEN** admin navigates to upload history and a job has status `committed`
- **THEN** a Revoke button is visible on that row

#### Scenario: Revoke deletes snapshots
- **WHEN** admin clicks Revoke and confirms the dialog
- **THEN** the job row disappears from history and the associated planning/inventory snapshots are removed from the database

#### Scenario: Revoke not available on non-committed jobs
- **WHEN** a job has status `preview` or `rejected`
- **THEN** no Revoke button is shown
