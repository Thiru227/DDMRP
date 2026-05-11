import csv
import io
import json
import os
import re
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, g, jsonify, render_template, request, session

DB = "ddmrp_v2.db"

import math

_GARMENT_RE = re.compile(
    r"(INNER|OUTER|VEST|BRIEFS|TRUNK|BOXER|SHORT|BRIEF|BOTTOM|TOP|RIB|PANTS|SHORTS|GYM)"
)
_ABBREVS = {"RN", "RNS", "LT", "OTB"}


def display_name(msku_code: str) -> str:
    upper = re.sub(r"\s+", " ", msku_code.strip()).upper()
    m = re.search(r"SOLID(.+?)(?:CLASSIC|POOMEX)", upper)
    if not m:
        return msku_code[:60]
    raw = m.group(1).strip()
    spaced = _GARMENT_RE.sub(r" \1", raw).strip()
    spaced = re.sub(r"\s+", " ", spaced)
    words = [w if w in _ABBREVS else w.title() for w in spaced.split()]
    name = " ".join(words)
    if "PREMIUM" in upper:
        name += " Prm"
    elif "ECONOMIC" in upper:
        seg = ""
        if "ACTIVE WEAR" in upper:
            seg = " Active"
        elif "DAILY WEAR" in upper:
            seg = " Daily"
        name += seg
    return name or msku_code[:60]


def pnum(s) -> float:
    if s is None:
        return 0.0
    try:
        return float(str(s).replace("%", "").replace(",", "").strip() or 0)
    except ValueError:
        return 0.0


def pp_status(pp: float) -> str:
    if pp < 0:
        return "red"
    if pp < 50:
        return "yellow"
    if pp < 100:
        return "green"
    return "blue"


def _derive_product_code(msku_code: str) -> str:
    upper = re.sub(r"\s+", " ", msku_code.strip()).upper()

    cat = "MI" if "MENS INNER WEAR" in upper or "MENSINNER WEAR" in upper else "GEN"

    if "PREMIUM" in upper:
        tier = "PRM"
    elif "ECONOMIC" in upper:
        tier = "ECO"
    else:
        tier = "STD"

    if "ACTIVE WEAR" in upper:
        occ = "ACT"
    elif "DAILY WEAR" in upper:
        occ = "DAI"
    else:
        occ = "GEN"

    style = "XX"
    m = re.search(r"SOLID(.+?)(?:CLASSIC|POOMEX)", upper)
    if m:
        raw = re.sub(r"\s+", " ", m.group(1).strip())
        raw = _GARMENT_RE.sub(r" \1", raw).strip()
        raw = re.sub(r"\s+", " ", raw)
        words = [w for w in raw.split() if w]
        if words:
            abbrev_map = {
                "GYM VEST": "GV", "GYM": "GV", "VEST": "VS",
                "BRIEFS": "BR", "BRIEF": "BR",
                "TRUNK": "TR",
                "BOXER": "BX", "BOXERS": "BX",
                "SHORTS": "SH", "SHORT": "SH",
                "RIB": "RB",
                "PANTS": "PT",
            }
            key1 = " ".join(words[:2]) if len(words) >= 2 else words[0]
            if key1 in abbrev_map:
                style = abbrev_map[key1]
            elif words[0] in abbrev_map:
                style = abbrev_map[words[0]]
            else:
                style = "".join(w[0] for w in words[:2]).upper() or "XX"

    return f"{cat}-{tier}-{occ}-{style}"


def _recompute_ddmrp(m: dict) -> dict:
    sales_90d = float(m.get("sales_90d") or 0)
    dlt       = float(m.get("dlt")       or 0)
    ltf       = float(m.get("ltf")       or 0)
    vf        = float(m.get("vf")        or 0)  # noqa: F841 (reserved for future red-safety calc)
    doc       = float(m.get("doc")       or 1)
    moq       = float(m.get("moq")       or 1)
    on_hand   = float(m.get("on_hand")   or 0)
    on_order  = float(m.get("on_order")  or 0)

    adu    = sales_90d / 90.0
    red    = adu * dlt * ltf
    yellow = adu * doc
    green  = max(moq, yellow)
    tor    = red + yellow
    toy    = tor + yellow
    tog    = tor + green
    nfp    = on_hand + on_order
    pp     = (nfp / tog * 100.0) if tog > 0 else 0.0
    order_rec = (math.ceil((tog - nfp) / moq) * moq) if (nfp < tor and moq > 0) else 0.0

    return {
        "adu":          round(adu, 2),
        "tor":          round(tor, 2),
        "toy":          round(toy, 2),
        "tog":          round(tog, 2),
        "nfp":          round(nfp, 1),
        "plan_priority": round(pp, 1),
        "order_rec":    round(order_rec, 0),
        "status":       pp_status(pp),
    }


