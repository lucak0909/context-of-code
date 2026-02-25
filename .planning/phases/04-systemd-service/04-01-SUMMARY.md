---
phase: 04-systemd-service
plan: 01
subsystem: infra
tags: [systemd, gunicorn, ufw, ubuntu, service-unit]

# Dependency graph
requires:
  - phase: 02-gunicorn-integration
    provides: "Confirmed Gunicorn invocation (venv path, workers, bind address, working directory)"
  - phase: 03-health-endpoint
    provides: "Flask /health route verified on port 5000"
provides:
  - "Systemd unit file at /etc/systemd/system/context-of-code.service"
  - "Gunicorn managed as a systemd service (auto-start on boot, restart on crash)"
  - "UFW enabled with port 5000 and 2214 rules (SSH lockout requires manual fix — see Next Phase Readiness)"
affects: [05-agent-update]

# Tech tracking
tech-stack:
  added: [systemd service unit, ufw]
  patterns:
    - "Absolute venv path in ExecStart — systemd does not search PATH"
    - "EnvironmentFile directive for .env — systemd compatible with bare key=value format"
    - "Restart=on-failure — restarts on crash, respects intentional systemctl stop"

key-files:
  created:
    - "/etc/systemd/system/context-of-code.service (on VM)"
  modified: []

key-decisions:
  - "workers=5: nproc returned 2 vCPUs so formula (2*2)+1=5 workers used"
  - "UFW enable caused SSH lockout: port 2214 is external gateway port, SSH internally uses port 22 — UFW allow 22/tcp is required, not 2214/tcp"
  - "Leftover Gunicorn process from Phase 2/3 was blocking port 5000; killed manually before systemd service could bind"

patterns-established:
  - "Pattern 1: systemd unit files go in /etc/systemd/system/ for local admin services"
  - "Pattern 2: Always run sudo ufw allow <ssh_internal_port>/tcp BEFORE sudo ufw enable"

requirements-completed: [SRV-02]  # SRV-03 partially blocked — UFW enabled but SSH lockout needs manual fix

# Metrics
duration: 15min
completed: 2026-02-25
---

# Phase 4 Plan 01: Systemd Service Unit File Summary

**Systemd unit file deployed and running (--workers 5, Restart=on-failure); UFW activated with port 5000 open but SSH lockout requires manual fix via console before plan is fully verified**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-25T10:33:34Z
- **Completed:** 2026-02-25T10:45:00Z (partial — blocked at SSH lockout)
- **Tasks:** 1.5 of 2 (Task 1 complete, Task 2 complete but SSH lockout prevents verification)
- **Files modified:** 0 in repo (all changes on VM filesystem)

## Accomplishments
- Systemd unit file written to `/etc/systemd/system/context-of-code.service` with correct absolute ExecStart path, WorkingDirectory, EnvironmentFile, and Restart=on-failure
- Service enabled and started via `systemctl enable --now context-of-code`
- Service confirmed `Active: active (running)` with 5 workers (nproc=2 → formula (2*2)+1=5)
- UFW rules added: port 2214/tcp and 5000/tcp both ALLOW
- UFW enabled with `sudo ufw enable` — SRV-03 UFW rule is in place
- Gunicorn responding on port 5000 externally (verified via curl)

## Task Commits

No repo-level code commits for this plan — all changes were to VM filesystem (`/etc/systemd/system/`) and VM firewall state.

**Plan metadata:** See final docs commit.

## Files Created/Modified
- `/etc/systemd/system/context-of-code.service` (on VM) — Systemd unit managing Gunicorn aggregator with 5 workers, EnvironmentFile, Restart=on-failure

## Decisions Made
- **Worker count = 5:** `nproc` returned 2 vCPUs; formula `(2 * 2) + 1 = 5` workers used in ExecStart
- **Killed leftover Gunicorn:** A manually-started Gunicorn process from Phase 2/3 was occupying port 5000. Killed it (PIDs 21649, 21660, 21662) so the systemd-managed service could bind. Systemd auto-restarted after RestartSec=5 and successfully bound to port 5000.
- **UFW port 22 oversight:** The UFW allow rule was added for port 2214/tcp (the external gateway port), but the VM's SSH daemon listens internally on port 22. The college gateway translates external port 2214 to internal port 22. UFW should have allowed port 22, not 2214. This caused SSH lockout when UFW was enabled.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Killed leftover Gunicorn process blocking port 5000**
- **Found during:** Task 1 (service activation)
- **Issue:** A manually-started Gunicorn process (PID 21649, workers 21660/21662) from Phase 2/3 foreground testing was bound to port 5000. The systemd service failed to bind: `Address already in use`
- **Fix:** Killed the orphaned Gunicorn master process (`sudo kill 21649 21660 21662`). The systemd service detected port freed and bound successfully on its next restart attempt (RestartSec=5 delay)
- **Files modified:** None — process management only
- **Verification:** `systemctl status context-of-code` showed `Active: active (running)` with 5 workers after kill
- **Committed in:** VM-only change; no repo commit

---

**Total deviations:** 1 auto-fixed (blocking process on port 5000)
**Impact on plan:** Necessary — without killing the orphaned process the service could not start.

## Issues Encountered

### SSH Lockout After UFW Enable

**Root cause:** The college gateway uses port-based NAT forwarding. External SSH port 2214 → VM internal port 22. The VM's SSH daemon binds to port 22 internally, not 2214.

The plan instructed `sudo ufw allow 2214/tcp` to preserve SSH, but the correct command is `sudo ufw allow 22/tcp`. When UFW was enabled with only port 2214 (external gateway port, not known to UFW on the VM) and port 5000 allowed, SSH (internal port 22) was blocked.

**Current state:**
- UFW is active on the VM
- Port 5000 is accessible externally (Gunicorn responding HTTP 200/404)
- Port 2214 is inaccessible — SSH blocked by UFW blocking internal port 22
- Systemd service is running (visible via curl response from Gunicorn)

**Recovery required (human action):**
1. Access VM via college console (out-of-band access, not SSH)
2. Run: `sudo ufw allow 22/tcp`
3. Run: `sudo ufw status` to verify port 22 and 5000 are both listed as ALLOW
4. Reconnect via SSH on port 2214 to verify

**Alternative recovery:**
1. Access VM via college console
2. Run: `sudo ufw disable` (removes UFW entirely — simpler but loses SRV-03 compliance)
3. Then: `sudo ufw allow 22/tcp && sudo ufw allow 5000/tcp && sudo ufw enable`

## User Setup Required

**Manual console action required to resolve SSH lockout.**

1. Log in to the college VM management console for VM `Student-vm-13`
2. Open the VM console/terminal (not SSH — SSH is currently blocked)
3. Run: `sudo ufw allow 22/tcp`
4. Run: `sudo ufw status` — verify output shows:
   ```
   Status: active
   22/tcp    ALLOW   Anywhere
   5000/tcp  ALLOW   Anywhere
   ```
5. Re-establish SSH from your machine: `ssh student` (using the configured alias)
6. Verify service: `sudo systemctl status context-of-code --no-pager`
7. Verify health: `curl http://localhost:5000/health`

After SSH access is restored, continuation agent can complete final verification.

## Next Phase Readiness

**Task 1 (SRV-02): COMPLETE**
- `/etc/systemd/system/context-of-code.service` deployed and active
- `systemctl is-enabled context-of-code` = `enabled`
- `systemctl is-active context-of-code` = `active`
- 5 workers running (nproc=2)

**Task 2 (SRV-03): BLOCKED — SSH lockout pending manual console fix**
- UFW is enabled with port 5000/tcp ALLOW and port 2214/tcp ALLOW
- Port 22/tcp (internal SSH) was not allowed before enabling UFW
- SSH access is currently unavailable
- Fix: `sudo ufw allow 22/tcp` via console, then re-verify

**Blocker for continuation:**
- Human must access VM via college console and run `sudo ufw allow 22/tcp`
- Then continuation agent can SSH in, verify UFW status, run health check, and complete the plan

---
*Phase: 04-systemd-service*
*Completed: 2026-02-25 (partial — blocked)*
