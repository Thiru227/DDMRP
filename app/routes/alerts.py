"""Alerts API: derived live from the latest planning snapshot."""
from flask import Blueprint, jsonify, request

from app.repositories import db

bp = Blueprint("alerts", __name__, url_prefix="/api/alerts")


@bp.get("/")
def list_alerts():
    severity = request.args.get("severity")  # 'red' | 'yellow'
    branch = request.args.get("branch")

    c = db.conn()
    latest_date = c.execute(
        "SELECT MAX(snapshot_date) AS d FROM planning_snapshots"
    ).fetchone()["d"]
    if not latest_date:
        return jsonify({"snapshot_date": None, "alerts": [], "counts": {"red": 0, "yellow": 0}})

    where = ["p.snapshot_date = ?"]
    params: list = [latest_date]
    if severity in {"red", "yellow"}:
        where.append("p.alert_level = ?")
        params.append(severity)
    elif severity != "all":
        # default: only red/yellow for planner alerts view
        where.append("p.alert_level IN ('red','yellow')")
    if branch:
        where.append("p.branch_code = ?")
        params.append(branch)

    rows = [dict(r) for r in c.execute(
        f"""SELECT p.msku_code, p.branch_code, p.alert_level, p.net_flow,
                   p.red_zone, p.toy, p.tog, p.order_recommendation,
                   p.planning_priority, p.adu,
                   i.on_hand_qty, i.on_order_qty, i.qualified_demand_qty,
                   COALESCE(m.display_name, p.msku_code) AS display_name,
                   COALESCE(m.short_code,   p.msku_code) AS short_code,
                   COALESCE(m.moq, 0) AS moq
              FROM planning_snapshots p
              LEFT JOIN msku_master m ON m.msku_code = p.msku_code
              LEFT JOIN inventory_snapshots i
                     ON i.msku_code = p.msku_code
                    AND i.branch_code = p.branch_code
                    AND i.snapshot_date = p.snapshot_date
             WHERE {' AND '.join(where)}
             ORDER BY p.alert_level = 'red' DESC, p.planning_priority ASC""",
        params,
    )]

    counts_row = c.execute(
        """SELECT SUM(alert_level = 'red')    AS red,
                  SUM(alert_level = 'yellow') AS yellow
             FROM planning_snapshots
            WHERE snapshot_date = ?""",
        (latest_date,),
    ).fetchone()

    return jsonify({
        "snapshot_date": latest_date,
        "counts": {"red": counts_row["red"] or 0, "yellow": counts_row["yellow"] or 0},
        "alerts": rows,
    })
