# Phase 2: Gunicorn Integration - Research

**Researched:** 2026-02-24
**Domain:** Gunicorn WSGI server, Flask app serving, Ubuntu network binding
**Confidence:** HIGH — core findings verified against official Flask docs, Gunicorn official docs, and PyPI

---

## Summary

Phase 2 installs Gunicorn into the project venv and runs it in the foreground to verify it can serve the Flask app externally. This is deliberately a manual, foreground-only step — no systemd, no process manager. The goal is to confirm the Gunicorn invocation works cleanly before wrapping it in anything automated (that comes in Phase 4).

The project's Flask app exports its `app` object from `web_app/app.py` at module path `web_app.app`. The correct Gunicorn invocation from the repo root is `gunicorn --bind 0.0.0.0:5000 web_app.app:app`. Gunicorn must be invoked from the repo root (`/home/student/context-of-code`) so Python's module resolution finds `web_app` as a package. Gunicorn is NOT currently in `requirements.txt` and must be installed explicitly with `pip install gunicorn` inside the activated venv.

The external reachability test requires port 5000 to be open in UFW. Since Phase 1 does not open any ports, this phase must add the UFW rule. The success criterion uses `curl` from an agent machine (not the VM itself) to confirm reachability — a 400 or 405 response from `/api/ingest` counts as proof.

**Primary recommendation:** `pip install gunicorn` in the venv, then run `gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app` from the project root. Add `sudo ufw allow 5000/tcp` before testing from an agent machine.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-04 | Gunicorn is installed in the project venv and manually verified to serve the app | `pip install gunicorn` installs into the active venv. Verified with `venv/bin/gunicorn --version`. Gunicorn 25.1.0 is current stable (as of 2026-02-13), requires Python >=3.10 — compatible with the venv created in Phase 1. |
| SRV-01 | Flask aggregator runs under Gunicorn (not Flask dev server) bound to `0.0.0.0` | `gunicorn --bind 0.0.0.0:5000 web_app.app:app` from the repo root achieves this. The `web_app.app` module path maps to `web_app/app.py`; the `:app` suffix references the Flask instance created at module level. UFW must allow port 5000 for external reachability. |
</phase_requirements>

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| `gunicorn` | 25.1.0 (current stable) | WSGI HTTP server for Flask app | Official Flask deployment recommendation; multi-worker, production-grade, no extra config needed for basic use |
| `venv/bin/gunicorn` | (matches pip install) | Entrypoint that uses venv Python and packages | Using the venv-relative binary avoids PATH confusion with any system-installed gunicorn |
| UFW (`ufw allow 5000/tcp`) | Ubuntu built-in | Open inbound port for external reachability | Ubuntu's default firewall; required to let agent machines reach the VM on port 5000 |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `--workers N` flag | — | Set number of worker processes | Recommended: 2 workers for a 1-vCPU VM; default is 1 which the official docs warn against |
| `--log-level debug` flag | — | Verbose gunicorn startup output | Use when troubleshooting import errors; not needed for normal verification |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `gunicorn` | `uwsgi`, `waitress` | Gunicorn is Flask's recommended option and the documented project choice; no reason to deviate |
| `--bind 0.0.0.0:5000` | Unix socket file | Sockets are preferred with Nginx (not present here); TCP bind is correct for direct external access |
| `pip install gunicorn` (standalone) | Add to `requirements.txt` | Adding to requirements.txt is the right long-term move; for Phase 2 (manual verification only) either works, but adding it to requirements.txt is cleaner |

**Installation:**
```bash
# Inside activated venv, from project root on the VM
pip install gunicorn

# Verify
venv/bin/gunicorn --version
```

---

## Architecture Patterns

### Relevant Project Structure

```
/home/student/context-of-code/    # Project root — MUST be cwd when running gunicorn
├── web_app/
│   ├── __init__.py               # Makes web_app a Python package
│   ├── app.py                    # Flask app object: `app = Flask(__name__)`
│   └── blueprints/
│       └── api.py                # /api/* routes including /api/ingest
├── requirements.txt              # Does NOT include gunicorn — install separately
└── venv/                         # Project venv; gunicorn installed here
    └── bin/
        └── gunicorn              # Gunicorn entrypoint after pip install
```

### Pattern 1: Module Path Syntax

**What:** Gunicorn's required argument is `{module_import}:{app_variable}`.

- `module_import` = dotted Python import path to the module containing the app object.
  - For this project: `web_app.app` (equivalent to `from web_app.app import app`)
