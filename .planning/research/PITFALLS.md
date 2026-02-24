# Domain Pitfalls

**Domain:** Flask/Gunicorn/systemd VM migration (PythonAnywhere → Ubuntu)
**Researched:** 2026-02-24
**Confidence:** HIGH — All pitfalls grounded in codebase inspection + well-established systemd/Gunicorn operational knowledge

---

## Critical Pitfalls

Mistakes that cause the service to not start, silently fail, or require a rewrite.

---

### Pitfall 1: Gunicorn Cannot Find the App Object — Wrong Module:Variable Syntax

**What goes wrong:** Gunicorn is invoked with the wrong app target string and fails with `ModuleNotFoundError` or `AttributeError`, or imports the module but finds no WSGI callable.

**Why it happens:** Gunicorn's target format is `module_path:variable_name`. This project's app lives at `web_app/app.py` and the object is named `app`. From the project root, the correct target is `web_app.app:app`. Common mistakes:
- Using a file path: `web_app/app.py:app` (invalid — not a Python module path)
- Using the wrong variable: `web_app.app:application` (object is named `app`, not `application`)
- Running Gunicorn from the wrong directory so the import path is wrong
- Running `gunicorn app:app` from inside `web_app/` (breaks the `from web_app.blueprints.api import api_bp` import in app.py)

**Consequences:** Service starts, immediately exits, systemd restart loop. Logs show `ModuleNotFoundError: No module named 'web_app'` or `Failed to find application object`.

**Prevention:**
- Always run Gunicorn from the project root: `gunicorn web_app.app:app`
- Confirm by testing manually before writing the systemd unit: `cd /path/to/project && .venv/bin/gunicorn web_app.app:app`
- The `WorkingDirectory=` in the systemd unit must be the project root, not any subdirectory

**Detection:** `journalctl -u aggregator.service -n 50` shows import errors on startup. `systemctl status aggregator.service` shows `Active: failed` immediately after start.

---

### Pitfall 2: Systemd Unit Uses System Python Instead of Virtualenv Python

**What goes wrong:** The systemd service uses `/usr/bin/python3` or the bare `gunicorn` command (which resolves to a system-installed binary), instead of the virtualenv's Gunicorn. The system Python may lack all installed dependencies, causing `ModuleNotFoundError` for Flask, SQLAlchemy, psycopg2, etc.

**Why it happens:** In a terminal session, `source .venv/bin/activate` is run and everything works. But systemd does not source the virtualenv. The `ExecStart=` line must use absolute paths to the virtualenv's binaries.

**Consequences:** Service appears to start (no immediate crash) but fails on first import. All custom packages (Flask, SQLAlchemy, psycopg2-binary, python-dotenv) are missing. May produce confusing errors like `No module named 'flask'` even though `pip list` shows Flask installed — because `pip list` runs inside the venv during the developer's session, not systemd's.

**Prevention:**
```ini
[Service]
ExecStart=/home/user/context-of-code/.venv/bin/gunicorn web_app.app:app
```
Never use: `ExecStart=gunicorn web_app.app:app` or `ExecStart=python -m gunicorn web_app.app:app` without full path.

**Detection:** Run `sudo systemctl cat aggregator.service` and verify ExecStart uses absolute venv path. Check: `sudo -u <service_user> /path/to/.venv/bin/gunicorn --version` — if this fails, the venv path is wrong.

---

### Pitfall 3: .env File Not Present on VM / Wrong Location / Not Loaded

**What goes wrong:** `common/settings.py` calls `load_dotenv()` which loads a `.env` file relative to the current working directory. If the `.env` file is missing from the VM, or the systemd `WorkingDirectory=` is wrong, `get_settings()` raises `ValueError: Missing required env vars for DB connection: user, password, host, port, dbname` and the app crashes on first database operation.

**Why it happens:** The `.env` file is typically in `.gitignore` and is never committed. Developers forget to manually create it on the VM, or create it in the wrong directory. The `load_dotenv()` call in `settings.py` silently succeeds even when no `.env` file exists — it just doesn't load anything, and `os.getenv()` returns `None` for all vars.

