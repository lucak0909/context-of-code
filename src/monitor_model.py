#!/usr/bin/env python3
import json
import sys

from agent.collector import DataCollector, DeviceInfo, MonitorReport, NetworkMetrics
from src.utils.logging_setup import setup_logger

logger = setup_logger(__name__)


def main() -> None:
    try:
        collector = DataCollector()
        # Non-cached for immediate CLI feedback
        metrics = collector.get_network_metrics(use_cache=False)
        info = collector.get_device_info()
        report = MonitorReport(device_info=info, network_metrics=metrics)
        logger.info(report.to_json())
    except Exception as exc:
        logger.exception(json.dumps({"error": str(exc)}))
        sys.exit(1)


if __name__ == "__main__":
    main()
