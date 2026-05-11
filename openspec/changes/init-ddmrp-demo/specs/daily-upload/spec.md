## ADDED Requirements

### Requirement: System exposes two upload entry points sharing one ingestion pipeline

The system SHALL expose `POST /api/uploads/stock` accepting a multipart-uploaded `.csv` or `.xlsx` file and a required `format` field with values `clean` or `legacy`.

Both formats MUST flow through the same pipeline: `parse → validate → preview → commit → recompute`. The two formats differ only in the parser invoked at the parse stage.

The endpoint MUST return a JSON `upload_job` resource describing the parsed-and-validated state of the file, including counts of total / accepted / rejected rows and a list of rejection reasons.

#### Scenario: A clean-template upload is accepted
- **WHEN** a planner POSTs a 50-row CSV with `format=clean` and a valid header
- **THEN** the response is `200 OK` with a job containing `total_rows = 50`, `valid_rows >= 0`, `invalid_rows >= 0`, and `status = "preview"`

#### Scenario: A legacy upload of the seed file is accepted
- **WHEN** a planner POSTs `01 MENS INNER - PILOT - CURRENT WORKING FILE 1(MSK_WORKING).csv` with `format=legacy`
- **THEN** the response is `200 OK` with a job containing the count of operational rows after the preamble is skipped, `TOT` rows are dropped, and blank rows are ignored

### Requirement: Clean-template parser enforces a strict single-row header

The clean-template parser SHALL accept CSV/XLSX files whose first non-empty row contains exactly the column names listed below. Required: `msku_code, branch_code, snapshot_date, on_hand_qty, on_order_qty, qualified_demand_qty, sales_90d, adu_days`. Optional: `source_adu, source_red, source_yellow, source_green, source_tog, source_net_flow, source_order_recommendation`.

A missing required column MUST cause the upload to fail with a 400 response listing the missing names. Unknown extra columns MUST be ignored with a warning in the response.

The system MUST provide a downloadable empty template at `GET /api/uploads/template` containing exactly these columns in this order.

#### Scenario: Missing required column fails fast
- **WHEN** a clean upload's header omits `branch_code`
- **THEN** the response is `400 Bad Request` with body listing `branch_code` as a missing required column
- **AND** no rows are inserted

#### Scenario: Extra unknown columns are ignored with warnings
- **WHEN** a clean upload includes the required columns plus an extra column `notes`
- **THEN** the response is `200 OK` and the response warnings contain `unknown column: notes`

### Requirement: Legacy parser tolerates the existing Excel-export format

The legacy parser SHALL skip every leading row until it finds a row whose first non-empty cell equals `S.NO` (case-insensitive). It SHALL treat that row as the header and read every subsequent non-empty row as data.

The parser SHALL fuzzy-map source columns to canonical names with the following minimum mapping (case-insensitive, whitespace-collapsed):

| Source label | Canonical field |
|---|---|
| `MASTER SKU` | `msku_code` |
| `BRANCH` | `branch_code` |
| `90 DAY SAL`, `90 DAYS SALES` | `sales_90d` |
| `ADU DAYS` | `adu_days` |
| `ON HAND` | `on_hand_qty` |
| `ON ORDER` | `on_order_qty` |
| `QUALIFIED DEMAND` | `qualified_demand_qty` |
| `MOQ` | `moq` (master) |
| `LEAD TIME` | `lead_time` (master) |
| `LTF` | `ltf` (master) |
| `VF` | `vf` (master) |
| `DOC` | `doc` (master) |
| `DLT` | `dlt` (master) |
| `ADU` | `source_adu` |
| `RED` | `source_red` |
| `YELLOW` | `source_yellow` |
| `GREEN` | `source_green` |
| `TOG` | `source_tog` |
| `NET FLOW` | `source_net_flow` |
| `ORDER RECOM` | `source_order_recommendation` |

Rows whose `BRANCH` cell equals `TOT` (case-insensitive) MUST be dropped silently. Rows whose `MASTER SKU` is empty MUST be dropped silently. Rows whose `BRANCH` is not present in the `branches` table MUST be reported as invalid.

If `snapshot_date` is not present in the legacy file, the parser SHALL use the upload timestamp's date.

#### Scenario: Preamble is skipped
- **WHEN** the legacy parser is given a file with twenty-six leading annotation rows followed by an `S.NO,...` header
- **THEN** the data rows read by the parser begin after the `S.NO` row

