from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, text
from sqlalchemy.orm import declarative_base
from datetime import datetime
from uuid import UUID

Base = declarative_base()


class User(Base):
    __tablename__ = 'users'

    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()"))
    email = Column(String, unique=True, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class Password(Base):
    __tablename__ = 'passwords'

    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"), nullable=False, unique=True)
    password_enc = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class Device(Base):
    __tablename__ = 'devices'

    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(String, ForeignKey('users.id', ondelete="CASCADE"), nullable=False)
    name = Column(String, nullable=False)
    device_type = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class Room(Base):
    __tablename__ = 'rooms'

    id = Column(String, primary_key=True, server_default=text("gen_random_uuid()"))
    user_id = Column(String, nullable=False)
    name = Column(String, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=text("now()"))


class Sample(Base):
    __tablename__ = 'samples'

    id = Column(Integer, primary_key=True, autoincrement=True)
    device_id = Column(String, ForeignKey('devices.id', ondelete="CASCADE"), nullable=False)
    room_id = Column(String, ForeignKey('rooms.id', ondelete="SET NULL"))
    sample_type = Column(String, nullable=False)
    ts = Column(DateTime(timezone=True), nullable=False)

    # Mobile WiFi metrics
    wifi_rssi_dbm = Column(Float)
    link_speed_mbps = Column(Float)
    is_connected = Column(Boolean)

    # Desktop network metrics
    latency_ms = Column(Float)
    packet_loss_pct = Column(Float)
    down_mbps = Column(Float)
    up_mbps = Column(Float)
    test_method = Column(String)
    ip = Column(String)

    # Cloud latency metrics
    latency_eu_ms = Column(Float)
    latency_us_ms = Column(Float)
    latency_asia_ms = Column(Float)

    created_at = Column(DateTime(timezone=True), server_default=text("now()"))