**Specific env vars required by this project** (from `common/settings.py`):
- `user` — DB username
- `password` — DB password
- `host` — DB host
- `port` — DB port
- `dbname` — DB name
- `AGGREGATOR_API_URL` — optional (defaults to localhost, which is wrong on VM)

**Consequences:** App boots, returns 500 on every request after the first database call, because `get_settings()` is `lru_cache`-wrapped and the error happens on first DB initialisation. Logs show `ValueError: Missing required env vars`.

**Prevention:**
- Create `.env` in project root on VM before starting the service
- Verify env vars are loaded: `cd /path/to/project && .venv/bin/python -c "from common.settings import get_settings; print(get_settings())"`
- Add env var validation to the startup smoke test (curl /health after start)

**Detection:** `journalctl -u aggregator.service | grep ValueError` or `grep "Missing required"`.

---

### Pitfall 4: Firewall Blocks the Gunicorn Port — Service Runs But Agents Cannot Connect

**What goes wrong:** Gunicorn starts successfully and listens on a port (e.g., 5000 or 8000), but agents on other machines cannot reach the aggregator. The VM's firewall (UFW on Ubuntu) blocks inbound connections by default.

**Why it happens:** Ubuntu 22.04/24.04 ships with UFW. Default policy is `deny incoming`. Even if Gunicorn is listening, the port is not reachable from outside without an explicit `ufw allow` rule. This is invisible locally (localhost always works) but breaks all remote agents.

**This project's specific exposure:** Agents use `AGGREGATOR_API_URL` to POST to the aggregator. If the port is blocked, agents silently queue payloads indefinitely (the upload queue retries forever). No error is visible on the agent side beyond connection timeouts.

**Consequences:** Service is running, systemd reports healthy, but zero data arrives in Supabase. Queue files on agent machines grow indefinitely. The `/health` endpoint is unreachable from outside.

**Prevention:**
```bash
# Check UFW status first
sudo ufw status

# Allow the Gunicorn port (choose one)
sudo ufw allow 5000/tcp    # if using default Flask-like port
sudo ufw allow 8000/tcp    # if using Gunicorn default
```
Also verify Gunicorn is binding to `0.0.0.0`, not `127.0.0.1` (localhost-only). The bind address must be `0.0.0.0:PORT` to accept external connections.

**Detection:** From agent machine: `curl http://<VM_IP>:<PORT>/health` — timeout means firewall block. From VM itself: `curl http://127.0.0.1:<PORT>/health` — if this works but remote doesn't, it's the firewall.

---

### Pitfall 5: lru_cache on get_settings() Caches a Failed State After Missing .env

**What goes wrong:** `get_settings()` is decorated with `@lru_cache(maxsize=1)`. If it is called before the `.env` file is created (e.g., during a failed startup), and the `.env` is later added without restarting the service, the cached `ValueError` or incomplete settings persist for the process lifetime.

**Why it happens:** Python's `lru_cache` caches both successful returns and raised exceptions (in Python 3.8+, exceptions are NOT cached — the function is re-called on next invocation). However, the `Database` singleton `_db` in `api.py` is module-level and initialised lazily. If the first request triggers `_get_db()` which calls `get_settings()` and fails, `_db` stays `None` but the `lru_cache` on `get_settings()` means the fix is straightforward: restart the service. The real risk is the developer adding `.env` and expecting the running service to pick it up without a restart.

**Consequences:** `.env` is present on disk, but the service still returns 500 because `load_dotenv()` was already called and `lru_cache` returned the (previously successful but wrong) settings object. OR: developer adds missing vars, sees them in shell, restarts nothing, wonders why it still fails.

**Prevention:**
- After any `.env` change, always restart the service: `sudo systemctl restart aggregator.service`
- Never assume `.env` changes are picked up by a running process
- During setup: verify env before starting the service for the first time

