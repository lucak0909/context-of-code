from urllib.parse import quote_plus
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import NullPool
from .db_dataclasses import Device, Room, Sample, User, Password
from ..settings import get_settings
from ..utils.logging_setup import setup_logger
from ..auth.passwords import verify_password

logger = setup_logger(name=__name__)


class Database:
    def __init__(self, dsn: Optional[str] = None):
        database_url = self._build_database_url(dsn)
        # Session pooler: disable SQLAlchemy client-side pooling to avoid holding stateful
        # connections in PgBouncer.
        self.engine = create_engine(database_url, poolclass=NullPool)
        logger.info("Database engine created with NullPool.")

    def close(self):
        logger.info("Disposing database engine.")
        self.engine.dispose()

    def get_user_by_email(self, email: str) -> Optional[User]:
        with Session(self.engine) as session:
            return session.scalars(select(User).where(User.email == email)).first()

    def create_user(self, email: str) -> UUID:
        with Session(self.engine) as session:
            user = User(email=email)
            session.add(user)
            session.commit()
            return user.id

    def set_password(self, user_id: UUID, password_enc: str) -> None:
        with Session(self.engine) as session:
            # Upsert logic
            password_record = session.scalars(select(Password).where(Password.user_id == str(user_id))).first()
            if password_record:
                password_record.password_enc = password_enc
            else:
                session.add(Password(user_id=str(user_id), password_enc=password_enc))
            session.commit()

    def get_password_hash(self, user_id: UUID) -> Optional[str]:
        with Session(self.engine) as session:
            password_record = session.scalars(select(Password).where(Password.user_id == str(user_id))).first()
            if not password_record:
                return None
            return password_record.password_enc

    def verify_user_password(self, user_id: UUID, password: str) -> bool:
        stored = self.get_password_hash(user_id)
        if not stored:
            return False
        return verify_password(password, stored)

    def get_device_by_user_and_name(self, user_id: UUID, name: str) -> Optional[Device]:
        with Session(self.engine) as session:
            return session.scalars(
                select(Device)
                .where(Device.user_id == str(user_id), Device.name == name)
                .order_by(Device.created_at.asc())
            ).first()

    def create_device(self, user_id: UUID, name: str, device_type: str = "pc") -> Device:
        with Session(self.engine) as session:
            device = Device(user_id=str(user_id), name=name, device_type=device_type)
            session.add(device)
            session.commit()
            session.refresh(device)
            # SQLAlchemy attaches returned object to session by default, expunge it so it can be returned
            session.expunge(device)
            return device

    def get_or_create_device(self, user_id: UUID, name: str, device_type: str = "pc") -> Device:
        device = self.get_device_by_user_and_name(user_id, name)
        if device:
            return device
        return self.create_device(user_id, name, device_type=device_type)

    def insert_desktop_network_sample(
        self,
        device_id: UUID,
        *,
        latency_ms: float,
        packet_loss_pct: float,
        down_mbps: float,
        up_mbps: float,
        test_method: Optional[str] = None,
        ip: Optional[str] = None,
        ts: Optional[datetime] = None,
        room_id: Optional[UUID] = None,
    ) -> None:
        timestamp = ts or datetime.now(timezone.utc)
        with Session(self.engine) as session:
            sample = Sample(
                device_id=str(device_id),
                room_id=str(room_id) if room_id else None,
                sample_type='desktop_network',
                ts=timestamp,
                latency_ms=latency_ms,
                packet_loss_pct=packet_loss_pct,
                down_mbps=down_mbps,
                up_mbps=up_mbps,
                test_method=test_method,
                ip=ip
            )
            session.add(sample)
            session.commit()

    def insert_cloud_latency_sample(
        self,
        device_id: UUID,
        *,
        latency_eu_ms: Optional[float],
        latency_us_ms: Optional[float],
        latency_asia_ms: Optional[float],
        ts: Optional[datetime] = None,
        room_id: Optional[UUID] = None,
    ) -> None:
        timestamp = ts or datetime.now(timezone.utc)
        with Session(self.engine) as session:
            sample = Sample(
                device_id=str(device_id),
                room_id=str(room_id) if room_id else None,
                sample_type='cloud_latency',
                ts=timestamp,
                latency_eu_ms=latency_eu_ms,
                latency_us_ms=latency_us_ms,
                latency_asia_ms=latency_asia_ms
            )
            session.add(sample)
            session.commit()

    @staticmethod
    def _build_database_url(dsn: Optional[str]) -> str:
        if dsn:
            logger.info("Using provided DSN for database connection.")
            return dsn

        settings = get_settings()
        user = settings.db_user
        password = settings.db_password
        host = settings.db_host
        port = settings.db_port
        dbname = settings.db_name
        logger.info("Building database URL for host=%s port=%s db=%s.", host, port, dbname)

        safe_user = quote_plus(user)
        safe_password = quote_plus(password)
        return (
            f"postgresql+psycopg2://{safe_user}:{safe_password}"
            f"@{host}:{port}/{dbname}?sslmode=require"
        )