- `app_variable` = the name of the Flask instance in that module.
  - For this project: `app` (defined at line 4 of `web_app/app.py`)

**When to use:** Always specify the full dotted path when the app lives inside a package. Running just `app:app` would fail because there is no top-level `app.py` in the repo root.

**Correct command:**
```bash
# Source: Flask official docs + verified against web_app/app.py
# Run from /home/student/context-of-code with venv activated
gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app
```

### Pattern 2: Working Directory Requirement

**What:** Gunicorn resolves module imports using the current working directory as the Python path root. The command MUST be run from the repo root (`/home/student/context-of-code`), not from inside `web_app/`.

**Why:** Python needs to resolve `web_app` as a top-level package. If cwd is `/home/student/context-of-code/web_app`, the import `web_app.app` fails because `web_app` is not visible as a package from that location.

```bash
# CORRECT — cwd is repo root
cd /home/student/context-of-code
source venv/bin/activate
gunicorn --bind 0.0.0.0:5000 web_app.app:app

# WRONG — cwd is inside the package
cd /home/student/context-of-code/web_app
gunicorn --bind 0.0.0.0:5000 web_app.app:app  # ImportError: No module named 'web_app'
```

### Pattern 3: Verifying from an Agent Machine (External Curl)

**What:** The success criterion requires a `curl` from outside the VM. This proves the app is bound to `0.0.0.0` (not just `127.0.0.1`) and that the firewall allows the traffic.

```bash
# From an agent machine — NOT from the VM itself
# A 400 or 405 response counts as success (proves gunicorn is answering)
curl http://200.69.13.70:5000/api/ingest
```

A 405 (Method Not Allowed) from `/api/ingest` on a GET request is expected and confirms the app is routing correctly. A 400 or any HTTP response (even an error page) proves reachability.

### Anti-Patterns to Avoid

- **Running gunicorn without activating venv:** The system `gunicorn` (if any exists) will not have the project packages (`Flask`, `flask-cors`, `SQLAlchemy`) and will produce import errors immediately.
- **Binding to `127.0.0.1` instead of `0.0.0.0`:** The default gunicorn bind is `127.0.0.1:8000`. Without `--bind 0.0.0.0:5000`, the app is not reachable from agent machines.
- **Testing reachability from the VM itself:** `curl http://localhost:5000/api/ingest` proves the process is running but does NOT prove external reachability (firewall and bind address are not exercised). The success criterion explicitly requires testing from an agent machine.
- **Running gunicorn as root:** The official docs warn against this (application code would run as root). On Ubuntu, `sudo gunicorn ...` is unnecessary and a security risk. The `student` user has sudo access but gunicorn should run as `student`.
- **Using `flask run` for this phase:** `flask run` is the development server. The entire point of this phase is to replace it with gunicorn.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Worker count calculation | Custom formula | Use `--workers 2` for a 1-vCPU VM | Official formula is `(2 * CPU_cores) + 1`; for 1 vCPU that is 3, but 2 is safe for a college project under low load. Exact CPU count unknown until SSH; start at 2. |
| Module path discovery | Grep/guess | Read `web_app/app.py` line 4: `app = Flask(__name__)` | Entry point is unambiguous; no guessing needed. |
| Port opening | iptables rules | `sudo ufw allow 5000/tcp` | UFW wraps iptables. One command, reversible, idiomatic Ubuntu. |

**Key insight:** This phase has zero new application code. Every task is a shell command — install, run, open port, verify.

---

## Common Pitfalls

### Pitfall 1: ImportError Due to Wrong Working Directory

**What goes wrong:** Gunicorn starts but immediately exits with `ModuleNotFoundError: No module named 'web_app'` or `ImportError: cannot import name 'app' from 'web_app'`.

**Why it happens:** The command was run from a directory other than the repo root, so Python cannot resolve `web_app` as a package.

**How to avoid:** Always `cd /home/student/context-of-code` before running gunicorn. Verify with `pwd` if unsure.

**Warning signs:** Error appears in the first few lines of gunicorn output before any `[INFO] Booting worker` messages.

---

### Pitfall 2: ImportError Because Venv Not Activated

**What goes wrong:** `gunicorn` is found (or not found), but when it runs, it fails with `ModuleNotFoundError: No module named 'flask'` despite Flask being installed.

**Why it happens:** The system Python or a different environment's gunicorn is used, which does not have the project packages. `flask` is installed in the venv, not the system Python.

