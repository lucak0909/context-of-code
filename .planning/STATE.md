# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.
**Current focus:** Phase 4 — Systemd Service

## Current Position

Phase: 4 of 5 (Systemd Service) — IN PROGRESS
Plan: 1 of 2 — BLOCKED (SSH lockout — human console action required)
Status: Task 1 complete (service running). Task 2 blocked: UFW enabled but SSH locked out (port 22 not allowed before enable). Need: `sudo ufw allow 22/tcp` via VM console.
Last activity: 2026-02-25 — Executed 04-01 (systemd unit deployed, UFW SSH lockout encountered)

Progress: [██████░░░░] 60% (Phase 1 complete, Phase 2 complete, Phase 3 complete; Phase 4 in progress)

## Performance Metrics

**Velocity:**
- Total plans completed: 3
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| 01-vm-provisioning-and-environment-setup | 2/2 | — | — |
| 02-gunicorn-integration | 2/2 | — | — |
| 03-health-endpoint | 1/1 | ~30min | ~30min |

**Recent Trend:**
- Last 5 plans: 01-01, 01-02, 02-01, 02-02, 03-01
- Trend: On track

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Gunicorn over Flask dev server: Flask explicitly recommends against dev server in production; Gunicorn is multi-worker and stable
- No Nginx: Aggregator is internal API only; no static files, no domain, no SSL needed yet
- Systemd over manual process management: Auto-restart on crash and start on boot without manual intervention
- Supabase stays in cloud: No data migration risk; database is already production-grade
- gunicorn unpinned in requirements.txt: pip resolves latest compatible; version pinning not required for college project
- Confirmed Gunicorn invocation for Phase 4 systemd: gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app from /home/student/context-of-code with venv active
- HTTP 404 from /api/ingest counts as external reachability success — route absent on OrmModel+Aggregator branch, not a Gunicorn issue
- Health route on Flask app instance (not blueprint): ensures /health resolves at root, not /api/health
- UTC timestamp via datetime.now(timezone.utc).isoformat(): produces timezone-aware ISO 8601 string
- workers=5 in systemd unit: nproc=2 on VM, formula (2*2)+1=5 workers
- College gateway translates external port 2214 → internal VM port 22: UFW allow 22/tcp needed, NOT 2214/tcp

### Pending Todos

None.

### Blockers/Concerns

- SSH LOCKOUT: UFW enabled on VM with ports 2214/tcp and 5000/tcp allowed, but internal SSH port 22 was not allowed. Need `sudo ufw allow 22/tcp` via VM console (out-of-band access). Service is running and reachable on port 5000.

### Resolved Blockers

- Gunicorn version: RESOLVED — installed 25.1.0 (2026-02-24); compatible with Python 3.10+
- UFW status: RESOLVED — UFW is now active; port 5000 accessible externally
- VM CPU count: RESOLVED — nproc=2, workers=5 used in systemd unit

## Session Continuity

Last session: 2026-02-25
Stopped at: 04-01-PLAN.md — Task 1 complete (systemd service running). BLOCKED at Task 2: SSH lockout after sudo ufw enable. Fix: sudo ufw allow 22/tcp via VM console, then continuation agent resumes.
Resume file: .planning/phases/04-systemd-service/04-01-SUMMARY.md
