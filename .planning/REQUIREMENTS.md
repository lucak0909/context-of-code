# Requirements: Context of Code

**Defined:** 2026-02-24
**Core Value:** Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.

## v1 Requirements

Requirements for VM migration milestone. Each maps to a roadmap phase.

### VM Setup

- [ ] **SETUP-01**: VM has Python 3.10+ with venv and all project dependencies installed
- [ ] **SETUP-02**: Project repository is cloned onto the VM
- [ ] **SETUP-03**: `.env` file is configured on the VM with all required credentials and settings
- [ ] **SETUP-04**: Gunicorn is installed in the project venv and manually verified to serve the app

### Server

- [ ] **SRV-01**: Flask aggregator runs under Gunicorn (not Flask dev server) bound to `0.0.0.0`
- [ ] **SRV-02**: Systemd service unit starts the aggregator on boot and restarts it on crash
- [ ] **SRV-03**: Firewall (UFW) permits inbound traffic on the aggregator port

### Health

- [ ] **HEALTH-01**: `GET /health` endpoint returns `{"status": "ok", "ts": "<utc-iso>"}` at HTTP 200

### Cutover

- [ ] **CUTOVER-01**: `AGGREGATOR_API_URL` updated on all agent machines to point to the VM
- [ ] **CUTOVER-02**: End-to-end verified — agents successfully POST metrics that appear in Supabase

## Future Requirements

*Nothing deferred — migration is fully scoped for v1.*

## Out of Scope

| Feature | Reason |
|---------|--------|
| Nginx reverse proxy | No static files, no domain, internal-only API — adds complexity without benefit at this scale |
| SSL / HTTPS | No domain provisioned; add when domain is acquired |
| CI/CD pipeline | Manual deployment sufficient for college project scale |
| Database migration | Supabase remains unchanged, no data movement needed |
| Monitoring / alerting | Health check endpoint covers observability needs for now |
| Docker / containerisation | Adds complexity without benefit for a single-service VM deployment |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| SETUP-01 | Phase 1 | Pending |
| SETUP-02 | Phase 1 | Pending |
| SETUP-03 | Phase 1 | Pending |
| SETUP-04 | Phase 2 | Pending |
| SRV-01 | Phase 2 | Pending |
| HEALTH-01 | Phase 3 | Pending |
| SRV-02 | Phase 4 | Pending |
| SRV-03 | Phase 4 | Pending |
| CUTOVER-01 | Phase 5 | Pending |
| CUTOVER-02 | Phase 5 | Pending |

**Coverage:**
- v1 requirements: 10 total
- Mapped to phases: 10
- Unmapped: 0 ✓

---
*Requirements defined: 2026-02-24*
*Last updated: 2026-02-24 — traceability updated after roadmap creation*
