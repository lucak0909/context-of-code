# Feature Landscape

**Domain:** Production Flask API deployment on Ubuntu VM
**Researched:** 2026-02-24
**Milestone:** v1.0 VM Migration (PythonAnywhere → Ubuntu VM)

---

## Scope Note

This file covers **new deployment and infrastructure features only**. The following are already built and out of scope:

- POST /api/ingest endpoint
- SQLAlchemy ORM with Supabase PostgreSQL
- PBKDF2 user authentication
- File-backed upload queue on agents

---

## Table Stakes

Features an agent must have for the deployment to be considered production-ready. Missing any of these means the server is not reliable.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Gunicorn as WSGI server | Flask's dev server is single-threaded, not crash-safe, and Flask docs explicitly say do not use in production. Gunicorn is the standard multi-worker WSGI server for Flask on Linux. | Low | Needs `pip install gunicorn`. WSGI entrypoint is `web_app.app:app`. |
| Systemd service unit | Without a process manager, the server dies on reboot or crash and requires manual restart. Systemd is built into Ubuntu and is the standard solution for service management. | Low | Single `.service` file. Enables `auto-restart` and `start on boot` with `systemctl enable`. |
| GET /health endpoint | Provides a way to verify the server is live after deployment and after any restart. Used manually during deploy and can be used by monitoring later. | Low | Returns JSON `{"status": "ok", "ts": "<utc-iso>"}` with HTTP 200. See Health Endpoint section below. |
| .env file on VM | The existing codebase uses `python-dotenv` and `load_dotenv()`. Without a populated `.env`, startup fails immediately with `ValueError: Missing required env vars for DB connection`. | Low | Requires 5 DB vars + optional log vars. See Environment Variables section below. |
| Agents updated to VM URL | Agents currently point to the PythonAnywhere URL via `AGGREGATOR_API_URL`. Without this update, no new data reaches the VM. | Low | Update `AGGREGATOR_API_URL` in each agent machine's `.env`. No code changes needed — `settings.py` already reads this var. |

---

## Nice-to-Haves

Features that improve reliability or observability but are not blockers for the initial deployment.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| Database connectivity check in /health | Confirms end-to-end liveness (server + DB). Catches misconfigured connection strings after deployment. | Low | Add a lightweight `SELECT 1` via SQLAlchemy before returning 200. Return `{"status": "degraded", "db": "unreachable"}` with HTTP 503 if it fails. |
| Gunicorn access log to file | Makes it possible to inspect request traffic without relying on systemd journal, which rolls over. | Low | `--access-logfile /path/to/access.log` Gunicorn flag. |
| `gunicorn.conf.py` config file | Moves Gunicorn config out of the systemd unit file and into a versioned file in the repo. Easier to read and modify. | Low | Standard pattern. File lives in project root. Replaces CLI flags in the systemd `ExecStart` line. |

---

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Nginx reverse proxy | The aggregator is an internal API with no domain, no static files, and no SSL. Nginx solves problems this project does not have yet. Added it would increase setup complexity and introduce a new failure point. | Direct Gunicorn bind on port 5000. Add Nginx later only if a public domain or SSL is acquired. |
| SSL/HTTPS | No domain provisioned. Self-signed certs on an internal API create more friction than value for agents on the same network. | Plain HTTP on the LAN. Revisit when a domain is acquired. |
| CI/CD pipeline | College project scale with one developer. Manual `git pull && systemctl restart` is fast, auditable, and has no external dependencies. | Manual deploy. Document the 3-step deploy process instead. |
| Dockerfile / containerisation | Adds a second abstraction layer (container runtime) on top of systemd. No benefit for a single-service single-server deployment. | Bare Gunicorn + systemd directly on the VM. |

---

## Health Endpoint Specification

**Route:** `GET /health`
**Blueprint:** Recommend adding to `web_app/blueprints/api.py` or a new `health_bp`.

**Minimum viable response (table stakes):**

```json
{
  "status": "ok",
  "ts": "2026-02-24T12:00:00+00:00"
}
```

HTTP 200. The `ts` field is a UTC ISO-8601 timestamp of when the check ran. Allows the caller to confirm the server is not returning a stale cached response.

**Extended response (nice-to-have, adds DB check):**

```json
{
  "status": "ok",
  "ts": "2026-02-24T12:00:00+00:00",
  "db": "ok"
}
```

If the DB is unreachable, return HTTP 503:

```json
{
  "status": "degraded",
  "ts": "2026-02-24T12:00:00+00:00",
  "db": "unreachable"
}
```

**Do not include:**
- Version numbers (not maintained, goes stale)
- Uptime counters (requires state management, overkill)
- Memory/CPU stats (not relevant for a simple liveness check)

---

## Environment Variables

The existing `common/settings.py` defines all required vars. The VM `.env` must populate all of them.

**Required for DB connection (startup fails without these):**

| Var | Purpose | Example |
|-----|---------|---------|
| `user` | Supabase DB username | `postgres.abcdefgh` |
| `password` | Supabase DB password | `<secret>` |
| `host` | Supabase DB host | `db.abcdefgh.supabase.co` |
| `port` | Supabase DB port | `5432` |
| `dbname` | Supabase DB name | `postgres` |

