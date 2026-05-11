"""Uploads API: accept a legacy CSV, preview parsed rows, commit to snapshots."""
from __future__ import annotations

import json
import uuid
from datetime import date
from io import StringIO

from flask import Blueprint, jsonify, request

from app.calculations.ddmrp_engine import EngineInputs, compute, compute_diffs
from app.repositories import db
from app.uploads.legacy_parser import (
    _derive_short_code,
    _extract_display_name,
    iter_engine_inputs,
    parse_legacy,
)
from app.uploads.sales_parser import parse_sales

bp = Blueprint("uploads", __name__, url_prefix="/api/uploads")


@bp.post("/stock")
def upload_stock():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "missing file"}), 400

    raw = file.stream.read()
    text = raw.decode("utf-8-sig", errors="replace") if isinstance(raw, bytes) else raw

    parsed = parse_legacy(StringIO(text))
    if parsed["missing_fields"]:
        return jsonify({
            "error": "missing required columns",
            "missing_fields": parsed["missing_fields"],
        }), 422

    rows = parsed["data"]
    job_id = uuid.uuid4().hex
    uploaded_by = (request.form.get("uploaded_by") or "").strip() or None

    with db.tx() as c:
        c.execute(
            """
            INSERT INTO upload_jobs (id, filename, format, uploaded_by,
                                     total_rows, valid_rows, invalid_rows,
                                     status, staged_rows)
            VALUES (?, ?, 'legacy', ?, ?, ?, 0, 'preview', ?)
            """,
            (
                job_id,
                file.filename,
                uploaded_by,
                len(rows),
                len(rows),
                json.dumps(rows),
            ),
        )

    return jsonify({
        "job_id": job_id,
        "filename": file.filename,
        "total_rows": len(rows),
        "valid_rows": len(rows),
        "preview": rows[:25],
        "warnings": parsed["warnings"],
    })


@bp.post("/sales")
def upload_sales():
    file = request.files.get("file")
    if file is None or not file.filename:
        return jsonify({"error": "missing file"}), 400

    parsed = parse_sales(file.stream)
    if parsed["missing_fields"]:
        return jsonify({"error": "missing required columns",
                        "missing_fields": parsed["missing_fields"]}), 422

    rows = parsed["data"]
    job_id = uuid.uuid4().hex
    uploaded_by = (request.form.get("uploaded_by") or "").strip() or None

    with db.tx() as c:
        c.execute(
            """INSERT INTO upload_jobs (id, filename, format, uploaded_by,
                                        total_rows, valid_rows, invalid_rows,
                                        status, staged_rows)
               VALUES (?, ?, 'sales', ?, ?, ?, 0, 'preview', ?)""",
            (job_id, file.filename, uploaded_by,
             len(rows), len(rows), json.dumps(rows)),
        )

    return jsonify({
        "job_id": job_id,
        "filename": file.filename,
        "total_rows": len(rows),
        "valid_rows": len(rows),
        "preview": rows[:25],
        "warnings": parsed["warnings"],
    })


