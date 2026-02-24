# Technology Stack — VM Migration Additions

**Project:** Context of Code — v1.0 VM Migration
**Researched:** 2026-02-24
**Scope:** Deployment additions only. Existing stack (Flask 3.1.2, SQLAlchemy 2.0.46, psycopg2-binary, python-dotenv) is unchanged.

---

## What Changes

The existing application code does not change. Only the **execution environment** changes:

| Before (PythonAnywhere) | After (Ubuntu VM) |
|-------------------------|-------------------|
| Flask dev server | Gunicorn WSGI server |
| PythonAnywhere process management | systemd service unit |
| PythonAnywhere Python environment | System venv at `/opt/context-of-code/venv/` |
| PythonAnywhere config UI | `.env` file on VM filesystem |

---

## New Package: Gunicorn

### Why Gunicorn

Flask's documentation explicitly states the built-in dev server "is not suitable for production use." Gunicorn is the standard sync WSGI server for Flask in production. It is:

- A pre-fork multi-worker model — no async complexity
- Directly compatible with Flask's WSGI interface
- Compatible with systemd socket activation and process supervision
- The standard choice for Flask + Ubuntu deployments

The existing `app = Flask(__name__)` in `web_app/app.py` is already in the correct format for Gunicorn (`web_app.app:app`). No code changes needed.

### Version

**Recommended:** `gunicorn>=21.2.0`

The 21.x line (released 2023) is the current stable series as of my knowledge cutoff (August 2025). Gunicorn 20.x is the previous LTS-style release still widely used.

**Confidence: MEDIUM** — Based on training data. Verify current version before pinning:

```bash
pip index versions gunicorn
# or check: https://pypi.org/project/gunicorn/
```

Pin to a specific version in requirements once verified. Example: `gunicorn==21.2.0`

### Workers

For a single-machine Flask aggregator receiving infrequent POSTs from a small number of agents:

```
workers = (2 * CPU_cores) + 1
```

For a typical 1-2 core VM: **3 workers** is correct. This allows concurrent ingest requests without over-provisioning.

**Worker type:** Default `sync` workers. No async needed — this app is I/O light, uses `NullPool` for database connections (each worker gets its own connection per request), and has no streaming or long-poll patterns.

**Critical note on NullPool:** The existing `Database` class uses SQLAlchemy `NullPool`. This means each request opens and closes its own database connection. This is correct for multi-worker Gunicorn — no shared connection state across workers. No pool configuration changes needed.

---

## System Packages (apt)

These must be installed on the Ubuntu VM before the Python venv is created.

```bash
sudo apt update
sudo apt install -y \
    python3.10 \
    python3.10-venv \
    python3.10-dev \
    python3-pip \
    libpq-dev \
    build-essential \
    git
```

| Package | Why Required |
|---------|-------------|
| `python3.10` | Matches existing codebase Python version |
| `python3.10-venv` | Provides `venv` module (not always included by default on Ubuntu) |
| `python3.10-dev` | C headers needed for compiling Python extensions (psycopg2 fallback, some pip builds) |
| `python3-pip` | Bootstrap pip (used to install pip into the venv) |
| `libpq-dev` | PostgreSQL client headers — required if `psycopg2` (non-binary) is ever used; harmless to install regardless |
| `build-essential` | C compiler toolchain — required by some pip packages that compile native extensions |
| `git` | Clone the repository onto the VM |

**Note on `python3.10` availability:** Ubuntu 22.04 ships Python 3.10 as the default. Ubuntu 24.04 ships Python 3.12 by default — on 24.04, `python3.10` requires the `deadsnakes` PPA or use Python 3.12 (compatible with this codebase). Either is fine.

**Confidence: HIGH** — Standard Ubuntu system package requirements for Python + PostgreSQL deployments.

---

## Python Virtual Environment

### Location

```
/opt/context-of-code/venv/
```

