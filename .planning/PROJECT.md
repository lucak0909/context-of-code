# Context of Code

## What This Is

A distributed network monitoring system for tracking student/user network quality over time. Agents run on user devices (laptops, PCs) and collect local network metrics (download/upload speed, latency, packet loss, and cloud latency via Globalping). Metrics are posted to a central Flask aggregator API which persists them to a Supabase PostgreSQL database.

## Core Value

Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.

## Current Milestone: v1.0 VM Migration

**Goal:** Migrate the Flask aggregator from PythonAnywhere to a dedicated VM running Gunicorn + systemd for production reliability.

**Target features:**
- VM provisioned with Python environment and project dependencies
- Gunicorn serving the Flask app as a production WSGI server
- Systemd service managing the aggregator process (auto-start, auto-restart)
- Health check endpoint for verifying server liveness
- Environment configuration (.env) established on the VM
- Agents updated to point to the VM's aggregator URL

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

- ✓ Agent-based network metric collection (download, upload, latency, packet loss) — pre-migration
- ✓ Cloud latency measurement via Globalping (EU, US, Asia regions) — pre-migration
- ✓ File-backed upload queue with offline resilience — pre-migration
- ✓ Flask aggregator API with POST /api/ingest endpoint — pre-migration
- ✓ SQLAlchemy ORM with Supabase PostgreSQL backend — pre-migration
- ✓ PBKDF2 user authentication and device registration — pre-migration

### Active

<!-- Current scope. Building toward these. -->

- [ ] VM environment provisioned with Python 3.10+ and project dependencies
- [ ] Gunicorn configured as WSGI server for the Flask aggregator
- [ ] Systemd service unit file managing the aggregator process
- [ ] GET /health endpoint returning server liveness status
- [ ] .env file configured on VM with all required environment variables
- [ ] AGGREGATOR_API_URL updated on agent machines to point to VM

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Nginx reverse proxy — overkill for internal-only API with no static files or domain requirement
- SSL/HTTPS — no domain provisioned; can be added when domain is acquired
- Database migration — Supabase remains unchanged, no data movement needed
- CI/CD pipeline — manual deployment sufficient for college project scale
- Monitoring/alerting — health check endpoint covers observability needs for now

## Context

- Previously hosted on PythonAnywhere (Python web hosting platform)
- Supabase PostgreSQL database stays in the cloud — no database migration needed
- Only the Flask aggregator moves to the VM; agents stay on end-user devices
- Flask dev server was used on PythonAnywhere — Gunicorn replaces it for production
- VM OS: Ubuntu (22.04 or 24.04)
- College project — design decisions need to be explainable and justified

## Constraints

- **Runtime**: Python 3.10+ — matches existing codebase and dependencies
- **Database**: Supabase PostgreSQL remains unchanged — connection string stays the same
- **Agent compatibility**: Agents must continue working unchanged except for AGGREGATOR_API_URL update
- **Scope**: College project — favour simplicity with strong justification over complexity

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Gunicorn over Flask dev server | Flask explicitly recommends against dev server in production; Gunicorn is multi-worker and stable | — Pending |
| No Nginx | Aggregator is internal API only; no static files, no domain, no SSL needed yet; Nginx solves problems we don't have | — Pending |
| Systemd over manual process management | Auto-restart on crash and start on boot without manual intervention | — Pending |
| Supabase stays in cloud | No data migration risk; database is already production-grade | — Pending |

---
*Last updated: 2026-02-24 — v1.0 milestone started (VM migration from PythonAnywhere)*
