## 1. Planner Action Column — Buffer-Gated Logic (demo.html)

- [x] 1.1 In `renderAlerts()`, update the `actionBtn` fallback branch: replace the unconditional "Create Order Recommendation Draft" button with a status check — show the button only when `m.status === 'yellow' || m.status === 'red'`; show `<span class="badge b-green">Sufficient Stock</span>` for `green`; show `<span class="badge b-blue" style="...">Not Needed</span>` for `blue`
- [x] 1.2 Add `.b-blue` CSS class for the "Not Needed" badge (blue-toned background, matching the existing `.b-green` / `.b-amber` style pattern)
