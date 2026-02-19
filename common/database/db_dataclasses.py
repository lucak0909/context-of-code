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
class Room:
    id: UUID
    user_id: UUID
    name: str
    created_at: datetime


@dataclass
class Sample:
    id: int
    device_id: UUID
    room_id: UUID
    ts: datetime
    wifi_rssi_dbm: float
    link_speed_mbps: Optional[float]
    is_connected: Optional[bool]
    test_method: Optional[str]
    created_at: datetime
