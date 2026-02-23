# External Integrations

**Analysis Date:** 2026-02-23

## APIs & External Services

**Cloud Latency Measurement:**
- Globalping - Global network latency measurement service
  - API Endpoint: `https://api.globalping.io/v1/measurements`
  - SDK/Client: Native HTTP via `urllib.request` in `agent/cloud_latency_collector/collector.py`
  - Auth: Optional Bearer token via `GLOBALPING_API_TOKEN` environment variable
  - Purpose: Measures latency to three global regions (EU, US, Asia) by triggering ping measurements from distributed probe locations
  - Implementation: `GlobalpingLatencyCollector` class in `agent/cloud_latency_collector/collector.py`
  - Request Type: JSON POST to create measurements, JSON GET to poll results
  - Response Format: JSON with measurement ID, status, and per-probe latency results
  - Configurable Locations: EU (default Germany), US (default Virginia), Asia (default China)

**Network Speed Testing:**
- Ookla Speedtest CLI - Bandwidth measurement service
  - SDK/Client: `speedtest-cli` library (dynamically imported in `agent/pc_data_collector/collector.py`)
  - Fallback: Simple HTTP download/upload tests if speedtest unavailable
  - Purpose: Measures download and upload bandwidth
  - Implementation: `DataCollector._measure_download_speed()`, `DataCollector._measure_upload_speed()`
  - Download Test URLs: Heanet/Tele2 mirrors and Cloudflare
  - Upload Test URLs: httpbin.org and Postman Echo

**Network Diagnostics:**
- ICMP Ping Service - Network latency and packet loss detection
  - SDK/Client: `ping3` library (optional) with subprocess fallback in `agent/pc_data_collector/collector.py`
  - Fallback: Platform-specific subprocess ping (Windows: `ping -n`, Unix: `ping -c`)
  - Purpose: Measures packet loss percentage and average latency to target hosts
  - Default Hosts: `1.1.1.1` (Cloudflare), `8.8.8.8` (Google DNS)
  - Configurable: `PACKET_LOSS_HOSTS` and `PACKET_LOSS_PACKETS` env vars
  - Implementation: `DataCollector._measure_packet_loss()`, `DataCollector._measure_packet_loss_host()`

## Data Storage

**Primary Database:**
- PostgreSQL (via Supabase cloud)
  - Connection: `postgresql+psycopg2://user:password@host:port/dbname?sslmode=require`
  - Client: `psycopg2-binary` adapter
  - ORM: SQLAlchemy 2.0.46
  - Schema Location: `common/database/db_dataclasses.py` (declarative ORM models)
  - Tables:
    - `users` - User accounts with email
    - `passwords` - Encrypted password storage
    - `devices` - Registered devices per user
    - `rooms` - Physical locations (optional)
    - `samples` - Telemetry metrics (desktop network, cloud latency, mobile WiFi)
  - Connection Pool: NullPool (disabled) to work with PgBouncer connection pooling
  - SSL: Required in production (`sslmode=require`)

**Queue Storage:**
- Local Filesystem (JSONL file-backed queue)
  - Location: `agent_queue.jsonl` (configurable via `AGENT_QUEUE_PATH`)
  - Format: JSON Lines (one JSON object per line)
  - Purpose: Offline-safe buffering of telemetry payloads before transmission to aggregator
  - Implementation: `UploadQueue` class in `agent/uploader_queue/queue.py`
  - Thread Safety: Protected by `threading.Lock()`

**File Storage:**
- Local filesystem only - No cloud file storage detected
- Logs: Directory configurable via `LOGS_DIR` env var, defaults to `logs/`

**Caching:**
- In-Memory Application Cache (no external cache service)
  - Network Metrics Cache: 5-minute TTL in `DataCollector._cached_metrics`
  - Speedtest Client Cache: 5-minute TTL in `DataCollector._speedtest_clients`
  - Lazy Database Singleton: Single instance per Flask process in `api_bp._get_db()`

## Authentication & Identity

**Auth Provider:**
- Custom implementation (no external OAuth/SSO)
  - User Registration: Email-based with hashed password
  - Password Storage: Encrypted via `common/auth/passwords.py`
  - Implementation: `Database.create_user()`, `Database.set_password()`, `Database.verify_user_password()`
  - Session Management: Per-request ORM session via SQLAlchemy

