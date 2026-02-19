from __future__ import annotations

import json
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional
from uuid import UUID

from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger("uploader_queue")


class UploadQueue:
    def __init__(self, path: Optional[str] = None) -> None:
        default_path = os.getenv("AGENT_QUEUE_PATH", "agent_queue.jsonl")
        self._path = Path(path or default_path)
        self._lock = threading.Lock()

    def enqueue(self, payload: dict) -> None:
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(payload, separators=(",", ":"))
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def flush(self, db: Database) -> int:
        with self._lock:
            if not self._path.exists():
                return 0

            try:
                lines = self._path.read_text(encoding="utf-8").splitlines()
            except OSError as exc:
                logger.warning("Queue read failed: %s", exc)
                return 0

            if not lines:
                return 0

            remaining: list[str] = []
            sent = 0
            for line in lines:
                if not line.strip():
                    continue
                try:
                    payload = json.loads(line)
                    if self._send_payload(db, payload):
                        sent += 1
                    else:
                        remaining.append(line)
                except Exception as exc:
                    logger.warning("Queue item failed to send: %s", exc)
                    remaining.append(line)

            self._rewrite_queue(remaining)
            return sent

    def _rewrite_queue(self, remaining: Iterable[str]) -> None:
        tmp_path = self._path.with_suffix(self._path.suffix + ".tmp")
        try:
            with tmp_path.open("w", encoding="utf-8") as handle:
                for line in remaining:
                    handle.write(line + "\n")
            tmp_path.replace(self._path)
        except OSError as exc:
            logger.warning("Queue rewrite failed: %s", exc)
            try:
                if tmp_path.exists():
                    tmp_path.unlink()
            except OSError:
                pass

    def _send_payload(self, db: Database, payload: dict) -> bool:
        device_id_raw = payload.get("device_id")
        if not device_id_raw:
            raise ValueError("Missing device_id in queued payload.")

        try:
            device_id = UUID(str(device_id_raw))
        except Exception as exc:
            raise ValueError("Invalid device_id in queued payload.") from exc

        ts_value = payload.get("ts")
        ts = self._parse_timestamp(ts_value)

        sample_type = payload.get("sample_type") or "desktop_network"
        if sample_type == "desktop_network":
            db.insert_desktop_network_sample(
                device_id=device_id,
                latency_ms=_parse_optional_float(payload.get("latency_ms"), default=0.0),
                packet_loss_pct=_parse_optional_float(
                    payload.get("packet_loss_pct"), default=0.0
                ),
                down_mbps=_parse_optional_float(payload.get("down_mbps"), default=0.0),
                up_mbps=_parse_optional_float(payload.get("up_mbps"), default=0.0),
                test_method=payload.get("test_method"),
                ts=ts,
                room_id=None,
            )
            return True

        if sample_type == "cloud_latency":
            db.insert_cloud_latency_sample(
                device_id=device_id,
                latency_eu_ms=_parse_optional_float(payload.get("latency_eu_ms")),
                latency_us_ms=_parse_optional_float(payload.get("latency_us_ms")),
                latency_asia_ms=_parse_optional_float(payload.get("latency_asia_ms")),
                ts=ts,
                room_id=None,
            )
            return True

        raise ValueError(f"Unsupported sample_type: {sample_type}")

    @staticmethod
    def _parse_timestamp(value: Optional[str]) -> datetime:
        if not value:
            return datetime.now(timezone.utc)
        try:
            ts = datetime.fromisoformat(value)
        except ValueError:
            return datetime.now(timezone.utc)
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=timezone.utc)
        return ts


def _parse_optional_float(value: Optional[object], default: Optional[float] = None) -> Optional[float]:
    if value is None:
        return default
    try:
        return float(value)
    except (TypeError, ValueError):
        return default