# ── DB ───────────────────────────────────────────────────────────────────────

def get_db():
    if "db" not in g:
        conn = sqlite3.connect(DB)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        g.db = conn
    return g.db


def init_db():
    conn = sqlite3.connect(DB)
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS mskus (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            msku_code   TEXT UNIQUE NOT NULL,
            display_nm  TEXT,
            sales_90d   REAL DEFAULT 0,
            adu         REAL DEFAULT 0,
            dlt         REAL DEFAULT 10,
            ltf         REAL DEFAULT 0.75,
            vf          REAL DEFAULT 0.25,
            doc         REAL DEFAULT 7,
            tor         REAL DEFAULT 0,
            toy         REAL DEFAULT 0,
            tog         REAL DEFAULT 0,
            on_hand     REAL DEFAULT 0,
            on_order    REAL DEFAULT 0,
            nfp         REAL DEFAULT 0,
            plan_priority REAL DEFAULT 0,
            order_rec   REAL DEFAULT 0,
            sizes       TEXT DEFAULT '[]',
            mrp_bands   TEXT DEFAULT '[]',
            moq         REAL DEFAULT 120,
            lead_time   REAL DEFAULT 10,
            colours     TEXT DEFAULT '["White","Black","Navy","Grey"]',
            segment     TEXT DEFAULT '',
            occasion    TEXT DEFAULT '',
            updated_at  TEXT,
            product_code TEXT
        );
        CREATE TABLE IF NOT EXISTS upload_logs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            filename    TEXT,
            fmt         TEXT,
            row_count   INTEGER,
            uploaded_by TEXT,
            uploaded_at TEXT DEFAULT (datetime('now')),
            revoked     INTEGER DEFAULT 0,
            revoked_at  TEXT
        );
        CREATE TABLE IF NOT EXISTS order_recs (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slip_no     TEXT UNIQUE,
            msku_id     INTEGER REFERENCES mskus(id),
            order_qty   REAL DEFAULT 0,
            notes       TEXT DEFAULT '',
            status      TEXT DEFAULT 'draft',
            allocation_json TEXT DEFAULT '{}',
            created_by  TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            sent_at     TEXT
        );
        CREATE TABLE IF NOT EXISTS requirement_slips (
            id          INTEGER PRIMARY KEY AUTOINCREMENT,
            slip_no     TEXT UNIQUE,
            order_rec_id INTEGER REFERENCES order_recs(id),
            lines_json  TEXT DEFAULT '[]',
            status      TEXT DEFAULT 'pending',
            created_by  TEXT,
            created_at  TEXT DEFAULT (datetime('now')),
            released_at TEXT
        );
    """)
    conn.commit()
    # Idempotent migration for existing DBs
    try:
        conn.execute("ALTER TABLE mskus ADD COLUMN product_code TEXT")
        conn.commit()
    except Exception:
        pass
    conn.close()


# ── Flask app ────────────────────────────────────────────────────────────────

app = Flask(__name__, template_folder="app/templates")
app.secret_key = os.environ.get("SECRET_KEY", "ddmrp-demo-secret-2024")


@app.teardown_appcontext
def close_db(e=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


# ── Auth ─────────────────────────────────────────────────────────────────────

_USERS = {
    "admin":   ("admin123",   "admin"),
    "planner": ("plan123",    "planner"),
    "executor":("exec123",    "executor"),
}


def _require(role):
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            if session.get("role") != role:
                return jsonify({"error": "Forbidden"}), 403
            return f(*args, **kwargs)
        return wrapper
    return decorator


def _logged_in(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        if not session.get("role"):
            return jsonify({"error": "Not authenticated"}), 401
        return f(*args, **kwargs)
    return wrapper


@app.get("/")
def index():
    return render_template("demo.html")


@app.post("/api/auth/login")
def login():
    data = request.get_json(force=True)
    username = (data.get("username") or "").strip()
    password = (data.get("password") or "").strip()
    if username not in _USERS:
        return jsonify({"error": "Invalid credentials"}), 401
    pwd, role = _USERS[username]
    if pwd != password:
        return jsonify({"error": "Invalid credentials"}), 401
    session["username"] = username
    session["role"] = role
    return jsonify({"ok": True, "role": role, "username": username})


@app.post("/api/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


# ── CSV helpers ──────────────────────────────────────────────────────────────

def _auto_fmt(rows):
    if not rows:
        return None
    for r in rows[:5]:
        if r and "MASTER SKU CODE" in (r[0] or ""):
            return "hub"
    for r in rows[:5]:
        if r and r[0].strip() == "S.NO":
            return "branch"
    return None


def _parse_hub(rows):
    # Skip the multi-row preamble; find the data header row (contains MASTER SKU CODE)
    hdr_idx = None
    for i, r in enumerate(rows):
        if r and "MASTER SKU CODE" in r[0]:
            hdr_idx = i
            break
    if hdr_idx is None:
        return []

    results = []
    for r in rows[hdr_idx + 1:]:
        if not r or not r[0].strip() or r[0].strip().lower().startswith("grand"):
            continue
        code = r[0].strip()
        rec = {
            "msku_code":    code,
            "display_nm":   display_name(code),
            "product_code": _derive_product_code(code),
            "sales_90d":    pnum(r[1] if len(r) > 1 else 0),
            "on_hand":      pnum(r[22] if len(r) > 22 else 0),
            "on_order":     pnum(r[23] if len(r) > 23 else 0),
            "adu":          pnum(r[4] if len(r) > 4 else 0),
            "ltf":          pnum(r[5] if len(r) > 5 else 0.75),
            "vf":           pnum(r[6] if len(r) > 6 else 0.25),
            "dlt":          pnum(r[7] if len(r) > 7 else 10),
            "doc":          pnum(r[8] if len(r) > 8 else 7),
            "tor":          pnum(r[17] if len(r) > 17 else 0),
            "toy":          pnum(r[18] if len(r) > 18 else 0),
            "tog":          pnum(r[19] if len(r) > 19 else 0),
            "nfp":          pnum(r[24] if len(r) > 24 else 0),
            "plan_priority": pnum(r[25] if len(r) > 25 else 0),
            "order_rec":    pnum(r[26] if len(r) > 26 else 0),
        }
        results.append(rec)
    return results


def _parse_branch(rows):
    hdr_idx = None
    for i, r in enumerate(rows):
        if r and r[0].strip() == "S.NO":
            hdr_idx = i
            break
    if hdr_idx is None:
        return []

    # col indices from header row inspection:
    # 1=MASTER SKU, 3=LEAD TIME, 4=PRICE RANGE, 5=SIZE, 7=MRP, 11=MOQ,
    # 12=SEASON, 13=BRANCH, 14=90 DAY SAL, 15=SHOP STK, 36=TOR, 37=TOY, 38=TOG,
    # 45=PLAN PRIORTY, 46=ORDER RECOM
    by_msku: dict = {}
    for r in rows[hdr_idx + 1:]:
        if not r or not r[0].strip():
            continue
        code = r[1].strip() if len(r) > 1 else ""
        if not code or code.lower().startswith("grand") or code.lower() == "master sku":
            continue
        if code not in by_msku:
            by_msku[code] = {
                "msku_code": code,
                "display_nm": display_name(code),
                "product_code": _derive_product_code(code),
                "lead_time": pnum(r[3] if len(r) > 3 else 10),
                "sizes": r[5].strip() if len(r) > 5 else "",
                "mrp_raw": r[7].strip() if len(r) > 7 else "",
                "moq": pnum(r[11] if len(r) > 11 else 120),
                "sales_90d": 0.0,
                "on_hand": 0.0,
                "tor": 0.0, "toy": 0.0, "tog": 0.0,
                "plan_priority": 0.0,
                "order_rec": 0.0,
                "_tor_found": False,
            }
        agg = by_msku[code]
        agg["sales_90d"] += pnum(r[14] if len(r) > 14 else 0)
        agg["on_hand"] += pnum(r[15] if len(r) > 15 else 0)
        tor = pnum(r[36] if len(r) > 36 else 0)
        if not agg["_tor_found"] and tor > 0:
            agg["tor"] = tor
            agg["toy"] = pnum(r[37] if len(r) > 37 else 0)
            agg["tog"] = pnum(r[38] if len(r) > 38 else 0)
            agg["plan_priority"] = pnum(r[45] if len(r) > 45 else 0)
            agg["order_rec"] = pnum(r[46] if len(r) > 46 else 0)
            agg["_tor_found"] = True

    results = []
    for code, agg in by_msku.items():
        adu = agg["sales_90d"] / 90.0 if agg["sales_90d"] > 0 else 0
        nfp = agg["on_hand"] - 0  # simplified: NFP = OH + OO - QD (OO/QD=0 here)
        sizes_list = [s.strip() for s in agg["sizes"].split(",") if s.strip()] if agg["sizes"] else []
        mrp_list = [s.strip() for s in agg["mrp_raw"].split(",") if s.strip()] if agg["mrp_raw"] else []
        results.append({
            "msku_code":    code,
            "display_nm":   agg["display_nm"],
            "product_code": agg["product_code"],
            "sales_90d":    agg["sales_90d"],
            "adu":          round(adu, 2),
            "on_hand":      agg["on_hand"],
            "on_order":     0.0,
            "nfp":          round(nfp, 1),
            "tor":          agg["tor"],
            "toy":          agg["toy"],
            "tog":          agg["tog"],
            "plan_priority": agg["plan_priority"],
            "order_rec":    agg["order_rec"],
            "sizes":        json.dumps(sizes_list),
            "mrp_bands":    json.dumps(mrp_list),
            "moq":          agg["moq"],
            "lead_time":    agg["lead_time"],
        })
        agg.pop("_tor_found", None)
    return results


# ── Upload routes ─────────────────────────────────────────────────────────────

@app.post("/api/upload")
@_require("admin")
def upload_csv():
    f = request.files.get("file")
    if not f:
        return jsonify({"error": "No file"}), 400
    raw = f.read().decode("utf-8-sig", errors="replace")
    rows = list(csv.reader(io.StringIO(raw)))

    # type hint from form overrides auto-detect
    upload_type = (request.form.get("type") or "").strip().lower()
    if upload_type == "msku":
        fmt = "branch"
    elif upload_type == "sales":
        fmt = "hub"
    else:
        fmt = _auto_fmt(rows)

    if fmt == "hub":
        records = _parse_hub(rows)
    elif fmt == "branch":
        records = _parse_branch(rows)
    else:
        return jsonify({"error": "No data parsed — check file format"}), 400

    if not records:
        return jsonify({"error": "No data parsed — check file format"}), 400

    db = get_db()
    now = datetime.utcnow().isoformat()
    for rec in records:
        pc = rec.get("product_code") or _derive_product_code(rec["msku_code"])
        if fmt == "hub":
            existing = db.execute(
                "SELECT sizes, mrp_bands, moq, lead_time FROM mskus WHERE msku_code=?",
                (rec["msku_code"],)
            ).fetchone()
            db.execute("""
                INSERT INTO mskus (msku_code,display_nm,product_code,sales_90d,adu,dlt,ltf,vf,doc,
                    tor,toy,tog,on_hand,on_order,nfp,plan_priority,order_rec,updated_at)
                VALUES (:msku_code,:display_nm,:product_code,:sales_90d,:adu,:dlt,:ltf,:vf,:doc,
                    :tor,:toy,:tog,:on_hand,:on_order,:nfp,:plan_priority,:order_rec,:now)
                ON CONFLICT(msku_code) DO UPDATE SET
                    display_nm=excluded.display_nm,
                    product_code=excluded.product_code,
                    sales_90d=excluded.sales_90d,
                    adu=excluded.adu,
                    dlt=excluded.dlt,
                    ltf=excluded.ltf,
                    vf=excluded.vf,
                    doc=excluded.doc,
                    tor=excluded.tor,
                    toy=excluded.toy,
                    tog=excluded.tog,
                    on_hand=excluded.on_hand,
                    on_order=excluded.on_order,
                    nfp=excluded.nfp,
                    plan_priority=excluded.plan_priority,
                    order_rec=excluded.order_rec,
                    updated_at=excluded.updated_at
            """, {**rec, "product_code": pc, "now": now,
                  "dlt": rec.get("dlt", 10), "ltf": rec.get("ltf", 0.75),
                  "vf": rec.get("vf", 0.25), "doc": rec.get("doc", 7),
                  "nfp": rec.get("nfp", 0)})
            if existing:
                db.execute("""
                    UPDATE mskus SET sizes=?, mrp_bands=?, moq=?, lead_time=?
                    WHERE msku_code=? AND (sizes IS NULL OR sizes='[]')
                """, (existing["sizes"], existing["mrp_bands"],
                      existing["moq"], existing["lead_time"], rec["msku_code"]))
        else:
            db.execute("""
                INSERT INTO mskus (msku_code,display_nm,product_code,sales_90d,adu,on_hand,on_order,
                    nfp,tor,toy,tog,plan_priority,order_rec,sizes,mrp_bands,moq,lead_time,updated_at)
                VALUES (:msku_code,:display_nm,:product_code,:sales_90d,:adu,:on_hand,:on_order,
                    :nfp,:tor,:toy,:tog,:plan_priority,:order_rec,:sizes,:mrp_bands,:moq,:lead_time,:now)
                ON CONFLICT(msku_code) DO UPDATE SET
                    display_nm=excluded.display_nm,
                    product_code=excluded.product_code,
                    sizes=excluded.sizes,
                    mrp_bands=excluded.mrp_bands,
                    moq=excluded.moq,
                    lead_time=excluded.lead_time,
                    updated_at=excluded.updated_at
            """, {**rec, "product_code": pc, "now": now})

    db.execute("""
        INSERT INTO upload_logs (filename,fmt,row_count,uploaded_by,uploaded_at)
        VALUES (?,?,?,?,?)
    """, (f.filename, fmt, len(records), session.get("username"), now))
    db.commit()
    return jsonify({"ok": True, "count": len(records), "format": fmt})


@app.get("/api/uploads")
@_require("admin")
def list_uploads():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM upload_logs ORDER BY uploaded_at DESC"
    ).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/uploads/<int:uid>/revoke")
@_require("admin")
def revoke_upload(uid):
    db = get_db()
    db.execute(
        "UPDATE upload_logs SET revoked=1, revoked_at=? WHERE id=?",
        (datetime.utcnow().isoformat(), uid)
    )
    db.commit()
    return jsonify({"ok": True})


# ── MSKU routes ───────────────────────────────────────────────────────────────

@app.get("/api/mskus")
@_require("planner")
def list_mskus():
    db = get_db()
    rows = db.execute(
        "SELECT * FROM mskus ORDER BY plan_priority ASC"
    ).fetchall()
    result = []
    for r in rows:
        d = dict(r)
        d["status"] = pp_status(d["plan_priority"])
        try:
            d["sizes"] = json.loads(d["sizes"] or "[]")
        except Exception:
            d["sizes"] = []
        try:
            d["mrp_bands"] = json.loads(d["mrp_bands"] or "[]")
        except Exception:
            d["mrp_bands"] = []
        try:
            d["colours"] = json.loads(d["colours"] or '["White","Black","Navy","Grey"]')
        except Exception:
            d["colours"] = ["White", "Black", "Navy", "Grey"]
        result.append(d)
    return jsonify(result)


@app.get("/api/mskus/<int:mid>")
@_logged_in
def get_msku(mid):
    db = get_db()
    r = db.execute("SELECT * FROM mskus WHERE id=?", (mid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    d = dict(r)
    d["status"] = pp_status(d["plan_priority"])
    for field in ("sizes", "mrp_bands", "colours"):
        try:
            d[field] = json.loads(d[field] or "[]")
        except Exception:
            d[field] = []
    if not d["colours"]:
        d["colours"] = ["White", "Black", "Navy", "Grey"]
    return jsonify(d)


@app.patch("/api/mskus/<int:mid>")
@_require("planner")
def patch_msku(mid):
    data = request.get_json(force=True)
    allowed = {"on_hand", "on_order", "dlt", "ltf", "vf", "doc", "moq"}
    updates = {}
    for k in allowed:
        if k in data:
            try:
                v = float(data[k])
            except (TypeError, ValueError):
                return jsonify({"error": f"invalid value for {k}"}), 400
            if v < 0:
                return jsonify({"error": f"{k} must be >= 0"}), 400
            updates[k] = v
    if not updates:
        return jsonify({"error": "no valid fields"}), 400

    db = get_db()
    row = db.execute("SELECT * FROM mskus WHERE id=?", (mid,)).fetchone()
    if not row:
        return jsonify({"error": "Not found"}), 404

    merged = dict(row)
    merged.update(updates)

    recomputed = _recompute_ddmrp(merged)
    # 'status' is derived at query time, not stored
    storable = {k: v for k, v in recomputed.items() if k != "status"}

    all_updates = {**updates, **storable}
    sets = ", ".join(f"{k}=?" for k in all_updates)
    vals = list(all_updates.values()) + [datetime.utcnow().isoformat(), mid]
    db.execute(f"UPDATE mskus SET {sets}, updated_at=? WHERE id=?", vals)
    db.commit()

    result = dict(db.execute("SELECT * FROM mskus WHERE id=?", (mid,)).fetchone())
    result["status"] = pp_status(result["plan_priority"])
    for field in ("sizes", "mrp_bands", "colours"):
        try:
            result[field] = json.loads(result[field] or "[]")
        except Exception:
            result[field] = []
    return jsonify(result)


# ── Order rec routes ──────────────────────────────────────────────────────────

def _next_slip(db, prefix):
    year = datetime.utcnow().year
    row = db.execute(
        f"SELECT COUNT(*) as c FROM order_recs WHERE slip_no LIKE '{prefix}-{year}-%'"
    ).fetchone()
    n = (row["c"] if row else 0) + 1
    return f"{prefix}-{year}-{n:03d}"


@app.post("/api/order-recs")
@_require("planner")
def create_order_rec():
    data = request.get_json(force=True)
    msku_id = data.get("msku_id")
    order_qty = pnum(data.get("order_qty", 0))
    notes = data.get("notes", "")
    db = get_db()
    slip_no = _next_slip(db, "OR")
    cur = db.execute("""
        INSERT INTO order_recs (slip_no,msku_id,order_qty,notes,status,created_by,created_at)
        VALUES (?,?,?,?,'draft',?,?)
    """, (slip_no, msku_id, order_qty, notes, session.get("username"),
          datetime.utcnow().isoformat()))
    db.commit()
    return jsonify({"ok": True, "id": cur.lastrowid, "slip_no": slip_no})


@app.get("/api/order-recs/<int:oid>")
@_logged_in
def get_order_rec(oid):
    db = get_db()
    r = db.execute("""
        SELECT o.*, m.display_nm, m.product_code, m.tor, m.toy, m.tog, m.nfp, m.plan_priority,
               m.on_hand, m.on_order, m.moq, m.sizes, m.mrp_bands, m.colours, m.msku_code
        FROM order_recs o JOIN mskus m ON m.id=o.msku_id
        WHERE o.id=?
    """, (oid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    d = dict(r)
    for field in ("sizes", "mrp_bands", "colours"):
        try:
            d[field] = json.loads(d[field] or "[]")
        except Exception:
            d[field] = []
    if not d["colours"]:
        d["colours"] = ["White", "Black", "Navy", "Grey"]
    try:
        d["allocation_json"] = json.loads(d["allocation_json"] or "{}")
    except Exception:
        d["allocation_json"] = {}
    return jsonify(d)


@app.patch("/api/order-recs/<int:oid>")
@_require("planner")
def patch_order_rec(oid):
    db = get_db()
    r = db.execute("SELECT status FROM order_recs WHERE id=?", (oid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    if r["status"] != "draft":
        return jsonify({"error": "Cannot edit after sending"}), 400
    data = request.get_json(force=True)
    fields, vals = [], []
    if "order_qty" in data:
        fields.append("order_qty=?"); vals.append(pnum(data["order_qty"]))
    if "notes" in data:
        fields.append("notes=?"); vals.append(data["notes"])
    if "allocation" in data:
        fields.append("allocation_json=?"); vals.append(json.dumps(data["allocation"]))
    if not fields:
        return jsonify({"ok": True})
    vals.append(oid)
    db.execute(f"UPDATE order_recs SET {','.join(fields)} WHERE id=?", vals)
    db.commit()
    return jsonify({"ok": True})


@app.post("/api/order-recs/<int:oid>/send")
@_require("planner")
def send_order_rec(oid):
    db = get_db()
    r = db.execute("SELECT * FROM order_recs WHERE id=?", (oid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    db.execute("""
        UPDATE order_recs SET status='sent_to_execution', sent_at=?
        WHERE id=? AND status='draft'
    """, (datetime.utcnow().isoformat(), oid))
    db.commit()
    return jsonify({"ok": True})


# ── RS line generation ────────────────────────────────────────────────────────

def _gen_rs_lines(msku: dict, order_qty: float, alloc: dict) -> list:
    mrp_bands = msku.get("mrp_bands") or []
    if isinstance(mrp_bands, str):
        try:
            mrp_bands = json.loads(mrp_bands)
        except Exception:
            mrp_bands = []

    colours = msku.get("colours") or ["White", "Black", "Navy", "Grey"]
    if isinstance(colours, str):
        try:
            colours = json.loads(colours)
        except Exception:
            colours = ["White", "Black", "Navy", "Grey"]

    sizes = msku.get("sizes") or []
    if isinstance(sizes, str):
        try:
            sizes = json.loads(sizes)
        except Exception:
            sizes = []

    lines = []

    if not alloc:
        # Fallback: equal split across MRP bands
        if not mrp_bands:
            mrp_bands = ["DEFAULT"]
        n = len(mrp_bands)
        base = int(order_qty // n)
        rem = int(order_qty) - base * n
        for i, mrp in enumerate(mrp_bands):
            qty = base + (1 if i == n - 1 else 0) * rem
            lines.append({"mrp": str(mrp), "size": "", "colour": "", "design": "", "qty": qty})
        return lines

    mrp_split = alloc.get("mrp_split", {})
    size_color = alloc.get("size_color", {})
    design_split = alloc.get("design_split", {})

    designs = list(design_split.keys()) if design_split else ["DES01"]
    design_pcts = {k: v / 100.0 for k, v in design_split.items()} if design_split else {"DES01": 1.0}

    all_lines = []
    for mrp in (mrp_bands if mrp_bands else ["DEFAULT"]):
        mrp_str = str(mrp)
        mrp_pct = mrp_split.get(mrp_str, 0) / 100.0 if mrp_split else 1.0 / max(len(mrp_bands), 1)
        mrp_qty = order_qty * mrp_pct

        if size_color:
            for colour, size_row in size_color.items():
                for size, cell_pct in size_row.items():
                    sc_qty = mrp_qty * (cell_pct / 100.0) if cell_pct else 0
                    for design, dpct in design_pcts.items():
                        all_lines.append({
                            "mrp": mrp_str, "size": str(size),
                            "colour": colour, "design": design,
                            "qty": sc_qty * dpct
                        })
        else:
            for design, dpct in design_pcts.items():
                all_lines.append({
                    "mrp": mrp_str, "size": "", "colour": "",
                    "design": design, "qty": mrp_qty * dpct
                })

    # Round quantities; put remainder on last line
    total_float = sum(l["qty"] for l in all_lines)
    total_int = int(round(order_qty))
    assigned = 0
    for i, line in enumerate(all_lines):
        if i == len(all_lines) - 1:
            line["qty"] = total_int - assigned
        else:
            q = int(round(line["qty"]))
            line["qty"] = q
            assigned += q

    return [l for l in all_lines if l["qty"] > 0]


# ── Executor routes ───────────────────────────────────────────────────────────

@app.get("/api/executor/inbox")
@_require("executor")
def executor_inbox():
    db = get_db()
    rows = db.execute("""
        SELECT o.id, o.slip_no, o.order_qty, o.sent_at, o.notes,
               m.display_nm, m.msku_code, m.product_code
        FROM order_recs o JOIN mskus m ON m.id=o.msku_id
        WHERE o.status='sent_to_execution'
        ORDER BY o.sent_at DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.post("/api/executor/order-recs/<int:oid>/create-rs")