**Device Registration:**
- Internal device tracking without external identity provider
  - Device Creation: Automatic registration on agent startup via `Database.get_or_create_device()`
  - Device Linking: Associated with user via `user_id` foreign key
  - Identification: UUID primary key, device name and type fields

## Monitoring & Observability

**Error Tracking:**
- None detected - No external error tracking service (Sentry, DataDog, etc.)

**Logs:**
- Structured logging to local filesystem
  - Framework: Python `logging` module via `common/utils/logging_setup.py`
  - Format: `"%(asctime)s | %(levelname)s | %(name)s | %(message)s"`
  - Output: File and console (formatted with ANSI color codes)
  - Configurable: `LOG_LEVEL`, `LOG_FORMAT`, `LOG_DATE_FORMAT` env vars

**Health/Status Checks:**
- Not detected - No external health check service

## CI/CD & Deployment

**Hosting:**
- Local development environment (no production deployment detected)
- Target: Distributed across agent machines and central cloud server
- Server Framework: Flask development server via `web_app/app.py`

**CI Pipeline:**
- None detected - Git repository present but no CI/CD workflows

**Database Migrations:**
- Manual schema management via SQLAlchemy ORM models
- Schema file: `common/database/db_dataclasses.py`
- No migration tool detected (Alembic not in dependencies)

## Environment Configuration

**Required env vars for runtime:**
- PostgreSQL connection: `user`, `password`, `host`, `port`, `dbname`
- Aggregator API: `AGGREGATOR_API_URL`, `AGGREGATOR_TIMEOUT_SECONDS`
- Queue management: `AGENT_QUEUE_PATH`
- Globalping service: `GLOBALPING_API_TOKEN`, `GLOBALPING_TARGET`, `GLOBALPING_INTERVAL_SECONDS`, `GLOBALPING_PACKETS`, `GLOBALPING_TIMEOUT_SECONDS`, `GLOBALPING_MAX_POLL_SECONDS`, `GLOBALPING_LOC_EU`, `GLOBALPING_LOC_US`, `GLOBALPING_LOC_ASIA`
- Packet loss testing: `PACKET_LOSS_HOSTS`, `PACKET_LOSS_PACKETS`, `PACKET_LOSS_DEBUG`
- Logging: `LOG_LEVEL`, `LOGS_DIR`, `LOG_FORMAT`, `LOG_DATE_FORMAT`

**Secrets location:**
- `.env` file in repository root (must not be committed in production)
- Loaded via `python-dotenv` in `common/settings.py`

**Credentials handling:**
- Database password: Passed via environment variable, URL-encoded in connection string
- Globalping API token: Optional Bearer token in HTTP Authorization header
- No other external credentials detected

## Webhooks & Callbacks

**Incoming:**
- None detected - No webhook receivers implemented

**Outgoing:**
- HTTP POST to aggregator API: `POST /api/ingest` endpoint
  - URL: Configurable via `AGGREGATOR_API_URL`, defaults to `http://127.0.0.1:5000/api/ingest`
  - Payload Format: JSON with `device_id`, `sample_type`, `ts`, and metric-specific fields
  - Sample Types: `desktop_network` (bandwidth, latency, packet loss) and `cloud_latency` (regional latencies)
  - Implementation: `UploadQueue._send_payload()` in `agent/uploader_queue/queue.py`
  - Timeout: Configurable via `AGGREGATOR_TIMEOUT_SECONDS`, defaults to 10 seconds
  - Retry Strategy: File-backed queue persists failed payloads for next flush attempt

**Server Endpoints:**
- POST `/api/ingest` - Metric ingestion endpoint
  - Handler: `api.ingest()` in `web_app/blueprints/api.py`
  - Accepts: JSON payloads from agents
  - Persists: Directly to PostgreSQL via `Database.insert_desktop_network_sample()` or `Database.insert_cloud_latency_sample()`
  - Returns: JSON `{"status": "ok", "sample_type": "..."}` on success, error object on failure

---

*Integration audit: 2026-02-23*
