"""
Aggregator API Blueprint
========================
Provides POST /api/ingest for agents to submit metric samples.
"""

from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from flask import Blueprint, jsonify, request

from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger(name=__name__)

api_bp = Blueprint("api", __name__)

# ── Shared database instance (created once, reused across requests) ──────────
_db: Optional[Database] = None


def _get_db() -> Database:
    """Lazy-initialise the Database singleton so we don't connect at import time."""
    global _db
    if _db is None:
        _db = Database()
        logger.info("Aggregator API database connection initialised.")
    return _db


# ── Helper utilities ─────────────────────────────────────────────────────────

def _parse_optional_float(
    value: Optional[object], default: Optional[float] = None
) -> Optional[float]:
    """Safely cast a JSON value to float, returning *default* on failure."""
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _parse_timestamp(value: Optional[str]) -> datetime:
    """Parse an ISO-8601 string into a timezone-aware datetime."""
    if not value:
        return datetime.now(timezone.utc)
    try:
        ts = datetime.fromisoformat(value)
    except ValueError:
        return datetime.now(timezone.utc)
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts


# ── POST /api/ingest ─────────────────────────────────────────────────────────

@api_bp.route("/ingest", methods=["POST"])
def ingest():
    """
    Receive a JSON metric payload from an agent and persist it via the ORM.

    Expected JSON body
    ------------------
    {
        "device_id":   "<uuid>",          # required
        "sample_type": "desktop_network"  # or "cloud_latency"
        "ts":          "2026-02-20T12:00:00+00:00",  # optional, defaults to now
        ...metric fields depending on sample_type...
    }
    """

    # ── 1. Validate Content-Type ──────────────────────────────────────────
    payload = request.get_json(silent=True)
    if payload is None:
        logger.warning("Ingest request rejected: body is not valid JSON.")
        return jsonify({"error": "Request body must be valid JSON."}), 400

    # ── 2. Extract & validate device_id ───────────────────────────────────
    device_id_raw = payload.get("device_id")
    if not device_id_raw:
        logger.warning("Ingest request rejected: missing device_id.")
        return jsonify({"error": "Missing required field: device_id."}), 400

    try:
        device_id = UUID(str(device_id_raw))
    except ValueError:
        logger.warning("Ingest request rejected: invalid device_id '%s'.", device_id_raw)
        return jsonify({"error": "Invalid device_id (must be a valid UUID)."}), 400

    # ── 3. Parse optional timestamp ───────────────────────────────────────
    ts = _parse_timestamp(payload.get("ts"))

    # ── 4. Route by sample_type ───────────────────────────────────────────
    sample_type = payload.get("sample_type", "desktop_network")
    db = _get_db()

    try:
        if sample_type == "desktop_network":
            db.insert_desktop_network_sample(
                device_id=device_id,
                latency_ms=_parse_optional_float(payload.get("latency_ms"), default=0.0),
                packet_loss_pct=_parse_optional_float(payload.get("packet_loss_pct"), default=0.0),
                down_mbps=_parse_optional_float(payload.get("down_mbps"), default=0.0),
                up_mbps=_parse_optional_float(payload.get("up_mbps"), default=0.0),
                test_method=payload.get("test_method"),
                ip=payload.get("ip"),
                ts=ts,
                room_id=None,
            )

        elif sample_type == "cloud_latency":
            db.insert_cloud_latency_sample(
                device_id=device_id,
                latency_eu_ms=_parse_optional_float(payload.get("latency_eu_ms")),
                latency_us_ms=_parse_optional_float(payload.get("latency_us_ms")),
                latency_asia_ms=_parse_optional_float(payload.get("latency_asia_ms")),
                ts=ts,
                room_id=None,
            )

        else:
            logger.warning("Ingest request rejected: unsupported sample_type '%s'.", sample_type)
            return jsonify({"error": f"Unsupported sample_type: {sample_type}"}), 400

    except Exception as exc:
        logger.error("Database write failed during ingest: %s", exc, exc_info=True)
        return jsonify({"error": "Internal server error while persisting sample."}), 500

    logger.info(
        "Ingested %s sample for device %s (ts=%s).",
        sample_type, device_id, ts.isoformat(),
    )
    return jsonify({"status": "ok", "sample_type": sample_type}), 200
