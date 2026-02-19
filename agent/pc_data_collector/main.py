from __future__ import annotations

import platform
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID

from agent.pc_data_collector.collector import DataCollector, MonitorReport
from agent.cloud_latency_collector import run_cloud_latency_loop
from agent.uploader_queue import UploadQueue
from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger("agent")

INTERVAL_SECONDS = 30


def collect_once(collector: DataCollector) -> None:
    metrics = collector.get_network_metrics(use_cache=False)
    report = MonitorReport(network_metrics=metrics)
    logger.info(report.to_json())


def run(interval_seconds: int = INTERVAL_SECONDS) -> None:
    collector = DataCollector()
    logger.info("Agent started (interval=%ss).", interval_seconds)
    try:
        while True:
            start = time.monotonic()
            try:
                collect_once(collector)
            except Exception:
                logger.exception("Agent collection failed")

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, interval_seconds - elapsed)
            if sleep_time:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info("Agent stopped.")


def _default_device_name() -> str:
    name = platform.node().strip()
    return name or "unknown-device"


def run_with_user(user_id: UUID, interval_seconds: int = INTERVAL_SECONDS) -> None:
    collector = DataCollector()
    db = Database()
    queue = UploadQueue()
    device_id: Optional[UUID] = None
    stop_event = threading.Event()
    cloud_thread: Optional[threading.Thread] = None
    try:
        device = db.get_or_create_device(
            user_id=user_id,
            name=_default_device_name(),
            device_type="pc",
        )
        device_id = device.id
        logger.info(
            "Agent started for user=%s device=%s (interval=%ss).",
            user_id,
            device_id,
            interval_seconds,
        )

        cloud_thread = threading.Thread(
            target=run_cloud_latency_loop,
            kwargs={
                "device_id": device_id,
                "queue": queue,
                "db": db,
                "stop_event": stop_event,
            },
            daemon=True,
        )
        cloud_thread.start()

        while True:
            start = time.monotonic()
            try:
                metrics = collector.get_network_metrics(use_cache=False)
                payload = {
                    "sample_type": "desktop_network",
                    "device_id": str(device_id),
                    "ts": datetime.now(timezone.utc).isoformat(),
                    "latency_ms": metrics.ping,
                    "packet_loss_pct": metrics.packet_loss_percent,
                    "down_mbps": metrics.download_speed_mbps,
                    "up_mbps": metrics.upload_speed_mbps,
                    "test_method": metrics.test_method,
                    "ip": metrics.ip_address,
                }
                queue.enqueue(payload)
                sent = queue.flush(db)
                if sent:
                    logger.info("Uploaded %s queued sample(s).", sent)
            except Exception:
                logger.exception("Agent collection or upload failed")

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, interval_seconds - elapsed)
            if sleep_time:
                stop_event.wait(sleep_time)
    except KeyboardInterrupt:
        logger.info("Agent stopped.")
    finally:
        stop_event.set()
        if cloud_thread:
            cloud_thread.join(timeout=5)
        db.close()


if __name__ == "__main__":
    run()
