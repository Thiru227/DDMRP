## MODIFIED Requirements

### Requirement: "Create Order Recommendation Draft" is gated by buffer status

**REPLACES** the prior requirement that showed "Create Order Recommendation Draft" for all MSKUs with no OR.

The `Create Order Recommendation Draft` button SHALL only appear when the MSKU buffer status is `yellow` or `red` AND no Order Recommendation exists. It SHALL NOT appear for `green` or `blue` buffer states.

| Buffer state | OR state | Action column |
|---|---|---|
| red (pp < 0%) | none | Button: "Create Order Recommendation Draft" |
| yellow (0% ≤ pp < 50%) | none | Button: "Create Order Recommendation Draft" |
| green (50% ≤ pp < 100%) | none | Badge: "Sufficient Stock" (no button) |
| blue (pp ≥ 100%) | none | Badge: "Not Needed" (no button) |
| any | draft | Button: "Continue Draft" |
| any | sent_to_execution | Badge: "Sent to Executor" (amber, no button) |
| any | rs_created | Badge: "RS Created ✓" (green, no button) |
