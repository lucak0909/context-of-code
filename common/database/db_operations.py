from urllib.parse import quote_plus
from typing import Optional
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