**Detection:** `sudo systemctl restart aggregator.service && sudo journalctl -u aggregator.service -f` — watch for successful startup after restart.

---

## Moderate Pitfalls

### Pitfall 1: Gunicorn Binds to 127.0.0.1 (Localhost Only) by Default

**What goes wrong:** Gunicorn's default bind address is `127.0.0.1:8000`. If the `--bind` flag is omitted or misconfigured, the service is only accessible from the VM itself, not from external agents.

**Prevention:** Always specify `--bind 0.0.0.0:PORT` explicitly in the Gunicorn command (or in a `gunicorn.conf.py`). Since this project has no Nginx in front of Gunicorn (by design decision), Gunicorn must accept external connections directly.

```ini
ExecStart=/home/user/project/.venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    web_app.app:app
```

**Detection:** `ss -tlnp | grep gunicorn` — if it shows `127.0.0.1:5000` instead of `0.0.0.0:5000`, it's localhost-only.

---

### Pitfall 2: Systemd Service User Has No Permission to Read the .env File or Project Directory

**What goes wrong:** The systemd service runs as a specific user (e.g., `www-data` or a dedicated `aggregator` user). If the project files are owned by a different user (e.g., the SSH login user), the service user cannot read the `.env` file, the JSONL queue, or write to the `logs/` directory.

**Why it happens:** The project is cloned via SSH as the login user. Systemd is then configured to run as `www-data` without adjusting file ownership.

**Consequences:** App starts but silently fails to load `.env` (permission denied is swallowed by `load_dotenv()`). Logs cannot be written. The logs directory does not get created. The `LOGS_DIR` env var path is relative, and the service user may not have write permission to the working directory.

**Prevention:**
- Run the service as the same user who owns the project files, OR
- Use `chown -R <service_user>:<service_user> /path/to/project` after cloning
- Ensure the `logs/` directory exists and is writable before first start: `mkdir -p /path/to/project/logs && chown <service_user> /path/to/project/logs`

**Detection:** `journalctl -u aggregator.service | grep "Permission denied"`. Also check: `sudo -u <service_user> cat /path/to/project/.env`.

---

### Pitfall 3: psycopg2-binary Fails to Install on Ubuntu ARM64 / Missing Build Dependencies

**What goes wrong:** `pip install -r requirements.txt` on the VM fails with `error: command 'gcc' failed` or `pg_config executable not found` when trying to install `psycopg2-binary`.

**Why it happens:** `psycopg2-binary` ships pre-compiled wheels for common platforms (x86_64 Linux, macOS). On ARM64 Ubuntu VMs (e.g., Oracle Cloud free tier) or unusual distro versions, pip falls back to building from source and requires `libpq-dev` and `python3-dev` system packages.

**Consequences:** `requirements.txt` install fails partway through. Flask installs but SQLAlchemy's PostgreSQL driver is missing. The app starts but crashes on first database call with `No module named 'psycopg2'`.

**Prevention:**
```bash
# Install system deps first on Ubuntu
sudo apt-get install -y libpq-dev python3-dev gcc
pip install psycopg2-binary
```
Or switch to `psycopg2` (source build, requires same deps) if the binary wheel is unavailable. The existing `requirements.txt` uses `psycopg2-binary` without a version pin — this could install a version incompatible with the system's libpq.

**Detection:** `pip install -r requirements.txt` output — look for wheel build failures. Post-install: `python -c "import psycopg2; print(psycopg2.__version__)"`.

---

### Pitfall 4: Gunicorn Workers Share the Lazy-Initialised Database Singleton Incorrectly

**What goes wrong:** `api.py` has a module-level `_db: Optional[Database] = None` singleton initialised on first request. With multiple Gunicorn workers (`--workers N`), each worker process gets its own copy of `_db`. This is actually correct — each process has its own memory space. However, if `--workers` is set too high relative to the Supabase connection limit, the VM will exhaust available database connections.

