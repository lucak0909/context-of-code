"""
Reporting API Blueprint
=======================
Provides read-only endpoints for the dashboard to query historical metric data.

Routes
------
GET /api/report/devices                     – list all registered devices
GET /api/report/samples?device_id=&...      – time-series samples for one device
GET /api/report/latest?device_id=           – most-recent sample per sample_type
"""

from typing import Optional

from flask import Blueprint, jsonify, request

from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger(name=__name__)

reporting_bp = Blueprint("reporting", __name__)

# ── Shared database singleton (same lazy-init pattern as api.py) ─────────────
_db: Optional[Database] = None


def _get_db() -> Database:
    global _db
    if _db is None:
        _db = Database()
        logger.info("Reporting API database connection initialised.")
    return _db


# ── Helpers ───────────────────────────────────────────────────────────────────

def _device_to_dict(device) -> dict:
    return {
        "id": device.id,
        "name": device.name,
        "device_type": device.device_type,
        "created_at": device.created_at.isoformat() if device.created_at else None,
    }


def _sample_to_dict(sample) -> dict:
    return {
        "id": sample.id,
        "device_id": sample.device_id,
        "sample_type": sample.sample_type,
        "ts": sample.ts.isoformat() if sample.ts else None,
        # desktop_network fields
        "latency_ms": sample.latency_ms,
        "packet_loss_pct": sample.packet_loss_pct,
        "down_mbps": sample.down_mbps,
        "up_mbps": sample.up_mbps,
        "test_method": sample.test_method,
        "ip": sample.ip,
        "tcp_connections": sample.tcp_connections,
        "bytes_sent": sample.bytes_sent,
        "bytes_recv": sample.bytes_recv,
        # cloud_latency fields
        "latency_eu_ms": sample.latency_eu_ms,
        "latency_us_ms": sample.latency_us_ms,
        "latency_asia_ms": sample.latency_asia_ms,
        # mobile fields
        "wifi_rssi_dbm": sample.wifi_rssi_dbm,
        "link_speed_mbps": sample.link_speed_mbps,
        "is_connected": sample.is_connected,
    }


# ── GET /api/report/devices ───────────────────────────────────────────────────

@reporting_bp.route("/devices", methods=["GET"])
def devices():
    """Return devices. If user_id is provided, only that user's devices are returned."""
    user_id = request.args.get("user_id")
    try:
        if user_id:
            device_list = _get_db().get_devices_by_user(user_id)
        else:
            device_list = _get_db().get_all_devices()
    except Exception as exc:
        logger.error("Failed to fetch devices: %s", exc, exc_info=True)
        return jsonify({"error": "Could not retrieve devices."}), 500

    return jsonify([_device_to_dict(d) for d in device_list]), 200


# ── GET /api/report/samples ───────────────────────────────────────────────────

@reporting_bp.route("/samples", methods=["GET"])
def samples():
    """
    Return time-series samples for a specific device.

    Query parameters
    ----------------
    device_id   (required) – UUID of the device
    sample_type (optional) – "desktop_network" or "cloud_latency"
    hours       (optional) – how many hours back to look (default 24)
    limit       (optional) – max rows to return (default 200)
    """
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "Missing required query param: device_id"}), 400

    sample_type = request.args.get("sample_type")  # None → return all types

    try:
        hours = int(request.args.get("hours", 24))
        limit = int(request.args.get("limit", 200))
    except ValueError:
        return jsonify({"error": "hours and limit must be integers."}), 400

    try:
        rows = _get_db().get_samples(device_id, sample_type=sample_type, hours=hours, limit=limit)
    except Exception as exc:
        logger.error("Failed to fetch samples: %s", exc, exc_info=True)
        return jsonify({"error": "Could not retrieve samples."}), 500

    return jsonify([_sample_to_dict(s) for s in rows]), 200


# ── GET /api/report/latest ────────────────────────────────────────────────────

@reporting_bp.route("/latest", methods=["GET"])
def latest():
    """
    Return the most recent sample of each sample_type for a device.

    Query parameters
    ----------------
    device_id (required) – UUID of the device
    """
    device_id = request.args.get("device_id")
    if not device_id:
        return jsonify({"error": "Missing required query param: device_id"}), 400

    result = {}
    try:
        for sample_type in ("desktop_network", "cloud_latency", "mobile_wifi"):
            sample = _get_db().get_latest_sample(device_id, sample_type)
            if sample:
                result[sample_type] = _sample_to_dict(sample)
    except Exception as exc:
        logger.error("Failed to fetch latest samples: %s", exc, exc_info=True)
        return jsonify({"error": "Could not retrieve latest samples."}), 500

    return jsonify(result), 200
