# Codebase Structure

**Analysis Date:** 2026-02-23

## Directory Layout

```
context-of-code/
├── agent/                           # Client-side metric collection agent
│   ├── __init__.py
│   ├── __main__.py                  # Entry point: delegates to console_auth
│   ├── pc_data_collector/           # PC/desktop network metrics
│   │   ├── __init__.py
│   │   ├── __main__.py
│   │   ├── collector.py             # DataCollector class for local measurements
│   │   ├── main.py                  # run() and run_with_user() orchestration
│   │   └── cli/
│   │       └── console_auth.py      # User auth and agent startup flow
│   ├── cloud_latency_collector/     # Global cloud latency via Globalping
│   │   ├── __init__.py
│   │   └── collector.py             # GlobalpingLatencyCollector class
│   └── uploader_queue/              # File-backed queue for resilient uploads
│       ├── __init__.py
│       └── queue.py                 # UploadQueue class
├── web_app/                         # Flask aggregator API server
│   ├── __init__.py
│   ├── app.py                       # Flask app initialization and blueprint registration
│   ├── blueprints/
│   │   ├── __init__.py
│   │   ├── api.py                   # POST /api/ingest endpoint (aggregator)
│   │   └── monitoring.py            # (Placeholder, not actively used)
│   └── monitor_model.py             # (Model definition, possibly legacy)
├── common/                          # Shared cross-layer utilities
│   ├── __init__.py
│   ├── settings.py                  # Environment configuration (DB, logging, aggregator API)
│   ├── database/
│   │   ├── __init__.py
│   │   ├── db_dataclasses.py        # SQLAlchemy ORM models (User, Device, Sample, etc.)
│   │   ├── db_operations.py         # Database class with CRUD methods
│   │   ├── test_connection.py       # Connection test helper
│   │   ├── test_orm.py              # ORM test helper
│   │   └── sql/                     # (SQL migration/schema files, if any)
│   ├── auth/
│   │   ├── __init__.py
│   │   └── passwords.py             # PBKDF2 hashing and verification
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logging_setup.py         # Centralized logger configuration
│   │   └── timer.py                 # BlockTimer context manager for profiling
│   └── logs/                        # Generated at runtime (rotated log files)
├── zTjLocalFiles/                   # Development/test scratch space
│   └── test.py
└── venv/                            # Python virtual environment (git-ignored)
```

## Directory Purposes

**agent/:**
- Purpose: Client-side metric collection and upload orchestration
- Contains: Data collectors, queue management, CLI authentication
- Key files: `main.py` (orchestration), `collector.py` (metrics), `queue.py` (upload buffer)

**agent/pc_data_collector/:**
- Purpose: Desktop/PC network metrics collection
- Contains: NetworkMetrics dataclass, DataCollector with caching and fallbacks
- Key files: `collector.py` (measurements), `main.py` (run loops), `console_auth.py` (auth flow)

**agent/cloud_latency_collector/:**
- Purpose: Global cloud latency measurement via Globalping API
- Contains: GlobalpingLatencyCollector with region classification and polling
- Key files: `collector.py` (API interaction and parsing)

**agent/uploader_queue/:**
- Purpose: Persistent file-backed queue for metric payload uploads
- Contains: UploadQueue with JSONL file storage, retry logic, thread safety
- Key files: `queue.py` (queue operations)

**web_app/:**
- Purpose: Server-side metric aggregation and persistence
- Contains: Flask app, API blueprint, database integration
- Key files: `app.py` (Flask setup), `api.py` (POST /api/ingest endpoint)

**common/:**
- Purpose: Shared abstractions across agent and aggregator
- Contains: Database ORM, authentication, logging, environment configuration
- Key files: `settings.py` (config), `db_operations.py` (ORM interface)

**common/database/:**
- Purpose: Data persistence layer with SQLAlchemy ORM
- Contains: Data model classes (User, Device, Sample, Room, Password)
- Key files: `db_dataclasses.py` (models), `db_operations.py` (CRUD), `test_*.py` (helpers)

