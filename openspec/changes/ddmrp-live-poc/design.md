## Context

The project has two independent pieces that need to be joined:

1. **Flask backend** (`app/`): SQLite-backed, has upload/parse/commit/revoke API, DDMRP engine, alerts API, planning API. No auth. No suppliers/order-rec/req-slip tables. The single `index.html` template is a thin stub.

2. **HTML prototype** (`poc_quick_demo.html`): Complete 3780-line static SPA. All screens for all three roles fully designed and interactive. All data is hardcoded JS. Login is fake client-side role switching.

The approach is **Approach A — wire the demo**: keep every pixel of the existing HTML/CSS/JS layout, strip the fake data, inject real API calls. The demo becomes the live app.

## Goals / Non-Goals

**Goals:**
- Auth with real Flask sessions (3 roles, hardcoded credentials for POC)
- `poc_quick_demo.html` → becomes the live single-page app served by Flask
- All page data replaced with fetch() calls to Flask APIs
- MSKU display names auto-extracted from concatenated classification codes
- New DB tables: `suppliers`, `order_recommendations`, `requirement_slips`
- Inline editing wired to real API calls (branches, suppliers, MSKU)
- Requirement Slip auto-numbering: RS-YYYY-NNN
- Upload history shows Revoke button (calls existing DELETE endpoint)
- Sales CSV upload wired to `sales-upload` admin page

**Non-Goals:**
- Real user management / password hashing (hardcoded creds only, POC)
- Multi-hub logic (MDU-HUB default, same as demo)
- Email/SMS notifications on req-slip release
- GRN / goods-received flow (PO Tracking manual status for POC)
- Supabase / production database migration

## Decisions

### D1 — Serve the demo HTML directly via Flask

**Decision**: `poc_quick_demo.html` is moved to `app/templates/` and served via Flask. Jinja adds a CSRF meta tag and a `window.__SESSION__` JSON block so the JS can know the current user/role without an extra API call.

**Why**: The demo's JS architecture (`goPage()`, inline event handlers, CSS classes for role visibility) is self-contained and already correct. A full React/Vue rewrite would take weeks with zero UX benefit for a POC.

**Alternative considered**: Build a separate frontend (React SPA). Rejected — too slow, and the demo already has the exact stakeholder-facing UX.

### D2 — Flask session auth with hardcoded credentials

**Decision**: `POST /api/auth/login` validates username+password against a hardcoded dict in config. On success, writes `{user, role, name}` to Flask session. All other API calls check `session["role"]` and return 401 if absent or wrong role.

**Why**: POC constraint. Adding a `users` DB table with hashed passwords is unnecessary overhead for a stakeholder demo. The demo itself used hardcoded JS credentials (`admin/admin`).

**Credentials**:
- admin / admin → role: `admin`
- planning / planning → role: `planner`
- executer / executer → role: `executor`

### D3 — MSKU display_name extracted in parser

**Decision**: The legacy parser extracts the product name from the raw concatenated MSKU code using a regex: the product name sits between `SOLID` and (`CLASSIC`|`POOMEX`). The mode (`ECONOMIC`→`ECO`, `PREMIUM`→`PRM`) is also extracted and appended where needed to disambiguate (e.g., two TRUNK OUTER MSKUs). A short hyphenated code is derived from initials.

**Why**: The raw code (`MENSINNER WEARECONOMICACTIVE WEAR INNER WEAR TOPSOLIDGYM VESTCLASSICPOOMEX`) is unreadable. The demo shows clean names ("Gym Vest", "RN Vest"). Fixing it at parse-time means the admin doesn't need to edit the CSV.

**Short code derivation** (stored as `short_code`):
```
Gym Vest ECO       → GYM-VEST-ECO
Briefs Inner ECO   → BRIEFS-INNER-ECO
RN Vest ECO        → RN-VEST-ECO
Trunk Outer PRM    → TRUNK-OUTER-PRM
```

### D4 — Hub allocation stored as JSON in order_recommendations

**Decision**: The 4-step hub allocation (Supplier split, MRP split, Colour×Size matrix, Design split) is stored as a single `allocation_json` TEXT column in `order_recommendations`, not normalised into child tables.

**Why**: The data is entered once, never queried individually by sub-field, and the shape varies per MSKU (different MRP bands, colours, sizes). JSON is the right fit for this POC. A production version would normalise.

### D5 — Requirement Slip auto-numbering

**Decision**: RS number format is `RS-{YYYY}-{NNN}` where NNN is zero-padded to 3 digits, incrementing per calendar year. Generated at the moment of `POST /api/order-recs/:id/submit`.

**Why**: Matches the naming convention shown throughout the demo (RS-2026-001). Simple, readable, unambiguous for stakeholders.

### D6 — PO Tracking derived from requirement_slips

**Decision**: The PO Tracking kanban reads from `requirement_slips` joined with `order_recommendations`. Status column on `requirement_slips` drives the kanban column: `pending_release` → "Pending Executor", `released` → "PO Released". "In Transit" and "Received" are manual status updates via a simple PATCH endpoint.

**Why**: Keeps the data model simple. For the POC, the executor releasing a slip is the main demo moment — transit/received are just shown as existing demo data.

## Risks / Trade-offs

- **SQLite concurrency**: Single write-lock. Acceptable for POC (single user at a time during demos). → No mitigation needed.
- **Hardcoded credentials**: Not safe for production. → Clearly labelled "POC only". Swap for real auth in v2.
- **Demo HTML mutation**: Editing a 3780-line file risks visual regressions. → Make minimal, targeted JS changes only. All CSS and layout stays untouched. Each change is scoped to a clearly-marked `/* === LIVE DATA: <section> === */` block.
- **Allocation JSON schema drift**: If the 4-step form changes, the JSON blob must be migrated. → For POC, acceptable. Document the schema in a comment.

## Migration Plan

1. Run new SQL migrations (alter msku_master, create suppliers/order_recs/req_slips)
2. Seed suppliers table (POOMEX-001, POOMEX-002) in a new migration file
3. Re-upload the existing CSV — parser now auto-extracts display_name/short_code
4. Move `poc_quick_demo.html` → `app/templates/demo.html`
5. All existing `/api/` routes unchanged — no breakage

## Open Questions

- Should the sales CSV (`sales&stocks.csv`) update the same `inventory_snapshots` table as the MSKU working file, or a separate `sales_snapshots` table? (Current assumption: same table, separate upload_job_id, parser handles the simpler format.)
- For the hub allocation Colour×Size matrix, should the matrix dimensions (colours, sizes) come from the MSKU master or be free-form per order? (Current assumption: free-form for POC — user types them in.)
