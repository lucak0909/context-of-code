# Architecture Patterns

**Domain:** Flask aggregator migration to Ubuntu VM with Gunicorn + systemd
**Researched:** 2026-02-24
**Overall confidence:** HIGH (Gunicorn, systemd, and python-dotenv are stable, well-documented technologies; all patterns verified against codebase)

---

## Recommended Architecture

```
[Agent devices]                     [Ubuntu VM]                    [Cloud]
    ┌─────────────┐  HTTP POST       ┌─────────────────────────┐
    │  UploadQueue│ ─────────────►  │  Gunicorn (WSGI server) │
    │  (queue.py) │  /api/ingest     │   workers: 2-4          │
    └─────────────┘                  │   bind: 0.0.0.0:5000    │
         ↑                           │         │               │
  AGGREGATOR_API_URL                 │   web_app/app.py        │
  (updated in .env                   │         │               │
   on agent machines)                │   Flask app object      │
                                     │         │               │
                                     │  systemd manages        │
                                     │  start/stop/restart     │
                                     └────────┬────────────────┘
                                              │ SQLAlchemy
                                              ▼
                                     [Supabase PostgreSQL]
                                      (unchanged, cloud)
```

### Component Boundaries

| Component | Responsibility | Communicates With |
|-----------|---------------|-------------------|
| systemd unit | Process lifecycle (start, stop, restart, boot) | Gunicorn process via SIGTERM/SIGHUP |
| Gunicorn | WSGI worker pool, request handling, port binding | Flask app object (imports it), agents (HTTP) |
| Flask app (`web_app/app.py`) | Blueprint registration, app object creation | Gunicorn (provides WSGI callable), blueprints |
| `/api/ingest` blueprint | Payload validation, ORM routing | Database layer |
| `/health` endpoint | Liveness response (200 OK + JSON) | External callers, monitoring |
| `.env` on VM | All secrets and config (DB creds, log settings) | `common/settings.py` via `load_dotenv()` |
| `.env` on agent machines | `AGGREGATOR_API_URL` pointing to VM IP | `common/settings.py` → `UploadQueue` |

### Data Flow

```
Agent boot:
  .env (AGGREGATOR_API_URL=http://<VM_IP>:5000/api/ingest)
    └─► UploadQueue.__init__() reads get_settings().aggregator_api_url
          └─► _send_payload() POSTs to VM IP

VM boot:
  systemd starts context-of-code.service
    └─► Executes: gunicorn --workers 3 --bind 0.0.0.0:5000 web_app.app:app
          └─► Gunicorn imports web_app.app, finds `app` object
                └─► Flask registers api_bp on /api prefix
                      └─► /api/ingest and /api/health routes available

Ingest request:
  Agent POST /api/ingest ──► Gunicorn worker ──► Flask ──► api.py:ingest()
    └─► _get_db() lazy-inits Database singleton
          └─► db.insert_*_sample() ──► SQLAlchemy ──► Supabase
```

---

## Gunicorn Integration with This Flask App

### Direct App Object (Recommended for This Project)

`web_app/app.py` already creates a module-level `app` object:

```python
# web_app/app.py — current state
app = Flask(__name__)
app.register_blueprint(api_bp, url_prefix="/api")

if __name__ == '__main__':
    app.run(debug=True)
```

Gunicorn references this as `web_app.app:app` — the module path then the variable name. No code changes are needed for this pattern.

**Why not app factory pattern:** App factory (`create_app()` returning a Flask instance) exists to support multiple configurations (testing, production, etc.) via function arguments. This project has a single configuration loaded from `.env` via `get_settings()` — there is no need for factory indirection. Direct module-level `app` is simpler and correct for this scope.

**The `if __name__ == '__main__'` block** in `app.py` does not execute when Gunicorn imports the module — Gunicorn imports `web_app.app` as a library, so only the top-level statements run (creating `app`, registering blueprints). The `app.run(debug=True)` block is harmlessly bypassed.

### Gunicorn Command

```bash
# Invoked from project root (where web_app/ is importable)
gunicorn \
  --workers 3 \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile /var/log/context-of-code/access.log \
  --error-logfile /var/log/context-of-code/error.log \
  web_app.app:app
```

**Worker count rationale:** The formula `(2 * CPU_cores) + 1` is the standard Gunicorn recommendation. For a single-core VM, that gives 3. Each ingest request is brief (DB write + return), so workers don't block long. 3 workers is correct for this load profile.

**`--timeout 120`:** The default 30s timeout is usually fine, but Supabase connection establishment on cold start can be slow. 120s gives headroom without hanging forever.

