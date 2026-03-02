from __future__ import annotations

import os
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Dict, Optional
from uuid import UUID

import json
import urllib.error
import urllib.request

from agent.uploader_queue import UploadQueue
from common.utils.logging_setup import setup_logger

logger = setup_logger("cloud_latency")

GLOBALPING_BASE_URL = "https://api.globalping.io/v1/measurements"
DEFAULT_TARGET = os.getenv("GLOBALPING_TARGET", "globalping.io")
DEFAULT_INTERVAL_SECONDS = int(os.getenv("GLOBALPING_INTERVAL_SECONDS", "300"))
DEFAULT_PACKETS = int(os.getenv("GLOBALPING_PACKETS", "3"))
REQUEST_TIMEOUT = int(os.getenv("GLOBALPING_TIMEOUT_SECONDS", "10"))
MAX_POLL_SECONDS = int(os.getenv("GLOBALPING_MAX_POLL_SECONDS", "15"))
DEBUG_RAW_RESPONSE = os.getenv("GLOBALPING_DEBUG", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "y",
}


@dataclass
class CloudLatencyResult:
    latency_eu_ms: Optional[float]
    latency_us_ms: Optional[float]
    latency_asia_ms: Optional[float]


class GlobalpingLatencyCollector:
    def __init__(self) -> None:
        self._target = DEFAULT_TARGET
        self._packets = max(1, min(DEFAULT_PACKETS, 10))
        self._headers = self._build_headers()
        self._locations = self._build_locations()

    def measure(self) -> CloudLatencyResult:
        measurement_id = self._create_measurement()
        if not measurement_id:
            return CloudLatencyResult(None, None, None)

        data = self._wait_for_results(measurement_id)
        if not data:
            return CloudLatencyResult(None, None, None)

        return self._extract_latencies(data)

    def _build_headers(self) -> dict:
        token = os.getenv("GLOBALPING_API_TOKEN", "").strip()
        headers = {"User-Agent": "context-of-code-agent/1.0"}
        if token:
            headers["Authorization"] = f"Bearer {token}"
        return headers

    def _build_locations(self) -> list:
        eu = os.getenv("GLOBALPING_LOC_EU", "").strip()
        us = os.getenv("GLOBALPING_LOC_US", "").strip()
        asia = os.getenv("GLOBALPING_LOC_ASIA", "").strip()

        locations = []
        if eu:
            locations.append({"magic": eu})
        else:
            locations.append({"country": "DE"})

        if us:
            locations.append({"magic": us})
        else:
            locations.append({"magic": "US+Virginia"})

        if asia:
            locations.append({"magic": asia})
        else:
            locations.append({"country": "CN"})

        return locations

    def _create_measurement(self) -> Optional[str]:
        payload = {
            "type": "ping",
            "target": self._target,
            "locations": self._locations,
            "measurementOptions": {"packets": self._packets},
        }
        data = self._request_json("POST", GLOBALPING_BASE_URL, payload)
        if not data:
            return None
        return data.get("id") or data.get("measurementId")

    def _wait_for_results(self, measurement_id: str) -> Optional[dict]:
        end_time = time.monotonic() + MAX_POLL_SECONDS
        delay = 0.5
        while time.monotonic() < end_time:
            data = self._request_json(
                "GET", f"{GLOBALPING_BASE_URL}/{measurement_id}", None
            )
            if not data:
                return None
            status = str(data.get("status", "")).lower()
            if status and status not in {"in-progress", "in_progress"}:
                if DEBUG_RAW_RESPONSE:
                    logger.debug("Globalping result payload: %s", data)
                return data

            time.sleep(delay)
            delay = min(delay + 0.5, 2.0)
        return None

    def _extract_latencies(self, data: dict) -> CloudLatencyResult:
        results = data.get("results") or []
        buckets: Dict[str, list[float]] = {"eu": [], "us": [], "asia": []}

        for item in results:
            probe = item.get("probe") or {}
            region = self._resolve_region(probe)
            if not region:
                continue
            avg_ms = self._extract_avg_ms(item.get("result") or {})
            if avg_ms is None:
                continue
            buckets[region].append(avg_ms)

        return CloudLatencyResult(
            latency_eu_ms=_safe_avg(buckets["eu"]),
            latency_us_ms=_safe_avg(buckets["us"]),
            latency_asia_ms=_safe_avg(buckets["asia"]),
        )

    @staticmethod
    def _resolve_region(probe: dict) -> Optional[str]:
        location = probe.get("location") or probe or {}
        country = _extract_country_code(location)

        if country == "DE":
            return "eu"
        if country == "US":
            return "us"
        if country == "CN":
            return "asia"

        continent = _extract_continent_code(location)
        if continent == "EU":
            return "eu"
        if continent in {"NA", "SA"}:
            return "us"
        if continent == "AS":
            return "asia"
        return None

    @staticmethod
    def _extract_avg_ms(result: dict) -> Optional[float]:
        stats = result.get("stats") or {}
        avg = _extract_avg_from_stats(stats)
        if avg is not None:
            return avg

        timings = result.get("timings")
        if isinstance(timings, dict):
            for key in ("avg", "average", "mean"):
                if key in timings and timings[key] is not None:
                    return float(timings[key])

        if isinstance(timings, list) and timings:
            numeric = _extract_numeric_timings(timings)
            if numeric:
                return float(sum(numeric)) / len(numeric)

        raw_output = result.get("rawOutput")
        if isinstance(raw_output, str):
            parsed = _parse_avg_from_raw_output(raw_output)
            if parsed is not None:
                return parsed

        return None

    def _request_json(
        self, method: str, url: str, payload: Optional[dict]
    ) -> Optional[dict]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        request = urllib.request.Request(url, data=data, method=method)
        for key, value in self._headers.items():
            request.add_header(key, value)
        if payload is not None:
            request.add_header("Content-Type", "application/json")

        try:
            with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
                body = response.read().decode("utf-8")
                return json.loads(body)
        except urllib.error.HTTPError as exc:
            logger.warning("Globalping HTTP error (%s): %s", exc.code, exc)
        except urllib.error.URLError as exc:
            logger.warning("Globalping request failed: %s", exc)
        except Exception as exc:
            logger.warning("Globalping response parse failed: %s", exc)
        return None


