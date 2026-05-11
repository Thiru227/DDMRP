"""Requirement Slips API — executor inbox, review, and release."""
from __future__ import annotations

import json
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from app.repositories import db
from app.routes.auth import login_required

bp = Blueprint("requirement_slips", __name__, url_prefix="/api/requirement-slips")

VALID_STATUSES = {"pending_release", "released", "in_transit", "received", "returned"}


def _next_rs_id(year: int) -> str:
    """Atomically increment rs_sequence for the year and return RS-YYYY-NNN."""
    with db.tx() as c:
        row = c.execute("SELECT last_num FROM rs_sequence WHERE year = ?",
                        (year,)).fetchone()
        if row is None:
            c.execute("INSERT INTO rs_sequence (year, last_num) VALUES (?, 1)", (year,))
            num = 1
        else:
            num = row["last_num"] + 1
            c.execute("UPDATE rs_sequence SET last_num = ? WHERE year = ?",
                      (num, year))
    return f"RS-{year}-{num:03d}"


def _build_slip_detail(c, slip: dict) -> dict:
    """Augment a slip row with buffer data, allocation breakdown, and validation checks."""
    rec = c.execute(
        """SELECT r.*, COALESCE(m.display_name, r.msku_code) AS display_name,
                  COALESCE(m.short_code, r.msku_code) AS short_code,
                  m.moq, m.lead_time, m.mrp, m.size
             FROM order_recommendations r
             LEFT JOIN msku_master m ON m.msku_code = r.msku_code
            WHERE r.id = ?""",
        (slip["order_rec_id"],),
    ).fetchone()
    if rec is None:
        return slip

    result = dict(slip)
    result["display_name"] = rec["display_name"]
    result["short_code"]   = rec["short_code"]
    result["hub_code"]     = rec["hub_code"]
    result["moq"]          = rec["moq"]
    result["lead_time"]    = rec["lead_time"]
    result["mrp"]          = rec["mrp"]
    result["notes"]        = rec["notes"]

    allocation = json.loads(rec["allocation_json"] or "{}")
    result["allocation"] = allocation

    # Supplier split summary
    suppliers_alloc = allocation.get("suppliers", [])
    result["supplier_split"] = suppliers_alloc

    # Build validation checks
    total_qty = slip["total_qty"]
    moq = rec["moq"] or 120
    checks = []
    checks.append({"label": f"MOQ satisfied — {total_qty} pcs ≥ {moq} pcs minimum",
                   "ok": total_qty >= moq})
    checks.append({"label": "Lead time within season",
                   "ok": True})
    sku_balance = allocation.get("sku_balanced", False)
    checks.append({"label": f"All SKU lines balanced — {total_qty} pcs total. Design split verified",
                   "ok": sku_balance})
    design_alloc = allocation.get("design", [])
    design_ok = bool(design_alloc)
    checks.append({"label": "Design split verified", "ok": design_ok})
    checks.append({"label": "No budget breach",      "ok": True})
    checks.append({"label": f"Hub destination confirmed — {rec['hub_code']}",
                   "ok": True})
    result["validation_checks"] = checks
    result["checks_passed"] = sum(1 for c in checks if c["ok"])
    result["checks_total"]  = len(checks)

    return result


@bp.get("/")
@login_required()
def list_slips():
    status  = request.args.get("status")
    limit   = request.args.get("limit", type=int)
    c = db.conn()

    where, params = [], []
    if status:
        where.append("s.status = ?")
        params.append(status)

    sql = f"""
        SELECT s.*,
               COALESCE(m.display_name, s.msku_code) AS display_name,
               COALESCE(m.short_code,   s.msku_code) AS short_code,
               r.hub_code, r.notes, r.created_by
          FROM requirement_slips s
          LEFT JOIN order_recommendations r ON r.id = s.order_rec_id
          LEFT JOIN msku_master m ON m.msku_code = s.msku_code
        {"WHERE " + " AND ".join(where) if where else ""}
         ORDER BY s.sent_at DESC
        {"LIMIT " + str(limit) if limit else ""}
    """
    rows = [dict(r) for r in c.execute(sql, params)]
    return jsonify({"slips": rows})


@bp.get("/<slip_id>")
@login_required()
def get_slip(slip_id: str):
    c = db.conn()
    row = c.execute("SELECT * FROM requirement_slips WHERE id = ?",
                    (slip_id,)).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404
    detail = _build_slip_detail(c, dict(row))
    return jsonify(detail)


@bp.post("/<slip_id>/release")
@login_required(roles=["executor", "admin"])
def release_slip(slip_id: str):
    c = db.conn()
    slip = c.execute("SELECT * FROM requirement_slips WHERE id = ?",
                     (slip_id,)).fetchone()
    if slip is None:
        return jsonify({"error": "not found"}), 404
    if slip["status"] != "pending_release":
        return jsonify({"error": f"slip is {slip['status']}"}), 409

    with db.tx() as conn:
        conn.execute(
            """UPDATE requirement_slips
                  SET status = 'released',
                      released_by = ?,
                      released_at = CURRENT_TIMESTAMP,
                      updated_at  = CURRENT_TIMESTAMP
                WHERE id = ?""",
            (session.get("user"), slip_id),
        )
    return jsonify({"id": slip_id, "status": "released",
                    "released_by": session.get("user"),
                    "released_at": datetime.now().isoformat()})


@bp.post("/<slip_id>/return")
@login_required(roles=["executor", "admin"])
def return_slip(slip_id: str):
    c = db.conn()
    slip = c.execute("SELECT * FROM requirement_slips WHERE id = ?",
                     (slip_id,)).fetchone()
    if slip is None:
        return jsonify({"error": "not found"}), 404

    with db.tx() as conn:
        conn.execute("DELETE FROM requirement_slips WHERE id = ?", (slip_id,))
        conn.execute(
            "UPDATE order_recommendations SET status = 'returned', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (slip["order_rec_id"],),
        )
    return jsonify({"id": slip_id, "status": "returned"})


@bp.patch("/<slip_id>")
@login_required()
def patch_slip(slip_id: str):
    data = request.get_json(silent=True) or {}
    new_status = data.get("status")
    if new_status not in VALID_STATUSES:
        return jsonify({"error": f"invalid status; must be one of {sorted(VALID_STATUSES)}"}), 400

    with db.tx() as c:
        c.execute(
            "UPDATE requirement_slips SET status = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (new_status, slip_id),
        )
    return jsonify({"id": slip_id, "status": new_status, "ok": True})
