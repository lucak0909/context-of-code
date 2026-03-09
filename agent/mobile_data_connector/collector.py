from __future__ import annotations

import threading
from datetime import datetime, timezone
from typing import Optional
from urllib.parse import quote_plus
from uuid import UUID

from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool

from agent.uploader_queue import UploadQueue
from common.auth.passwords import verify_password
from common.utils.logging_setup import setup_logger

logger = setup_logger("mobile_connector")

DEFAULT_INTERVAL_SECONDS = 30


class MobileDataConnector:
    """Connects to the mobile app's Supabase DB and reads wifi_samples."""

    def __init__(self, dsn: str) -> None:
        self._engine = create_engine(dsn, poolclass=NullPool)
        logger.info("Mobile data connector engine created.")

    def authenticate(self, email: str, password: str) -> Optional[str]:
        """Return user_id from mobile DB if credentials match, else None."""
        with self._engine.connect() as conn:
            row = conn.execute(
                text("SELECT id FROM users WHERE email = :email"),
                {"email": email},
            ).first()
            if not row:
                logger.warning("Mobile auth: no user found for email '%s'.", email)
                return None
            user_id = str(row[0])

            pw_row = conn.execute(
                text("SELECT password_enc FROM passwords WHERE user_id = :uid"),
                {"uid": user_id},
            ).first()
            if not pw_row:
                logger.warning("Mobile auth: no password record for user '%s'.", user_id)
                return None

            if not verify_password(password, pw_row[0]):
                logger.warning("Mobile auth: invalid credentials for email '%s'.", email)
                return None

        logger.info("Mobile auth: authenticated user '%s' successfully.", user_id)
        return user_id

    def get_new_samples(self, mobile_user_id: str, since: datetime) -> list[dict]:
        """Return wifi_samples created after *since* for *mobile_user_id*, oldest first."""
        with self._engine.connect() as conn:
            rows = conn.execute(
                text(
                    "SELECT wifi_rssi_dbm, link_speed_mbps, is_connected, ts, created_at "
                    "FROM wifi_samples "
                    "WHERE user_id = :uid AND created_at > :since "
                    "ORDER BY created_at ASC"
                ),
                {"uid": mobile_user_id, "since": since},
            ).fetchall()

        return [
            {
                "wifi_rssi_dbm": float(row[0]) if row[0] is not None else None,
                "link_speed_mbps": float(row[1]) if row[1] is not None else None,
                "is_connected": row[2],
                "ts": row[3],
                "created_at": row[4],
            }
            for row in rows
        ]

    def close(self) -> None:
        self._engine.dispose()
        logger.info("Mobile data connector engine disposed.")


def run_mobile_connector_loop(
    *,
    email: str,
    password: str,
    device_id: UUID,
    queue: UploadQueue,
    stop_event: threading.Event,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> None:
    """Daemon loop: poll mobile DB for new wifi samples and enqueue them."""
    from common.settings import get_mobile_db_settings

    try:
        settings = get_mobile_db_settings()
    except ValueError as exc:
        logger.warning("Mobile connector disabled: %s", exc)
        return

    safe_user = quote_plus(settings.mobile_db_user)
    safe_password = quote_plus(settings.mobile_db_password)
    dsn = (
        f"postgresql+psycopg2://{safe_user}:{safe_password}"
        f"@{settings.mobile_db_host}:{settings.mobile_db_port}/{settings.mobile_db_name}"
        f"?sslmode=require"
    )

    connector = MobileDataConnector(dsn)
    try:
        mobile_user_id = connector.authenticate(email, password)
        if not mobile_user_id:
            logger.error("Mobile connector: authentication failed, thread exiting.")
            return

        last_seen: datetime = datetime.now(timezone.utc)
        logger.info("Mobile connector started for device=%s.", device_id)

        while not stop_event.is_set():
            try:
                samples = connector.get_new_samples(mobile_user_id, since=last_seen)
                for s in samples:
                    ts_val = s["ts"]
                    ts_str = ts_val.isoformat() if isinstance(ts_val, datetime) else str(ts_val)
                    payload = {
                        "sample_type": "mobile_wifi",
                        "device_id": str(device_id),
                        "ts": ts_str,
                        "wifi_rssi_dbm": s["wifi_rssi_dbm"],
                        "link_speed_mbps": s["link_speed_mbps"],
                        "is_connected": s["is_connected"],
                    }
                    queue.enqueue(payload)

                if samples:
                    last_seen = samples[-1]["created_at"]
                    sent = queue.flush()
                    if sent:
                        logger.info("Uploaded %s mobile wifi sample(s).", sent)

            except Exception:
                logger.exception("Mobile connector poll failed")

            stop_event.wait(interval_seconds)
    finally:
        connector.close()
