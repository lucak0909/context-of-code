"""
Admin Blueprint
===============
GET /api/admin – return raw DB counts (no auth required)
"""

from typing import Optional

from flask import Blueprint, jsonify

from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger(name=__name__)

admin_bp = Blueprint("admin", __name__)

_db: Optional[Database] = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        logger.info("Admin API database connection initialised.")
    return _db


@admin_bp.route("", methods=["GET"])
def admin_stats():
    try:
        stats = _get_db().get_db_stats()
    except Exception as exc:
        logger.error("Failed to fetch admin stats: %s", exc, exc_info=True)
        return jsonify({"error": "Could not retrieve stats."}), 500
    return jsonify(stats), 200
