---
phase: 02-gunicorn-integration
plan: "02"
subsystem: infra
tags: [gunicorn, wsgi, flask, ufw, port-5000]

# Dependency graph
requires:
  - phase: 02-gunicorn-integration/02-01
    provides: Gunicorn installed in venv, UFW confirmed inactive, port 5000 accessible
provides:
  - Confirmed Gunicorn invocation command for production use
  - External reachability of Flask app on port 5000 proven from off-VM machine
  - Exact systemd unit command validated (gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app)
affects:
  - 04-systemd-unit (will wrap this exact Gunicorn command in a unit file)

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Gunicorn foreground launch from repo root with venv active: gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app"
    - "WSGI entry point: web_app.app:app (module path resolved from /home/student/context-of-code)"

key-files:
  created: []
  modified: []

key-decisions:
  - "Gunicorn invocation confirmed: gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app from /home/student/context-of-code with venv active"
  - "2 workers used for foreground verification; Phase 4 systemd unit will use nproc-based formula (2*CPU+1)"
  - "HTTP 404 from /api/ingest counts as external reachability success — route absent on this branch, not a Gunicorn issue"

patterns-established:
  - "Gunicorn cwd must be repo root (/home/student/context-of-code) to resolve web_app module"
  - "External reachability test: any HTTP response (200/400/404/405) from curl on non-VM machine proves Gunicorn is serving"

requirements-completed:
  - SRV-01

# Metrics
duration: ~15min
completed: 2026-02-24
---

# Phase 2 Plan 02: Gunicorn Foreground Start + External Reachability Summary

**Gunicorn serving Flask app on 0.0.0.0:5000 with 2 workers, confirmed reachable from MacBook via HTTP 404 — exact invocation locked in for Phase 4 systemd unit**

## Performance

- **Duration:** ~15 min
- **Started:** 2026-02-24
- **Completed:** 2026-02-24
- **Tasks:** 2 (both human-executed on VM)
- **Files modified:** 0

## Accomplishments

- Gunicorn started on VM at 0.0.0.0:5000 with 2 workers and zero import errors
- Two worker boot messages confirmed in Gunicorn log (PID 18616)
- External curl from MacBook to http://200.69.13.70:5000/api/ingest returned HTTP 404 (Flask response), proving end-to-end WSGI connectivity
- Phase 2 success criteria fully met: Gunicorn serves the app, bind address is 0.0.0.0, external clients can reach it

## Task Commits

These tasks were human-executed on the VM (foreground process and external curl). No code commits were generated.

1. **Task 1: Start Gunicorn in the foreground** - human-executed on VM (no commit)
2. **Task 2: Verify external reachability** - human-verified (checkpoint approved)

**Plan metadata:** (docs commit created after this summary)

## Files Created/Modified

None — this plan is purely operational verification. No source files were changed.

## Decisions Made

- The confirmed Gunicorn invocation is: `gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app` run from `/home/student/context-of-code` with the venv active. Phase 4 will use this exact command in the systemd `ExecStart` line.
- Worker count set to 2 for foreground verification. The Phase 4 systemd unit should run `nproc` on the VM and apply the `(2 * CPU_cores) + 1` formula before committing to a final count.
- HTTP 404 from `/api/ingest` was correctly interpreted as reachability success. The route does not exist on the current branch (`OrmModel+Aggregator`), which is unrelated to Gunicorn's ability to serve requests.

## Deviations from Plan

None — plan executed exactly as written.

## Issues Encountered

None. Gunicorn started without import errors. UFW was already confirmed inactive in Plan 01, so no firewall intervention was needed. The 404 response from /api/ingest was anticipated (route absent on this branch) and counted as success per the checkpoint criteria.

## User Setup Required

None — no external service configuration required.

## Next Phase Readiness

- Phase 2 is fully complete. Both plans (02-01 Gunicorn install, 02-02 foreground verification) are done.
- Phase 3 (ORM model + aggregator) can proceed independently — it is code work on the application layer.
- Phase 4 (systemd unit) is unblocked. The exact `ExecStart` command is confirmed. Remaining action before writing the unit: run `nproc` on the VM to determine the correct worker count.
- Outstanding concern: confirm VM vCPU count via `nproc` before writing the Phase 4 systemd unit — worker formula `(2 * CPU_cores) + 1` depends on it.

---
*Phase: 02-gunicorn-integration*
*Completed: 2026-02-24*