@bp.post("/<job_id>/commit")
def commit_upload(job_id: str):
    snapshot_date = (request.json or {}).get("snapshot_date") if request.is_json else None
    snapshot_date = snapshot_date or date.today().isoformat()

    c = db.conn()
    job = c.execute(
        "SELECT id, status, staged_rows FROM upload_jobs WHERE id = ?",
        (job_id,),
    ).fetchone()
    if job is None:
        return jsonify({"error": "job not found"}), 404
    if job["status"] != "preview":
        return jsonify({"error": f"job is {job['status']}, not preview"}), 409

    rows = json.loads(job["staged_rows"] or "[]")
    job_format = c.execute("SELECT format FROM upload_jobs WHERE id = ?",
                           (job_id,)).fetchone()["format"]
    is_sales = job_format == "sales"
    parsed = {"data": rows}

    inv_count = 0
    plan_count = 0

    with db.tx() as c:
        for row in rows:
            if is_sales:
                _fill_master_params_for_sales(c, row)
            else:
                _upsert_msku(c, row)
            _upsert_branch(c, row["branch_code"])

        for msku, branch, kwargs, source in iter_engine_inputs(parsed):
            c.execute(
                """
                INSERT OR REPLACE INTO inventory_snapshots
                  (msku_code, branch_code, snapshot_date,
                   on_hand_qty, on_order_qty, qualified_demand_qty,
                   sales_90d, adu_days,
                   source_adu, source_red, source_yellow, source_green,
                   source_tog, source_net_flow, source_order_recommendation,
                   uploaded_by, upload_job_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msku, branch, snapshot_date,
                    kwargs["on_hand_qty"], kwargs["on_order_qty"], kwargs["qualified_demand_qty"],
                    kwargs["sales_90d"], kwargs["adu_days"] or 90,
                    source.get("source_adu"), source.get("source_red"),
                    source.get("source_yellow"), source.get("source_green"),
                    source.get("source_tog"), source.get("source_net_flow"),
                    source.get("source_order_recommendation"),
                    job["id"], job["id"],
                ),
            )
            inv_count += 1

            outputs = compute(EngineInputs(**kwargs))
            diffs = compute_diffs(outputs, source)
            c.execute(
                """
                INSERT OR REPLACE INTO planning_snapshots
                  (msku_code, branch_code, snapshot_date,
                   adu, red_zone, yellow_zone, green_zone,
                   tor, toy, tog, net_flow, planning_priority,
                   order_recommendation, alert_level,
                   engine_minus_source_adu, engine_minus_source_red,
                   engine_minus_source_yellow, engine_minus_source_green,
                   engine_minus_source_tog, engine_minus_source_net_flow,
                   engine_minus_source_order_recommendation, flagged_diff)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    msku, branch, snapshot_date,
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
                ),
            )
            plan_count += 1

        c.execute(
            """
            UPDATE upload_jobs
               SET status = 'committed',
                   committed_at = CURRENT_TIMESTAMP,
                   staged_rows = NULL
             WHERE id = ?
            """,
            (job_id,),
        )

    return jsonify({
        "job_id": job_id,
        "status": "committed",
        "snapshot_date": snapshot_date,
        "inventory_rows": inv_count,
        "planning_rows": plan_count,
    })


@bp.delete("/<job_id>")
def revoke_upload(job_id: str):
    """Revoke a committed upload: delete its snapshots so the data disappears.

    Master rows (msku_master, branches) are kept — they may be referenced by
    other snapshots. Use /api/uploads (DELETE) to wipe everything.
    """
    c = db.conn()
    job = c.execute(
        "SELECT id, status FROM upload_jobs WHERE id = ?", (job_id,)
    ).fetchone()
    if job is None:
        return jsonify({"error": "job not found"}), 404

    with db.tx() as conn:
        plan_deleted = conn.execute(
            """DELETE FROM planning_snapshots
                WHERE (msku_code, branch_code, snapshot_date) IN (
                  SELECT msku_code, branch_code, snapshot_date
                    FROM inventory_snapshots WHERE upload_job_id = ?)""",
            (job_id,),
        ).rowcount
        inv_deleted = conn.execute(
            "DELETE FROM inventory_snapshots WHERE upload_job_id = ?", (job_id,)
        ).rowcount
        conn.execute("DELETE FROM upload_jobs WHERE id = ?", (job_id,))

    return jsonify({
        "job_id": job_id,
        "status": "revoked",
        "inventory_deleted": inv_deleted,
        "planning_deleted": plan_deleted,
    })


@bp.delete("")
def clear_all():
    """Wipe all snapshots and upload jobs. Master tables are preserved."""
    with db.tx() as conn:
        plan = conn.execute("DELETE FROM planning_snapshots").rowcount
        inv  = conn.execute("DELETE FROM inventory_snapshots").rowcount
        jobs = conn.execute("DELETE FROM upload_jobs").rowcount
    return jsonify({"planning_deleted": plan, "inventory_deleted": inv, "jobs_deleted": jobs})


