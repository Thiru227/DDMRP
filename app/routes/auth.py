"""Auth: session-based login for the DDMRP POC (hardcoded credentials)."""
from __future__ import annotations

import functools
from typing import Callable

from flask import Blueprint, jsonify, request, session

bp = Blueprint("auth", __name__, url_prefix="/api/auth")

# POC-only credentials — role: {username, password, display info}
_USERS = {
    "admin": {
        "username": "admin",
        "password": "admin",
        "role": "admin",
        "name": "Ragukumar B.",
        "initials": "RK",
        "color": "var(--gold-m)",
        "landing": "admin-dashboard",
    },
    "planning": {
        "username": "planning",
        "password": "planning",
        "role": "planner",
        "name": "Senthilkumar",
        "initials": "SK",
        "color": "var(--teal-m)",
        "landing": "planner-alerts",
    },
    "executer": {
        "username": "executer",
        "password": "executer",
        "role": "executor",
        "name": "Senthilkumar",
        "initials": "SK",
        "color": "var(--purple-m)",
        "landing": "executer-inbox",
    },
}


@bp.post("/login")
def login():
    data = request.get_json(silent=True) or {}
    username = (data.get("username") or "").strip().lower()
    password = (data.get("password") or "").strip()

    user = _USERS.get(username)
    if user is None or user["password"] != password:
        return jsonify({"error": "Invalid username or password"}), 401

    session.permanent = True
    session["user"]     = user["username"]
    session["role"]     = user["role"]
    session["name"]     = user["name"]
    session["initials"] = user["initials"]
    session["color"]    = user["color"]
    session["landing"]  = user["landing"]

    return jsonify({
        "ok": True,
        "user":     user["username"],
        "role":     user["role"],
        "name":     user["name"],
        "initials": user["initials"],
        "color":    user["color"],
        "landing":  user["landing"],
    })


@bp.post("/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


@bp.get("/me")
def me():
    if "role" not in session:
        return jsonify({"error": "not authenticated"}), 401
    return jsonify({
        "user":     session.get("user"),
        "role":     session.get("role"),
        "name":     session.get("name"),
        "initials": session.get("initials"),
        "color":    session.get("color"),
        "landing":  session.get("landing"),
    })


def login_required(roles: list[str] | None = None) -> Callable:
    """Decorator: requires an active session, optionally restricted to given roles."""
    def decorator(fn: Callable) -> Callable:
        @functools.wraps(fn)
        def wrapper(*args, **kwargs):
            if "role" not in session:
                return jsonify({"error": "authentication required"}), 401
            if roles and session["role"] not in roles:
                return jsonify({"error": "insufficient permissions"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator
