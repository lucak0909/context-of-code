from __future__ import annotations

import platform
import time
from typing import Optional
from uuid import UUID

from agent.collector import DataCollector, MonitorReport
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
    device_id: Optional[UUID] = None
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
        while True:
            start = time.monotonic()
            try:
                metrics = collector.get_network_metrics(use_cache=False)
                db.insert_desktop_network_sample(
                    device_id=device_id,
                    latency_ms=metrics.ping,
                    packet_loss_pct=metrics.packet_loss_percent,
                    down_mbps=metrics.download_speed_mbps,
                    up_mbps=metrics.upload_speed_mbps,
                    test_method=metrics.test_method,
                )
                logger.info("Sample saved for device=%s.", device_id)
            except Exception:
                logger.exception("Agent collection or DB insert failed")

            elapsed = time.monotonic() - start
            sleep_time = max(0.0, interval_seconds - elapsed)
            if sleep_time:
                time.sleep(sleep_time)
    except KeyboardInterrupt:
        logger.info("Agent stopped.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
