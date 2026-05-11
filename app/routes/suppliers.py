"""Suppliers master API."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.repositories import db
from app.routes.auth import login_required

bp = Blueprint("suppliers", __name__, url_prefix="/api/suppliers")

_ALLOWED_FIELDS = {
    "name", "unit", "location", "contact_email",
    "credit_period_days", "is_msme", "stock_clearance_rule", "moq",
    "hub_cleared_pct", "active",
}


@bp.get("/")
def list_suppliers():
    active_only = request.args.get("active")
    c = db.conn()
    if active_only == "1":
        rows = c.execute(
            "SELECT * FROM suppliers WHERE active = 1 ORDER BY supplier_code"
        ).fetchall()
    else:
        rows = c.execute("SELECT * FROM suppliers ORDER BY supplier_code").fetchall()
    return jsonify({"suppliers": [dict(r) for r in rows]})


@bp.post("/")
@login_required(roles=["admin"])
def create_supplier():
    data = request.get_json(silent=True) or {}
    code = (data.get("supplier_code") or "").strip().upper()
    if not code:
        return jsonify({"error": "supplier_code required"}), 400
    if not data.get("name"):
        return jsonify({"error": "name required"}), 400

    with db.tx() as c:
        c.execute(
            """INSERT INTO suppliers
                 (supplier_code, name, unit, location, contact_email,
                  credit_period_days, is_msme, stock_clearance_rule, moq,
                  hub_cleared_pct, active)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)""",
            (
                code, data.get("name"), data.get("unit"),
                data.get("location"), data.get("contact_email"),
                int(data.get("credit_period_days") or 45),
                1 if data.get("is_msme") else 0,
                data.get("stock_clearance_rule"),
                int(data.get("moq") or 120),
                float(data.get("hub_cleared_pct") or 100.0),
            ),
        )
    return jsonify({"supplier_code": code, "ok": True}), 201


@bp.patch("/<code>")
@login_required(roles=["admin"])
def update_supplier(code: str):
    data = request.get_json(silent=True) or {}
    updates = {k: v for k, v in data.items() if k in _ALLOWED_FIELDS}
    if not updates:
        return jsonify({"error": "no valid fields"}), 400

    sets = ", ".join(f"{k} = ?" for k in updates)
    sets += ", updated_at = CURRENT_TIMESTAMP"
    with db.tx() as c:
        c.execute(
            f"UPDATE suppliers SET {sets} WHERE supplier_code = ?",
            (*updates.values(), code.upper()),
        )
    return jsonify({"supplier_code": code, "ok": True})