**Why it happens:** With `NullPool` (from `db_operations.py`), each `Session` creates a new PostgreSQL connection and closes it immediately. With 4 workers each handling concurrent requests, the number of active connections scales rapidly.

**Consequences:** Supabase returns `FATAL: remaining connection slots are reserved` and requests fail with 500 errors. The free tier of Supabase has a connection limit (typically ~60 for the free plan).

**Prevention:** Keep worker count low: `--workers 2` is sufficient for this project's scale (college internal tool). Document why 2 workers is the intentional limit.

**Detection:** Supabase dashboard → Database → Connection pooling metrics. Or `journalctl | grep "remaining connection slots"`.

---

### Pitfall 5: Relative Log Paths Break in Systemd Context

**What goes wrong:** `common/settings.py` defaults `LOGS_DIR` to `"logs"` (a relative path). When systemd starts the service, the working directory matters. If `WorkingDirectory=` is not set in the unit file, systemd defaults to `/` or the service user's home directory — not the project root. The `logs/` directory is then created in the wrong location or fails to create at all.

**Why it happens:** During development, the app is run from the project root, so `logs/` is created relative to the project. Systemd does not replicate this context automatically.

**Consequences:** Log files are scattered across the filesystem, or the app crashes if it cannot create the `logs/` directory in a restricted location.

**Prevention:** Set `WorkingDirectory=` in the systemd unit file:
```ini
[Service]
WorkingDirectory=/home/user/context-of-code
```
Alternatively, set `LOGS_DIR=/home/user/context-of-code/logs` as an absolute path in the `.env` file.

**Detection:** `find / -name "*.log" -newer /tmp 2>/dev/null` after service start — if logs appear in unexpected locations, `WorkingDirectory` is wrong.

---

### Pitfall 6: Hardcoded localhost Default for AGGREGATOR_API_URL Is Silently Wrong on Agents

**What goes wrong:** `common/settings.py` defaults `AGGREGATOR_API_URL` to `"http://127.0.0.1:5000/api/ingest"`. Any agent machine that does not have `AGGREGATOR_API_URL` set in its `.env` will silently POST to localhost — which either hits nothing (connection refused) or hits a different local process.

**Why it happens:** This is a pre-existing issue (flagged in CONCERNS.md). The migration makes it critical: before the migration, PythonAnywhere's URL was hardcoded or set via env. After migration, every agent `.env` file must be updated with the new VM IP/port.

**Consequences:** Agents silently queue payloads that never reach the VM. Queue files grow. No error visible in Gunicorn logs because requests never arrive. The symptom looks identical to a firewall block.

**Prevention:**
- After VM is provisioned and port confirmed open, update `AGGREGATOR_API_URL` in every agent's `.env`
- Verify by checking the agent queue: if payloads accumulate after the VM is running, the URL is wrong or blocked
- Consider adding a log warning in `settings.py` when `AGGREGATOR_API_URL` is the localhost default

**Detection:** On an agent machine: `cat .env | grep AGGREGATOR_API_URL`. If missing or pointing to localhost, update it.

---

## Minor Pitfalls

### Pitfall 1: Python Version Mismatch Between Development and VM

**What goes wrong:** The project requires Python 3.10+. Ubuntu 22.04 ships Python 3.10. Ubuntu 24.04 ships Python 3.12. If the `venv` is created with `python3` and the default is an unexpected version, dependency behaviour may differ.

**Prevention:** Always create the venv with an explicit version: `python3.10 -m venv .venv` or `python3.12 -m venv .venv`. Check: `.venv/bin/python --version` before installing dependencies.

---

### Pitfall 2: Systemd Service Not Enabled — Does Not Survive Reboots

**What goes wrong:** `sudo systemctl start aggregator.service` starts the service for the current boot. On next reboot, the service does not start automatically.

**Prevention:** Run `sudo systemctl enable aggregator.service` in addition to `start`. This creates the symlink that causes systemd to start the service on boot.

**Detection:** `systemctl is-enabled aggregator.service` — must return `enabled`, not `disabled` or `static`.