@_require("executor")
def create_rs(oid):
    db = get_db()
    r = db.execute("""
        SELECT o.*, m.display_nm, m.msku_code, m.sizes, m.mrp_bands, m.colours
        FROM order_recs o JOIN mskus m ON m.id=o.msku_id
        WHERE o.id=?
    """, (oid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    if r["status"] != "sent_to_execution":
        return jsonify({"error": "Order rec not in sent_to_execution status"}), 400

    msku = dict(r)
    for field in ("sizes", "mrp_bands", "colours"):
        try:
            msku[field] = json.loads(msku[field] or "[]")
        except Exception:
            msku[field] = []
    if not msku["colours"]:
        msku["colours"] = ["White", "Black", "Navy", "Grey"]

    try:
        alloc = json.loads(r["allocation_json"] or "{}")
    except Exception:
        alloc = {}

    lines = _gen_rs_lines(msku, r["order_qty"], alloc)

    year = datetime.utcnow().year
    row = db.execute(
        f"SELECT COUNT(*) as c FROM requirement_slips WHERE slip_no LIKE 'RS-{year}-%'"
    ).fetchone()
    n = (row["c"] if row else 0) + 1
    slip_no = f"RS-{year}-{n:03d}"

    cur = db.execute("""
        INSERT INTO requirement_slips (slip_no,order_rec_id,lines_json,status,created_by,created_at)
        VALUES (?,?,?,'pending',?,?)
    """, (slip_no, oid, json.dumps(lines), session.get("username"),
          datetime.utcnow().isoformat()))
    db.execute("UPDATE order_recs SET status='rs_created' WHERE id=?", (oid,))
    db.commit()
    return jsonify({"ok": True, "rs_id": cur.lastrowid, "slip_no": slip_no})


@app.post("/api/rs/<int:rid>/release")
@_require("executor")
def release_rs(rid):
    db = get_db()
    db.execute("""
        UPDATE requirement_slips SET status='released', released_at=?
        WHERE id=?
    """, (datetime.utcnow().isoformat(), rid))
    db.commit()
    return jsonify({"ok": True})


# ── RS / tracking routes ──────────────────────────────────────────────────────

@app.get("/api/rs")
@_require("admin")
def list_rs():
    db = get_db()
    rows = db.execute("""
        SELECT rs.id, rs.slip_no, rs.status, rs.created_at, rs.released_at,
               o.slip_no as or_slip_no,
               m.display_nm, m.product_code,
               json_array_length(rs.lines_json) as line_count
        FROM requirement_slips rs
        JOIN order_recs o ON o.id=rs.order_rec_id
        JOIN mskus m ON m.id=o.msku_id
        ORDER BY rs.created_at DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


@app.get("/api/rs/<int:rid>")
@_logged_in
def get_rs(rid):
    db = get_db()
    r = db.execute("""
        SELECT rs.*, o.slip_no as or_slip_no, o.order_qty as or_qty,
               m.display_nm, m.msku_code, m.product_code
        FROM requirement_slips rs
        JOIN order_recs o ON o.id=rs.order_rec_id
        JOIN mskus m ON m.id=o.msku_id
        WHERE rs.id=?
    """, (rid,)).fetchone()
    if not r:
        return jsonify({"error": "Not found"}), 404
    d = dict(r)
    try:
        d["lines"] = json.loads(d["lines_json"] or "[]")
    except Exception:
        d["lines"] = []
    return jsonify(d)


@app.get("/api/po-tracking")
@_require("executor")
def po_tracking():
    db = get_db()
    rows = db.execute("""
        SELECT rs.id, rs.slip_no, rs.status, rs.created_at, rs.released_at,
               o.slip_no as or_slip_no, o.order_qty,
               m.display_nm, m.product_code,
               json_array_length(rs.lines_json) as line_count
        FROM requirement_slips rs
        JOIN order_recs o ON o.id=rs.order_rec_id
        JOIN mskus m ON m.id=o.msku_id
        ORDER BY rs.created_at DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Draft list for planner ────────────────────────────────────────────────────

@app.get("/api/order-recs")
@_require("planner")
def list_order_recs():
    db = get_db()
    rows = db.execute("""
        SELECT o.id, o.slip_no, o.msku_id, o.order_qty, o.status, o.created_at, o.sent_at,
               m.display_nm, m.msku_code, m.product_code
        FROM order_recs o JOIN mskus m ON m.id=o.msku_id
        ORDER BY o.created_at DESC
    """).fetchall()
    return jsonify([dict(r) for r in rows])


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    init_db()
    app.run(host="0.0.0.0", port=5001, debug=True)
