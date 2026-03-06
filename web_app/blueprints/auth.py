"""
Auth Blueprint
==============
POST /api/auth/login    – verify credentials, return user info
POST /api/auth/register – create account, return user info
"""

from typing import Optional

from flask import Blueprint, jsonify, request

from common.auth.passwords import hash_password
from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger(name=__name__)

auth_bp = Blueprint("auth", __name__)

_db: Optional[Database] = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        logger.info("Auth API database connection initialised.")
    return _db


@auth_bp.route("/login", methods=["POST"])
def login():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", "")).strip()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    db = _get_db()
    user = db.get_user_by_email(email)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401

    if not db.verify_user_password(user.id, password):
        return jsonify({"error": "Invalid credentials"}), 401

    return jsonify({"user_id": str(user.id), "email": user.email}), 200


@auth_bp.route("/register", methods=["POST"])
def register():
    body = request.get_json(silent=True) or {}
    email = str(body.get("email", "")).strip().lower()
    password = str(body.get("password", "")).strip()

    if not email or not password:
        return jsonify({"error": "email and password are required"}), 400

    db = _get_db()
    if db.get_user_by_email(email):
        return jsonify({"error": "An account with that email already exists"}), 400

    password_hash = hash_password(password)
    user_id = db.create_user(email)
    db.set_password(user_id, password_hash)

    return jsonify({"user_id": str(user_id), "email": email}), 201
