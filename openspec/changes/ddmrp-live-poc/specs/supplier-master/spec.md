## ADDED Requirements

### Requirement: Supplier master CRUD
The system SHALL maintain a `suppliers` table and expose a REST API for listing, creating, and updating suppliers. The admin UI SHALL display suppliers grouped by product segment (e.g., "Mens Inner Wear") with inline editing.

Fields per supplier: `supplier_code` (e.g., POOMEX-001), `name`, `unit` (e.g., Unit 1 — Primary), `location`, `contact_email`, `credit_period_days`, `is_msme` (boolean), `stock_clearance_rule` (text), `moq`, `active`.

Two suppliers are seeded in a migration: POOMEX-001 (Poomex Textiles Ltd., Unit 1 — Primary) and POOMEX-002 (Poomex Textiles Ltd., Unit 2 — Secondary).

#### Scenario: Supplier list loads from API
- **WHEN** admin navigates to Supplier Master
- **THEN** `GET /api/suppliers/` is called and the response populates the supplier table

#### Scenario: Edit supplier inline
- **WHEN** admin clicks the Edit button on a supplier row
- **THEN** a drawer opens with prefilled fields; on Save, `PATCH /api/suppliers/<code>` is called and the row updates without page reload

#### Scenario: Add new supplier
- **WHEN** admin clicks "+ Add Supplier"
- **THEN** a blank drawer opens; on Save, `POST /api/suppliers/` is called and the new supplier appears in the list

#### Scenario: Seeded suppliers visible on first launch
- **WHEN** the app is started for the first time with a fresh database
- **THEN** POOMEX-001 and POOMEX-002 are already present in the supplier list

### Requirement: Supplier hub stock clearance indicator
In the Order Recommendation hub allocation step, the system SHALL display each supplier's hub stock clearance percentage and flag suppliers with >50% of previous order still in hub as "Not Recommended".

#### Scenario: Recommended supplier highlighted
- **WHEN** the planner opens the Supplier step of hub allocation
- **THEN** the supplier with hub_cleared >= 50% shows a green "Recommended" badge; the one below threshold shows an amber "Not Recommended" badge
