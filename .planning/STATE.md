# Project State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.
**Current focus:** Phase 1 — VM Provisioning and Environment Setup

## Current Position

Phase: 1 of 5 (VM Provisioning and Environment Setup)
Plan: Not yet planned
Status: Ready to plan
Last activity: 2026-02-24 — Roadmap created for v1.0 VM Migration

Progress: [░░░░░░░░░░] 0%

## Performance Metrics

**Velocity:**
- Total plans completed: 0
- Average duration: —
- Total execution time: —

**By Phase:**

| Phase | Plans | Total | Avg/Plan |
|-------|-------|-------|----------|
| - | - | - | - |

**Recent Trend:**
- Last 5 plans: —
- Trend: —

*Updated after each plan completion*

## Accumulated Context

### Decisions

Decisions are logged in PROJECT.md Key Decisions table.
Recent decisions affecting current work:

- Gunicorn over Flask dev server: Flask explicitly recommends against dev server in production; Gunicorn is multi-worker and stable
- No Nginx: Aggregator is internal API only; no static files, no domain, no SSL needed yet
- Systemd over manual process management: Auto-restart on crash and start on boot without manual intervention
- Supabase stays in cloud: No data migration risk; database is already production-grade

### Pending Todos

None yet.

### Blockers/Concerns

- Gunicorn version: Verify current stable version with `pip index versions gunicorn` at install time (research used training data 21.x)
- VM CPU count: Worker formula `(2 * CPU_cores) + 1` depends on actual vCPU count — confirm before writing systemd unit; start at 2-3 workers
- UFW status: Research assumes UFW is active (Ubuntu default) — verify with `sudo ufw status` early in Phase 1

## Session Continuity

Last session: 2026-02-24
Stopped at: Roadmap created — ready to plan Phase 1
Resume file: None
