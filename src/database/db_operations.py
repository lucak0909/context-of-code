from urllib.parse import quote_plus
from typing import Optional
from sqlalchemy import create_engine, text
from sqlalchemy.pool import NullPool
from .db_dataclasses import Device, Room, Sample
from ..settings import get_settings
from ..logging_setup import setup_logger

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
