from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import logging
import os
from typing import Optional

from dotenv import load_dotenv

DB_ENV_USER = "user"
DB_ENV_PASSWORD = "password"
DB_ENV_HOST = "host"
DB_ENV_PORT = "port"
DB_ENV_NAME = "dbname"

DB_REQUIRED_ENV_VARS = (
    DB_ENV_USER,
    DB_ENV_PASSWORD,
    DB_ENV_HOST,
    DB_ENV_PORT,
    DB_ENV_NAME,
)

ENV_AGGREGATOR_API_URL = "AGGREGATOR_API_URL"
DEFAULT_API_URL = "http://127.0.0.1:5000/api/ingest"

DEFAULT_LOGS_DIR = "logs"
DEFAULT_LOG_LEVEL = logging.INFO
DEFAULT_LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
DEFAULT_LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
COLOR_RESET = "\x1b[0m"
LEVEL_COLORS = {
    logging.DEBUG: "\x1b[36m",
    logging.INFO: "\x1b[32m",
    logging.WARNING: "\x1b[33m",
    logging.ERROR: "\x1b[31m",
    logging.CRITICAL: "\x1b[35m",
}

ENV_LOG_LEVEL = "LOG_LEVEL"
ENV_LOGS_DIR = "LOGS_DIR"
ENV_LOG_FORMAT = "LOG_FORMAT"
ENV_LOG_DATE_FORMAT = "LOG_DATE_FORMAT"


def _require_env(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise ValueError(f"Missing env var: {name}")
    return value


def _parse_log_level(value: Optional[str], default: int) -> int:
    if not value:
        return default

    if value.isdigit():
        return int(value)

    level = logging.getLevelName(value.upper())
    if isinstance(level, int):
        return level

    return default


@dataclass(frozen=True)
class LogSettings:
    logs_dir: str
    level: int
    fmt: str
    datefmt: str


@dataclass(frozen=True)
class Settings:
    db_user: str
    db_password: str
    db_host: str
    db_port: int
    db_name: str
    aggregator_api_url: str


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    load_dotenv()

    missing = [name for name in DB_REQUIRED_ENV_VARS if not os.getenv(name)]
    if missing:
        raise ValueError(
            "Missing required env vars for DB connection: "
            + ", ".join(missing)
        )

    return Settings(
        db_user=_require_env(DB_ENV_USER),
        db_password=_require_env(DB_ENV_PASSWORD),
        db_host=_require_env(DB_ENV_HOST),
        db_port=int(_require_env(DB_ENV_PORT)),
        db_name=_require_env(DB_ENV_NAME),
        aggregator_api_url=os.getenv(ENV_AGGREGATOR_API_URL, DEFAULT_API_URL),
    )


@lru_cache(maxsize=1)
def get_log_settings() -> LogSettings:
    load_dotenv()

    logs_dir = os.getenv(ENV_LOGS_DIR, DEFAULT_LOGS_DIR)
    level = _parse_log_level(os.getenv(ENV_LOG_LEVEL), DEFAULT_LOG_LEVEL)
    fmt = os.getenv(ENV_LOG_FORMAT, DEFAULT_LOG_FORMAT)
    datefmt = os.getenv(ENV_LOG_DATE_FORMAT, DEFAULT_LOG_DATE_FORMAT)

    return LogSettings(
        logs_dir=logs_dir,
        level=level,
        fmt=fmt,
        datefmt=datefmt,
    )
