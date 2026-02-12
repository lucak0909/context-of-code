#!/usr/bin/env python3
import dataclasses
import json
import platform
import getpass
import sys
import os
import time
import subprocess
import socket
from dataclasses import dataclass
from typing import Dict, Any, Optional, Tuple
from src.utils.timer import BlockTimer

@dataclass
class DeviceInfo:
    """
    Holds static information about the device.
    These values are unlikely to change during a session.
    """
    username: str
    cpu_name: str
    architecture: str
    ip_address: str

@dataclass
class SystemMetrics:
    """
    Holds dynamic system metrics.
    These values change over time.
    """
    cpu_count: int

@dataclass
class NetworkMetrics:
    """
    Holds network performance metrics.
    """
    download_speed_mbps: float  # Megabits per second
    upload_speed_mbps: float    # Megabits per second
    packet_loss_percent: float  # Percentage of packets lost
    ping: float                 # Average ping latency in ms

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
            architecture=platform.machine(),
            ip_address=self._get_ip_address()
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

    def _get_ip_address(self) -> str:
        """
        Attempts to fetch the public IP address.
        Falls back to local IP if public lookup fails.
        """
        # Public IP lookup
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

        # Local IP fallback
        try:
            return socket.gethostbyname(socket.gethostname())
        except Exception:
            return "Unknown"