---

### Pitfall 3: Forgetting to Install Gunicorn in the Virtualenv

**What goes wrong:** Gunicorn is not in `requirements.txt` (confirmed: not present in the current `requirements.txt`). If Gunicorn is not explicitly installed in the venv, the `ExecStart` path to `.venv/bin/gunicorn` will not exist and the service will fail with `No such file or directory`.

**Prevention:** Install Gunicorn into the venv explicitly: `pip install gunicorn`. Add it to `requirements.txt` or a `requirements-server.txt` so the step is not forgotten.

**Detection:** `.venv/bin/gunicorn --version` — if this fails, Gunicorn is not installed in the venv.

---

### Pitfall 4: Git Clone Leaves the Repo in a Detached HEAD or Wrong Branch State

**What goes wrong:** The project is cloned to the VM and the service is started, but the codebase is on an old branch or a detached HEAD from a specific commit that lacks recent changes.

**Prevention:** After cloning, run `git status` and `git log --oneline -5` to confirm the expected branch and commit are checked out.

---

### Pitfall 5: .env File Has Windows-Style Line Endings (CRLF) From Windows Development

**What goes wrong:** If the `.env` file was created or edited on Windows and transferred to the VM, `\r\n` line endings cause `python-dotenv` to include the `\r` as part of the value. This causes env vars like `password\r` which do not match the expected `password`, breaking database connections with authentication errors.

**Prevention:** Use `dos2unix .env` on the VM after copying from Windows, or ensure the `.env` is created directly on the VM.

**Detection:** `cat -A .env | grep '\^M'` — the `^M` character indicates CRLF endings.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Provisioning Python venv | Wrong Python binary for venv creation | Specify Python version explicitly: `python3.10 -m venv .venv` |
| Installing dependencies | psycopg2-binary wheel missing for platform | Install `libpq-dev python3-dev gcc` before `pip install` |
| Installing dependencies | Gunicorn not in requirements.txt | Install `gunicorn` explicitly, add to requirements |
| Configuring .env on VM | Env vars missing or wrong location | Create `.env` in project root; validate with `python -c "from common.settings import get_settings; ..."` |
| Writing systemd unit | Wrong ExecStart path or missing WorkingDirectory | Use absolute venv path; set WorkingDirectory to project root |
| Writing systemd unit | Service not enabled for boot persistence | Always run `systemctl enable` not just `systemctl start` |
| Configuring Gunicorn bind | Localhost-only bind prevents remote agents | Explicit `--bind 0.0.0.0:PORT` required |
| Firewall / network | UFW blocks inbound port by default | `sudo ufw allow PORT/tcp` before testing from agents |
| Updating agents | Agents still pointing to old PythonAnywhere URL | Update `AGGREGATOR_API_URL` in every agent `.env` |
| Verifying migration | Queue accumulates but no DB writes | Check firewall, then check agent `AGGREGATOR_API_URL`, then check Gunicorn bind address |
| Worker count | Too many workers exhaust Supabase connections | Keep `--workers 2` for this project's scale and connection budget |

---

## Sources

- Project codebase inspection: `web_app/app.py`, `common/settings.py`, `common/database/db_operations.py`, `web_app/blueprints/api.py` — HIGH confidence
- `.planning/codebase/CONCERNS.md` — codebase-specific concerns, HIGH confidence
- `.planning/PROJECT.md` — project scope and constraints, HIGH confidence
- Gunicorn documentation (https://docs.gunicorn.org/en/stable/run.html) — bind address and worker configuration — MEDIUM confidence (training data, no live fetch available)
- Systemd service unit documentation (https://www.freedesktop.org/software/systemd/man/systemd.service.html) — ExecStart, WorkingDirectory, User directives — MEDIUM confidence (well-established, stable spec)
- Ubuntu UFW documentation — firewall default deny policy — MEDIUM confidence
- python-dotenv source behaviour — load_dotenv() returns False silently if no file found — MEDIUM confidence (verified against codebase usage pattern)
