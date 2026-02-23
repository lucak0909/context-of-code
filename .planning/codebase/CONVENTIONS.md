# Coding Conventions

**Analysis Date:** 2026-02-23

## Naming Patterns

**Files:**
- Lowercase with underscores: `db_operations.py`, `cloud_latency_collector.py`, `logging_setup.py`
- Test files follow pattern: `test_*.py` (e.g., `test_orm.py`, `test_connection.py`)
- Package directories use lowercase: `database/`, `utils/`, `blueprints/`, `pc_data_collector/`

**Functions:**
- Lowercase with underscores for all functions: `get_network_metrics()`, `measure_packet_loss()`, `setup_logger()`
- Private/internal functions prefixed with underscore: `_collect_network_metrics_parallel()`, `_get_speedtest_client()`, `_request_json()`
- Helper functions follow same convention: `_parse_optional_float()`, `_parse_timestamp()`, `_extract_latencies()`

**Variables:**
- Lowercase with underscores: `device_id`, `download_speed`, `packet_loss_packets`
- Constants in UPPERCASE: `DEFAULT_ITERATIONS`, `ALGORITHM`, `DEFAULT_TIMEOUT`, `DEFAULT_API_URL`, `REQUEST_TIMEOUT`
- Private module variables prefixed with underscore: `_db`, `_LOGGING_CONFIGURED`, `_speedtest_clients`
- Cache/mutable module state with underscore: `_cached_metrics`, `_last_cache_time`

**Types:**
- Classes use PascalCase: `DataCollector`, `Database`, `NetworkMetrics`, `User`, `Device`, `Sample`, `GlobalpingLatencyCollector`, `UploadQueue`
- Dataclass fields use snake_case: `packet_loss_percent`, `download_speed_mbps`, `ip_address`, `latency_eu_ms`

## Code Style

**Formatting:**
- No explicit formatter configured (no `.prettierrc` or `black` config found)
- Uses standard Python conventions: 4-space indentation
- Line lengths appear flexible (examples show lines up to 100+ characters)
- Imports organized with `from __future__ import annotations` at top (Python 3.7+ style hints)

**Linting:**
- No `.eslintrc` or equivalent Python linter config found
- Follows PEP 8 conventions implicitly
- Type hints used throughout for function parameters and return types: `def get_user_by_email(self, email: str) -> Optional[User]:`

## Import Organization

**Order:**
1. `__future__` imports: `from __future__ import annotations`
2. Standard library imports: `import os`, `import json`, `from pathlib import Path`
3. Third-party imports: `from sqlalchemy import ...`, `from flask import Blueprint`
4. Local imports: `from common.utils.logging_setup import setup_logger`, `from .db_operations import Database`

**Path Aliases:**
- No import aliases configured; all imports use full module paths
- Relative imports within package: `from .db_operations import Database`
- Absolute imports for cross-package: `from common.database.db_operations import Database`

**Examples from codebase:**
```python
# From db_operations.py
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
```

```python
# From collector.py
from dataclasses import dataclass
from typing import Optional, Tuple
from common.utils.timer import BlockTimer
from common.utils.logging_setup import setup_logger
```

## Error Handling

**Patterns:**
- Try/except blocks catch broad exceptions and log them: `except Exception as exc: logger.warning(...)`
- Specific exception handling where needed: `except ValueError as exc:`, `except urllib.error.HTTPError as exc:`
- Context managers used extensively with try/finally cleanup: `finally: if db is not None: try: db.close()`
- Silent failures with return defaults common in utility functions: `except Exception: return "127.0.0.1"`
- Assertions used in test flows: `assert user is not None`, `assert user.id == user_id`

**Examples:**
```python
# From db_operations.py - broad exception catch with logging
try:
    db = Database()
    # ... operations ...
except Exception:
    logger.exception("Failed ORM tests.")
    raise
finally:
    if db is not None:
        try:
            db.close()
        except Exception:
            pass
```

```python
# From passwords.py - specific exception handling
try:
    algorithm, iterations_str, salt_b64, digest_b64 = stored.split("$", 3)
except ValueError as exc:
    raise ValueError("Invalid password hash format.") from exc
```

```python
# From collector.py - graceful degradation
try:
    with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as s:
        s.connect(("8.8.8.8", 80))
        return s.getsockname()[0]
except Exception:
    return "127.0.0.1"
```

## Logging

**Framework:** `logging` standard library with custom setup in `common/utils/logging_setup.py`