#### Scenario: TOT rows are dropped
- **WHEN** the legacy parser encounters a row with `BRANCH = TOT`
- **THEN** that row is excluded from `total_rows` and from the committed snapshots

#### Scenario: Unknown branch is rejected
- **WHEN** the legacy parser encounters a row with `BRANCH = "XYZ"` not present in `branches`
- **THEN** the row is reported as invalid with reason `unknown branch_code: XYZ`

### Requirement: Validation rules apply uniformly after parsing

After parsing, every candidate row MUST be validated against the following rules. A row failing any rule is reported in the preview and is not committed:

- All required fields present and non-null after parsing.
- `on_hand_qty >= 0`, `on_order_qty >= 0`, `qualified_demand_qty >= 0`, `sales_90d >= 0`.
- `adu_days > 0` (zero would cause division-by-zero in the engine).
- `snapshot_date` parses as a valid ISO date and is not in the future.
- `(msku_code, branch_code, snapshot_date)` is unique within the same upload (later occurrences are rejected as duplicates).
- `msku_code` exists in `msku_master` (for the clean format only; legacy upserts it).
- `branch_code` exists in `branches`.

Empty rows (all source fields blank) MUST be ignored without contributing to either `valid_rows` or `invalid_rows`.

#### Scenario: Negative quantity is rejected
- **WHEN** an upload contains `on_hand_qty = -5`
- **THEN** the row appears in the preview with reason `on_hand_qty must be >= 0`

#### Scenario: Within-file duplicate is rejected
- **WHEN** an upload contains two rows with the same `(msku_code, branch_code, snapshot_date)`
- **THEN** the first row is accepted and the second is rejected with reason `duplicate (msku, branch, date) within upload`

#### Scenario: adu_days = 0 is rejected
- **WHEN** an upload contains `adu_days = 0`
- **THEN** the row is rejected with reason `adu_days must be > 0`

### Requirement: Preview must be confirmed before commit

The system SHALL hold the parsed-and-validated rows in the `upload_jobs` record with `status = "preview"` until the planner POSTs `POST /api/uploads/{job_id}/commit`. Only on commit are accepted rows written to `inventory_snapshots`.

A preview SHALL expire and be eligible for cleanup after 24 hours.

If the same `(msku_code, branch_code, snapshot_date)` already exists in `inventory_snapshots`, the commit MUST upsert (overwrite) the existing row.

#### Scenario: Preview is not committed automatically
- **WHEN** an upload returns a preview with `valid_rows = 50`
- **THEN** `inventory_snapshots` is unchanged until `POST /api/uploads/{job_id}/commit` is called

#### Scenario: Commit upserts on conflict
- **GIVEN** `inventory_snapshots` contains a row for `(ABC, TUP, 2026-05-06)` with `on_hand_qty = 40`
- **WHEN** an upload commits a row for `(ABC, TUP, 2026-05-06)` with `on_hand_qty = 45`
- **THEN** after commit the existing row's `on_hand_qty` equals `45`

### Requirement: Commit triggers planning recompute for all affected `(msku, branch)` rows

After commit, the system SHALL invoke the planning engine for every distinct `(msku_code, branch_code)` pair touched by the upload, write the results to `planning_snapshots`, and re-evaluate alerts. The commit response MUST include the count of recomputed snapshots.

The recompute MUST complete within the same HTTP request as the commit.

#### Scenario: Recompute count matches committed pairs
- **WHEN** a commit accepts rows touching 30 distinct `(msku, branch)` pairs
- **THEN** the response reports `recomputed_planning_snapshots = 30`

### Requirement: Upload history is recorded

Every upload (whether eventually committed or not) SHALL produce an `upload_jobs` row recording: `id`, `filename`, `format` (`clean` or `legacy`), `uploaded_at`, `total_rows`, `valid_rows`, `invalid_rows`, `committed_at` (nullable), `status` (`preview | committed | rejected | expired`).

`GET /api/uploads/history` SHALL return upload jobs ordered by `uploaded_at` descending.

#### Scenario: A rejected upload still appears in history
- **WHEN** an upload fails parsing because its header is malformed
- **THEN** an `upload_jobs` row exists with `status = "rejected"`, `valid_rows = 0`, `invalid_rows = total_rows`
