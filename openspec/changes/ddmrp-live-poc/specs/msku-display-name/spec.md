## ADDED Requirements

### Requirement: Display name extraction at parse time
The legacy parser SHALL extract a human-readable `display_name` and a short hyphenated `short_code` from the concatenated MSKU classification string when parsing the MSKU working CSV. Both SHALL be stored on `msku_master` and used everywhere the MSKU is displayed in the UI.

Extraction rule:
- `display_name`: substring between the token `SOLID` and the next occurrence of `CLASSIC` or `POOMEX`. Title-cased. If the raw code contains `PREMIUM`, append ` PRM`; if `ECONOMIC` and disambiguation is needed (another MSKU has the same base name), it is left as-is.
- `short_code`: display_name words joined by `-`, uppercased, max 4 words (e.g., `GYM-VEST-ECO`, `TRUNK-OUTER-PRM`).

#### Scenario: Gym Vest extraction
- **WHEN** the parser processes `MENSINNER WEARECONOMICACTIVE WEAR INNER WEAR TOPSOLIDGYM VESTCLASSICPOOMEX`
- **THEN** `display_name` = `Gym Vest` and `short_code` = `GYM-VEST-ECO`

#### Scenario: RN Vest extraction
- **WHEN** the parser processes `MENSINNER WEARECONOMICDAILY WEARINNER WEAR TOPSOLIDRN VESTCLASSICPOOMEX`
- **THEN** `display_name` = `RN Vest` and `short_code` = `RN-VEST-ECO`

#### Scenario: Premium disambiguation
- **WHEN** the parser processes a code containing `PREMIUM` and `TRUNKOUTERPOOMEX`
- **THEN** `display_name` = `Trunk Outer PRM` and `short_code` = `TRUNK-OUTER-PRM`

#### Scenario: Fallback when pattern not matched
- **WHEN** the parser cannot find `SOLID` in the MSKU code
- **THEN** `display_name` falls back to the raw `msku_code` value (no crash)

### Requirement: API returns display_name everywhere
All API endpoints that return MSKU data SHALL include `display_name` and `short_code` fields alongside `msku_code`.

#### Scenario: Alert API includes display name
- **WHEN** `GET /api/alerts/` is called
- **THEN** each alert row includes `display_name` and `short_code`
