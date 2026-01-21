#!/usr/bin/env python3
import dataclasses
import json
import platform
import getpass
import sys
import os
import subprocess
from dataclasses import dataclass
from typing import Dict, Any, Optional

@dataclass
class DeviceInfo:
    """
    Holds static information about the device.
    These values are unlikely to change during a session.
    """
    username: str
    cpu_name: str
    architecture: str

@dataclass
class SystemMetrics:
    """
    Holds dynamic system metrics.
    These values change over time.
    """
    cpu_count: int

class DataCollector:
    """
    Responsible for gathering system information and metrics.
    Designed to be extensible: add new methods here and update the data model classes.
    """
    
    def get_device_info(self) -> DeviceInfo:
        """Collects static device information."""
        return DeviceInfo(
            username=getpass.getuser(),
            cpu_name=self._get_cpu_name(),
            architecture=platform.machine()
        )

    def get_system_metrics(self) -> SystemMetrics:
        """Collects dynamic system metrics."""
        return SystemMetrics(
            cpu_count=os.cpu_count() or 0
        )

    def _get_cpu_name(self) -> str:
        """Attempt to get a readable CPU name."""
        try:
            # Platform specific checks could go here
            if platform.system() == "Darwin": # macOS
                command = ["sysctl", "-n", "machdep.cpu.brand_string"]
                return subprocess.check_output(command).decode().strip()
            return platform.processor() or "Unknown CPU"
        except Exception:
            return "Unknown CPU"

@dataclass
class MonitorReport:
    """
    Top-level data model combining all gathered information.
    """
    device_info: DeviceInfo
    metrics: SystemMetrics
    
    def to_json(self) -> str:
        """Serializes the entire report to a JSON string."""
        return json.dumps(dataclasses.asdict(self), indent=2)

def main():
    try:
        collector = DataCollector()
        
        # 1. Gather Data
        device_info = collector.get_device_info()
        metrics = collector.get_system_metrics()
        
        # 2. Construct Report
        report = MonitorReport(device_info=device_info, metrics=metrics)
        
        # 3. Output as JSON
        print(report.to_json())
        
        # 4. Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        # In a real app, you might log this error to a file
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
