# Technology Stack

**Analysis Date:** 2026-02-23

## Languages

**Primary:**
- Python 3.10 - Agent data collection, web server, database operations, API

**Secondary:**
- None detected

## Runtime

**Environment:**
- Python 3.10 via Virtual Environment (`venv/`)

**Package Manager:**
- pip 3.10
- Lockfile: `requirements.txt` present

## Frameworks

**Core:**
- Flask 3.1.2 - Web framework for REST API server (`web_app/app.py`)
- SQLAlchemy 2.0.46 - ORM for database abstraction and schema mapping (`common/database/db_operations.py`)

**Networking & HTTP:**
- urllib3 1.25.11 - HTTP client library (bundled with requests)
- requests 2.22.0 - HTTP library for API requests
- Werkzeug 3.1.5 - WSGI application server (Flask dependency)

**CLI & Execution:**
- click 8.1.8 - Command-line interface framework
- python-daemon 2.2.4 - Daemonization support for agent processes

**Testing & Data:**
- ping3 - Network ping utility library
- speedtest-cli - Ookla Speedtest integration for bandwidth testing

**Build/Dev:**
- Jinja2 3.1.6 - Template engine (Flask dependency)
- blinker 1.9.0 - Signal/event dispatch (Flask dependency)

## Key Dependencies

**Critical:**
- psycopg2-binary - PostgreSQL database adapter for SQLAlchemy
- SQLAlchemy 2.0.46 - ORM for SQL abstraction and session management
- Flask 3.1.2 - Core HTTP framework for aggregator API
- flask-cors - Cross-Origin Resource Sharing support

**Infrastructure:**
- python-dotenv 1.2.1 - Environment variable loading from `.env` files
- certifi 2026.1.4 - CA certificate bundle for HTTPS validation
- chardet 3.0.4 - Character encoding detection
- greenlet 3.3.1 - Lightweight concurrency (SQLAlchemy dependency)
- filelock 3.0.12 - File-based locking mechanism
- lockfile 0.12.2 - Cross-platform file locking

## Configuration

**Environment:**
- Configuration via `.env` file (present but not readable due to security constraints)
- Settings loaded via `common/settings.py` using `python-dotenv`

**Required Environment Variables:**
- `user` - PostgreSQL database username
- `password` - PostgreSQL database password
- `host` - PostgreSQL database host
- `port` - PostgreSQL database port
- `dbname` - PostgreSQL database name
- `AGGREGATOR_API_URL` (optional) - Override default aggregator endpoint, defaults to `http://127.0.0.1:5000/api/ingest`
- `AGGREGATOR_TIMEOUT_SECONDS` (optional) - HTTP request timeout, defaults to 10
- `AGENT_QUEUE_PATH` (optional) - Queue file location, defaults to `agent_queue.jsonl`
- `LOG_LEVEL` (optional) - Logging level (DEBUG/INFO/WARNING/ERROR), defaults to INFO
- `LOGS_DIR` (optional) - Log directory, defaults to `logs/`
- `GLOBALPING_API_TOKEN` (optional) - API token for Globalping cloud latency service
- `GLOBALPING_TARGET` (optional) - Target for Globalping ping tests, defaults to `globalping.io`
- `GLOBALPING_INTERVAL_SECONDS` (optional) - Interval between cloud latency tests, defaults to 300
- `GLOBALPING_PACKETS` (optional) - Number of ping packets per test, defaults to 3
- `GLOBALPING_TIMEOUT_SECONDS` (optional) - Timeout for Globalping requests, defaults to 10
- `GLOBALPING_MAX_POLL_SECONDS` (optional) - Max poll time for measurement results, defaults to 15
- `GLOBALPING_LOC_EU` (optional) - Globalping location selector for EU
- `GLOBALPING_LOC_US` (optional) - Globalping location selector for US
- `GLOBALPING_LOC_ASIA` (optional) - Globalping location selector for Asia
- `PACKET_LOSS_HOSTS` (optional) - Comma-separated hosts for packet loss testing, defaults to `1.1.1.1,8.8.8.8`
- `PACKET_LOSS_PACKETS` (optional) - Packets per host test, defaults to 2, max 50
- `PACKET_LOSS_DEBUG` (optional) - Enable debug logging for packet loss tests

**Build:**
- No explicit build configuration detected
- Direct Python execution via `python -m agent.pc_data_collector.main` or Flask dev server

## Platform Requirements

**Development:**
- Python 3.10+
- Virtual environment for dependency isolation
- PostgreSQL 12+ or compatible (Supabase cloud database)
- Network access for:
  - Speedtest CLI server queries
  - Globalping API (`https://api.globalping.io/v1/measurements`)
  - PostgreSQL database (configurable host/port)

**Production:**
- Python 3.10 runtime environment
- PostgreSQL database connectivity (SSL required: `sslmode=require` in connection string)
- Network connectivity for:
  - HTTP POST requests to aggregator API endpoint
  - Globalping cloud latency service
  - Public DNS resolution (for IP address detection)

---

*Stack analysis: 2026-02-23*
