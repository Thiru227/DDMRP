"""Order Recommendations API — draft PO through hub-allocation to executor."""
from __future__ import annotations

import json
import math
import uuid
from datetime import datetime

from flask import Blueprint, jsonify, request, session

from app.repositories import db
from app.routes.auth import login_required

bp = Blueprint("order_recs", __name__, url_prefix="/api/order-recs")


def _next_or_id() -> str:
    return f"OR-{datetime.now().year}-{uuid.uuid4().hex[:6].upper()}"


def _latest_plan_row(c, msku_code: str) -> dict | None:
    latest_date = c.execute(
        "SELECT MAX(snapshot_date) AS d FROM planning_snapshots"
    ).fetchone()["d"]
    if not latest_date:
        return None
    row = c.execute(
        """SELECT p.msku_code, p.branch_code, p.snapshot_date,
                  p.adu, p.red_zone, p.yellow_zone, p.green_zone,
                  p.tor, p.toy, p.tog, p.net_flow, p.planning_priority,
                  p.order_recommendation, p.alert_level,
                  i.on_hand_qty, i.on_order_qty, i.qualified_demand_qty,
                  m.moq, m.lead_time, m.dlt, m.ltf, m.vf, m.doc,
                  COALESCE(m.display_name, p.msku_code) AS display_name,
                  COALESCE(m.short_code,   p.msku_code) AS short_code,
                  m.mrp, m.size
             FROM planning_snapshots p
             LEFT JOIN inventory_snapshots i
                    ON i.msku_code = p.msku_code
                   AND i.branch_code = p.branch_code
                   AND i.snapshot_date = p.snapshot_date
             LEFT JOIN msku_master m ON m.msku_code = p.msku_code
            WHERE p.msku_code = ? AND p.snapshot_date = ?
            ORDER BY p.branch_code = 'TOT' DESC, p.planning_priority ASC
            LIMIT 1""",
        (msku_code, latest_date),
    ).fetchone()
    return dict(row) if row else None


def _compute_recommended_qty(plan: dict) -> int:
    tog = plan.get("tog") or 0.0
    nfp = plan.get("net_flow") or 0.0
    moq = plan.get("moq") or 120
    raw = tog - nfp
    if raw <= 0:
        return int(moq)
    rounded = math.ceil(raw / moq) * int(moq)
    return max(rounded, int(moq))


@bp.post("/")
@login_required(roles=["planner", "admin"])
def create_order_rec():
    data = request.get_json(silent=True) or {}
    msku_code = (data.get("msku_code") or "").strip()
    if not msku_code:
        return jsonify({"error": "msku_code required"}), 400

    c = db.conn()
    plan = _latest_plan_row(c, msku_code)
    if plan is None:
        return jsonify({"error": "no planning snapshot for this MSKU"}), 404

    rec_id = _next_or_id()
    qty = _compute_recommended_qty(plan)

    with db.tx() as conn:
        conn.execute(
            """INSERT INTO order_recommendations
                 (id, msku_code, hub_code, total_qty, status, created_by)
               VALUES (?, ?, 'MDU-HUB', ?, 'draft', ?)""",
            (rec_id, msku_code, qty, session.get("user")),
        )

    return jsonify({"id": rec_id, "msku_code": msku_code, "total_qty": qty,
                    "status": "draft", **plan}), 201


@bp.get("/")
@login_required()
def list_order_recs():
    status = request.args.get("status")
    c = db.conn()
    if status:
        rows = c.execute(
            """SELECT r.*, COALESCE(m.display_name, r.msku_code) AS display_name,
                      COALESCE(m.short_code, r.msku_code) AS short_code
                 FROM order_recommendations r
                 LEFT JOIN msku_master m ON m.msku_code = r.msku_code
                WHERE r.status = ? ORDER BY r.created_at DESC""",
            (status,),
        ).fetchall()
    else:
        rows = c.execute(
            """SELECT r.*, COALESCE(m.display_name, r.msku_code) AS display_name,
                      COALESCE(m.short_code, r.msku_code) AS short_code
                 FROM order_recommendations r
                 LEFT JOIN msku_master m ON m.msku_code = r.msku_code
                ORDER BY r.created_at DESC""",
        ).fetchall()
    result = []
    for r in rows:
        row = dict(r)
        if row.get("allocation_json"):
            row["allocation"] = json.loads(row["allocation_json"])
        result.append(row)
    return jsonify({"order_recs": result})


