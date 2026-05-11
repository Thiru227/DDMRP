## ADDED Requirements

### Requirement: Action column is gated by buffer status when no OR exists

When no Order Recommendation exists for an MSKU, the action column SHALL reflect the buffer status rather than always offering order creation.

#### Scenario: Overstock — no action needed
- **GIVEN** an MSKU with buffer status `blue` (plan priority ≥ 100%)
- **AND** no Order Recommendation exists for it
- **THEN** the action column SHALL show a `Not Needed` informational badge
- **AND** no button SHALL be present

#### Scenario: Healthy — stock sufficient
- **GIVEN** an MSKU with buffer status `green` (50% ≤ plan priority < 100%)
- **AND** no Order Recommendation exists for it
- **THEN** the action column SHALL show a `Sufficient Stock` informational badge
- **AND** no button SHALL be present

#### Scenario: Order Soon — create button shown
- **GIVEN** an MSKU with buffer status `yellow` (0% ≤ plan priority < 50%)
- **AND** no Order Recommendation exists for it
- **THEN** the action column SHALL show the `Create Order Recommendation Draft` button

#### Scenario: Order Immediately — create button shown
- **GIVEN** an MSKU with buffer status `red` (plan priority < 0%)
- **AND** no Order Recommendation exists for it
- **THEN** the action column SHALL show the `Create Order Recommendation Draft` button

#### Scenario: OR lifecycle takes priority over buffer status
- **GIVEN** an MSKU has an existing Order Recommendation (any status)
- **THEN** the action column SHALL show the OR lifecycle state (Continue Draft / Sent to Executor / RS Created ✓)
- **AND** the buffer status SHALL NOT affect the display
