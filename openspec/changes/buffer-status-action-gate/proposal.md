## Why

The planner action column currently shows "Create Order Recommendation Draft" for every MSKU that has no existing OR — including MSKUs in Overstock (blue) and Healthy (green) buffer states. This is incorrect DDMRP practice: a replenishment order is only needed when Net Flow Position is in the yellow or red zone. Showing a create-order button on overstocked items causes confusion and mis-signals urgency.

## What Changes

- **Blue (Overstock, pp ≥ 100%)** with no OR: action column shows `Not Needed` informational badge — no button
- **Green (Healthy, 50% ≤ pp < 100%)** with no OR: action column shows `Sufficient Stock` informational badge — no button
- **Yellow (Order Soon, 0% ≤ pp < 50%)** with no OR: action column shows `Create Order Recommendation Draft` button (unchanged)
- **Red (Order Immediately, pp < 0%)** with no OR: action column shows `Create Order Recommendation Draft` button (unchanged)
- OR lifecycle states (draft / sent_to_execution / rs_created) continue to take priority over buffer state when an OR already exists

## Capabilities

### New Capabilities
- `buffer-gated-action`: Action column renders based on buffer status × OR lifecycle state matrix

### Modified Capabilities
- `planner-action-states`: Requirement change — "Create Order Recommendation Draft" is now gated by yellow/red buffer status, not shown universally for no-OR rows

## Impact

- `app/templates/demo.html`: `renderAlerts()` JS function — action cell logic (~5 lines)
- No backend changes needed; buffer status (`m.status`) is already returned in `GET /api/mskus`
