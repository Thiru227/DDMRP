## ADDED Requirements

### Requirement: Admin uploads MSKU master CSV
The system SHALL accept a CSV file upload from the Admin role and parse it into the `mskus` table. The system SHALL auto-detect whether the file is hub-level format (`sales&stocks.csv` style) or branch-level format (`01 MENS INNER…` style) based on header content, with no format selection required from the user.

#### Scenario: Hub-level CSV upload succeeds
- **WHEN** admin uploads a file whose first row contains "MASTER SKU CODE" in column 0
- **THEN** system parses one MSKU record per data row (skipping blank rows), upserts into `mskus`, and returns `{ok: true, count: N, format: "hub"}`

#### Scenario: Branch-level CSV upload succeeds
- **WHEN** admin uploads a file where any of the first 5 rows contains "S.NO" in column 0
- **THEN** system groups rows by MSKU code, sums 90-day sales and OH across all branches, recomputes ADU/NFP/plan_priority/order_rec, and upserts one record per unique MSKU into `mskus`

#### Scenario: Upload preserves existing sizes and MRP bands
- **WHEN** admin uploads a hub-level file (which has no sizes/MRP band columns) for an MSKU that already has sizes from a previous branch-level upload
- **THEN** the existing `sizes`, `mrp_bands`, `moq`, and `lead_time` fields are preserved; only DDMRP calculation fields are updated

#### Scenario: Empty or unparseable file
- **WHEN** admin uploads a file that yields zero parsed records
- **THEN** system returns HTTP 400 with `{error: "No data parsed — check file format"}`

### Requirement: Upload log with revoke
The system SHALL record every upload in `upload_logs` with filename, type, row count, timestamp, and uploading user. The Admin SHALL be able to revoke an upload (marking it as `revoked=1` in the log). Revoking a log entry does NOT delete the MSKU data — it is an audit action only.

#### Scenario: Upload log entry created
- **WHEN** a CSV upload succeeds
- **THEN** a row appears in `upload_logs` with `revoked=0` and the correct `uploaded_by` username

#### Scenario: Admin revokes an upload
- **WHEN** admin calls `POST /api/uploads/<id>/revoke`
- **THEN** `upload_logs.revoked` is set to 1 and `revoked_at` timestamp is recorded

#### Scenario: Upload log visible to admin only
- **WHEN** a non-admin role calls `GET /api/uploads`
- **THEN** system returns HTTP 403
