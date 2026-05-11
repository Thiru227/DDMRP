## 1. Database & Backend Foundation

- [x] 1.1 Add `ALTER TABLE mskus ADD COLUMN product_code TEXT` migration inside `init_db()` (wrapped in try/except for idempotency)
- [x] 1.2 Add `_derive_product_code(msku_code)` function to `app.py` using CAT/TIER/OCC/STYLE pattern (MI-ECO-ACT-GV)
- [x] 1.3 Call `_derive_product_code()` inside `_parse_branch()` and `_parse_hub()` and include in INSERT/UPDATE for `mskus`
- [x] 1.4 Fix OR sequential codes: replace `uuid4().hex[:6].upper()` in `create_order_rec()` with `_next_slip(db, "OR")` (same pattern as RS)
- [x] 1.5 Add `PATCH /api/mskus/<id>` endpoint: accepts subset of `{on_hand, on_order, dlt, ltf, vf, doc, moq}`, validates (no negatives), persists, recomputes all derived DDMRP fields, returns full row
- [x] 1.6 Add `type` form field support to `POST /api/upload`: if `type=msku` force `_parse_branch()`; if `type=sales` force `_parse_hub()`; otherwise fall back to `_auto_fmt()`
- [x] 1.7 Return `product_code` in `GET /api/mskus`, `GET /api/mskus/<id>`, `GET /api/order-recs`, `GET /api/rs`, `GET /api/po-tracking` responses

## 2. Admin Upload Page (demo.html)

- [x] 2.1 Replace the single upload card with two side-by-side cards: "Upload MSKU Data" (branch CSV) and "Upload Sales & Stocks" (hub CSV)
- [x] 2.2 Each card has its own file input, Upload button, file name display, and format hint text
- [x] 2.3 Each upload button sets `type=msku` or `type=sales` in the FormData before calling `POST /api/upload`
- [x] 2.4 Update upload history table: replace raw `fmt` value with display label ("MSKU" for `branch`, "Sales & Stocks" for `hub`)

## 3. Product Code Display (demo.html)

- [x] 3.1 Planner alert table: add `product_code` as a `.msku-code` monospace badge below the `display_nm` in the MSKU column
- [x] 3.2 Admin RS Tracker table: add "Product Code" column (monospace badge) between MSKU name and Lines columns
- [x] 3.3 PO Tracking detail panel (built in task 5): include `product_code` badge in the panel header

## 4. Planner Inline Editing (demo.html)

- [x] 4.1 In the planner table row, make OH, OO, DLT, LTF, VF, DOC, MOQ cells render as `<input type="number">` with current value
- [x] 4.2 On input `change` event: call `PATCH /api/mskus/<id>` with the changed field, then update all derived cells in the same row with returned values
- [x] 4.3 Flash updated cells briefly (CSS transition: background highlight fades out) to confirm the recalculation
- [x] 4.4 Keep ADU, NFP, Red, Yellow, Green, TOR, TOG, Plan Priority, Order Rec as plain `<td>` text — not editable

## 5. Planner Action Column — 4 States (demo.html)

- [x] 5.1 On `loadAlerts()`, also fetch `GET /api/order-recs` and build a lookup map `orByMskuId = {msku_id: or_record}`
- [x] 5.2 In `buildRow()`, replace the current single action button with a function `actionCell(msku)` that returns one of four states based on `orByMskuId[msku.id]?.status`
- [x] 5.3 State: no OR → `<button class="btn btn-gold btn-sm">Create Order Recommendation Draft</button>` (calls `createOr(msku.id)`)
- [x] 5.4 State: `draft` → `<button class="btn btn-ghost btn-sm">Continue Draft</button>` (calls `openOrPanel(orId)` to re-open the existing draft)
- [x] 5.5 State: `sent_to_execution` → `<span class="badge b-amber">Sent to Executor</span>` (no button)
- [x] 5.6 State: `rs_created` → `<span class="badge b-green">RS Created ✓</span>` (no button, green)
- [x] 5.7 Remove any "Requirement Slip" label or RS terminology from the planner page

## 6. Allocation Panel — 100% Explanation (demo.html)

- [x] 6.1 Add label above the size/color grid: "Distribute 100% so all ordered units are assigned to variants"
- [x] 6.2 Add an `ⓘ` info icon next to the label; on hover show tooltip: "Example: 25% of 480 units = 120 pcs for that size/colour"

## 7. PO Tracking Detail Panel (demo.html)

- [x] 7.1 Add a slide-in right-side panel element (`#rs-detail-panel`) to the PO tracking page HTML, initially hidden, with a close button
- [x] 7.2 Make kanban card div clickable (add `onclick="openRsDetail(r.id)"` on the card wrapper, excluding the Release button)
- [x] 7.3 `openRsDetail(id)`: calls `GET /api/rs/<id>`, populates and shows the panel
- [x] 7.4 Panel content: RS code (mono), OR code (mono), product name + product_code badge, hub, total qty (large number), then a table of lines (MRP | Size | Colour | Design | Qty)
- [x] 7.5 Handle empty lines gracefully: show "No line items" if `lines` array is empty
- [x] 7.6 Ensure Release button on card still works after panel is added; after release show toast and re-render kanban without full reload
