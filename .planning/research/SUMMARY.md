# Project Research Summary

**Project:** Context of Code — v1.0 VM Migration
**Domain:** Flask aggregator API production deployment (PythonAnywhere → Ubuntu VM)
**Researched:** 2026-02-24
**Confidence:** HIGH

## Executive Summary

This project is a straightforward migration of an already-working Flask aggregator API from a managed hosting platform (PythonAnywhere) to a self-managed Ubuntu VM. The application code is complete and correct — no business logic changes are required. The entire scope of work is infrastructure: swapping the development server for Gunicorn, wrapping the process in a systemd service unit, configuring credentials via a `.env` file, adding a `/health` liveness endpoint, and updating each monitoring agent to point at the new host. Every technology involved (Gunicorn, systemd, python-dotenv) is mature, well-documented, and follows established patterns with no architectural ambiguity.

The recommended approach is sequential provisioning with manual verification at each step before proceeding: provision the VM and validate Supabase connectivity, install and manually smoke-test Gunicorn, add the `/health` endpoint, install the systemd unit, then update agents. This order matches the hard dependency chain identified in both FEATURES.md and ARCHITECTURE.md and ensures each layer is confirmed working before building on top of it. The explicit no-Nginx, no-Docker, no-CI/CD scope keeps complexity appropriate for a college-scale internal tool.

The key risk is silent failure: the upload queue on agents retries indefinitely, so a misconfigured firewall port, wrong bind address, or stale `AGGREGATOR_API_URL` will manifest as zero data in Supabase with no obvious error — not as a crash. The mitigation is a disciplined verification step after each phase using `curl` from an agent machine, not just from localhost on the VM.

## Key Findings

### Recommended Stack

The existing stack (Flask 3.1.2, SQLAlchemy 2.0.46, psycopg2-binary, python-dotenv, Python 3.10) is entirely unchanged. The only new package is Gunicorn, installed separately into the VM's virtualenv and not added to `requirements.txt` (which is shared with developer machines). The VM-level additions are: system packages (`python3.10-venv`, `libpq-dev`, `build-essential`, `git`), a virtualenv at `/opt/context-of-code/venv/`, a systemd unit at `/etc/systemd/system/context-of-code.service`, and a `.env` file at `/opt/context-of-code/.env`.

**Core technologies:**
- **Gunicorn (>=21.2.0):** WSGI server replacing Flask's dev server — Flask's official docs explicitly state the dev server must not be used in production; Gunicorn is the standard sync WSGI server for Flask on Linux
- **systemd:** Process lifecycle management (start on boot, restart on crash) — built into Ubuntu, supersedes supervisor; `Type=simple` with `Restart=on-failure` is the correct pattern for a foreground Gunicorn process
- **python-dotenv (existing):** Credential injection — already in use; `EnvironmentFile=` in the systemd unit is the preferred complement, injecting vars before process start so `load_dotenv()` finds them already set
- **NullPool (existing):** Per-request database connections — already in use; correctly safe for multi-worker Gunicorn with no shared connection state across workers

### Expected Features

**Must have (table stakes) — deployment is not production-ready without these:**
- **Gunicorn as WSGI server** — Flask dev server is single-threaded and explicitly unsupported for production
- **systemd service unit** — without a process manager the server dies on reboot or crash and requires manual restart
- **GET /health endpoint** — minimum liveness check; required for deploy verification and future monitoring
- **.env file on VM** — startup fails immediately with `ValueError` for missing DB vars without this
- **Agents updated to VM URL** — without `AGGREGATOR_API_URL` updated on every agent machine, no data reaches the VM

**Should have (reliability improvements):**
- Database connectivity check in `/health` (SELECT 1) — distinguishes "server alive" from "server + DB alive"; returns HTTP 503 with `{"status": "degraded"}` if DB unreachable
- `gunicorn.conf.py` config file — moves Gunicorn config out of the systemd unit and into version control for easier maintenance

**Defer (not blocking v1.0):**
- Nginx reverse proxy — no domain, no SSL, no static files; adds failure points with no benefit at this scale
- SSL/HTTPS — no domain provisioned; plain HTTP on LAN is appropriate for internal agents
- CI/CD pipeline — college project with one developer; manual `git pull && systemctl restart` is sufficient and auditable
- Dockerfile/containerisation — single service, single server; systemd is the direct and simpler equivalent

### Architecture Approach

The architecture is a direct Gunicorn-in-front-of-Flask pattern: agents POST to `http://<VM_IP>:5000/api/ingest`, Gunicorn distributes requests across 3 sync workers (formula: `(2 * CPU_cores) + 1` for a 1-vCPU VM), each worker imports `web_app.app:app`, Flask routes to `api_bp`, and `db_operations.py` writes to Supabase via SQLAlchemy NullPool (each request opens and closes its own connection). systemd manages process lifecycle. The existing `app = Flask(__name__)` module-level object in `web_app/app.py` is already WSGI-compatible — no app factory refactor is needed.

