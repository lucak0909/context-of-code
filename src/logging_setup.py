from __future__ import annotations

import logging
from datetime import datetime
from pathlib import Path
from typing import Optional, Union

from .settings import COLOR_RESET, LEVEL_COLORS, get_log_settings


class ColorFormatter(logging.Formatter):
    def __init__(self, *args, use_color: bool = True, **kwargs) -> None:
        super().__init__(*args, **kwargs)
        self._use_color = use_color

    def format(self, record: logging.LogRecord) -> str:
        original_levelname = record.levelname
        try:
            if self._use_color:
                color = LEVEL_COLORS.get(record.levelno)
                if color:
                    record.levelname = f"{color}{record.levelname}{COLOR_RESET}"
            return super().format(record)
        finally:
            record.levelname = original_levelname


# Runtime guard to ensure handlers are attached only once per process. (NOT A CONSTANT)
_LOGGING_CONFIGURED = False


class FlaggingFileHandler(logging.FileHandler):
    def __init__(
        self,
        logs_path: Path,
        timestamp: str,
        encoding: str = "utf-8",
    ) -> None:
        self._logs_path = logs_path
        self._timestamp = timestamp
        initial_path = logs_path / f"RUN_{timestamp}.log"
        super().__init__(initial_path, mode="w", encoding=encoding)
        self._base_path = Path(initial_path)
        self._max_level = logging.NOTSET

    def emit(self, record: logging.LogRecord) -> None:
        if record.levelno > self._max_level:
            self._max_level = record.levelno
        super().emit(record)

    def close(self) -> None:
        try:
            super().close()
        finally:
            self._rename_if_needed()

    def _rename_if_needed(self) -> None:
        if not self._base_path.exists():
            return

        if self._max_level == logging.NOTSET:
            level_name = "NOTSET"
        else:
            level_name = logging.getLevelName(self._max_level)
            if not isinstance(level_name, str):
                level_name = f"LEVEL{self._max_level}"
            level_name = level_name.upper()

        target = self._logs_path / f"{level_name}_{self._timestamp}.log"
        if target == self._base_path:
            return

        target = _unique_path(target)
        try:
            self._base_path.rename(target)
        except OSError:
            pass


def setup_logger(
    name: Optional[str] = None,
    *,
    level: Optional[int] = None,
    logs_dir: Optional[str] = None,
    base_dir: Optional[Union[str, Path]] = None,
    fmt: Optional[str] = None,
    datefmt: Optional[str] = None,
) -> logging.Logger:
    log_settings = get_log_settings()

    level = level if level is not None else log_settings.level
    logs_dir = logs_dir or log_settings.logs_dir
    fmt = fmt or log_settings.fmt
    datefmt = datefmt or log_settings.datefmt

    global _LOGGING_CONFIGURED
    root_logger = logging.getLogger()

    if not _LOGGING_CONFIGURED:
        root_logger.setLevel(level)

        console_formatter = ColorFormatter(fmt=fmt, datefmt=datefmt, use_color=True)
        file_formatter = logging.Formatter(fmt=fmt, datefmt=datefmt)

        console_handler = logging.StreamHandler()
        console_handler.setFormatter(console_formatter)
        root_logger.addHandler(console_handler)

        base_path = Path(base_dir) if base_dir else Path(__file__).resolve().parent
        logs_path = base_path / logs_dir
        logs_path.mkdir(parents=True, exist_ok=True)

        timestamp = _build_timestamp()
        file_handler = FlaggingFileHandler(logs_path, timestamp)
        file_handler.setFormatter(file_formatter)
        root_logger.addHandler(file_handler)

        _LOGGING_CONFIGURED = True

    logger_name = name or "app"
    return logging.getLogger(logger_name)


def _build_timestamp() -> str:
    return datetime.now().strftime("%Y%m%d_%H%M%S_%f")


def _unique_path(path: Path) -> Path:
    if not path.exists():
        return path

    for idx in range(1, 1000):
        candidate = path.with_name(f"{path.stem}_{idx}{path.suffix}")
        if not candidate.exists():
            return candidate

    return path
