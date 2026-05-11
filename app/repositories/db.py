"""Thin DB abstraction. Defaults to SQLite for the demo; Supabase swap is one factory."""
from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from threading import Lock
from typing import Iterator

_state = {"conn": None, "backend": "sqlite"}
_lock = Lock()


def init(config) -> None:
    backend = getattr(config, "BACKEND", "sqlite").lower()
    _state["backend"] = backend
    if backend == "sqlite":
        path = Path(config.SQLITE_PATH)
        path.parent.mkdir(parents=True, exist_ok=True)
        conn = sqlite3.connect(str(path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        _state["conn"] = conn
        _run_migrations(conn)
    elif backend == "supabase":
        raise NotImplementedError(
            "Supabase backend is wired but not implemented in this demo build. "
            "Set DDMRP_BACKEND=sqlite or implement app/repositories/supabase_client.py."
        )
    else:
        raise ValueError(f"Unknown DDMRP_BACKEND: {backend}")


def _run_migrations(conn: sqlite3.Connection) -> None:
    migrations_dir = Path(__file__).resolve().parent.parent / "migrations"
    tracking_missing = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name='_migrations'"
    ).fetchone() is None
    conn.execute(
        "CREATE TABLE IF NOT EXISTS _migrations "
        "(name TEXT PRIMARY KEY, applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP)"
    )
    conn.commit()
    if tracking_missing:
        existing_tables = {r[0] for r in conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table'"
        )}
        if existing_tables - {"_migrations"}:
            for f in sorted(migrations_dir.glob("*.sql")):
                conn.execute("INSERT OR IGNORE INTO _migrations (name) VALUES (?)", (f.name,))
            conn.commit()
    applied = {row[0] for row in conn.execute("SELECT name FROM _migrations")}
    for f in sorted(migrations_dir.glob("*.sql")):
        if f.name in applied:
            continue
        sql = f.read_text(encoding="utf-8")
        with conn:
            conn.executescript(sql)
            conn.execute("INSERT INTO _migrations (name) VALUES (?)", (f.name,))
            conn.commit()


def conn() -> sqlite3.Connection:
    if _state["conn"] is None:
        raise RuntimeError("DB not initialised — call db.init(config) first")
    return _state["conn"]


@contextmanager
def tx() -> Iterator[sqlite3.Connection]:
    c = conn()
    with _lock:
        try:
            yield c
            c.commit()
        except Exception:
            c.rollback()
            raise
