from __future__ import annotations

import json
import os
import threading
import urllib.error
from pathlib import Path
from typing import Iterable, Optional

from common.settings import get_settings
from common.utils.logging_setup import setup_logger

logger = setup_logger("uploader_queue")

# ── Default Aggregator API URL (configurable via env var) ────────────────────
DEFAULT_API_URL = "http://127.0.0.1:5000/api/ingest"
REQUEST_TIMEOUT = int(os.getenv("AGGREGATOR_TIMEOUT_SECONDS", "10"))


class UploadQueue:
    """
    A file-backed queue that buffers metric payloads as JSONL lines.

    On flush(), each queued payload is transmitted to the Aggregator API
    via HTTP POST.  Payloads that fail to send are kept in the queue file
    for the next attempt (offline-safe).
    """

    def __init__(
        self,
        path: Optional[str] = None,
        api_url: Optional[str] = None,
    ) -> None:
        default_path = os.getenv("AGENT_QUEUE_PATH", "agent_queue.jsonl")
        self._path = Path(path or default_path)
        self._api_url = api_url or get_settings().aggregator_api_url
        self._lock = threading.Lock()

    # ── Public API ───────────────────────────────────────────────────────

    def enqueue(self, payload: dict) -> None:
        """Append a JSON payload to the queue file (thread-safe)."""
        with self._lock:
            self._path.parent.mkdir(parents=True, exist_ok=True)
            line = json.dumps(payload, separators=(",", ":"))
            with self._path.open("a", encoding="utf-8") as handle:
                handle.write(line + "\n")

    def flush(self) -> int:
        """
        Read every queued payload and POST it to the Aggregator API.

        Returns the number of payloads successfully sent.
        Payloads that fail are written back to the queue file for retry.
        """
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
                    if self._send_payload(payload):
                        sent += 1
                    else:
                        remaining.append(line)
                except Exception as exc:
                    logger.warning("Queue item failed to send: %s", exc)
                    remaining.append(line)

            self._rewrite_queue(remaining)
            return sent

    # ── Internal helpers ─────────────────────────────────────────────────

    def _rewrite_queue(self, remaining: Iterable[str]) -> None:
        """Atomically rewrite the queue file with only the unsent lines."""
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

    def _send_payload(self, payload: dict) -> bool:
        """
        POST a single JSON payload to the Aggregator API.

        Returns True on success (HTTP 200), False otherwise.
        The payload is sent as-is — the Aggregator API handles all
        validation and persistence.
        """
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            self._api_url,
            data=data,
            method="POST",
            headers={"Content-Type": "application/json"},
        )

        try:
            with urllib.request.urlopen(req, timeout=REQUEST_TIMEOUT) as resp:
                if resp.status == 200:
                    logger.debug("Payload accepted by aggregator.")
                    return True
                logger.warning(
                    "Aggregator returned unexpected status %s.", resp.status
                )
                return False
        except urllib.error.HTTPError as exc:
            logger.warning(
                "Aggregator HTTP error (%s): %s", exc.code, exc.reason
            )
        except urllib.error.URLError as exc:
            logger.warning("Aggregator unreachable: %s", exc.reason)
        except Exception as exc:
            logger.warning("Aggregator request failed: %s", exc)

        return False
