# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.
**Current focus:** Phase 2 — Gunicorn Integration

## Current Position

Phase: 2 of 5 (Gunicorn Integration) — COMPLETE
Plan: 2 of 2 — COMPLETE (next: Phase 3 — ORM Model + Aggregator)
Status: Phase 2 complete
Last activity: 2026-02-24 — Completed 02-02 (Gunicorn foreground start + external reachability confirmed)

Progress: [████░░░░░░] 40% (Phase 1 complete, Phase 2 complete, Phase 3 next)

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

**Recent Trend:**
- Last 5 plans: 01-01, 01-02, 02-01, 02-02
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
- UFW inactive on VM: no ufw allow rule added; enabling UFW would block SSH on port 2214
- Confirmed Gunicorn invocation for Phase 4 systemd: gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app from /home/student/context-of-code with venv active
- HTTP 404 from /api/ingest counts as external reachability success — route absent on OrmModel+Aggregator branch, not a Gunicorn issue

### Pending Todos

None.

### Blockers/Concerns

- VM CPU count: Worker formula `(2 * CPU_cores) + 1` depends on actual vCPU count — confirm before writing systemd unit; start at 2-3 workers (use `nproc` on VM when writing Phase 4 systemd unit)

### Resolved Blockers

- Gunicorn version: RESOLVED — installed 25.1.0 (2026-02-24); compatible with Python 3.10+
- UFW status: RESOLVED — UFW is inactive on this VM; port 5000 accessible without rules

## Session Continuity

Last session: 2026-02-24
Stopped at: Completed 02-02-PLAN.md — Gunicorn foreground start verified, external reachability confirmed from MacBook (HTTP 404), Phase 2 complete
Resume file: None
