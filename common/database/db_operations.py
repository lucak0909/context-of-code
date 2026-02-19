from urllib.parse import quote_plus
from typing import Optional
from datetime import datetime, timezone
from uuid import UUID
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from .db_dataclasses import Device, Room, Sample, User
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
        query = text(
            """
            select id, email, created_at
            from users
            where email = :email
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(query, {"email": email}).fetchone()
        if not row:
            return None
        return User(id=row.id, email=row.email, created_at=row.created_at)

    def create_user(self, email: str) -> UUID:
        query = text(
            """
            insert into users (email)
            values (:email)
            returning id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(query, {"email": email}).fetchone()
        if not row:
            raise RuntimeError("Failed to create user.")
        return row.id

    def set_password(self, user_id: UUID, password_enc: str) -> None:
        query = text(
            """
            insert into passwords (user_id, password_enc)
            values (:user_id, :password_enc)
            on conflict (user_id) do update
            set password_enc = excluded.password_enc
            """
        )
        with self.engine.begin() as conn:
            conn.execute(query, {"user_id": user_id, "password_enc": password_enc})

    def get_password_hash(self, user_id: UUID) -> Optional[str]:
        query = text(
            """
            select password_enc
            from passwords
            where user_id = :user_id
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(query, {"user_id": user_id}).fetchone()
        if not row:
            return None
        return row.password_enc

    def verify_user_password(self, user_id: UUID, password: str) -> bool:
        stored = self.get_password_hash(user_id)
        if not stored:
            return False
        return verify_password(password, stored)

    def get_device_by_user_and_name(self, user_id: UUID, name: str) -> Optional[Device]:
        query = text(
            """
            select id, user_id, name, device_type, created_at
            from devices
            where user_id = :user_id and name = :name
            order by created_at asc
            limit 1
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(query, {"user_id": user_id, "name": name}).fetchone()
        if not row:
            return None
        return Device(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            device_type=row.device_type,
            created_at=row.created_at,
        )

    def create_device(self, user_id: UUID, name: str, device_type: str = "pc") -> Device:
        query = text(
            """
            insert into devices (user_id, name, device_type)
            values (:user_id, :name, :device_type)
            returning id, user_id, name, device_type, created_at
            """
        )
        with self.engine.begin() as conn:
            row = conn.execute(
                query,
                {"user_id": user_id, "name": name, "device_type": device_type},
            ).fetchone()
        if not row:
            raise RuntimeError("Failed to create device.")
        return Device(
            id=row.id,
            user_id=row.user_id,
            name=row.name,
            device_type=row.device_type,
            created_at=row.created_at,
        )

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
        query = text(
            """
            insert into samples (
                device_id,
                room_id,
                sample_type,
                ts,
                latency_ms,
                packet_loss_pct,
                down_mbps,
                up_mbps,
                test_method,
                ip
            )
            values (
                :device_id,
                :room_id,
                'desktop_network',
                :ts,
                :latency_ms,
                :packet_loss_pct,
                :down_mbps,
                :up_mbps,
                :test_method,
                :ip
            )
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "device_id": device_id,
                    "room_id": room_id,
                    "ts": timestamp,
                    "latency_ms": latency_ms,
                    "packet_loss_pct": packet_loss_pct,
                    "down_mbps": down_mbps,
                    "up_mbps": up_mbps,
                    "test_method": test_method,
                    "ip": ip,
                },
            )

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
        query = text(
            """
            insert into samples (
                device_id,
                room_id,
                sample_type,
                ts,
                latency_eu_ms,
                latency_us_ms,
                latency_asia_ms
            )
            values (
                :device_id,
                :room_id,
                'cloud_latency',
                :ts,
                :latency_eu_ms,
                :latency_us_ms,
                :latency_asia_ms
            )
            """
        )
        with self.engine.begin() as conn:
            conn.execute(
                query,
                {
                    "device_id": device_id,
                    "room_id": room_id,
                    "ts": timestamp,
                    "latency_eu_ms": latency_eu_ms,
                    "latency_us_ms": latency_us_ms,
                    "latency_asia_ms": latency_asia_ms,
                },
            )

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
