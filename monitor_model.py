#!/usr/bin/env python3
import dataclasses
import json
import platform
import getpass
import sys
import os
import time
import subprocess
from dataclasses import dataclass
from typing import Dict, Any, Optional
from utils.timer import BlockTimer

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

    def __init__(self):
        # --- CACHING SETUP ---
        self._cached_metrics: Optional[SystemMetrics] = None
        self._last_cache_time = 0.0
        self._cache_duration = 30.0 # Seconds to hold data
    
    def get_device_info(self) -> DeviceInfo:
        """Collects static device information."""
        return DeviceInfo(
            username=getpass.getuser(),
            cpu_name=self._get_cpu_name(),
            architecture=platform.machine()
        )

    def get_system_metrics(self) -> SystemMetrics:
        """Collects dynamic system metrics with caching and timing"""
        current_time = time.time()
        
        # 1. Check if we have valid cached data
        if self._cached_metrics and (current_time - self._last_cache_time < self._cache_duration):
            return self._cached_metrics

        # 2. If not, fetch new data (and Time it!)
        # The timer prints to the console automatically when this block finishes
        with BlockTimer():
            new_metrics = SystemMetrics(
                cpu_count=os.cpu_count() or 0
            )
            #check to see if block timer works
            x = 0
            for i in range (1000000):
                x = x + 1
        
        # 3. Update the cache
        self._cached_metrics = new_metrics
        self._last_cache_time = current_time
        
        return new_metrics

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
 