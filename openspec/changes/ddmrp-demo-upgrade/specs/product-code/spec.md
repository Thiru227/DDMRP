## ADDED Requirements

### Requirement: Product code is derived at upload time
The system SHALL derive a short hyphenated product code from the MSKU string during CSV upload and store it in the `mskus.product_code` column. The code SHALL follow the pattern `{CAT}-{TIER}-{OCC}-{STYLE}`.

Derivation rules:
- **CAT**: `MENS INNER WEAR` → `MI`; default → `GEN`
- **TIER**: `ECONOMIC` → `ECO`; `PREMIUM` → `PRM`; default → `STD`
- **OCC**: `ACTIVE WEAR` → `ACT`; `DAILY WEAR` → `DAI`; default → `GEN`
- **STYLE**: first two words between `SOLID` and `CLASSIC/POOMEX`, abbreviated (e.g. `GYM VEST` → `GV`, `BRIEFS` → `BR`, `TRUNK` → `TR`); default → `XX`

#### Scenario: Full MSKU string is parsed correctly
- **WHEN** the MSKU string `MENSINNER WEARECONOMICACTIVE WEAR INNER WEAR TOPSOLIDGYM VESTCLASSICPOOMEX` is uploaded
- **THEN** the derived `product_code` SHALL be `MI-ECO-ACT-GV`

#### Scenario: Premium MSKU string
- **WHEN** the MSKU string contains `PREMIUM` instead of `ECONOMIC`
- **THEN** the `product_code` tier segment SHALL be `PRM`

#### Scenario: Unrecognised MSKU string
- **WHEN** the MSKU string does not match any known segment patterns
- **THEN** the `product_code` SHALL fall back gracefully (e.g. `GEN-STD-GEN-XX`) and never be NULL or crash

### Requirement: Product code is displayed throughout the app
The system SHALL display `product_code` as a monospace badge alongside the product display name in: the Planner alert table, the Admin RS Tracker table, and the PO Tracking detail panel.

#### Scenario: Planner table shows product code badge
- **WHEN** the planner views the alert dashboard after a CSV upload
- **THEN** each MSKU row SHALL show the `product_code` value in a `.msku-code` styled badge below or beside the display name

#### Scenario: RS Tracker shows product code column
- **WHEN** the admin views the RS Tracker
- **THEN** the table SHALL include a Product Code column with the `product_code` value for each row