Use `/opt/` (not the user's home directory) because the systemd service will run as a dedicated system user. This keeps the project self-contained and independent of any user session.

### Creation

```bash
python3.10 -m venv /opt/context-of-code/venv
```

### Activation for pip installs

```bash
/opt/context-of-code/venv/bin/pip install --upgrade pip
/opt/context-of-code/venv/bin/pip install -r /opt/context-of-code/requirements.txt
/opt/context-of-code/venv/bin/pip install gunicorn==21.2.0
```

Do not activate the venv with `source activate` for install steps — use absolute paths to the venv's pip/python. This avoids path confusion when scripting setup.

### Do not add Gunicorn to requirements.txt

`requirements.txt` is shared across all deployment targets including developer machines. Gunicorn is a production server — developers don't need it. Install it separately on the VM only.

**Alternative if pinning is needed:** Create a `requirements.prod.txt` with just `gunicorn==21.2.0` and install both files on the VM.

**Confidence: HIGH** — Standard Python venv best practice.

---

## systemd Service

Gunicorn itself is not a daemon — it runs in the foreground. systemd manages the process lifecycle: start on boot, restart on crash, log to journald.

### Service user

Create a dedicated system user with no login shell:

```bash
sudo useradd --system --no-create-home --shell /usr/sbin/nologin context-of-code
sudo chown -R context-of-code:context-of-code /opt/context-of-code/
```

### Unit file location

```
/etc/systemd/system/context-of-code.service
```

### Gunicorn command for the service

```
/opt/context-of-code/venv/bin/gunicorn \
    --workers 3 \
    --bind 0.0.0.0:5000 \
    --access-logfile - \
    --error-logfile - \
    web_app.app:app
```

- `--bind 0.0.0.0:5000` — bind on all interfaces at port 5000 (no Nginx proxy, so direct bind)
- `--access-logfile -` / `--error-logfile -` — send logs to stdout/stderr, systemd captures them to journald
- `web_app.app:app` — Python module path to the Flask app object (matches `web_app/app.py` → `app = Flask(...)`)
- Working directory must be set to `/opt/context-of-code/` so Python module imports resolve correctly

**Confidence: HIGH** — Standard Gunicorn + systemd pattern, directly compatible with this codebase's module structure.

---

## Environment Variables (.env on VM)

The existing `python-dotenv` dependency handles `.env` loading via `common/settings.py`. The same `.env` approach works on the VM.

### Location

```
/opt/context-of-code/.env
```

### Required variables (from existing codebase)

```bash
user=<supabase-db-user>
password=<supabase-db-password>
host=<supabase-host>
port=5432
dbname=<db-name>
AGGREGATOR_API_URL=http://<vm-ip>:5000/api/ingest
```

### File permissions

```bash
sudo chmod 600 /opt/context-of-code/.env
sudo chown context-of-code:context-of-code /opt/context-of-code/.env
```

Only the service user should be able to read database credentials.

**Confidence: HIGH** — Direct use of existing dotenv pattern, no changes to application code.

---

## What NOT to Add

| Package | Why Not |
|---------|---------|
| Nginx | Out of scope (PROJECT.md decision). Internal API, no domain, no static files. Adds config complexity with no benefit at this scale. |
| Certbot / SSL | Out of scope. No domain provisioned. Can be added later. |
| supervisor | systemd is the right tool for process supervision on Ubuntu. supervisor is redundant when systemd is available and adds another daemon. |
| uWSGI | More complex than Gunicorn with no benefit for a sync Flask app. Gunicorn is the simpler, better-supported choice. |
| gevent / eventlet workers | Not needed. Sync workers handle this workload. Async workers introduce concurrency bugs with the existing SQLAlchemy NullPool pattern. |
| Docker | Overkill for a single-service college project. Adds image build/registry complexity. systemd is the direct equivalent for this scope. |
| Flask-Script / Flask-CLI runner | Gunicorn replaces the dev server entirely. No custom runner needed. |
| Waitress | Windows-native WSGI server. Not appropriate for Ubuntu. |

---

## Complete Installation Sequence

```bash
# 1. System packages
sudo apt update
sudo apt install -y python3.10 python3.10-venv python3.10-dev python3-pip libpq-dev build-essential git

# 2. Create system user
sudo useradd --system --no-create-home --shell /usr/sbin/nologin context-of-code

# 3. Clone repo
sudo git clone <repo-url> /opt/context-of-code
sudo chown -R context-of-code:context-of-code /opt/context-of-code

# 4. Create venv and install dependencies
sudo /usr/bin/python3.10 -m venv /opt/context-of-code/venv
sudo /opt/context-of-code/venv/bin/pip install --upgrade pip
sudo /opt/context-of-code/venv/bin/pip install -r /opt/context-of-code/requirements.txt
sudo /opt/context-of-code/venv/bin/pip install gunicorn==21.2.0  # verify version first

# 5. Create .env file
sudo nano /opt/context-of-code/.env  # add credentials
sudo chmod 600 /opt/context-of-code/.env
sudo chown context-of-code:context-of-code /opt/context-of-code/.env

# 6. Create systemd unit (see ARCHITECTURE.md or milestone tasks)
# 7. systemctl enable --now context-of-code
```

---

## Confidence Assessment

| Area | Confidence | Source |
|------|------------|--------|
| Gunicorn version (21.x) | MEDIUM | Training data (Aug 2025 cutoff). Verify: `pip index versions gunicorn` |
| Gunicorn + Flask compatibility | HIGH | Official Flask docs explicitly recommend Gunicorn |
| NullPool = safe for multi-worker | HIGH | SQLAlchemy docs: NullPool opens/closes per-request, no shared state |
| `web_app.app:app` entry point | HIGH | Direct inspection of `web_app/app.py` — `app` is module-level |
| systemd unit pattern | HIGH | Standard Ubuntu service management pattern |
| apt packages required | HIGH | Standard Ubuntu Python + PostgreSQL dev setup |
| venv at /opt/ | HIGH | Conventional location for system-level Python services |
| No Nginx needed | HIGH | PROJECT.md explicit decision with documented rationale |

---

## Sources

- Flask documentation: "Do not use the development server in production" — https://flask.palletsprojects.com/en/stable/deploying/
- Gunicorn documentation — https://docs.gunicorn.org/en/stable/
- SQLAlchemy NullPool documentation — https://docs.sqlalchemy.org/en/20/core/pooling.html#sqlalchemy.pool.NullPool
- PROJECT.md — documented decisions: Gunicorn over dev server, no Nginx, systemd over manual process management
- `web_app/app.py` — direct codebase inspection confirming `app = Flask(__name__)` module-level object
- `common/database/db_operations.py` via ARCHITECTURE.md — confirmed NullPool usage