**common/auth/:**
- Purpose: Cryptographic authentication utilities
- Contains: PBKDF2 password hashing and verification
- Key files: `passwords.py` (hash/verify logic)

**common/utils/:**
- Purpose: Reusable utilities for all components
- Contains: Logging setup, timing utilities
- Key files: `logging_setup.py` (logger factory), `timer.py` (profiling)

## Key File Locations

**Entry Points:**
- `agent/__main__.py`: CLI entry point for agent
- `web_app/app.py`: Flask app entry point (must call `app.run()`)
- `agent/pc_data_collector/cli/console_auth.py:main()`: Interactive user auth and agent start

**Configuration:**
- `common/settings.py`: All environment variable parsing (DB credentials, logging, aggregator URL)

**Core Logic:**
- `agent/pc_data_collector/collector.py`: Network metric gathering (speedtest, ping, download/upload)
- `agent/cloud_latency_collector/collector.py`: Globalping API integration and region mapping
- `agent/uploader_queue/queue.py`: JSONL queue persistence and HTTP upload
- `web_app/blueprints/api.py`: Aggregator API payload routing and validation
- `common/database/db_operations.py`: Database CRUD methods and ORM session management

**Testing:**
- `common/database/test_connection.py`: Database connection verification
- `common/database/test_orm.py`: ORM model testing

## Naming Conventions

**Files:**
- `*_collector.py`: Metric collection classes (e.g., `collector.py` in pc_data_collector, cloud_latency_collector)
- `db_*.py`: Database-related modules (e.g., `db_operations.py`, `db_dataclasses.py`)
- `test_*.py`: Test/helper modules in common/database
- `console_*.py`: CLI-related modules (e.g., `console_auth.py`)
- `*_setup.py`: Configuration setup functions (e.g., `logging_setup.py`)

**Directories:**
- `*_collector/`: Metric collection subsystems
- `blueprints/`: Flask blueprint modules (one per endpoint group)
- `cli/`: Command-line interface code
- `auth/`: Authentication-related utilities
- `utils/`: Generic utility modules
- `database/`: Database-related code

## Where to Add New Code

**New Metric Type (e.g., mobile metrics):**
- Primary code: Create new directory `agent/mobile_data_collector/` with `collector.py`
- Sample model: Add new columns or sample_type to `Sample` in `common/database/db_dataclasses.py`
- Aggregator route: Add new elif branch in `api.py` for sample_type
- Database method: Add new `insert_*_sample()` method in `common/database/db_operations.py`

**New API Endpoint:**
- Primary code: Add route in `web_app/blueprints/api.py` or create new blueprint file `web_app/blueprints/myfeature.py`
- Register: Import and register in `web_app/app.py` with `app.register_blueprint()`
- Tests: Create tests in `common/database/test_*.py` or new test file alongside endpoint

**New Collector Feature:**
- Shared utilities: Add to `common/utils/` (e.g., parsing, timing, transformation)
- Collector-specific: Add methods to existing collector class (e.g., `DataCollector._measure_x()`)
- Configuration: Add env variables to `common/settings.py` and `get_settings()` if needed

**Authentication Feature:**
- Password hashing: `common/auth/passwords.py`
- Database schema: Add table to `common/database/db_dataclasses.py`
- CRUD: Add methods to `common/database/db_operations.py`
- CLI flow: Modify `agent/pc_data_collector/cli/console_auth.py`

## Special Directories

**logs/:**
- Purpose: Runtime-generated log files (created on first logger initialization)
- Generated: Yes (created at runtime by `logging_setup.py`)
- Committed: No (git-ignored)

**venv/:**
- Purpose: Python virtual environment
- Generated: Yes (created by `python -m venv venv`)
- Committed: No (git-ignored)

**common/database/sql/:**
- Purpose: SQL migrations or schema definitions (if applicable)
- Generated: No (manual schema management or alembic migrations)
- Committed: Yes (version control for schema)

**zTjLocalFiles/:**
- Purpose: Local development files and test scratch space
- Generated: Ad-hoc
- Committed: Optionally (test artifacts, not core to application)

---

*Structure analysis: 2026-02-23*
