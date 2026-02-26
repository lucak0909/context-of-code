# Roadmap: Context of Code — v1.0 VM Migration

## Overview

Five sequential phases migrate the Flask aggregator from PythonAnywhere to a dedicated Ubuntu VM. The dependency chain is strict: each phase builds directly on the one before it. Phase 1 provisions the environment and validates database connectivity. Phase 2 verifies Gunicorn can serve the app in a foreground process before any process manager is involved. Phase 3 adds the only code change in the migration — the `/health` endpoint — so the systemd phase has a lightweight liveness check to verify against. Phase 4 wraps the proven Gunicorn invocation in a systemd unit and confirms boot persistence. Phase 5 updates agents and confirms end-to-end data flow to Supabase, completing the migration.

## Phases

**Phase Numbering:**
- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- [x] **Phase 1: VM Provisioning and Environment Setup** - Provision the VM with Python, project code, and credentials; confirm Supabase connectivity
- [x] **Phase 2: Gunicorn Integration** - Install Gunicorn and manually verify it serves the app on `0.0.0.0:5000`
- [x] **Phase 3: Health Endpoint** - Add `GET /health` route and confirm it responds from an agent machine
- [x] **Phase 4: Systemd Service** - Install and enable the systemd unit; verify boot persistence and crash recovery
- [ ] **Phase 5: Agent Cutover and End-to-End Verification** - Update agent URLs and confirm metrics reach Supabase

## Phase Details

### Phase 1: VM Provisioning and Environment Setup
**Goal**: The VM has a working Python environment with all project dependencies and valid credentials, and can connect to Supabase
**Depends on**: Nothing (first phase)
**Requirements**: SETUP-01, SETUP-02, SETUP-03
**Plans**: 2 plans
**Success Criteria** (what must be TRUE):
  1. `python3.10 --version` on the VM returns 3.10 or higher and a virtualenv exists at the project path
  2. `pip list` inside the venv shows all packages from `requirements.txt` installed without errors
  3. The `.env` file exists on the VM with all required credentials and `python -c "from common.settings import get_settings; print(get_settings())"` exits without error
  4. A direct database connectivity check from the VM (e.g. `python -c "from common.database import ..."`  or a manual SQLAlchemy ping) succeeds and returns results from Supabase

Plans:
- [x] 01-01-PLAN.md — SSH into VM, install system packages, clone repo, create python3.10 venv, install all requirements.txt dependencies
- [x] 01-02-PLAN.md — Transfer .env to VM via SCP, validate settings with get_settings(), confirm Supabase connectivity with test_connection

### Phase 2: Gunicorn Integration
**Goal**: Gunicorn is installed in the project venv and serving the Flask app on `0.0.0.0:5000`, reachable from outside the VM
**Depends on**: Phase 1
**Requirements**: SETUP-04, SRV-01
**Plans**: 2 plans
**Success Criteria** (what must be TRUE):
  1. `gunicorn` is present in the venv (`venv/bin/gunicorn --version` returns without error)
  2. Running `gunicorn --bind 0.0.0.0:5000 web_app.app:app` from the project root starts without import errors and shows worker boot messages
  3. `curl http://<VM_IP>:5000/api/ingest` from an agent machine (not from the VM itself) receives a response (even a 400 or 405 is proof of reachability)

Plans:
- [x] 02-01-PLAN.md — Install Gunicorn into venv, add to requirements.txt, open UFW port 5000
- [x] 02-02-PLAN.md — Start Gunicorn in foreground and verify external reachability from an agent machine

### Phase 3: Health Endpoint
**Goal**: The Flask app exposes a `GET /health` endpoint that returns a liveness response, reachable from outside the VM
**Depends on**: Phase 2
**Requirements**: HEALTH-01
**Plans**: 1 plan
**Success Criteria** (what must be TRUE):
  1. `curl http://localhost:5000/health` via SSH tunnel returns HTTP 200
  2. The response body is `{"status": "ok", "ts": "<utc-iso>"}` with a valid ISO 8601 timestamp

Plans:
- [x] 03-01-PLAN.md — Implement the `/health` liveness probe endpoint on the Flask application and verify it is reachable externally

### Phase 4: Systemd Service
**Goal**: The aggregator runs as a managed systemd service that starts on boot and restarts automatically on crash
**Depends on**: Phase 3
**Requirements**: SRV-02, SRV-03
**Plans**: 2 plans
**Note**: UFW is NOT used — the college gateway controls external port access, not the VM firewall. A second port must be requested via the ISE port request form before external reachability can be verified. Until the port is assigned, external curl tests use SSH tunnel only.
**Success Criteria** (what must be TRUE):
  1. `systemctl status context-of-code` shows `Active: active (running)` after the unit is enabled and started ✓
  2. After a VM reboot, `systemctl status context-of-code` shows the service came up automatically without manual intervention ✓
  3. After killing the Gunicorn process (e.g. `kill -9 <pid>`), systemd restarts it within the configured restart delay ✓
  4. `curl http://localhost:5000/health` via SSH tunnel returns HTTP 200 while service is under systemd ✓

Plans:
- [x] 04-01-PLAN.md — Write and activate systemd unit file (UFW step skipped — not applicable to this network setup)
- [x] 04-02-PLAN.md — Human verification: reboot persistence, crash recovery, /health reachability via tunnel

### Phase 5: Agent Cutover and End-to-End Verification
**Goal**: All agent machines point to the VM and metrics are confirmed arriving in Supabase
**Depends on**: Phase 4 + college-assigned external port
**Requirements**: CUTOVER-01, CUTOVER-02
**Plans**: 2 plans
**Prerequisite**: A second port must be requested via the ISE port request form and assigned before this phase can begin. Gunicorn will be reconfigured to bind to that assigned port. (2 ports requested 2026-02-26 — awaiting email confirmation)
**Success Criteria** (what must be TRUE):
  1. `AGGREGATOR_API_URL` in each agent machine's `.env` points to `http://<VM_IP>:<ASSIGNED_PORT>/api/ingest` (not a PythonAnywhere URL)
  2. An agent run produces a successful HTTP POST to the VM (agent logs show 200 or 201 response, no queue retention)
  3. New rows appear in the Supabase `samples` table with timestamps matching the agent run

Plans:
- [ ] 05-01-PLAN.md — Rebind Gunicorn to the college-assigned external port and verify internal + direct external reachability
- [ ] 05-02-PLAN.md — Pre-cutover tunnel test, coordinate agent .env updates, and confirm end-to-end Supabase row

## Progress

**Execution Order:**
Phases execute in numeric order: 1 → 2 → 3 → 4 → 5

| Phase | Plans Complete | Status | Completed |
|-------|----------------|--------|-----------|
| 1. VM Provisioning and Environment Setup | 2/2 | Complete | 2026-02-24 |
| 2. Gunicorn Integration | 2/2 | Complete | 2026-02-24 |
| 3. Health Endpoint | 1/1 | Complete | 2026-02-25 |
| 4. Systemd Service | 2/2 | Complete | 2026-02-26 |
| 5. Agent Cutover and End-to-End Verification | 0/TBD | Pending port assignment | - |

---
*Roadmap created: 2026-02-24 — v1.0 VM Migration*
