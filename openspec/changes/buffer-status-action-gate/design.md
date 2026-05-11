## Context

The planner action column has a two-axis decision: buffer status (red/yellow/green/blue) and OR lifecycle (none/draft/sent_to_execution/rs_created). Currently only the OR lifecycle axis is checked; buffer status is ignored when no OR exists, causing "Create Order Recommendation Draft" to appear even for Overstock rows.

## Goals / Non-Goals

**Goals:**
- Gate the create-OR button behind yellow/red buffer status
- Show meaningful informational badges for green/blue rows with no OR
- Preserve all OR lifecycle state rendering unchanged

**Non-Goals:**
- Changing buffer zone thresholds or DDMRP formulas
- Any backend API changes
- Changing behavior for rows that already have an OR

## Decisions

### Decision 1: OR lifecycle takes full priority

If an OR exists for an MSKU (any status), the OR lifecycle state is shown regardless of current buffer status. A planner who created a draft OR when the item was yellow should still see "Continue Draft" even if stock recovered to blue — the OR needs to be consciously cancelled, not silently hidden.

### Decision 2: Badge copy

| Buffer state | Badge text         | Style        |
|---|---|---|
| blue (≥100%) | Not Needed         | `.b-blue` (blue, soft) |
| green (50–99%) | Sufficient Stock | `.b-green` (teal/green, soft) |

These are already defined CSS classes in the app. No new styles needed.

### Decision 3: Pure frontend change

`m.status` (derived from `plan_priority` via `pp_status()`) is already included in every MSKU row returned by `GET /api/mskus`. The `renderAlerts()` function in `demo.html` already has access to it. No API change needed.

## Implementation

Single change in `demo.html` `renderAlerts()` — the `actionBtn` fallback branch (currently the unconditional "Create Order Recommendation Draft"):

```
// BEFORE
actionBtn = '<button ...>Create Order Recommendation Draft</button>'

// AFTER
if (m.status === 'yellow' || m.status === 'red') {
  actionBtn = '<button ...>Create Order Recommendation Draft</button>'
} else if (m.status === 'green') {
  actionBtn = '<span class="badge b-green">Sufficient Stock</span>'
} else {
  actionBtn = '<span class="badge b-blue">Not Needed</span>'
}
```