def _extract_country_code(location: dict) -> str:
    country = location.get("country")
    if isinstance(country, dict):
        code = country.get("code") or country.get("isoCode")
        if code:
            return str(code).upper()
        name = country.get("name")
        if name:
            return _map_country_name(str(name))
    if isinstance(country, str):
        return _map_country_name(country)
    for key in ("countryCode", "country_code"):
        value = location.get(key)
        if value:
            return str(value).upper()
    return ""


def _map_country_name(value: str) -> str:
    normalized = value.strip().upper()
    if normalized in {"GERMANY", "DE"}:
        return "DE"
    if normalized in {"UNITED STATES", "UNITED STATES OF AMERICA", "US", "USA"}:
        return "US"
    if normalized in {"CHINA", "CN"}:
        return "CN"
    if len(normalized) == 2:
        return normalized
    return ""


def _extract_continent_code(location: dict) -> str:
    continent = location.get("continent")
    if isinstance(continent, dict):
        code = continent.get("code") or continent.get("isoCode")
        if code:
            return str(code).upper()
    if isinstance(continent, str):
        return continent.strip().upper()
    for key in ("continentCode", "continent_code"):
        value = location.get(key)
        if value:
            return str(value).upper()
    return ""


def _extract_avg_from_stats(stats: dict) -> Optional[float]:
    for key in ("avg", "average", "mean"):
        if key in stats and stats[key] is not None:
            return float(stats[key])

    for group_key in ("rtt", "latency", "roundTrip"):
        group = stats.get(group_key)
        if isinstance(group, dict):
            for key in ("avg", "average", "mean"):
                if key in group and group[key] is not None:
                    return float(group[key])

    return None


def _extract_numeric_timings(timings: list) -> list[float]:
    numeric: list[float] = []
    for item in timings:
        if isinstance(item, (int, float)):
            numeric.append(float(item))
            continue
        if isinstance(item, dict):
            for key in ("time", "ms", "value"):
                if key in item and item[key] is not None:
                    try:
                        numeric.append(float(item[key]))
                        break
                    except (TypeError, ValueError):
                        continue
    return numeric


def _parse_avg_from_raw_output(raw_output: str) -> Optional[float]:
    # Example: rtt min/avg/max/mdev = 3.758/3.894/4.051/0.120 ms
    match = re.search(r"min/avg/max[^\d]*([\d.]+/[\d.]+/[\d.]+)", raw_output)
    if match:
        try:
            parts = match.group(1).split("/")
            if len(parts) >= 2:
                return float(parts[1])
        except ValueError:
            return None
    return None


def run_cloud_latency_loop(
    *,
    device_id: UUID,
    queue: UploadQueue,
    stop_event,
    interval_seconds: int = DEFAULT_INTERVAL_SECONDS,
) -> None:
    collector = GlobalpingLatencyCollector()
    while not stop_event.is_set():
        start = time.monotonic()
        try:
            result = collector.measure()
            payload = {
                "sample_type": "cloud_latency",
                "device_id": str(device_id),
                "ts": datetime.now(timezone.utc).isoformat(),
                "latency_eu_ms": result.latency_eu_ms,
                "latency_us_ms": result.latency_us_ms,
                "latency_asia_ms": result.latency_asia_ms,
            }
            queue.enqueue(payload)
            sent = queue.flush()
            if sent:
                logger.info("Uploaded %s queued sample(s).", sent)
        except Exception:
            logger.exception("Cloud latency collection failed")

        elapsed = time.monotonic() - start
        sleep_time = max(0.0, interval_seconds - elapsed)
        if sleep_time:
            stop_event.wait(sleep_time)


def _safe_avg(values: list[float]) -> Optional[float]:
    if not values:
        return None
    return float(sum(values)) / len(values)