**Setup Pattern:**
- Custom `setup_logger()` function used to initialize loggers: `logger = setup_logger(name=__name__)`
- Global `_LOGGING_CONFIGURED` flag prevents duplicate handler attachment
- Two handlers: console (with color) + file handler
- File handler renames log file after completion based on max log level (e.g., `RUN_timestamp.log` → `ERROR_timestamp.log`)

**Logging Levels:**
- `logger.debug()` for detailed diagnostics
- `logger.info()` for operation progress and data flow
- `logger.warning()` for recoverable issues
- `logger.error()` for failures without crash
- `logger.exception()` for caught exceptions with traceback

**Patterns:**
```python
# From collector.py - structured logging with metrics
logger.info(
    "Ingested %s sample for device %s (ts=%s).",
    sample_type, device_id, ts.isoformat(),
)

# From cloud_latency_collector.py - warning on external service failure
logger.warning("Globalping HTTP error (%s): %s", exc.code, exc)

# From api.py - exception logging with context
logger.error("Database write failed during ingest: %s", exc, exc_info=True)
```

## Comments

**When to Comment:**
- Inline comments explain non-obvious logic: `# Upsert logic`, `# Session pooler: disable SQLAlchemy...`
- Comments mark sections with separator lines: `# ── Helper utilities ──────...`
- Comments document workarounds: `#self note: return None NOT self because...`
- Comments explain configuration: `# 5 minutes cache for expensive network operations`

**JSDoc/TSDoc:**
- Docstrings used for classes and public methods
- Docstrings show expected JSON body structure in Flask routes
- Function docstrings explain purpose and complexity: `"""Lazy-initialise the Database singleton..."""`

**Examples:**
```python
# From db_operations.py
class Database:
    def __init__(self, dsn: Optional[str] = None):
        database_url = self._build_database_url(dsn)
        # Session pooler: disable SQLAlchemy client-side pooling to avoid holding stateful
        # connections in PgBouncer.
        self.engine = create_engine(database_url, poolclass=NullPool)

# From api.py - section markers
# ── 1. Validate Content-Type ──────────────────────────────────────────
```

## Function Design

**Size:**
- Functions are generally 10-50 lines
- Larger functions (100+ lines) are helper methods that orchestrate multiple subtasks
- Examples: `_collect_network_metrics_parallel()` (60 lines), `_extract_latencies()` (20 lines)

**Parameters:**
- Parameters use type hints: `def get_user_by_email(self, email: str) -> Optional[User]:`
- Keyword-only arguments use `*` separator for clarity: `def insert_desktop_network_sample(self, device_id: UUID, *, latency_ms: float, ...)`
- Optional parameters have defaults: `use_cache: bool = True`, `timeout: int = 10`

**Return Values:**
- Functions return types explicitly: `-> Optional[User]`, `-> Tuple[float, str]`, `-> CloudLatencyResult`
- Optional returns use `Optional[T]` notation
- Multiple return values use tuples: `-> Tuple[float, float, str, float, float, str]`

**Examples:**
```python
# Keyword-only pattern for clarity
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
    ...

# Multiple return values in tuple
def _collect_network_metrics_parallel(
    self,
) -> Tuple[float, float, str, float, float, str]:
    ...
```

## Module Design

**Exports:**
- Modules export public classes and functions at module level
- Private functions/classes prefixed with underscore not exported
- `__init__.py` files minimize exports (most are minimal or empty)

**Barrel Files:**
- `common/__init__.py`, `agent/__init__.py` are minimal/empty
- No star imports observed
- Explicit imports preferred: `from common.database.db_operations import Database`

**Examples:**
```python
# From cloud_latency_collector/__init__.py
# Exports the main function for use elsewhere
from .collector import run_cloud_latency_loop

# From database/__init__.py - minimal
# Mostly just defines structure
```

## Database/ORM Patterns

**SQLAlchemy 2.0:**
- Uses declarative base: `Base = declarative_base()`
- Models inherit from Base: `class User(Base):`
- Uses modern `Session(engine)` context manager pattern
- Modern select() syntax: `select(User).where(...)`
- Explicit session expunge for returned objects: `session.expunge(device)`

**Configuration:**
- Connection strings built dynamically from env vars
- NullPool used to avoid holding stateful connections
- URL encoding for credentials: `quote_plus(password)`

---

*Convention analysis: 2026-02-23*
