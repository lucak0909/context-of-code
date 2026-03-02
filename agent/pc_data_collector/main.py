from __future__ import annotations

import platform
import threading
import time
from datetime import datetime, timezone
from typing import Optional
from uuid import UUID, uuid4

from agent.pc_data_collector.collector import DataCollector, MonitorReport
from agent.cloud_latency_collector import run_cloud_latency_loop
from agent.uploader_queue import UploadQueue

from common.utils.logging_setup import setup_logger

logger = setup_logger("agent")

INTERVAL_SECONDS = 30


def collect_once(collector: DataCollector) -> None:
    metrics = collector.get_network_metrics(use_cache=False)
    report = MonitorReport(network_metrics=metrics)
    logger.info(report.to_json())

#test function
def run(interval_seconds: int = INTERVAL_SECONDS) -> None:
    collector = DataCollector()
    queue = UploadQueue()
    # Use a real device_id from the development database so the API doesn't fail the FK constraint
    device_id = UUID("647fb7f6-9988-4656-b3db-49f19e834f63")
    
    logger.info("Agent started in standalone mode (device=%s, interval=%ss).", device_id, interval_seconds)
    try:
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
                sent = queue.flush()
                
                if sent:
                    logger.info("Uploaded %s queued sample(s).", sent)
                else:
                    logger.info("Locally queued payload. Will retry on next flush.")
                    
                # Continue printing local report for manual visibility
                report = MonitorReport(network_metrics=metrics)
                logger.info("Local Metrics:\n%s", report.to_json())
                
            except Exception:
                logger.exception("Agent collection or upload failed")

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, interval_seconds - elapsed)
            if sleep_time:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info("Agent stopped.")


def _default_device_name() -> str:
    name = platform.node().strip()
    return name or "unknown-device"

#Production Function
def run_with_user(user_id: UUID, interval_seconds: int = INTERVAL_SECONDS) -> None:
    collector = DataCollector()

    queue = UploadQueue()
    device_id: Optional[UUID] = None
    stop_event = threading.Event()
    cloud_thread: Optional[threading.Thread] = None
    try:
        from common.database.db_operations import Database
        db = Database()
        try:
            device = db.get_or_create_device(
                user_id=user_id,
                name=_default_device_name(),
                device_type="pc",
            )
        finally:
            db.close()
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
                sent = queue.flush()
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


if __name__ == "__main__":
    run()