class NetworkMetricsCollector:
    """
    Collects network performance metrics including download speed, upload speed, and packet loss.
    Uses speedtest-cli for speed tests and ping for packet loss measurement.
    """
    
    def __init__(self, timeout: int = 10):
        """
        Initialize the network metrics collector.
        
        Args:
            timeout: Maximum seconds to wait for network tests
        """
        self.timeout = timeout
        self._cached_metrics: Optional[NetworkMetrics] = None
        self._last_cache_time = 0.0
        self._cache_duration = 300.0  # 5 minutes cache for expensive network operations
        self._speedtest_client = None
        self._speedtest_last_init = 0.0
        self._speedtest_cache_duration = 300.0
        self.packet_loss_hosts = self._load_packet_loss_hosts()
        self.packet_loss_packets = self._load_packet_loss_packets()
        self._packet_loss_debug = self._load_packet_loss_debug()

    def _load_packet_loss_debug(self) -> bool:
        """
        Enables verbose packet loss diagnostics when PACKET_LOSS_DEBUG is truthy.
        """
        raw = os.environ.get("PACKET_LOSS_DEBUG", "").strip().lower()
        return raw in {"1", "true", "yes", "y"}

    def _debug_packet_loss(self, message: str) -> None:
        if self._packet_loss_debug:
            print(message, file=sys.stderr)
    
    def get_network_metrics(self, use_cache: bool = True) -> NetworkMetrics:
        """
        Collects network metrics with optional caching.
        
        Args:
            use_cache: Whether to use cached results if available
            
        Returns:
            NetworkMetrics object with speed and packet loss data
        """
        current_time = time.time()
        
        # Check cache if enabled
        if use_cache and self._cached_metrics and (current_time - self._last_cache_time < self._cache_duration):
            return self._cached_metrics
        
        # Fetch new metrics
        with BlockTimer():
            speedtest_client = self._get_speedtest_client()
            download_speed = self._measure_download_speed(speedtest_client)
            upload_speed = self._measure_upload_speed(speedtest_client)
            packet_loss, ping_ms = self._measure_packet_loss()
        
        new_metrics = NetworkMetrics(
            download_speed_mbps=download_speed,
            upload_speed_mbps=upload_speed,
            packet_loss_percent=packet_loss,
            ping=ping_ms
        )
        
        # Update cache
        self._cached_metrics = new_metrics
        self._last_cache_time = current_time
        
        return new_metrics
    
    def _get_speedtest_client(self):
        """
        Initializes and caches a speedtest client so download/upload share the same server.
        """
        try:
            import speedtest
        except ImportError:
            return None

        now = time.time()
        if self._speedtest_client and (now - self._speedtest_last_init < self._speedtest_cache_duration):
            return self._speedtest_client

        try:
            client = speedtest.Speedtest(secure=True, timeout=self.timeout)
            client.get_best_server()
            self._speedtest_client = client
            self._speedtest_last_init = now
            return client
        except Exception as e:
            print(f"Speedtest initialization failed: {e}", file=sys.stderr)
            return None

    def _measure_download_speed(self, speedtest_client=None) -> float:
        """
        Measures download speed by fetching a file from a public server.
        Returns speed in Mbps. If speedtest-cli is installed, uses that; otherwise falls back to simple HTTP test.
        
        Returns:
            Download speed in Mbps
        """
        if speedtest_client is None:
            speedtest_client = self._get_speedtest_client()

        if speedtest_client is not None:
            try:
                download_speed_bps = speedtest_client.download()
                return download_speed_bps / 1_000_000  # Convert bits/s to Mbps
            except Exception as e:
                print(f"Speedtest download failed: {e}", file=sys.stderr)

        # Fallback: simple HTTP download test
        return self._simple_download_test()
    
    def _measure_upload_speed(self, speedtest_client=None) -> float:
        """
        Measures upload speed. Uses speedtest-cli if available.
        
        Returns:
            Upload speed in Mbps
        """
        if speedtest_client is None:
            speedtest_client = self._get_speedtest_client()

        if speedtest_client is not None:
            try:
                upload_speed_bps = speedtest_client.upload()
                return upload_speed_bps / 1_000_000  # Convert bits/s to Mbps
            except Exception as e:
                print(f"Speedtest upload failed: {e}", file=sys.stderr)

        # Fallback: simple HTTP upload test
        return self._simple_upload_test()
    
    def _simple_download_test(self) -> float:
        """
        Simple fallback download speed test using HTTP requests.
        Downloads a file and measures the speed.
        
        Returns:
            Download speed in Mbps
        """
        try:
            import urllib.request
            import time
            
            # Try multiple reliable test URLs
            test_urls = [
                "https://speed.cloudflare.com/__down?bytes=5000000",
                "https://speed.hetzner.de/10MB.bin",
                "https://proof.ovh.net/files/10Mb.dat",
            ]
            
            for test_url in test_urls:
                try:
                    start_time = time.time()
                    response = urllib.request.urlopen(test_url, timeout=self.timeout)
                    total_bytes = 0
                    max_bytes = 5_000_000
                    while total_bytes < max_bytes:
                        chunk = response.read(min(64 * 1024, max_bytes - total_bytes))
                        if not chunk:
                            break
                        total_bytes += len(chunk)
                    elapsed_time = time.time() - start_time
                    
                    if elapsed_time > 0:
                        file_size_bits = total_bytes * 8
                        speed_mbps = file_size_bits / elapsed_time / 1_000_000
                        return speed_mbps
                except Exception:
                    continue
            
            return 0.0
        except Exception as e:
            print(f"Simple download test failed: {e}", file=sys.stderr)
            return 0.0

    def _simple_upload_test(self) -> float:
        """
        Simple fallback upload speed test using HTTP POST.
        
        Returns:
            Upload speed in Mbps
        """
        try:
            import urllib.request
            import time

            test_urls = [
                "https://httpbin.org/post",
                "https://postman-echo.com/post",
            ]
            payload = os.urandom(2_000_000)

            for test_url in test_urls:
                try:
                    start_time = time.time()
                    request = urllib.request.Request(test_url, data=payload, method="POST")
                    request.add_header("Content-Type", "application/octet-stream")
                    response = urllib.request.urlopen(request, timeout=self.timeout)
                    response.read()
                    elapsed_time = time.time() - start_time

                    if elapsed_time > 0:
                        file_size_bits = len(payload) * 8
                        speed_mbps = file_size_bits / elapsed_time / 1_000_000
                        return speed_mbps
                except Exception:
                    continue

            return 0.0
        except Exception as e:
            print(f"Simple upload test failed: {e}", file=sys.stderr)
            return 0.0
    
    def _load_packet_loss_hosts(self) -> list:
        """
        Loads packet loss hosts from PACKET_LOSS_HOSTS (comma-separated).
        Defaults to a small multi-host set for redundancy.
        """
        raw = os.environ.get("PACKET_LOSS_HOSTS", "").strip()
        if raw:
            hosts = [h.strip() for h in raw.split(",") if h.strip()]
            if hosts:
                return hosts
        return ["1.1.1.1", "8.8.8.8"]

    def _load_packet_loss_packets(self) -> int:
        """
        Loads packet count from PACKET_LOSS_PACKETS.
        """
        raw = os.environ.get("PACKET_LOSS_PACKETS", "").strip()
        if raw:
            try:
                value = int(raw)
                return max(1, min(value, 50))
            except ValueError:
                pass
        return 10

    def _measure_packet_loss(self, hosts: Optional[list] = None, packets: Optional[int] = None) -> Tuple[float, float]:
        """
        Measures packet loss by pinging one or more hosts.
        
        Args:
            hosts: List of hosts to ping (defaults to configured hosts)
            packets: Number of packets to send (defaults to configured count)
            
        Returns:
            Tuple of (packet loss percent, average ping latency in ms)
        """
        if hosts is None:
            hosts = self.packet_loss_hosts
        if packets is None:
            packets = self.packet_loss_packets

        if not hosts:
            return 0.0, 0.0

        losses = []
        pings = []
        self._debug_packet_loss(f"[packet_loss] hosts={hosts} packets={packets}")
        for host in hosts:
            loss, ping_ms = self._measure_packet_loss_host(host, packets)
            losses.append(loss)
            if ping_ms > 0:
                pings.append(ping_ms)
            self._debug_packet_loss(
                f"[packet_loss] host={host} loss={loss:.2f}% ping_ms={ping_ms:.2f}"
            )

        # Use the worst observed loss to surface intermittent issues.
        self._debug_packet_loss(f"[packet_loss] losses={losses}")
        loss_percent = max(losses) if losses else 0.0
        avg_ping = (sum(pings) / len(pings)) if pings else 0.0
        return loss_percent, avg_ping

    def _measure_packet_loss_host(self, host: str, packets: int) -> Tuple[float, float]:
        """
        Measures packet loss by pinging a single host.
        """
        try:
            # Try using ping3 library first
            try:
                import ping3
                ping3.EXCEPTIONS = True
                try:
                    loss_count = 0
                    timeouts = 0
                    latencies_ms = []
                    for _ in range(packets):
                        result = ping3.ping(host, timeout=self.timeout)
                        if result is None or result is False:
                            loss_count += 1
                            timeouts += 1
                        else:
                            latencies_ms.append(result * 1000)
                    self._debug_packet_loss(
                        f"[packet_loss] ping3 host={host} timeouts={timeouts}/{packets}"
                    )
                    avg_ping = (sum(latencies_ms) / len(latencies_ms)) if latencies_ms else 0.0
                    return (loss_count / packets) * 100, avg_ping
                except Exception:
                    # If ping3 is installed but lacks permissions (common on Windows), fall back.
                    return self._subprocess_ping(host, packets)
            except ImportError:
                # Fallback to subprocess ping command
                return self._subprocess_ping(host, packets)
        except Exception as e:
            print(f"Packet loss measurement failed: {e}", file=sys.stderr)
            return 0.0, 0.0
    
    def _subprocess_ping(self, host: str, packets: int) -> Tuple[float, float]:
        """
        Fallback packet loss measurement using subprocess ping command.
        
        Args:
            host: Host to ping
            packets: Number of packets to send
            
        Returns:
            Tuple of (packet loss percent, average ping latency in ms)
        """
        try:
            import re
            
            # Platform-specific ping command
            if platform.system() == "Windows":
                per_packet_timeout = min(self.timeout, 2)
                total_timeout = (per_packet_timeout * packets) + 2
                command = ["ping", "-n", str(packets), "-w", str(int(per_packet_timeout * 1000)), host]
                output = subprocess.run(command, capture_output=True, text=True, timeout=total_timeout)
                output_text = (output.stdout + "\n" + output.stderr).lower()
                self._debug_packet_loss(f"[packet_loss] ping cmd={' '.join(command)} rc={output.returncode}")
                if self._packet_loss_debug:
                    snippet = output_text.strip().replace("\r", "")
                    self._debug_packet_loss(f"[packet_loss] ping output:\n{snippet[:600]}")
                # Parse Windows ping output for loss count (e.g., "Lost = 0")
                match = re.search(r"lost\s*=\s*(\d+)", output_text)
                loss_percent = None
                if match:
                    loss_packets = int(match.group(1))
                    loss_percent = (loss_packets / packets) * 100 if packets > 0 else 0.0
                # Try alternate format: "X% loss"
                if loss_percent is None:
                    match = re.search(r"(\d+)%\s*loss", output_text)
                    if match:
                        loss_percent = float(match.group(1))
            else:
                # macOS and Linux
                per_packet_timeout = min(self.timeout, 2)
                total_timeout = (per_packet_timeout * packets) + 2
                command = ["ping", "-c", str(packets), host]
                output = subprocess.run(command, capture_output=True, text=True, timeout=total_timeout)
                output_text = (output.stdout + "\n" + output.stderr).lower()
                self._debug_packet_loss(f"[packet_loss] ping cmd={' '.join(command)} rc={output.returncode}")
                if self._packet_loss_debug:
                    snippet = output_text.strip().replace("\r", "")
                    self._debug_packet_loss(f"[packet_loss] ping output:\n{snippet[:600]}")
                # Parse Unix ping output: looks for "X% packet loss"
                match = re.search(r"(\d+\.?\d*)%\s*(?:packet\s*)?loss", output_text)
                loss_percent = float(match.group(1)) if match else None

            # Parse per-reply times (ms) for average latency
            times = []
            for match in re.findall(r"time[=<]\s*([0-9.]+)", output_text):
                try:
                    times.append(float(match))
                except ValueError:
                    continue
            avg_ping = (sum(times) / len(times)) if times else 0.0

            if loss_percent is not None:
                return loss_percent, avg_ping
            
            # Fallback: count successful replies by TTL/time tokens (locale-agnostic)
            reply_count = len(re.findall(r"ttl=", output_text))
            if reply_count == 0:
                reply_count = len(re.findall(r"time[=<]", output_text))
            if reply_count > 0 and packets > 0:
                loss_packets = max(packets - reply_count, 0)
                loss_percent = (loss_packets / packets) * 100
                return loss_percent, avg_ping

            if output.returncode != 0 and packets > 0:
                return 100.0, avg_ping

            # If no losses detected, return 0%
            return 0.0, avg_ping
        except subprocess.TimeoutExpired:
            # If ping hangs, treat as 100% loss to avoid false zeros.
            self._debug_packet_loss("[packet_loss] ping timed out; treating as 100% loss")
            return 100.0, 0.0
        except Exception as e:
            print(f"Subprocess ping failed: {e}", file=sys.stderr)
            return 0.0, 0.0

@dataclass
class MonitorReport:
    """
    Top-level data model combining all gathered information.
    """
    device_info: DeviceInfo
    metrics: SystemMetrics
    network_metrics: Optional[NetworkMetrics] = None
    
    def to_json(self) -> str:
        """Serializes the entire report to a JSON string."""
        return json.dumps(dataclasses.asdict(self), indent=2)

def main():
    try:
        collector = DataCollector()
        network_collector = NetworkMetricsCollector()
        
        # 1. Gather Data
        device_info = collector.get_device_info()
        metrics = collector.get_system_metrics()
        
        # 2. Optionally gather network metrics (commented out by default as it's time-consuming)
        # Uncomment the line below to include network metrics in the report
        network_metrics = network_collector.get_network_metrics(use_cache=False)

        
        # 3. Construct Report
        report = MonitorReport(device_info=device_info, metrics=metrics, network_metrics=network_metrics)
        
        # 4. Output as JSON 
        print(report.to_json())
        
        # 5. Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        # In a real app, you might log this error to a file
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        sys.exit(1)

if __name__ == "__main__":
    main()
 