**`0.0.0.0:5000`:** Binds all interfaces so agents on other machines can reach the VM. `127.0.0.1:5000` would only accept local connections.

---

## systemd Unit File

### File Location

`/etc/systemd/system/context-of-code.service`

### Unit File Content

```ini
[Unit]
Description=Context of Code — Flask aggregator via Gunicorn
After=network.target

[Service]
Type=simple
User=<deploy_user>
Group=<deploy_user>
WorkingDirectory=/home/<deploy_user>/context-of-code
EnvironmentFile=/home/<deploy_user>/context-of-code/.env
ExecStart=/home/<deploy_user>/context-of-code/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:5000 \
    --timeout 120 \
    --access-logfile /var/log/context-of-code/access.log \
    --error-logfile /var/log/context-of-code/error.log \
    web_app.app:app
Restart=on-failure
RestartSec=5s
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
```

### Key Decisions Explained

**`After=network.target`:** Ensures the network stack is ready before Gunicorn starts, so the port bind and Supabase connection attempts don't fail immediately on boot.

**`EnvironmentFile=`:** systemd reads the `.env` file and injects each `KEY=VALUE` line as an environment variable before launching the process. This means `common/settings.py`'s `load_dotenv()` call finds variables already present in the environment and does not need to read the file itself — but it is harmless either way because `load_dotenv()` does not override already-set environment variables by default.

**`WorkingDirectory=`:** Sets the CWD to the project root before Gunicorn starts. This is required so that `web_app.app` is importable as a Python package (Python adds CWD to `sys.path` when running modules).

**`ExecStart` uses venv binary:** `/home/<deploy_user>/context-of-code/venv/bin/gunicorn` uses the project's virtualenv Gunicorn directly, ensuring the correct Python environment and all project dependencies are available without activation scripts.

**`Restart=on-failure`:** Restarts the service only if it exits with a non-zero code (crash). Does not restart on clean `systemctl stop`. `RestartSec=5s` prevents rapid restart loops if the crash is immediate.

**`Type=simple`:** Correct for Gunicorn. Gunicorn is a foreground process — it does not daemonize itself when invoked this way. systemd tracks the direct PID.

**`WantedBy=multi-user.target`:** Standard target for services that should start in normal multi-user mode (non-graphical server). Activates the service on boot when `systemctl enable` is run.

### Activation Commands

```bash
# After writing the unit file:
sudo systemctl daemon-reload
sudo systemctl enable context-of-code   # auto-start on boot
sudo systemctl start context-of-code    # start immediately
sudo systemctl status context-of-code   # verify running
journalctl -u context-of-code -f        # follow logs
```

---

## .env File on the VM

### Recommended Location

```
/home/<deploy_user>/context-of-code/.env
```

Co-located with the project root. This is where `load_dotenv()` in `common/settings.py` looks by default (it searches upward from CWD). With `WorkingDirectory` set to the project root in the systemd unit, `load_dotenv()` finds `.env` without any path argument needed.

### Permissions

```bash
chmod 600 /home/<deploy_user>/context-of-code/.env
chown <deploy_user>:<deploy_user> /home/<deploy_user>/context-of-code/.env
```

`600` (owner read/write only) prevents other users on the VM from reading database credentials. The service runs as `<deploy_user>` so it can read the file.

### Required .env Contents

```bash
# Database (Supabase PostgreSQL — unchanged from PythonAnywhere)
user=<supabase_db_user>
password=<supabase_db_password>
host=<supabase_db_host>
port=5432
dbname=<supabase_db_name>

# Logging (optional — defaults apply if omitted)
LOG_LEVEL=INFO
LOGS_DIR=/var/log/context-of-code

# Aggregator URL (not used by the aggregator itself, only by agents)
# Agents read this from their own .env — leave blank or omit on the VM
# AGGREGATOR_API_URL=http://127.0.0.1:5000/api/ingest  # (default, no change needed on VM)
```

**Note on variable naming:** `common/settings.py` uses bare names (`user`, `password`, `host`, `port`, `dbname`) — not `DB_USER` etc. This matches the existing PythonAnywhere configuration and should not be changed.

### `.env` Must Not Be Committed

`.env` should be in `.gitignore`. Verify this before deploying:

```bash
grep -r "\.env" /home/<deploy_user>/context-of-code/.gitignore
```

---

## Agent Reconfiguration

### What Changes

