from flask import Blueprint, jsonify, request

from app.repositories import db

bp = Blueprint("dashboard", __name__, url_prefix="/api/dashboard")


@bp.get("/")
@bp.get("/summary")
def summary():
    c = db.conn()
    latest_date = c.execute(
        "SELECT MAX(snapshot_date) AS d FROM planning_snapshots"
    ).fetchone()["d"]

    kpis = {"total_skus": 0, "red": 0, "yellow": 0, "healthy": 0,
            "order_recommendation_total": 0.0, "flagged_diff": 0,
            "snapshot_date": latest_date,
            "pending_slips": 0, "released_slips": 0}
    branches: list[dict] = []
    recent_uploads: list[dict] = []

    if latest_date:
        row = c.execute(
            """SELECT COUNT(DISTINCT msku_code)           AS total_mskus,
                      COUNT(*)                            AS total_skus,
                      SUM(alert_level = 'red')            AS red,
                      SUM(alert_level = 'yellow')         AS yellow,
                      SUM(alert_level = 'healthy')        AS healthy,
                      COALESCE(SUM(order_recommendation), 0) AS order_total,
                      SUM(flagged_diff)                   AS flagged_diff
                 FROM planning_snapshots WHERE snapshot_date = ?""",
            (latest_date,),
        ).fetchone()
        kpis.update({
            "total_mskus": row["total_mskus"] or 0,
            "total_skus": row["total_skus"] or 0,
            "red": row["red"] or 0,
            "yellow": row["yellow"] or 0,
            "healthy": row["healthy"] or 0,
            "order_recommendation_total": float(row["order_total"] or 0.0),
            "flagged_diff": row["flagged_diff"] or 0,
        })
        branches = [dict(r) for r in c.execute(
            """SELECT branch_code,
                      COUNT(*)                                AS skus,
                      SUM(alert_level = 'red')                AS red,
                      SUM(alert_level = 'yellow')             AS yellow,
                      SUM(alert_level = 'healthy')            AS healthy,
                      COALESCE(SUM(order_recommendation), 0)  AS order_total
                 FROM planning_snapshots WHERE snapshot_date = ?
                GROUP BY branch_code ORDER BY red DESC, yellow DESC, branch_code""",
            (latest_date,),
        )]

    slip_row = c.execute(
        """SELECT SUM(status = 'pending_release') AS pending,
                  SUM(status = 'released')        AS released
             FROM requirement_slips"""
    ).fetchone()
    if slip_row:
        kpis["pending_slips"]  = slip_row["pending"]  or 0
        kpis["released_slips"] = slip_row["released"] or 0

    recent_uploads = [dict(r) for r in c.execute(
        """SELECT id, filename, format, status, uploaded_at, committed_at,
                  total_rows, valid_rows, invalid_rows
             FROM upload_jobs ORDER BY uploaded_at DESC LIMIT 5"""
    )]
    return jsonify({"kpis": kpis, "branches": branches, "recent_uploads": recent_uploads})


@bp.get("/msku")
def list_msku():
    """List all MSKUs with display names — for the MSKU Master admin page."""
    c = db.conn()
    rows = c.execute(
        """SELECT msku_code, product_classification, season, price_range,
                  size, mrp, moq, lead_time, dlt, ltf, vf, doc, active,
                  COALESCE(display_name, msku_code) AS display_name,
                  COALESCE(short_code,   msku_code) AS short_code
             FROM msku_master ORDER BY display_name"""
    ).fetchall()
    return jsonify({"mskus": [dict(r) for r in rows]})


@bp.get("/branches")
def list_branches():
    c = db.conn()
    rows = c.execute("SELECT * FROM branches ORDER BY branch_code").fetchall()
    return jsonify({"branches": [dict(r) for r in rows]})


@bp.patch("/branches/<code>")
def update_branch(code: str):
    data = request.get_json(silent=True) or {}
    allowed = {"display_name", "active"}
    updates = {k: v for k, v in data.items() if k in allowed}
    if not updates:
        return jsonify({"error": "no valid fields"}), 400
    sets = ", ".join(f"{k} = ?" for k in updates)
    with db.tx() as c:
        c.execute(f"UPDATE branches SET {sets} WHERE branch_code = ?",
                  (*updates.values(), code.upper()))
    return jsonify({"branch_code": code, "ok": True})
