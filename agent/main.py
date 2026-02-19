from __future__ import annotations

import time

from agent.collector import DataCollector, MonitorReport
from src.utils.logging_setup import setup_logger

logger = setup_logger("agent")

INTERVAL_SECONDS = 30


def collect_once(collector: DataCollector) -> None:
    metrics = collector.get_network_metrics(use_cache=False)
    info = collector.get_device_info()
    report = MonitorReport(device_info=info, network_metrics=metrics)
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


if __name__ == "__main__":
    run()