**Major components:**
1. **systemd unit** (`/etc/systemd/system/context-of-code.service`) — boot persistence, crash restart, credential injection via `EnvironmentFile=`
2. **Gunicorn** (3 sync workers, `0.0.0.0:5000`) — multi-worker WSGI server; replaces Flask dev server entirely
3. **Flask app** (`web_app.app:app`) — unchanged; `if __name__ == '__main__'` block is harmlessly bypassed when Gunicorn imports the module
4. **`/api/health` endpoint** — new code addition in `web_app/blueprints/api.py`; returns `{"status": "ok", "ts": "<utc-iso>"}` with HTTP 200
5. **.env on VM** — co-located with project root; permissions `600` owned by service user; `EnvironmentFile=` in unit file preferred over relying solely on `load_dotenv()`
6. **Agent `.env` update** — `AGGREGATOR_API_URL=http://<VM_IP>:5000/api/ingest` on each agent machine; no agent code changes required

### Critical Pitfalls

1. **Wrong Gunicorn module path** — use `web_app.app:app` (not `app:app`, not a file path); always run from project root; set `WorkingDirectory=` to project root in the systemd unit; confirm with a manual test before writing the unit
2. **Systemd uses system Python instead of venv** — `ExecStart=` must use the full absolute path `/opt/context-of-code/venv/bin/gunicorn`; never rely on `$PATH` resolution in systemd units
3. **.env missing on VM or wrong location** — `load_dotenv()` silently succeeds even when no `.env` exists; validate vars before first start with `python -c "from common.settings import get_settings; print(get_settings())"`; restart service after any `.env` change (lru_cache caches the settings object)
4. **Firewall blocks inbound port** — UFW default policy on Ubuntu is deny incoming; `sudo ufw allow 5000/tcp` is required; verify from an agent machine with `curl`, not from the VM itself (localhost always bypasses the firewall)
5. **Gunicorn binds to localhost** — Gunicorn defaults to `127.0.0.1:8000`; must explicitly specify `--bind 0.0.0.0:5000` or agents on other machines cannot reach the aggregator — symptoms are identical to a firewall block

## Implications for Roadmap

Based on the hard dependency chain confirmed by all four research files, a 5-phase structure is the correct approach. Each phase has a single responsibility and a clear pass/fail gate before the next phase begins.

### Phase 1: VM Provisioning and Environment Setup
**Rationale:** Every subsequent phase depends on the VM having the correct system packages, virtualenv, project code, and database credentials. This phase has no code changes — it validates the existing app can connect to Supabase from the new host before any new infrastructure is layered on top.
**Delivers:** A VM with Python 3.10, a populated venv with all existing dependencies, a valid `.env` with Supabase credentials, and a confirmed database connection from the VM.
**Addresses:** Table stakes features: `.env` file on VM; `AGGREGATOR_API_URL` preconditions
**Avoids:** Pitfall 3 (missing .env), Pitfall: psycopg2-binary install failure (install libpq-dev, build-essential first), Pitfall: wrong Python binary in venv (use `python3.10 -m venv` explicitly)

### Phase 2: Gunicorn Manual Integration
**Rationale:** Gunicorn must be verified working before wrapping it in systemd. A manual test from the project root confirms the WSGI entrypoint is correct, the bind address reaches agents, and the Flask app loads without errors. This is the cheapest way to catch module path errors and missing packages before they become systemd debugging problems.
**Delivers:** Gunicorn running in the foreground, reachable on `0.0.0.0:5000`, responding to requests.
**Uses:** `gunicorn>=21.2.0`, `web_app.app:app` entrypoint, `--bind 0.0.0.0:5000`, 3 sync workers
**Avoids:** Pitfall 1 (wrong module path), Pitfall: Gunicorn not installed in venv, Pitfall: localhost-only bind

### Phase 3: Health Endpoint
**Rationale:** The only code change in the entire migration. Must be deployed before the systemd phase so the unit's first-start verification can use a lightweight HTTP check rather than sending a full ingest payload. Keeping this as a discrete phase makes the code change visible and reviewable.
**Delivers:** `GET /api/health` returning `{"status": "ok", "ts": "<utc-iso>"}` with HTTP 200; confirmed working via manual `curl` from an agent machine.
**Implements:** New route in `web_app/blueprints/api.py`; no new blueprint or file required
**Avoids:** Deploying the systemd unit without a liveness check endpoint

### Phase 4: systemd Service Unit
**Rationale:** Only install the systemd unit after Gunicorn is proven working (Phase 2) and the health endpoint is deployed (Phase 3). This phase adds boot persistence and crash recovery. All five critical pitfall areas for systemd configuration apply here and must be verified with `systemctl status` and `journalctl` output.
**Delivers:** `context-of-code.service` enabled and running; service survives a reboot test; `systemctl status` shows `Active: active (running)`.
**Uses:** `EnvironmentFile=` for credential injection, `WorkingDirectory=` set to project root, `Restart=on-failure`, absolute venv path in `ExecStart`
**Avoids:** Pitfall 2 (system Python instead of venv), Pitfall: service not enabled for boot, Pitfall: relative log paths breaking in systemd context, Pitfall: wrong service user permissions