@bp.get("/<rec_id>")
@login_required()
def get_order_rec(rec_id: str):
    c = db.conn()
    row = c.execute(
        """SELECT r.*, COALESCE(m.display_name, r.msku_code) AS display_name,
                  COALESCE(m.short_code, r.msku_code) AS short_code,
                  m.moq, m.lead_time, m.mrp, m.size
             FROM order_recommendations r
             LEFT JOIN msku_master m ON m.msku_code = r.msku_code
            WHERE r.id = ?""",
        (rec_id,),
    ).fetchone()
    if row is None:
        return jsonify({"error": "not found"}), 404

    result = dict(row)
    if result.get("allocation_json"):
        result["allocation"] = json.loads(result["allocation_json"])
    else:
        result["allocation"] = {}

    plan = _latest_plan_row(c, result["msku_code"])
    if plan:
        result["buffer"] = plan

    return jsonify(result)


@bp.patch("/<rec_id>")
@login_required(roles=["planner", "admin"])
def update_order_rec(rec_id: str):
    data = request.get_json(silent=True) or {}
    c = db.conn()
    rec = c.execute("SELECT id, status FROM order_recommendations WHERE id = ?",
                    (rec_id,)).fetchone()
    if rec is None:
        return jsonify({"error": "not found"}), 404
    if rec["status"] == "sent_to_executor":
        return jsonify({"error": "cannot edit a submitted order rec"}), 409

    updates: dict = {}
    if "total_qty" in data:
        updates["total_qty"] = int(data["total_qty"])
    if "notes" in data:
        updates["notes"] = data["notes"]
    if "allocation" in data:
        updates["allocation_json"] = json.dumps(data["allocation"])
    if "hub_code" in data:
        updates["hub_code"] = data["hub_code"]

    if not updates:
        return jsonify({"error": "no valid fields"}), 400

    updates["updated_at"] = "CURRENT_TIMESTAMP"
    sets = ", ".join(
        f"{k} = CURRENT_TIMESTAMP" if v == "CURRENT_TIMESTAMP" else f"{k} = ?"
        for k, v in updates.items()
    )
    values = [v for v in updates.values() if v != "CURRENT_TIMESTAMP"]

    with db.tx() as conn:
        conn.execute(f"UPDATE order_recommendations SET {sets} WHERE id = ?",
                     (*values, rec_id))

    return jsonify({"id": rec_id, "ok": True})


@bp.post("/<rec_id>/submit")
@login_required(roles=["planner", "admin"])
def submit_order_rec(rec_id: str):
    from app.routes.requirement_slips import _next_rs_id

    c = db.conn()
    rec = c.execute("SELECT * FROM order_recommendations WHERE id = ?",
                    (rec_id,)).fetchone()
    if rec is None:
        return jsonify({"error": "not found"}), 404
    if rec["status"] != "draft":
        return jsonify({"error": f"order rec is {rec['status']}"}), 409

    allocation = json.loads(rec["allocation_json"] or "{}")
    if not allocation:
        return jsonify({"error": "allocation not complete — run through hub allocation steps first"}), 422

    year = datetime.now().year
    rs_id = _next_rs_id(year)

    with db.tx() as conn:
        conn.execute(
            "UPDATE order_recommendations SET status = 'sent_to_executor', updated_at = CURRENT_TIMESTAMP WHERE id = ?",
            (rec_id,),
        )
        conn.execute(
            """INSERT INTO requirement_slips (id, order_rec_id, msku_code, total_qty, status)
               VALUES (?, ?, ?, ?, 'pending_release')""",
            (rs_id, rec_id, rec["msku_code"], rec["total_qty"]),
        )

    return jsonify({"id": rec_id, "status": "sent_to_executor",
                    "requirement_slip_id": rs_id})
