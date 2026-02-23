# Architecture

**Analysis Date:** 2026-02-23

## Pattern Overview

**Overall:** Distributed agent-aggregator architecture with layered separation of concerns.

**Key Characteristics:**
- Agent-based data collection from edge devices
- Centralized aggregation API for metric persistence
- File-backed queue for offline resilience
- Multi-threaded collection (parallel metric gathering)
- ORM-based database abstraction

## Layers

**Agent Layer (Data Collection):**
- Purpose: Collects network and latency metrics from local devices
- Location: `agent/` directory
- Contains: PC data collectors, cloud latency collectors, uploader queue
- Depends on: Common utilities, uploader queue, settings
- Used by: Console auth, scheduled execution

**Aggregator API Layer (Data Ingestion):**
- Purpose: Receives and validates metric payloads from agents, routes to database
- Location: `web_app/blueprints/api.py`
- Contains: Flask blueprint with POST /api/ingest endpoint
- Depends on: Database operations, logging, request parsing
- Used by: Agents via UploadQueue, external metric sources

**Database Layer (Persistence):**
- Purpose: Manages all data persistence via SQLAlchemy ORM
- Location: `common/database/`
- Contains: ORM models, database operations, connection management
- Depends on: SQLAlchemy, PostgreSQL driver, settings
- Used by: Aggregator API, agent setup, authentication

**Common/Shared Layer (Cross-Cutting):**
- Purpose: Shared utilities consumed by all other layers
- Location: `common/` directory
- Contains: Settings, logging, auth, database abstractions
- Depends on: External libraries (sqlalchemy, dotenv, etc.)
- Used by: All other layers

## Data Flow

**Desktop Network Metrics Collection Flow:**

1. Agent starts via `console_auth.main()` after user login
2. Calls `run_with_user(user_id)` in `agent/pc_data_collector/main.py`
3. DataCollector in `agent/pc_data_collector/collector.py` gathers metrics in parallel:
   - Download speed (speedtest or HTTP fallback)
   - Upload speed (speedtest or HTTP fallback)
   - Packet loss and latency (ping3 or subprocess ping)
   - Local IP address via socket connection
4. Metrics wrapped in payload dict with device_id and timestamp
5. Payload enqueued to `agent_queue.jsonl` via `UploadQueue.enqueue()`
6. `UploadQueue.flush()` attempts HTTP POST to `/api/ingest`
7. Failed payloads retained in queue for retry
8. Aggregator API validates device_id UUID, parses timestamp
9. Routes by sample_type: "desktop_network" or "cloud_latency"
10. Database inserts via `insert_desktop_network_sample()` ORM operation
11. Sample persisted to `samples` table with all metric fields

**Cloud Latency Collection Flow (Parallel Thread):**

1. `run_cloud_latency_loop()` started as daemon thread in main agent loop
2. `GlobalpingLatencyCollector` creates measurement via Globalping API
3. Polls for results with exponential backoff (max 15s wait)
4. Extracts latencies for EU, US, Asia regions from probe results
5. Payload formatted with cloud_latency sample_type
6. Enqueued and flushed via same UploadQueue mechanism
7. Aggregator routes to `insert_cloud_latency_sample()`

**State Management:**

- Device state: Created per user on first agent start via `get_or_create_device()`
- Metrics cache: Held in-memory in DataCollector with 5-minute TTL
- Queue state: Persisted to disk as JSONL for offline resilience
- User state: Database-backed with password hashes (PBKDF2)

## Key Abstractions

**DataCollector:**
- Purpose: Encapsulates all network metric collection logic
- Examples: `agent/pc_data_collector/collector.py`
- Pattern: Parallel ThreadPoolExecutor for concurrent measurements, fallback strategies for unavailable metrics

**UploadQueue:**
- Purpose: Buffers and transmits metric payloads with offline support
- Examples: `agent/uploader_queue/queue.py`
- Pattern: File-backed JSONL queue with atomic rewrites, thread-safe locking

**GlobalpingLatencyCollector:**
- Purpose: Abstracts cloud latency measurement via Globalping API
- Examples: `agent/cloud_latency_collector/collector.py`
- Pattern: Region classification from probe metadata, resilient parsing of multiple response formats

**Database:**
- Purpose: ORM wrapper providing type-safe database operations
- Examples: `common/database/db_operations.py`
- Pattern: Session-per-operation with NullPool to avoid stateful connection pooling

**Sample Data Model:**
- Purpose: Unified schema for multiple metric types (desktop, cloud, mobile)
- Examples: `common/database/db_dataclasses.py` - Sample class
- Pattern: Single table with nullable columns for different sample_type variations

## Entry Points

**Agent (CLI Entry):**
- Location: `agent/__main__.py` → `agent/pc_data_collector/cli/console_auth.py`
- Triggers: `python -m agent`
- Responsibilities: User authentication (register/login), device creation, metric collection loop initiation

**Aggregator API Server:**
- Location: `web_app/app.py`
- Triggers: Flask development server or WSGI container
- Responsibilities: Receive metric payloads, validate, route to database persistence

**Standalone Test Collection:**
- Location: `agent/pc_data_collector/main.py` - `run()` function
- Triggers: Direct Python execution for testing
- Responsibilities: One-time metric collection with hardcoded device_id (for development)

## Error Handling

**Strategy:** Defensive with graceful degradation and offline resilience.

**Patterns:**
- Network failures in DataCollector: Fallback to simpler measurement methods (speedtest → HTTP fallback)
- Failed ping hosts: Continue with available hosts, return 0.0 if all fail
- Aggregator unreachable: Payload remains in queue for retry
- Invalid JSON payloads: Logged but skipped, queue continues processing
- Missing optional metrics: Default to 0.0 or None
- Database constraints: FK violations rejected with 400 error in aggregator, device_id validated before insert

## Cross-Cutting Concerns

**Logging:**
- Centralized via `setup_logger()` in `common/utils/logging_setup.py`
- ColorFormatter for console output (timestamped, level, logger name, message)
- File-based rotation via FlaggingFileHandler that renames logs by max log level encountered
- Async-safe with threading support

**Validation:**
- UUID validation in aggregator (device_id must be valid UUID)
- Timestamp parsing with timezone awareness and UTC defaults
- Float parsing with safe fallbacks to None
- Email validation in authentication (lowercased, required)
- Password validation via PBKDF2 timing-safe comparison

**Authentication:**
- PBKDF2-SHA256 with 200k iterations
- Unique passwords per user via Password table
- Session-less: User ID provided at agent startup
- No token/session persistence (device-to-server via bearer token optional via env)

---

*Architecture analysis: 2026-02-23*
