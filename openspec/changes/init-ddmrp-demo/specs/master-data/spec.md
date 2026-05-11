## ADDED Requirements

### Requirement: Branch directory holds the canonical set of branch codes

The system SHALL maintain a `branches` table containing the canonical branch codes used throughout planning. The seed set MUST include the twelve codes observed in the source workbook: `TUP`, `CBE`, `ERD`, `CB2`, `TNV`, `SLM`, `MDU`, `VPM`, `TUT`, `DGL`, `PDY`, `NGL`. Each branch row carries `branch_code` (primary key), an optional `display_name`, and an `active` flag.

The synthetic aggregate code `TOT` MUST NOT be stored as a branch.

#### Scenario: Seed data loads the twelve canonical branches
- **WHEN** the database is initialised from the migration scripts
- **THEN** the `branches` table contains exactly the twelve canonical codes, each with `active = true`

#### Scenario: TOT is rejected as a branch code
- **WHEN** an administrator attempts to insert a `branches` row with `branch_code = 'TOT'`
- **THEN** the insert SHALL fail with a check-constraint violation

### Requirement: MSKU master holds product identity and planning parameters

The system SHALL maintain an `msku_master` table keyed by `msku_code` (primary key). Each row carries: descriptive fields (`product_classification`, `style`, `fit`, `brand`, `season`, `price_range`, `size`, `mrp`), planning parameters (`moq`, `lead_time`, `dlt`, `ltf`, `vf`, `doc`), and an `active` flag.

Planning parameters MUST satisfy: `moq >= 0`, `lead_time >= 0`, `dlt >= 0`, `0 <= ltf <= 1`, `0 <= vf <= 1`, `doc > 0`. Rows violating these bounds MUST be rejected at write time.

#### Scenario: A valid MSKU is upserted via the master upload path
- **WHEN** a master upload contains a row `msku_code = "ABC", moq = 120, dlt = 10, ltf = 0.75, vf = 0.25, doc = 7`
- **THEN** an `msku_master` row with those values exists after commit, with `active = true`

#### Scenario: Out-of-range parameters are rejected
- **WHEN** a master upload contains a row with `ltf = 1.5`
- **THEN** the row is reported as invalid in the validation preview and is not committed

### Requirement: Editing a master parameter triggers downstream recompute

The system SHALL recompute the `planning_snapshots` for every `(msku_code, branch_code)` pair belonging to an MSKU whenever any of `moq, lead_time, dlt, ltf, vf, doc` is updated on that MSKU's master record.

The recompute MUST complete within the same HTTP request that performed the edit and the response MUST include the resulting planning snapshots.

#### Scenario: Updating LTF cascades to all branches of that MSKU
- **GIVEN** MSKU `ABC` has `inventory_snapshots` rows for branches `TUP`, `CBE`, and `ERD`
- **WHEN** a planner sets `ltf = 0.80` (was `0.75`) on `msku_master[ABC]`
- **THEN** the response contains three updated planning snapshots — one for each of `(ABC, TUP)`, `(ABC, CBE)`, `(ABC, ERD)` — with red zones reflecting the new LTF

### Requirement: MSKU master is required before daily snapshots can be ingested via the clean template

The system SHALL reject any clean-template daily-upload row whose `msku_code` does not already exist in `msku_master`. The rejection MUST surface the offending `msku_code` in the validation preview.

The legacy-Excel upload path is exempt from this requirement and SHALL upsert master records on the fly from columns present in the legacy file (`MASTER SKU`, `MOQ`, `LEAD TIME`, `LTF`, `VF`, `DOC`, `DLT`, etc.).

#### Scenario: Clean template rejects unknown MSKUs
- **GIVEN** `msku_master` does not contain `msku_code = "XYZ"`
- **WHEN** a clean-template upload includes a row with `msku_code = "XYZ"`
- **THEN** the validation preview reports the row as invalid with reason `unknown msku_code: XYZ`
- **AND** the row is not committed even if the user proceeds with import

#### Scenario: Legacy upload upserts master records
- **GIVEN** `msku_master` does not contain `msku_code = "XYZ"`
- **WHEN** the legacy importer commits a file containing `MASTER SKU = "XYZ", MOQ = 120, LTF = 0.75, VF = 0.25, DOC = 7, DLT = 10, LEAD TIME = 10`
- **THEN** an `msku_master[XYZ]` row exists after commit with those parameter values