**Optional (have safe defaults in settings.py):**

| Var | Purpose | Default |
|-----|---------|---------|
| `AGGREGATOR_API_URL` | Used by agent — not needed on the server itself | `http://127.0.0.1:5000/api/ingest` |
| `LOG_LEVEL` | Logging verbosity | `INFO` |
| `LOGS_DIR` | Directory for log files | `logs` |

**Secure .env management on the VM:**

1. Create `.env` in the project root (`/home/<user>/context-of-code/.env` or equivalent).
2. Restrict permissions immediately: `chmod 600 .env` — only the file owner can read or write.
3. Confirm `.env` is in `.gitignore` — it already should be, but verify before any `git pull`.
4. **Preferred alternative for production:** Use systemd's `EnvironmentFile=` directive in the service unit instead of relying on `python-dotenv` at runtime. This loads vars directly into the process environment before the app starts, which is more explicit and avoids the `load_dotenv()` call needing to find the file. Both approaches work; the `EnvironmentFile=` pattern is standard on Ubuntu servers.

**EnvironmentFile= pattern (preferred):**

In the systemd unit:
```
[Service]
EnvironmentFile=/home/<user>/context-of-code/.env
```

The file uses the same `KEY=VALUE` format as `.env`. `python-dotenv`'s `load_dotenv()` becomes a no-op when vars are already in the environment (it does not override existing env vars by default), so no code change is needed.

---

## Gunicorn Worker Configuration

**Context:** Single-service aggregator API. Requests are short-lived (JSON parse + DB insert). Workers are CPU-bound during request handling but mostly idle between requests from ~10 agents.

**Worker count:**

The standard formula is `(2 * CPU_cores) + 1`. For a typical college project VM with 1 vCPU, this gives **3 workers**. For 2 vCPUs, **5 workers**. Start with 3 unless VM specs dictate otherwise.

Rationale: Multiple workers mean one slow DB call does not block all other agents from ingesting. With NullPool (already in use — see ARCHITECTURE.md), each worker creates its own connection per request and closes it, so there is no connection pool contention between workers.

**Worker class:** `sync` (Gunicorn default). Do not use `gevent` or `eventlet` — the current Flask app is not async and psycopg2 is not gevent-patched. Sync workers are correct for this workload.

**Recommended flags / `gunicorn.conf.py`:**

```python
# gunicorn.conf.py — place in project root
bind = "0.0.0.0:5000"
workers = 3          # adjust to (2 * CPU_cores) + 1
worker_class = "sync"
timeout = 30         # seconds; DB inserts complete well within this
accesslog = "logs/gunicorn_access.log"
errorlog = "logs/gunicorn_error.log"
loglevel = "info"
```

**What NOT to configure:**
- `--reload` — this is the development equivalent of Flask's debug mode. Never use in the systemd service.
- `--daemon` — systemd manages the process lifecycle. Running Gunicorn as a daemon inside systemd causes systemd to lose track of the PID.
- `--preload` — not needed. The app is lightweight and workers can initialise independently.

---

## Feature Dependencies

```
VM provisioned (Python 3.10+, pip, project cloned)
    → .env file populated
        → Gunicorn installed (pip install gunicorn)
            → Gunicorn launchable manually (smoke test)
                → /health endpoint added
                    → Gunicorn verified via /health
                        → Systemd service unit installed
                            → Service enabled + started via systemctl
                                → Agents updated to VM URL
                                    → End-to-end ingest verified
```

---

## MVP Recommendation

Prioritise in this order:

1. **VM provisioned + .env populated** — prerequisite for everything else
2. **Gunicorn configured and manually launchable** — confirms WSGI layer works
3. **GET /health endpoint** — minimum viable liveness check; needed to verify the above
4. **Systemd service unit** — makes the deployment persistent across reboots and crashes
5. **Agents updated to VM URL** — completes the migration

Defer:
- Database check in `/health` — useful but not blocking; add after the base deployment is confirmed stable
- `gunicorn.conf.py` file — can start with CLI flags in the systemd unit and extract to a config file later

---

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Gunicorn as WSGI server | HIGH | Flask official docs explicitly state this. Standard Ubuntu deployment pattern. |
| Systemd service unit | HIGH | Ubuntu 22.04/24.04 standard. Well-documented pattern. |
| Health endpoint response format | HIGH | JSON `{"status": "ok"}` is the universal convention. `ts` field is standard practice. |
| .env permissions (`chmod 600`) | HIGH | Standard Linux file permission practice. |
| `EnvironmentFile=` in systemd | HIGH | Ubuntu/systemd standard, documented in `systemd.exec(5)`. |
| Gunicorn worker formula `(2*N)+1` | HIGH | Published in Gunicorn docs. Consistent across official and community sources. |
| NullPool + sync workers interaction | HIGH | Based on direct codebase analysis — NullPool is already used, per-request connections are safe with multiple sync workers. |

---

*Sources: Codebase analysis (common/settings.py, web_app/app.py, web_app/blueprints/api.py, common/database/), Flask documentation, Gunicorn documentation, systemd.exec(5) man page. No WebSearch available — confidence ratings reflect direct codebase inspection and well-established Linux deployment conventions.*
