"""PO Tracking — kanban view across all requirement slip lifecycle stages."""
from __future__ import annotations

from flask import Blueprint, jsonify

from app.repositories import db
from app.routes.auth import login_required

bp = Blueprint("po_tracking", __name__, url_prefix="/api/po-tracking")

_STATUS_COLUMNS = ["pending_release", "released", "in_transit", "received"]
_COLUMN_LABELS = {
    "pending_release": "Pending Executor",
    "released":        "PO Released",
    "in_transit":      "In Transit",
    "received":        "Received",
}


@bp.get("/")
@login_required()
def kanban():
    c = db.conn()
    rows = c.execute(
        """SELECT s.id, s.msku_code, s.total_qty, s.status,
                  s.sent_at, s.released_at, s.updated_at,
                  COALESCE(m.display_name, s.msku_code) AS display_name,
                  COALESCE(m.short_code,   s.msku_code) AS short_code,
                  r.hub_code, r.allocation_json,
                  r.created_by AS planner
             FROM requirement_slips s
             LEFT JOIN order_recommendations r ON r.id = s.order_rec_id
             LEFT JOIN msku_master m ON m.msku_code = s.msku_code
            ORDER BY s.sent_at DESC"""
    ).fetchall()

    columns: dict = {s: [] for s in _STATUS_COLUMNS}
    for row in rows:
        slip = dict(row)
        status = slip.get("status", "pending_release")
        if status in columns:
            columns[status].append(slip)

    result = [
        {"status": s, "label": _COLUMN_LABELS[s], "slips": columns[s]}
        for s in _STATUS_COLUMNS
    ]
    return jsonify({"columns": result})