**How to avoid:** Always activate the venv first (`source venv/bin/activate`) and verify the correct gunicorn is used: `which gunicorn` should print `.../context-of-code/venv/bin/gunicorn`. Alternatively, use the absolute path: `venv/bin/gunicorn --bind 0.0.0.0:5000 web_app.app:app` — this bypasses PATH entirely.

**Warning signs:** `which gunicorn` prints `/usr/bin/gunicorn` or similar system path, not a venv path.

---

### Pitfall 3: Port Not Open in UFW

**What goes wrong:** Gunicorn starts successfully (visible in the terminal on the VM), but `curl` from an agent machine hangs or times out with `Connection refused` or no response.

**Why it happens:** UFW is active by default on Ubuntu and blocks all inbound traffic on non-allowed ports. Port 5000 is not opened by Phase 1.

**How to avoid:** Run `sudo ufw allow 5000/tcp` on the VM before testing from an agent machine. Verify with `sudo ufw status` to confirm the rule appears.

**Warning signs:** `curl` from the VM itself (`curl http://localhost:5000/api/ingest`) works but `curl` from an agent machine times out.

---

### Pitfall 4: Default Workers = 1

**What goes wrong:** Gunicorn starts fine with one worker, but the official docs note this is probably not what you want. For Phase 2 (foreground verification), 1 worker is technically sufficient, but the planner should document the worker count explicitly.

**Why it happens:** Gunicorn's default is `--workers 1` (a single synchronous worker). The Flask dev server also has one thread by default.

**How to avoid:** Always specify `--workers 2` (or 3 if the VM has 1 vCPU, using the `(2 * 1) + 1 = 3` formula). For this phase (manual verification), 2 workers is safe and avoids confusion in Phase 4 when writing the systemd unit.

**Warning signs:** No explicit `--workers` flag in the command; gunicorn log shows only one `[INFO] Booting worker` line.

---

### Pitfall 5: Gunicorn Version Unknown Until Install Time

**What goes wrong:** Plan specifies a version but the VM resolves a different version via pip.

**Why it happens:** PyPI evolves. As of research date (2026-02-24), current stable is 25.1.0, requiring Python >=3.10. This is compatible with the Phase 1 venv. However, the actual installed version may differ if pip resolves differently.

**How to avoid:** Pin the version in the install command if exact version matters, or accept whatever pip installs and record it with `venv/bin/gunicorn --version` after installation. For this phase, version pinning is unnecessary — any recent Gunicorn with Python 3.10+ support works.

**Warning signs:** None expected; this is a note to verify and record the version, not a likely failure mode.

---

## Code Examples

Verified patterns from official Flask docs and project source code:

### Full Phase 2 Command Sequence (on VM)

```bash
# Source: Official Flask docs (flask.palletsprojects.com/en/stable/deploying/gunicorn/)
#         + project-specific paths from web_app/app.py

# 1. SSH into VM
ssh -i ~/path/to/key student@200.69.13.70 -p 2214

# 2. Navigate to project root and activate venv
cd /home/student/context-of-code
source venv/bin/activate

# 3. Install gunicorn into venv
pip install gunicorn

# 4. Verify installation
venv/bin/gunicorn --version
# Expected output: gunicorn (version 25.x.x)

# 5. Open port 5000 in UFW (required before external reachability test)
sudo ufw allow 5000/tcp
sudo ufw status  # confirm rule appears

# 6. Start gunicorn (foreground — will block terminal)
gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app
# Expected output includes:
#   [INFO] Starting gunicorn X.X.X
#   [INFO] Listening at: http://0.0.0.0:5000
#   [INFO] Booting worker with pid: XXXX
#   [INFO] Booting worker with pid: XXXX  (second worker)
```

### External Reachability Test (from agent machine)

```bash
# Source: Phase 2 success criterion
# Run from an agent machine (MacBook, lab machine — NOT the VM)

curl http://200.69.13.70:5000/api/ingest

# Expected responses that all count as SUCCESS:
# - HTTP 405 Method Not Allowed (GET not accepted by POST-only route)
# - HTTP 400 Bad Request (route exists, request malformed)
# - HTTP 200 OK (route accepts GET — depends on blueprint implementation)
# Any HTTP response proves gunicorn is serving and the port is open

# A connection refused or timeout is FAILURE (UFW blocking or wrong bind address)
```

### Manual Import Test (pre-flight before gunicorn)

```bash
# Test that the module path resolves before starting gunicorn
# Run from repo root with venv activated
python -c "from web_app.app import app; print(app)"
# Expected: <Flask 'web_app.app'>
# If this fails, gunicorn will also fail with the same ImportError
```

