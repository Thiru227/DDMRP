## ADDED Requirements

### Requirement: PO Tracking kanban cards are clickable and open a detail panel
Clicking anywhere on a PO tracking kanban card (except the Release button) SHALL open a right-side detail panel showing the full Requirement Slip breakdown.

#### Scenario: Clicking a card opens the detail panel
- **WHEN** the executor clicks a kanban card in the PO Tracking view
- **THEN** a slide-in panel (right side, ~380px) SHALL appear with the full RS detail

#### Scenario: Detail panel shows all RS information
- **WHEN** the detail panel is open
- **THEN** it SHALL display: RS code, OR code, product display name, product code badge, hub destination, total quantity, and a table of all RS lines with columns: MRP Band | Size | Colour | Design | Qty

#### Scenario: Detail panel for RS with no lines
- **WHEN** the RS has zero lines (edge case)
- **THEN** the panel SHALL show "No line items" rather than an empty table

#### Scenario: Release button remains on the card
- **WHEN** an RS card is in Pending status
- **THEN** the Release button SHALL remain visible on the kanban card itself (not only inside the panel), so the executor can release without opening the detail

#### Scenario: Release action triggers visual feedback
- **WHEN** the executor clicks Release on a pending card
- **THEN** the system SHALL call `POST /api/rs/<id>/release`, show a success toast, and move the card from Pending to Released column without a full page reload
