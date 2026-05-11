## Context

The current POC has a Flask app with 9 separate blueprint files, a multi-migration SQLite schema, and a `demo.html` that hardcodes all MSKU data in JS arrays (`MSKUS`, `PO_LINES`, `REQ_LINES`) with a `demoMode` toggle. This architecture made the POC fast to prototype but produces a misleading demo — stakeholders see numbers that don't reflect actual uploaded data.

The `DDMRP Prototype.html` (430KB, 4420 lines) establishes the correct visual language: design tokens (ink/bg/gold/teal/ruby/amber CSS vars), component library (stat cards, badge system, alert table, wizard steps, size×colour matrix), and a clean role-login flow. We borrow its CSS entirely and throw away its JS data layer.

Current state:
- DB: `app/data/ddmrp.db` with 12 migrations
- Routes: 9 blueprint files in `app/routes/`
- Template: `app/templates/demo.html` — hybrid static/API
- Two real CSVs on disk: `sales&stocks.csv` (8 MSKU rows, hub-level) and `01 MENS INNER - PILOT…csv` (109 rows, branch-level)

## Goals / Non-Goals

**Goals:**
- Zero static data in the browser — every number comes from `GET /api/*` endpoints
- Single `app.py` with all routes (≤ 500 lines) — no blueprints, no migration files
- CSV auto-detection: both existing file formats parse into the same `mskus` table
- Hub allocation wizard is interactive and saves real JSON to `order_recs.allocation_json`
- RS lines are computed server-side from allocation JSON when executor clicks "Create RS"
- Admin dashboard RS tracker refreshes from DB on every load
- Port prototype CSS verbatim — no design regressions

**Non-Goals:**
- Multi-hub allocation (single hub: Madurai)
- Multi-supplier (single supplier: Poomex)
- Real authentication / JWT / session expiry
- Migrating old `ddmrp.db` data
- Branch-level replenishment (L3 in prototype)
- Forecast / Inventory Review / Season Opening Plan template types

## Decisions

### D1: Single flat `app.py` over blueprints
**Decision:** All routes inline in one file.  
**Rationale:** The demo has ~15 endpoints total. Blueprint overhead (import graph, `init_app`, register calls) adds complexity with no benefit at this scale. Single file = zero ambiguity about where a route lives.  
**Alternative considered:** Keep blueprints, just rewrite them. Rejected — the old blueprints carry dead code and conflicting abstractions (e.g., separate `planning.py` and `order_recs.py` doing overlapping things).

### D2: New `ddmrp_v2.db`, don't migrate old DB
**Decision:** Fresh SQLite file; schema created inline via `executescript` on first run.  
**Rationale:** Old schema has 12 migrations and constraints (e.g., `upload_jobs` CHECK constraint that needed patch 012). Starting fresh removes that debt. Old DB left on disk — no data loss risk for the demo.  
**Schema (4 tables):**
```
mskus           — MSKU master + DDMRP buffer values + NFP/plan_priority/order_rec
upload_logs     — CSV upload audit log with revoke flag
order_recs      — planning's order recommendation, allocation_json, status lifecycle
requirement_slips — executor's RS, lines_json (generated from allocation_json)
```

### D3: CSV auto-detect by header content
**Decision:** Detect format by inspecting row[0] of the first row.  
- `"MASTER SKU CODE"` in row[0] → hub format (`sales&stocks.csv`)  
- `"S.NO"` in any of first 5 rows → branch format (`01 MENS INNER…csv`)  
**Rationale:** Admin shouldn't need to choose format — both files are already on disk, and both should "just work" when uploaded.  
**Hub format:** 1 row/MSKU, all DDMRP calcs pre-done (use as-is)  
**Branch format:** N rows/MSKU (one per branch), aggregate sales+OH across branches, recompute ADU/NFP/plan_priority/order_rec from aggregated totals; take buffer zone values (TOR/TOY/TOG) from first branch row where TOR > 0

### D4: Allocation JSON as the single source of truth for RS lines
**Decision:** `order_recs.allocation_json` stores `{mrp_split, size_color, design_split}` as JSON. RS line generation is pure server-side: `POST /api/executor/order-recs/<id>/create-rs` runs `_gen_rs_lines()` from that JSON.  
**Rationale:** Keeps the executor endpoint simple (one click, no form data needed). Allocation is fully captured by the planner before sending. If allocation is empty (planner skipped wizard), fall back to equal split across MRP bands.

### D5: SPA navigation via `goPage(id)` — no client-side router
**Decision:** Keep prototype's `show/hide div` pattern. Each page is a `<div class="page" id="page-X">`. Navigation is `goPage('X')` which hides all, shows target, and loads data.  
**Rationale:** Prototype already established this pattern. Adding a router (History API) would require Flask to serve all paths, adding complexity with no stakeholder-visible benefit.

### D6: Prototype CSS copied verbatim, JS rewritten from scratch
**Decision:** Extract prototype's `<style>` block (lines 7–708) into the new template. All JS is new — no reuse of prototype's hardcoded `MSKUS[]`, `renderAlertTable()`, etc.  
**Rationale:** The prototype CSS is production-quality with a complete design token system. The JS is tightly coupled to static arrays and can't be salvaged incrementally.

## Risks / Trade-offs

**Branch CSV DDMRP values are per-branch, not hub-level**  
→ When parsing the branch CSV, TOR/TOY/TOG taken from one branch row will be smaller than the hub-level values in `sales&stocks.csv`. Mitigation: recommend uploading `sales&stocks.csv` as the primary file for accurate buffer zones. Branch CSV upload is primarily useful for extracting sizes, MRP bands, MOQ.

**plan_priority in hub CSV is stored as "106%" string**  
→ `pnum()` helper strips `%` before parsing float. Verified against both CSVs.

**No concurrency control on order_rec status transitions**  
→ If two planners click "Send" simultaneously, both succeed (SQLite last-write-wins). Acceptable for a single-session demo.

**Allocation JSON not validated server-side**  
→ Planner could send nonsense percentages. `_gen_rs_lines()` uses `round()` arithmetic, so worst case is a RS with 0-qty lines. Mitigation: frontend validates total = 100% before enabling "Send to Execution".

**SQLite WAL mode on macOS**  
→ WAL is enabled per-connection. For the demo (single-user, single process) this is fine.

## Migration Plan

1. Run `.venv/bin/python3 app.py` — new `ddmrp_v2.db` created automatically on first boot
2. Old `ddmrp.db` remains untouched
3. Admin uploads the two CSVs via the new upload UI — data flows to planner immediately
4. Old blueprint files in `app/routes/` can be deleted after validation (not blocking)

## Open Questions

- Should the size×colour matrix use actual sizes from the MSKU's `sizes` field (e.g., `80, 85, 90, 95`) or map them to generic S/M/L/XL labels for readability?  
  → **Decision:** Use actual size values from CSV (e.g., `80, 85, 90, 95`) — more authentic for the demo
- Should colours be hardcoded (White/Black/Navy/Grey) or pulled from a separate upload?  
  → **Decision:** Hardcoded defaults stored in `mskus.colours` JSON column; editable per-MSKU in a future iteration