@bp.get("/history")
def history():
    rows = db.conn().execute(
        """
        SELECT id, filename, format, uploaded_by, uploaded_at,
               total_rows, valid_rows, invalid_rows, committed_at, status
          FROM upload_jobs
         ORDER BY uploaded_at DESC
         LIMIT 100
        """
    ).fetchall()
    return jsonify({"jobs": [dict(r) for r in rows]})


def _fill_master_params_for_sales(c, row: dict) -> None:
    """For sales-format rows, fill missing planning params from msku_master."""
    master = c.execute("SELECT * FROM msku_master WHERE msku_code = ?",
                       (row["msku_code"],)).fetchone()
    if master is None:
        row.setdefault("moq", 120.0)
        row.setdefault("lead_time", 15.0)
        row.setdefault("dlt", 10.0)
        row.setdefault("ltf", 0.75)
        row.setdefault("vf", 0.25)
        row.setdefault("doc", 7.0)
        row.setdefault("adu_days", 90.0)
        row.setdefault("qualified_demand_qty", 0.0)
        row.setdefault("on_order_qty", 0.0)
    else:
        row.setdefault("moq",       master["moq"])
        row.setdefault("lead_time", master["lead_time"])
        row.setdefault("dlt",       master["dlt"])
        row.setdefault("ltf",       master["ltf"])
        row.setdefault("vf",        master["vf"])
        row.setdefault("doc",       master["doc"] or 1.0)
        row.setdefault("adu_days",  90.0)
        row.setdefault("qualified_demand_qty", 0.0)
        row.setdefault("on_order_qty", 0.0)


def _upsert_msku(c, row: dict) -> None:
    moq = _nz(row.get("moq"))
    lead_time = _nz(row.get("lead_time"))
    dlt = _nz(row.get("dlt"))
    ltf = _clamp01(row.get("ltf"))
    vf = _clamp01(row.get("vf"))
    doc = _nz(row.get("doc")) or 1.0  # CHECK (doc > 0)

    msku_code = row["msku_code"]
    display_name = _extract_display_name(msku_code)
    short_code = _derive_short_code(msku_code)

    c.execute(
        """
        INSERT INTO msku_master
          (msku_code, product_classification, style, fit, brand, season,
           price_range, size, mrp, moq, lead_time, dlt, ltf, vf, doc,
           display_name, short_code, updated_at)
        VALUES (?, ?, NULL, NULL, NULL, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ON CONFLICT(msku_code) DO UPDATE SET
            product_classification = excluded.product_classification,
            season      = excluded.season,
            price_range = excluded.price_range,
            size        = excluded.size,
            mrp         = excluded.mrp,
            moq         = excluded.moq,
            lead_time   = excluded.lead_time,
            dlt         = excluded.dlt,
            ltf         = excluded.ltf,
            vf          = excluded.vf,
            doc         = excluded.doc,
            display_name = excluded.display_name,
            short_code   = excluded.short_code,
            updated_at  = CURRENT_TIMESTAMP
        """,
        (
            msku_code,
            row.get("product_classification"),
            row.get("season"),
            row.get("price_range"),
            row.get("size"),
            row.get("mrp"),
            moq, lead_time, dlt, ltf, vf, doc,
            display_name, short_code,
        ),
    )


def _upsert_branch(c, branch_code: str) -> None:
    c.execute(
        "INSERT OR IGNORE INTO branches (branch_code, display_name) VALUES (?, ?)",
        (branch_code, branch_code),
    )


def _nz(v) -> float:
    try:
        return max(0.0, float(v or 0))
    except (TypeError, ValueError):
        return 0.0


def _clamp01(v) -> float:
    try:
        f = float(v or 0)
    except (TypeError, ValueError):
        return 0.0
    if f < 0:
        return 0.0
    if f > 1:
        return 1.0
    return f
