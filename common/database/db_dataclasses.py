from dataclasses import dataclass
from datetime import datetime
from uuid import UUID
from typing import Optional


@dataclass
class User:
    id: UUID
    email: str
    created_at: datetime


@dataclass
class Device:
    id: UUID
    user_id: UUID
    name: str
    device_type: str
    created_at: datetime


@dataclass
class Sample:
    id: int
    device_id: UUID
    sample_type: str
    ts: datetime
    wifi_rssi_dbm: Optional[float]
    link_speed_mbps: Optional[float]
    is_connected: Optional[bool]
    latency_ms: Optional[float]
    packet_loss_pct: Optional[float]
    down_mbps: Optional[float]
    up_mbps: Optional[float]
    ip: Optional[str]
    latency_eu_ms: Optional[float]
    latency_us_ms: Optional[float]
    latency_asia_ms: Optional[float]
    created_at: Optional[datetime]
    test_method: Optional[str]