### Phase 5: Agent Reconfiguration and End-to-End Verification
**Rationale:** Only update agents after the VM service is stable and confirmed reachable from outside the VM (firewall open, correct bind address). This phase has no code changes — only `.env` updates on each agent machine. Completing this phase constitutes migration complete.
**Delivers:** All agents posting to `http://<VM_IP>:5000/api/ingest`; data confirmed arriving in Supabase; PythonAnywhere deployment retired.
**Addresses:** Table stakes feature: Agents updated to VM URL
**Avoids:** Pitfall: stale `AGGREGATOR_API_URL` defaulting to localhost silently queuing payloads forever

### Phase Ordering Rationale

- The dependency chain is strict: `.env` → Gunicorn binary → manual test → health endpoint → systemd unit → agents. No phase can be validated without all prior phases complete.
- Separating Gunicorn manual testing (Phase 2) from systemd (Phase 4) surfaces configuration errors in the simplest possible context — a foreground terminal process — before adding systemd's layer of indirection.
- The health endpoint (Phase 3) sits between Gunicorn and systemd because it provides the primary verification tool for Phase 4 and all subsequent checks.
- Agent reconfiguration (Phase 5) is intentionally last: pointing agents at a VM that is not yet stable would cause the upload queue to accumulate with no benefit, and silent queue growth is the hardest failure mode to diagnose in this system.

### Research Flags

Phases with standard, well-documented patterns (skip research-phase):
- **Phase 1 (VM Provisioning):** Standard Ubuntu Python setup; `apt` packages and virtualenv creation are unambiguous
- **Phase 2 (Gunicorn):** Flask + Gunicorn is a canonical deployment pair; documentation is authoritative and stable
- **Phase 3 (Health Endpoint):** Trivial Flask route addition; no research needed
- **Phase 4 (systemd):** systemd service units for Python/Gunicorn are well-documented with no gotchas beyond those already captured in PITFALLS.md
- **Phase 5 (Agent reconfiguration):** `.env` variable update with no code changes; no research needed

No phases require deeper research during planning. All technology choices are mature and patterns are well-established. The main risk areas are operational (checklist discipline) rather than technical uncertainty.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Gunicorn version needs pre-install verification (`pip index versions gunicorn`); all other stack elements directly confirmed from codebase inspection and official Flask/Gunicorn docs |
| Features | HIGH | Feature list derived from direct codebase analysis (`common/settings.py`, `web_app/app.py`, `web_app/blueprints/api.py`) and well-established deployment conventions |
| Architecture | HIGH | Architecture is a direct consequence of the existing code structure; `web_app.app:app` entrypoint and NullPool compatibility confirmed by codebase reading; no inference required |
| Pitfalls | HIGH | Pitfalls grounded in codebase inspection; UFW default policy, systemd `ExecStart` path resolution, and `load_dotenv()` silent-fail behaviour are all well-documented facts |

**Overall confidence:** HIGH

### Gaps to Address

- **Gunicorn version pin:** Verify the current stable version with `pip index versions gunicorn` before pinning in the install script. Research used training data (21.x) — this should be confirmed at install time.
- **VM specs (CPU count):** The worker count formula `(2 * CPU_cores) + 1` depends on the actual VM's vCPU count. Confirm this before writing the systemd unit; start at 2–3 workers and adjust.
- **Supabase connection limit:** PITFALLS.md flags that the Supabase free tier has ~60 connections. If worker count is increased above 3, verify the connection budget. Keep workers at 2–3 for this project scale.
- **UFW status on target VM:** Research assumes UFW is active (Ubuntu default). Verify with `sudo ufw status` early in Phase 1; if UFW is inactive, the firewall pitfall does not apply but should still be noted.

## Sources

### Primary (HIGH confidence)
- Flask documentation — "Do not use the development server in production"; Gunicorn deployment guide — https://flask.palletsprojects.com/en/stable/deploying/
- Gunicorn documentation — worker formula, bind address, `Type=simple` process model — https://docs.gunicorn.org/en/stable/
- SQLAlchemy NullPool documentation — per-request connection lifecycle — https://docs.sqlalchemy.org/en/20/core/pooling.html
- systemd.service(5) man page — `EnvironmentFile`, `WorkingDirectory`, `Type=simple`, `Restart=on-failure`, `WantedBy=multi-user.target`
- Codebase direct inspection — `web_app/app.py`, `web_app/blueprints/api.py`, `common/settings.py`, `common/database/db_operations.py`, `agent/uploader_queue/queue.py`
- `.planning/PROJECT.md` — scope decisions (no Nginx, no Docker, Gunicorn + systemd confirmed)
- `.planning/codebase/CONCERNS.md` — pre-existing codebase concerns including `AGGREGATOR_API_URL` localhost default

### Secondary (MEDIUM confidence)
- Training knowledge (Aug 2025 cutoff) — Gunicorn 21.x as current stable series; verify before install
- Ubuntu UFW default deny-incoming policy — standard behaviour, no live verification available

---
*Research completed: 2026-02-24*
*Ready for roadmap: yes*