Agents read `AGGREGATOR_API_URL` from their own `.env` (on each agent's machine). The `UploadQueue` constructor calls `get_settings().aggregator_api_url`, which defaults to `http://127.0.0.1:5000/api/ingest` if the env var is absent.

To point agents at the VM, each agent machine's `.env` needs:

```bash
AGGREGATOR_API_URL=http://<VM_IP>:5000/api/ingest
```

### No Code Changes Required

`UploadQueue.__init__()` already reads `get_settings().aggregator_api_url`. The URL is injected via environment variable. No Python source changes are needed on agent machines — only a `.env` update.

### Agent `.env` Location

Same pattern: co-located with project root on each agent machine. `load_dotenv()` in `get_settings()` will pick it up.

### Verification After Update

From an agent machine, a quick test before running the full agent:

```bash
curl -X POST http://<VM_IP>:5000/api/ingest \
  -H "Content-Type: application/json" \
  -d '{"device_id":"invalid","sample_type":"desktop_network"}'
# Expected: 400 {"error":"Invalid device_id (must be a valid UUID)."}
# (proves the VM is reachable and Flask is running)
```

A 400 with the expected error body confirms the aggregator is running and routing requests correctly.

---

## New Components and Modified Components

### New Files (to create on VM)

| File | Type | Purpose |
|------|------|---------|
| `/etc/systemd/system/context-of-code.service` | New — VM config | systemd unit managing Gunicorn process |
| `/home/<deploy_user>/context-of-code/.env` | New — VM config | Environment variables (DB creds, log settings) |
| `/var/log/context-of-code/` | New — VM directory | Gunicorn access and error log destination |

### Modified Files (in codebase)

| File | Change | Reason |
|------|--------|--------|
| `web_app/blueprints/api.py` | Add `GET /health` endpoint | Liveness check per PROJECT.md requirements |
| `web_app/app.py` | Register health blueprint or add route | Expose `/health` (can also go in `api_bp`) |

### Unchanged (by design)

| Component | Reason |
|-----------|--------|
| `web_app/app.py` app creation | Module-level `app` object is already WSGI-compatible |
| `common/settings.py` | `load_dotenv()` already works with co-located `.env` |
| `agent/uploader_queue/queue.py` | URL already env-var driven; no code change needed |
| `common/database/` | ORM and connection logic unchanged; Supabase stays in cloud |
| `.env` variable names (`user`, `password`, etc.) | Must match existing `settings.py` constants |

---

## Health Endpoint

The `/health` endpoint is a new addition required by PROJECT.md. It belongs in the existing `api_bp` blueprint:

```python
# web_app/blueprints/api.py — add alongside existing routes
@api_bp.route("/health", methods=["GET"])
def health():
    """Liveness check — returns 200 if the server is running."""
    return jsonify({"status": "ok"}), 200
```

This results in `GET /api/health` (because `api_bp` is registered with `url_prefix="/api"`). Agents and operators can poll this to confirm the aggregator is reachable.

---

## Patterns to Follow

### Pattern 1: venv binary invocation (not activation)

**What:** Reference Gunicorn via its full venv path in ExecStart rather than activating the venv first.

**When:** Always in systemd unit files.

**Why:** `source venv/bin/activate` is a shell builtin that cannot be used directly in `ExecStart`. The venv binary approach is simpler and more reliable.

```ini
# Correct
ExecStart=/home/deploy/context-of-code/venv/bin/gunicorn ...

# Incorrect — will not work in systemd
ExecStart=/bin/bash -c "source venv/bin/activate && gunicorn ..."
```

### Pattern 2: WorkingDirectory + module import path

**What:** Set `WorkingDirectory` to the project root so `web_app.app` is importable as a package without modifying `PYTHONPATH`.

**When:** Any systemd service that imports Python packages by dotted path.

**Why:** Python adds CWD to `sys.path` during module execution. Gunicorn imports `web_app.app` as a package, which requires `web_app/` to be discoverable from CWD.

### Pattern 3: EnvironmentFile for secrets injection

**What:** Use `EnvironmentFile=` in the systemd unit rather than exporting variables in a wrapper script or hardcoding in the unit.

**When:** Any service with credentials or environment-specific config.

**Why:** `EnvironmentFile` is the systemd-native secret injection mechanism. It keeps secrets out of the unit file (which is readable by all users), allows `.env` file permissions to restrict access, and works transparently with `load_dotenv()` (which does not override already-set env vars).

---

## Anti-Patterns to Avoid

### Anti-Pattern 1: Running Gunicorn as root

**What:** Starting the systemd service as `root` user.

**Why bad:** If the process is compromised, an attacker has root access. Gunicorn binds port 5000 (>1024), so root is not required.

**Instead:** Create a dedicated system user or use the deploy user. Set `User=` and `Group=` in the unit file.

### Anti-Pattern 2: Using `app.run()` in production

**What:** Running `python web_app/app.py` directly, which invokes Flask's development server.

**Why bad:** Flask explicitly documents its dev server as unsuitable for production — single-threaded, not hardened, not designed for concurrent load.

**Instead:** Always use `gunicorn web_app.app:app`. The `if __name__ == '__main__'` block in `app.py` should remain for local development convenience but never be used on the VM.

### Anti-Pattern 3: Binding to 127.0.0.1 on the VM

**What:** `--bind 127.0.0.1:5000` in the Gunicorn command.

**Why bad:** Only accepts connections from localhost. Agents on other machines cannot reach the aggregator.

**Instead:** `--bind 0.0.0.0:5000` — binds all interfaces. This is correct for an internal API on a VM that agents need to reach from outside.

### Anti-Pattern 4: Storing .env in version control

**What:** Committing `.env` to git.

**Why bad:** Database credentials end up in git history and are accessible to anyone with repo access.

**Instead:** `.env` must be in `.gitignore`. Provision the VM's `.env` manually (scp, secrets manager, or manual entry). Keep a `.env.example` in the repo documenting required variables without values.

### Anti-Pattern 5: Changing DB variable names in .env

**What:** Renaming env vars from `user`, `password`, `host` to `DB_USER`, `DB_PASSWORD`, `DB_HOST`.

**Why bad:** `common/settings.py` hard-codes the current names (`DB_ENV_USER = "user"`, etc.). Renaming the `.env` variables without updating `settings.py` will break the DB connection silently (environment variables won't be found, `_require_env()` raises `ValueError`).

**Instead:** Keep the existing variable names. They are already functional.

---

## Build Order for Phases

Based on dependencies, the phases should proceed in this order:

1. **VM provisioning** — Python, venv, project dependencies installed; `.env` file created with DB credentials. No new code. Validates that the existing app can connect to Supabase from the VM.

2. **Gunicorn setup** — Install Gunicorn into venv, verify `gunicorn web_app.app:app` runs manually, confirm `/api/ingest` is reachable. Validates the WSGI integration before introducing systemd complexity.

3. **Health endpoint** — Add `GET /api/health` to `api_bp`. Small code change; must be deployed before systemd so the unit's liveness testing can use it.

4. **systemd unit** — Write, enable, and start `context-of-code.service`. Validates that the service starts on boot and restarts on failure. Depends on Gunicorn working correctly (Phase 2) so that the unit has a stable `ExecStart` to point at.

5. **Agent reconfiguration** — Update `AGGREGATOR_API_URL` on each agent machine's `.env`. Depends on the VM service being stable and reachable (Phases 2-4 complete).

**Dependency graph:**

```
VM provisioning
     └─► Gunicorn manual test
               └─► Health endpoint (code change)
                         └─► systemd unit
                                   └─► Agent .env update
```

---

## Scalability Considerations

This is a college project with a handful of agents. These considerations are noted for awareness, not action.

| Concern | Current scale (10 agents) | Future scale (100+ agents) |
|---------|--------------------------|---------------------------|
| Workers | 3 workers is sufficient | Increase workers or use async worker class (gevent) |
| DB connections | NullPool in Database class avoids connection accumulation | Already correct — NullPool creates/destroys per operation |
| Logging volume | File rotation via FlaggingFileHandler | Already handled; logrotate on VM for disk management |
| Port exposure | 0.0.0.0:5000 no firewall | Add UFW rule restricting to known agent IPs |

---

## Sources

- Gunicorn WSGI server documentation — gunicorn.org/run.html (training knowledge, HIGH confidence for stable `module:app` syntax)
- Flask deployment documentation — flask.palletsprojects.com/en/stable/deploying/gunicorn/ (training knowledge, HIGH confidence)
- systemd service unit documentation — freedesktop.org/software/systemd/man/systemd.service.html (training knowledge, HIGH confidence for `EnvironmentFile`, `Type=simple`, `Restart=on-failure`)
- python-dotenv documentation — `load_dotenv()` does not override existing env vars (HIGH confidence — verified against `common/settings.py` behaviour and dotenv specification)
- Codebase reading — `web_app/app.py`, `web_app/blueprints/api.py`, `common/settings.py`, `agent/uploader_queue/queue.py` (HIGH confidence — direct source reading)

*Note: WebSearch and WebFetch were unavailable during this research session. All recommendations are drawn from direct codebase reading plus training knowledge of these well-established, stable technologies. Gunicorn, systemd, and python-dotenv APIs have not changed materially in years. Confidence is HIGH for all claims made.*
