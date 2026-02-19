#!/usr/bin/env python3
from __future__ import annotations

import dataclasses
import getpass
import json
import os
import platform
import socket
import subprocess
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from typing import Optional, Tuple

from src.utils.timer import BlockTimer
from src.utils.logging_setup import setup_logger

logger = setup_logger(__name__)


@dataclass
class DeviceInfo:
    """
    Holds static information about the device.
    These values are unlikely to change during a session.
    """

    username: str


@dataclass
class NetworkMetrics:
    """
    Holds network performance metrics.
    """

    packet_loss_percent: float  # Percentage of packets lost
    ping: float  # Average ping latency in ms
    download_speed_mbps: float  # Megabits per second
    upload_speed_mbps: float  # Megabits per second
    ip_address: str  # Local IP
    public_ip: str  # Public IP
    test_method: str  # Method used for speed test


class DataCollector:
    """
    Responsible for gathering system information and metrics.
    Designed to be extensible: add new methods here and update the data model classes.
    """

    def __init__(self, timeout: int = 10):
        # --- CACHING SETUP ---
        self._cached_metrics: Optional[NetworkMetrics] = None
        self._last_cache_time = 0.0
        self._cache_duration = 300.0  # 5 minutes cache for expensive network operations

        self.timeout = timeout
        self._speedtest_clients: dict[str, tuple[object, float]] = {}
        self._speedtest_cache_duration = 300.0

        self.packet_loss_hosts = self._load_packet_loss_hosts()
        self.packet_loss_packets = self._load_packet_loss_packets()
        self._packet_loss_debug = self._load_packet_loss_debug()

    def get_device_info(self) -> DeviceInfo:
        """Collects static device information."""
        return DeviceInfo(username=getpass.getuser())

    def get_network_metrics(self, use_cache: bool = True) -> NetworkMetrics:
        """
        Collects network metrics with optional caching.
        """
        current_time = time.time()

        # Check cache if enabled
        if (
            use_cache
            and self._cached_metrics
            and (current_time - self._last_cache_time < self._cache_duration)
        ):
            return self._cached_metrics

        # Fetch new metrics in parallel where safe
        with BlockTimer():
            (
                download_speed,
                upload_speed,
                method,
                packet_loss,
                ping_ms,
                local_ip,
                public_ip,
            ) = self._collect_network_metrics_parallel()

        new_metrics = NetworkMetrics(
            download_speed_mbps=download_speed,
            upload_speed_mbps=upload_speed,
            packet_loss_percent=packet_loss,
            ping=ping_ms,
            ip_address=local_ip,
            public_ip=public_ip,
            test_method=method,
        )

        # Update cache
        self._cached_metrics = new_metrics
        self._last_cache_time = current_time

        return new_metrics

    # --- HELPER METHODS ---

    def _collect_network_metrics_parallel(
        self,
    ) -> Tuple[float, float, str, float, float, str, str]:
        download_speed = 0.0
        upload_speed = 0.0
        method = "Unavailable"
        packet_loss = 0.0
        ping_ms = 0.0
        local_ip = "127.0.0.1"
        public_ip = "Unknown"

        def download_task() -> Tuple[float, str]:
            client = self._get_speedtest_client(cache_key="download")
            return self._measure_download_speed(client)

        def upload_task() -> float:
            client = self._get_speedtest_client(cache_key="upload")
            return self._measure_upload_speed(client)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = {
                "download": executor.submit(download_task),
                "upload": executor.submit(upload_task),
                "packet_loss": executor.submit(self._measure_packet_loss),
                "local_ip": executor.submit(self._get_local_ip),
                "public_ip": executor.submit(self._get_public_ip),
            }

            for name, future in futures.items():
                try:
                    result = future.result()
                except Exception as exc:
                    logger.warning("Network metric task '%s' failed: %s", name, exc)
                    continue

                if name == "download":
                    download_speed, method = result
                elif name == "upload":
                    upload_speed = result
                elif name == "packet_loss":
                    packet_loss, ping_ms = result
                elif name == "local_ip":
                    local_ip = result
                elif name == "public_ip":
                    public_ip = result

        return (
            download_speed,
            upload_speed,
            method,
            packet_loss,
            ping_ms,
            local_ip,
            public_ip,
        )

    def _get_local_ip(self) -> str:
        """Connects to Google DNS to find the local IP of the active interface."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
                s.connect(("8.8.8.8", 80))
                return s.getsockname()[0]
        except Exception:
            return "127.0.0.1"

    def _get_public_ip(self) -> str:
        """Attempts to fetch the public IP address."""
        try:
            import urllib.request

            services = [
                "https://api.ipify.org?format=text",
                "https://ifconfig.me/ip",
                "https://checkip.amazonaws.com",
            ]
            for url in services:
                try:
                    with urllib.request.urlopen(url, timeout=5) as response:
                        ip = response.read().decode().strip()
                        if ip:
                            return ip
                except Exception:
                    continue
        except Exception:
            pass
        return "Unknown"

    def _load_packet_loss_debug(self) -> bool:
        raw = os.environ.get("PACKET_LOSS_DEBUG", "").strip().lower()
        return raw in {"1", "true", "yes", "y"}

    def _debug_packet_loss(self, message: str) -> None:
        if self._packet_loss_debug:
            logger.debug(message)

    def _get_speedtest_client(self, cache_key: str = "default"):
        try:
            import speedtest
        except ImportError:
            return None

        now = time.time()
        cached = self._speedtest_clients.get(cache_key)
        if cached and (now - cached[1] < self._speedtest_cache_duration):
            return cached[0]

        try:
            client = speedtest.Speedtest(secure=True, timeout=self.timeout)
            client.get_best_server()
            self._speedtest_clients[cache_key] = (client, now)
            return client
        except Exception as exc:
            logger.warning("Speedtest initialization failed: %s", exc)
            return None

    def _measure_download_speed(self, speedtest_client=None) -> Tuple[float, str]:
        if speedtest_client is None:
            speedtest_client = self._get_speedtest_client()

        if speedtest_client is not None:
            try:
                download_speed_bps = speedtest_client.download()
                return (download_speed_bps / 1_000_000), "Official Speedtest CLI"
            except Exception as exc:
                logger.warning("Speedtest download failed: %s", exc)

        speed = self._simple_download_test()
        return speed, "Simple HTTP Download"

    def _measure_upload_speed(self, speedtest_client=None) -> float:
        if speedtest_client is None:
            speedtest_client = self._get_speedtest_client()

        if speedtest_client is not None:
            try:
                upload_speed_bps = speedtest_client.upload()
                return upload_speed_bps / 1_000_000
            except Exception as exc:
                logger.warning("Speedtest upload failed: %s", exc)

        return self._simple_upload_test()

    def _simple_download_test(self) -> float:
        try:
            import urllib.request

            # Using Irish/UK mirrors for better latency
            test_urls = [
                "http://ftp.heanet.ie/mirrors/ubuntu/ls-lR.gz",
                "http://speedtest.tele2.net/10MB.zip",
                "https://speed.cloudflare.com/__down?bytes=10000000",
            ]
            for test_url in test_urls:
                try:
                    start_time = time.time()
                    response = urllib.request.urlopen(test_url, timeout=self.timeout)
                    total_bytes = 0
                    max_bytes = 10_000_000  # Cap at 10MB test
                    while total_bytes < max_bytes:
                        chunk = response.read(min(64 * 1024, max_bytes - total_bytes))
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        return (total_bytes * 8) / elapsed / 1_000_000
                except Exception:
                    continue
            return 0.0
        except Exception as exc:
            logger.warning("Simple download test failed: %s", exc)
            return 0.0

    def _simple_upload_test(self) -> float:
        try:
            import urllib.request

            test_urls = ["https://httpbin.org/post", "https://postman-echo.com/post"]
            payload = os.urandom(2_000_000)
            for test_url in test_urls:
                try:
                    start_time = time.time()
                    req = urllib.request.Request(test_url, data=payload, method="POST")
                    req.add_header("Content-Type", "application/octet-stream")
                    urllib.request.urlopen(req, timeout=self.timeout).read()
                    elapsed = time.time() - start_time
                    if elapsed > 0:
                        return (len(payload) * 8) / elapsed / 1_000_000
                except Exception:
                    continue
            return 0.0
        except Exception as exc:
            logger.warning("Simple upload test failed: %s", exc)
            return 0.0

    def _load_packet_loss_hosts(self) -> list:
        raw = os.environ.get("PACKET_LOSS_HOSTS", "").strip()
        if raw:
            return [h.strip() for h in raw.split(",") if h.strip()]
        return ["1.1.1.1", "8.8.8.8"]

    def _load_packet_loss_packets(self) -> int:
        raw = os.environ.get("PACKET_LOSS_PACKETS", "").strip()
        if raw:
            try:
                return max(1, min(int(raw), 50))
            except ValueError:
                pass
        return 2

    def _measure_packet_loss(self) -> Tuple[float, float]:
        hosts = self.packet_loss_hosts
        packets = self.packet_loss_packets
        if not hosts:
            return 0.0, 0.0

        losses, pings = [], []
        for host in hosts:
            loss, ping = self._measure_packet_loss_host(host, packets)
            losses.append(loss)
            if ping > 0:
                pings.append(ping)

        loss_percent = max(losses) if losses else 0.0
        avg_ping = (sum(pings) / len(pings)) if pings else 0.0
        return loss_percent, avg_ping

    def _measure_packet_loss_host(self, host: str, packets: int) -> Tuple[float, float]:
        # Try ping3
        try:
            import ping3

            ping3.EXCEPTIONS = True
            try:
                loss_count, latencies = 0, []
                for _ in range(packets):
                    res = ping3.ping(host, timeout=self.timeout)
                    if res is None or res is False:
                        loss_count += 1
                    else:
                        latencies.append(res * 1000)
                avg = (sum(latencies) / len(latencies)) if latencies else 0.0
                return (loss_count / packets) * 100, avg
            except Exception:
                return self._subprocess_ping(host, packets)
        except ImportError:
            return self._subprocess_ping(host, packets)

    def _subprocess_ping(self, host: str, packets: int) -> Tuple[float, float]:
        try:
            import re

            is_win = platform.system() == "Windows"
            args = ["ping", "-n" if is_win else "-c", str(packets), host]
            if is_win:
                args.insert(3, "-w")
                args.insert(4, "2000")

            proc = subprocess.run(
                args, capture_output=True, text=True, timeout=(packets * 2) + 5
            )
            out = (proc.stdout + "\n" + proc.stderr).lower()

            # Loss
            if is_win:
                match = re.search(r"lost\s*=\s*(\d+)", out)
                loss = (int(match.group(1)) / packets) * 100 if match else None
            else:
                match = re.search(r"(\d+\.?\d*)%\s*(?:packet\s*)?loss", out)
                loss = float(match.group(1)) if match else None

            # Latency
            times = [float(m) for m in re.findall(r"time[=<]\s*([0-9.]+)", out)]
            avg = (sum(times) / len(times)) if times else 0.0

            if loss is not None:
                return loss, avg
            return 0.0, avg
        except Exception:
            return 100.0, 0.0


@dataclass
class MonitorReport:
    device_info: DeviceInfo
    network_metrics: NetworkMetrics

    def to_json(self) -> str:
        return json.dumps(dataclasses.asdict(self), indent=2)
