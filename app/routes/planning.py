"""Planning API: latest snapshot list + per-row inline editing with recompute."""
from __future__ import annotations

from flask import Blueprint, jsonify, request

from app.calculations.ddmrp_engine import EngineInputs, compute, compute_diffs
from app.repositories import db

bp = Blueprint("planning", __name__, url_prefix="/api/planning")

EDITABLE_INVENTORY_FIELDS = {"on_hand_qty", "on_order_qty", "qualified_demand_qty"}
EDITABLE_MASTER_FIELDS = {"moq", "lead_time", "ltf", "vf", "doc", "dlt"}


@bp.get("/snapshot")
def snapshot():
    branch = request.args.get("branch")
    alert = request.args.get("alert")
    search = (request.args.get("q") or "").strip().lower()

    c = db.conn()
    latest_date = c.execute(
        "SELECT MAX(snapshot_date) AS d FROM planning_snapshots"
    ).fetchone()["d"]
    if not latest_date:
        return jsonify({"snapshot_date": None, "items": []})

    where = ["p.snapshot_date = ?"]
    params: list = [latest_date]
    if branch:
        where.append("p.branch_code = ?")
        params.append(branch)
    if alert in {"red", "yellow", "healthy"}:
        where.append("p.alert_level = ?")
        params.append(alert)

    sql = f"""
        SELECT p.msku_code, p.branch_code, p.snapshot_date,
               p.adu, p.red_zone, p.yellow_zone, p.green_zone,
               p.tor, p.toy, p.tog, p.net_flow, p.planning_priority,
               p.order_recommendation, p.alert_level, p.flagged_diff,
               i.on_hand_qty, i.on_order_qty, i.qualified_demand_qty,
               i.sales_90d, i.adu_days,
               m.moq, m.lead_time, m.dlt, m.ltf, m.vf, m.doc,
               m.product_classification, m.season, m.size,
               COALESCE(m.display_name, p.msku_code) AS display_name,
               COALESCE(m.short_code,   p.msku_code) AS short_code
          FROM planning_snapshots p
          JOIN inventory_snapshots i USING (msku_code, branch_code, snapshot_date)
          JOIN msku_master         m USING (msku_code)
         WHERE {' AND '.join(where)}
         ORDER BY p.alert_level = 'red' DESC,
                  p.alert_level = 'yellow' DESC,
                  p.planning_priority ASC,
                  p.msku_code, p.branch_code
    """
    rows = [dict(r) for r in c.execute(sql, params)]
    if search:
        rows = [r for r in rows if search in (r["msku_code"] or "").lower()]

    return jsonify({"snapshot_date": latest_date, "items": rows})


@bp.put("/<msku>/<branch>")
def update_row(msku: str, branch: str):
    payload = request.get_json(silent=True) or {}
    inv_updates = {k: float(v) for k, v in payload.items()
                   if k in EDITABLE_INVENTORY_FIELDS and v is not None}
    master_updates = {k: float(v) for k, v in payload.items()
                      if k in EDITABLE_MASTER_FIELDS and v is not None}

    if not inv_updates and not master_updates:
        return jsonify({"error": "no editable fields supplied"}), 400

    c = db.conn()
    latest_date = c.execute(
        "SELECT MAX(snapshot_date) AS d FROM planning_snapshots"
    ).fetchone()["d"]
    if not latest_date:
        return jsonify({"error": "no snapshots yet"}), 404

    inv = c.execute(
        """SELECT * FROM inventory_snapshots
            WHERE msku_code = ? AND branch_code = ? AND snapshot_date = ?""",
        (msku, branch, latest_date),
    ).fetchone()
    master = c.execute(
        "SELECT * FROM msku_master WHERE msku_code = ?", (msku,)
    ).fetchone()
    if inv is None or master is None:
        return jsonify({"error": "row not found"}), 404

    with db.tx() as conn:
        if inv_updates:
            sets = ", ".join(f"{k} = ?" for k in inv_updates)
            conn.execute(
                f"""UPDATE inventory_snapshots SET {sets}
                     WHERE msku_code = ? AND branch_code = ? AND snapshot_date = ?""",
                (*inv_updates.values(), msku, branch, latest_date),
            )
        if master_updates:
            if "doc" in master_updates and master_updates["doc"] <= 0:
                master_updates["doc"] = 0.0001
            for k in ("ltf", "vf"):
                if k in master_updates:
                    master_updates[k] = max(0.0, min(1.0, master_updates[k]))
            sets = ", ".join(f"{k} = ?" for k in master_updates) + ", updated_at = CURRENT_TIMESTAMP"
            conn.execute(
                f"UPDATE msku_master SET {sets} WHERE msku_code = ?",
                (*master_updates.values(), msku),
            )

        merged_inv = {**dict(inv), **inv_updates}
        merged_master = {**dict(master), **master_updates}
        kwargs = dict(
            sales_90d=merged_inv.get("sales_90d") or 0.0,
            adu_days=merged_inv.get("adu_days") or 90,
            on_hand_qty=merged_inv.get("on_hand_qty") or 0.0,
            on_order_qty=merged_inv.get("on_order_qty") or 0.0,
            qualified_demand_qty=merged_inv.get("qualified_demand_qty") or 0.0,
            moq=merged_master.get("moq") or 0.0,
            lead_time=merged_master.get("lead_time") or 0.0,
            dlt=merged_master.get("dlt") or 0.0,
            ltf=merged_master.get("ltf") or 0.0,
            vf=merged_master.get("vf") or 0.0,
            doc=merged_master.get("doc") or 1.0,
        )
        outputs = compute(EngineInputs(**kwargs))
        source = {f"source_{k}": merged_inv.get(f"source_{k}") for k in
                  ("adu", "red", "yellow", "green", "tog", "net_flow", "order_recommendation")}
        diffs = compute_diffs(outputs, source)

        conn.execute(
            """UPDATE planning_snapshots SET
                  adu = ?, red_zone = ?, yellow_zone = ?, green_zone = ?,
                  tor = ?, toy = ?, tog = ?, net_flow = ?, planning_priority = ?,
                  order_recommendation = ?, alert_level = ?,
                  engine_minus_source_adu = ?, engine_minus_source_red = ?,
                  engine_minus_source_yellow = ?, engine_minus_source_green = ?,
                  engine_minus_source_tog = ?, engine_minus_source_net_flow = ?,
                  engine_minus_source_order_recommendation = ?, flagged_diff = ?,
                  calculated_at = CURRENT_TIMESTAMP
                WHERE msku_code = ? AND branch_code = ? AND snapshot_date = ?""",
            (
                outputs.adu, outputs.red_zone, outputs.yellow_zone, outputs.green_zone,
                outputs.tor, outputs.toy, outputs.tog,
                outputs.net_flow, outputs.planning_priority,
                outputs.order_recommendation, outputs.alert_level,
                diffs.get("engine_minus_source_adu"),
                diffs.get("engine_minus_source_red"),
                diffs.get("engine_minus_source_yellow"),
                diffs.get("engine_minus_source_green"),
                diffs.get("engine_minus_source_tog"),
                diffs.get("engine_minus_source_net_flow"),
                diffs.get("engine_minus_source_order_recommendation"),
                1 if diffs.get("flagged_diff") else 0,
                msku, branch, latest_date,
            ),
        )

    return jsonify({"msku_code": msku, "branch_code": branch, **outputs.as_dict()})