### Verify Correct Gunicorn Binary

```bash
# Confirm which gunicorn will be used (must be the venv one)
which gunicorn
# Expected: /home/student/context-of-code/venv/bin/gunicorn
# If output is /usr/bin/gunicorn — venv is not activated
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|---|---|---|
| `flask run --host=0.0.0.0` | `gunicorn --bind 0.0.0.0:5000 web_app.app:app` | Dev server explicitly not for production; gunicorn is multi-worker and handles concurrent requests |
| Gunicorn 20.x (prior stable) | Gunicorn 25.1.0 (2026-02-13) | Gunicorn 25 added HTTP/2 support (beta) and per-app worker allocation; none of these features are needed for this phase |
| `--bind 0.0.0.0:8000` (gunicorn default port) | `--bind 0.0.0.0:5000` | Port 5000 is Flask's conventional port and what the project uses; gunicorn defaults to 8000 so the port must be specified explicitly |

**Deprecated/outdated:**
- Gunicorn 20.x documentation: Still widely cited in tutorials but superseded. Gunicorn 25.1.0 is current. API and CLI flags are unchanged for basic use — the install and run commands are identical.
- `flask run` for any deployment scenario: Flask docs explicitly state the dev server is not suitable for production.

---

## Open Questions

1. **Actual VM vCPU count (affects --workers recommendation)**
   - What we know: The `(2 * CPU_cores) + 1` formula is the official recommendation. For Phase 2 foreground verification, workers = 2 is safe regardless.
   - What's unclear: The university VM's allocated vCPU count. Phase 1 research flagged this as unknown.
   - Recommendation: Use `--workers 2` for Phase 2. When writing the systemd unit in Phase 4, check with `nproc` and apply the formula then.

2. **Should gunicorn be added to requirements.txt?**
   - What we know: Gunicorn is not in requirements.txt currently. Flask's own docs install it separately from the application.
   - What's unclear: Whether the project wants to codify gunicorn as a project dependency (making it reproducible) or keep it a deployment concern.
   - Recommendation: Add `gunicorn` (unpinned) to requirements.txt as part of this phase. It should be a tracked dependency since the app cannot run without it in production. This keeps the VM setup reproducible.

3. **UFW pre-condition: is UFW active on the VM?**
   - What we know: Phase 1 research noted UFW status is unconfirmed. Ubuntu 22.04 ships with UFW installed but it may or may not be enabled.
   - What's unclear: Current UFW status on Student-vm-13.
   - Recommendation: Check `sudo ufw status` early in the phase. If it reports `Status: inactive`, port 5000 is already accessible without a rule change (no firewall is blocking). If active, run `sudo ufw allow 5000/tcp`. The plan should handle both cases.

---

## Sources

### Primary (HIGH confidence)

- Flask official docs — Gunicorn deployment: https://flask.palletsprojects.com/en/stable/deploying/gunicorn/ — installation command, `module_import:app_variable` syntax, worker count warning, root user warning
- PyPI gunicorn page: https://pypi.org/project/gunicorn/ — current version 25.1.0, release date 2026-02-13, Python >=3.10 requirement
- Project source `web_app/app.py` — confirms `app = Flask(__name__)` at module level, making `web_app.app:app` the correct entry point
- Project `requirements.txt` — confirms gunicorn is NOT present and must be installed separately

### Secondary (MEDIUM confidence)

- Gunicorn official workers formula docs: https://docs.gunicorn.org/en/stable/design.html — `(2 * CPU_cores) + 1` recommendation, verified via search against official docs domain
- DigitalOcean Flask + Gunicorn + Ubuntu guide: https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04 — `sudo ufw allow 5000/tcp` command and external reachability testing pattern; verified against UFW documentation
- Phase 1 RESEARCH.md — VM details: IP `200.69.13.70`, SSH port `2214`, username `student`, project path `/home/student/context-of-code`, venv at `venv/`

### Tertiary (LOW confidence)

- WebSearch result re: ImportError causes (working directory, venv activation) — consistent across multiple sources; core claims verified by official Flask docs behavior description

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — Gunicorn version confirmed from PyPI; Flask integration confirmed from official Flask docs; app entry point confirmed from source code
- Architecture: HIGH — project structure read directly from source; module path derived from actual `web_app/app.py`; no assumptions
- Pitfalls: MEDIUM — most derived from official docs warnings + common deployment patterns; UFW state on the specific VM is unconfirmed (open question 3)

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (Gunicorn is stable; Flask 3.1.x deployment guidance is stable; revisit if VM OS changes)
