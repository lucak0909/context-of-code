# Phase 1: VM Provisioning and Environment Setup - Research

**Researched:** 2026-02-24
**Domain:** Ubuntu VM setup, Python virtualenv, psycopg2/SQLAlchemy, Supabase connectivity via PostgreSQL
**Confidence:** HIGH — all findings grounded in project source code and existing VM documentation

---

## Summary

Phase 1 provisions a university-provided Ubuntu VM (Student-vm-13, IP 200.69.13.70, SSH port 2214) with the project's Python runtime, virtualenv, all dependencies from `requirements.txt`, and valid Supabase credentials in a `.env` file. The end state is confirmed by a direct database connectivity check that proves the VM can reach Supabase without any application server running.

The project already has a VM migration guide (`zTjLocalFiles/IseVm/VM_Migration_Guide.md`) and the codebase is structured so that connectivity verification is as simple as running `python -m common.database.test_connection` from the project root inside the activated venv. All required credential keys are known from the local `.env` file, and the settings module (`common/settings.py`) will raise a `ValueError` listing any missing keys at import time — making validation deterministic.

The principal risk is `psycopg2-binary` installation failing on the VM because the binary wheel may not exist for the VM's exact OS/architecture combination. The fallback is to install `psycopg2` (source build) which requires `libpq-dev` and `python3-dev` system packages. This must be planned for.

**Primary recommendation:** Follow the existing VM migration guide steps sequentially: SSH in, install system packages, clone repo, create venv, `pip install -r requirements.txt`, create `.env` by hand (SCP or `nano`), activate venv, and run the test_connection script to confirm Supabase connectivity.

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SETUP-01 | VM has Python 3.10+ with venv and all project dependencies installed | The VM access guide confirms `sudo apt install python3 python3-pip python3-venv -y` works. `python3.10` is the minimum; the VM is Ubuntu so `python3.10` or later should be available via `apt`. The `requirements.txt` is pinned and well-understood. |
| SETUP-02 | Project repository is cloned onto the VM | Repo is at `https://github.com/lucak0909/context-of-code.git` (per VM migration guide). Git is standard on Ubuntu and the VM has outbound internet access (confirmed by prior use for Supabase calls). |
| SETUP-03 | `.env` file is configured on the VM with all required credentials and settings | The exact keys are known from local `.env`: `user`, `password`, `host`, `port`, `dbname`, `AGGREGATOR_API_URL`. `common/settings.py` documents which are mandatory vs optional. SCP transfer or manual `nano` entry are both viable approaches. |
</phase_requirements>

---

## Standard Stack

### Core

| Tool/Library | Version | Purpose | Why Standard |
|---|---|---|---|
| Python 3.10 | 3.10.x | Runtime (minimum per ROADMAP success criteria) | Project pinned to 3.10+; `python3.10` is installable on Ubuntu 22.04 via `apt` without PPAs |
| `venv` (stdlib) | stdlib | Isolate project dependencies | Standard Python tool, no extra install needed, used in existing VM guide |
| `pip` | Latest in venv | Install `requirements.txt` packages | Standard, comes with venv |
| `psycopg2-binary` | pinned in requirements.txt | PostgreSQL adapter for SQLAlchemy | Pre-built binary avoids system build deps; fallback to source build if binary unavailable |
| `SQLAlchemy` | 2.0.46 (pinned) | ORM and engine for Supabase/PostgreSQL | Project uses it for all DB operations; already in requirements.txt |
| `python-dotenv` | 1.2.1 (pinned) | Load `.env` file into environment at runtime | Used by `common/settings.py` via `load_dotenv()` |

### Supporting

| Tool | Version | Purpose | When to Use |
|------|---------|---------|-------------|
| `git` | Ubuntu default | Clone repository from GitHub | Always — the recommended transfer method per the VM guide |
| `scp` | OpenSSH built-in | Transfer `.env` file from local machine to VM | Preferred over typing credentials into nano — avoids typos in sensitive values |
| `libpq-dev` | Ubuntu apt | C headers for psycopg2 source build | Only needed if `psycopg2-binary` wheel fails to install |
| `python3-dev` | Ubuntu apt | Python C extension build support | Only needed if psycopg2 source build is required |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|---|---|---|
| `python3.10` (apt) | `pyenv` to compile from source | apt is faster and reliable; pyenv is useful when apt version is wrong but adds setup complexity |
| `scp` for `.env` transfer | `nano` on VM, type manually | SCP avoids credential typos; nano works but is riskier for long secrets |
| `psycopg2-binary` | `psycopg2` (source) | Binary is faster to install; source requires system packages but is more reliable on some ARM/non-standard Ubuntu versions |

**Installation (VM setup sequence):**
```bash
# System packages
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip git -y

# Optional: only if psycopg2-binary fails
sudo apt install python3-dev libpq-dev -y

# Clone and venv
git clone https://github.com/lucak0909/context-of-code.git
cd context-of-code
python3.10 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---

## Architecture Patterns

### Project Structure (as it exists)

```
context-of-code/              # Repo root — also working directory for all commands
├── common/
│   ├── settings.py           # get_settings() — loads .env, validates required keys
│   ├── database/
│   │   ├── db_operations.py  # Database class — builds SQLAlchemy engine, all DB methods
│   │   ├── db_dataclasses.py # SQLAlchemy ORM models (User, Device, Sample, etc.)
│   │   └── test_connection.py # Standalone connectivity check — run with: python -m common.database.test_connection
│   └── ...
├── requirements.txt          # Pinned dependencies including SQLAlchemy, psycopg2-binary, Flask
├── venv/                     # Virtual environment (created during setup, gitignored)
└── .env                      # Credentials (gitignored, must be created manually on VM)
```

### Pattern 1: Settings Validation via `get_settings()`

**What:** `common/settings.py` uses `@lru_cache` and `load_dotenv()` to load the `.env` file once. It validates all required DB keys at import time and raises `ValueError` listing missing vars. This means the success criterion `python -c "from common.settings import get_settings; print(get_settings())"` will either succeed cleanly or tell you exactly which key is missing.

**When to use:** Run this command immediately after creating the `.env` file to confirm all required vars are present before attempting any database calls.

**Required `.env` keys:**
```bash
# Mandatory (raises ValueError if missing)
user=<supabase-db-user>
password=<supabase-db-password>
host=<supabase-db-host>
port=<supabase-db-port>
dbname=<supabase-db-name>

# Optional (has default: http://127.0.0.1:5000/api/ingest)
AGGREGATOR_API_URL=http://200.69.13.70:<ASSIGNED_PORT>/api/ingest
```

Note: `AGGREGATOR_API_URL` is optional for Phase 1 and can be set to the localhost default or left for Phase 5.

### Pattern 2: Database Connectivity Check

**What:** `common/database/test_connection.py` creates a `Database()` instance (which builds a SQLAlchemy engine with `NullPool`) and runs `SELECT 1` via `conn.execute(text("SELECT 1;")).scalar_one()`. Uses Supabase's session pooler connection string format with `sslmode=require`.

**Connection string built by `Database._build_database_url()`:**
```
postgresql+psycopg2://<user>:<password>@<host>:<port>/<dbname>?sslmode=require
```

The `?sslmode=require` is hardcoded — Supabase requires TLS. The `NullPool` is intentional: it avoids holding stateful connections through PgBouncer (Supabase's connection pooler).

**How to run:**
```bash
# From the repo root with venv activated:
python -m common.database.test_connection
```

### Pattern 3: SSH and File Transfer

**What:** The VM uses key-based SSH authentication only (no password). Username is always `student`. SSH port is 2214. SCP uses the same key and port.

```bash
# Connect
ssh -i ~/path/to/key student@200.69.13.70 -p 2214

# Transfer .env from local machine to VM
scp -i ~/path/to/key -P 2214 .env student@200.69.13.70:/home/student/context-of-code/.env
```

Note: `ssh` uses lowercase `-p` for port; `scp` uses uppercase `-P` for port.

### Anti-Patterns to Avoid

- **Running `python3` without activating venv:** Commands will use the system Python and miss all project dependencies. Always `source venv/bin/activate` first, or prefix with `venv/bin/python`.
- **Creating `.env` with wrong key names:** `common/settings.py` expects lowercase `user`, `password`, `host`, `port`, `dbname` — NOT `DB_USER`, `DATABASE_USER`, etc. Copy from the local `.env` key names exactly.
- **Using `git push` to transfer `.env` to VM:** `.env` is gitignored and contains secrets. It must be transferred out-of-band via `scp` or created manually.
- **Running the connectivity check from outside the venv:** `import sqlalchemy` will fail with `ModuleNotFoundError`.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---|---|---|---|
| Settings validation | Custom env-loading code | `common/settings.py` `get_settings()` — already exists | It's already written, raises clear errors, handles `lru_cache` |
| DB connectivity check | New test script | `python -m common.database.test_connection` — already exists | It creates a real engine, runs `SELECT 1`, and handles cleanup in `finally` |
| `.env` key list | Grep the codebase | Read `common/settings.py` `DB_REQUIRED_ENV_VARS` — source of truth | Prevents drift between the list you write and what the code actually needs |

**Key insight:** This phase is entirely infrastructure setup with no new code. Every verification tool already exists in the codebase — the planner should use them, not create new ones.

---

## Common Pitfalls

### Pitfall 1: `psycopg2-binary` Fails to Install

**What goes wrong:** `pip install -r requirements.txt` exits with an error on the `psycopg2-binary` line. Error message mentions "no matching distribution found" or a build error.

**Why it happens:** Pre-built binary wheels for `psycopg2-binary` may not exist for the VM's exact OS version/architecture. The VM is Ubuntu (Linux x86_64 is most likely, but unconfirmed).

**How to avoid:** If `psycopg2-binary` fails, install system build dependencies and switch to source build:
```bash
sudo apt install python3-dev libpq-dev -y
pip install psycopg2  # source build, no -binary suffix
```
This works on any Linux with the PostgreSQL client headers.

**Warning signs:** Error during `pip install -r requirements.txt` mentioning `psycopg2` specifically.

---

### Pitfall 2: Wrong Python Version Used for Venv

**What goes wrong:** `venv` created with system `python3` (which may be 3.9 or 3.8 on older Ubuntu), not `python3.10`. The success criterion explicitly checks `python3.10 --version`.

**Why it happens:** Ubuntu may have multiple Python versions installed; `python3` symlinks to the system default, not necessarily 3.10.

**How to avoid:** Always create the venv explicitly with `python3.10 -m venv venv`. Verify first with `python3.10 --version`. If not found, install it: `sudo apt install python3.10 python3.10-venv -y`.

**Warning signs:** `python3.10 --version` inside venv returns an error or version below 3.10.

---

### Pitfall 3: `.env` Key Name Mismatch

**What goes wrong:** Settings validation fails with `ValueError: Missing required env vars for DB connection: user, password` even though the `.env` file contains database credentials.

**Why it happens:** Using common conventions like `DB_USER=` or `DATABASE_USER=` instead of the bare lowercase names the code expects (`user=`, `password=`, etc.). The `DB_ENV_USER = "user"` constant in `settings.py` is the source of truth.

**How to avoid:** Copy key names directly from the local development `.env` file using `scp`, or reference `common/settings.py` `DB_REQUIRED_ENV_VARS` tuple: `("user", "password", "host", "port", "dbname")`.

**Warning signs:** `get_settings()` raises `ValueError` listing keys you thought you set.

---

### Pitfall 4: `lru_cache` Masks `.env` Changes

**What goes wrong:** After editing `.env` on the VM, re-running the settings check in the same Python process still shows stale/missing values.

**Why it happens:** `get_settings()` is decorated with `@lru_cache(maxsize=1)`. The first call caches the result; subsequent calls in the same process return the cached object.

**How to avoid:** Always restart the Python process (run a fresh `python -c "..."` command) after editing `.env`. Don't rely on re-importing within a REPL session.

**Warning signs:** Editing `.env` mid-session doesn't seem to fix missing-key errors.

---

### Pitfall 5: `scp` Port Flag vs `ssh` Port Flag

**What goes wrong:** `scp -p 2214 ...` silently does something unexpected or errors; the `.env` file never appears on the VM.

**Why it happens:** `scp` uses uppercase `-P` for port; lowercase `-p` means "preserve timestamps". This is the opposite of `ssh` which uses lowercase `-p`.

**How to avoid:**
```bash
# CORRECT: scp uses uppercase -P for port
scp -i ~/key -P 2214 .env student@200.69.13.70:/home/student/context-of-code/.env

# WRONG: lowercase -p means preserve timestamps, not port
scp -i ~/key -p 2214 .env student@200.69.13.70:/home/student/context-of-code/  # silently wrong
```

---

## Code Examples

Verified patterns from project source code:

### Settings Validation Check
```bash
# Source: common/settings.py — get_settings() validates and returns all required vars
# Run from repo root with venv activated
python -c "from common.settings import get_settings; print(get_settings())"
```
Success output: `Settings(db_user=..., db_password=..., db_host=..., db_port=..., db_name=..., aggregator_api_url=...)`
Failure output: `ValueError: Missing required env vars for DB connection: user, password`

### Database Connectivity Check
```bash
# Source: common/database/test_connection.py — runs SELECT 1 against Supabase
# Run from repo root with venv activated
python -m common.database.test_connection
```
Success output: `INFO | Connection successful.`
Failure output: `ERROR | Failed to connect.` followed by the exception.

### Full Setup Sequence (from VM_Migration_Guide.md)
```bash
# 1. SSH in
ssh -i ~/path/to/key student@200.69.13.70 -p 2214

# 2. Install system packages
sudo apt update
sudo apt install python3.10 python3.10-venv python3-pip git -y

# 3. Clone repo
git clone https://github.com/lucak0909/context-of-code.git
cd context-of-code

# 4. Create venv with Python 3.10 explicitly
python3.10 -m venv venv
source venv/bin/activate

# 5. Install dependencies
pip install -r requirements.txt

# 6. Transfer .env (run from local machine in a new terminal)
scp -i ~/path/to/key -P 2214 .env student@200.69.13.70:/home/student/context-of-code/.env

# 7. Verify settings
python -c "from common.settings import get_settings; print(get_settings())"

# 8. Verify Supabase connectivity
python -m common.database.test_connection
```

### psycopg2-binary Fallback (if wheel unavailable)
```bash
# Source: Standard Ubuntu workaround for psycopg2 source build
sudo apt install python3-dev libpq-dev -y
pip install psycopg2  # source build — no -binary suffix
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|---|---|---|
| PythonAnywhere hosting (previous) | Ubuntu VM with manual setup | This migration is the entire v1.0 milestone |
| `flask run` (dev server) | Gunicorn (Phase 2) | Phase 1 only sets up environment; no server started yet |
| `python3` generic | `python3.10` explicit | Required to satisfy ROADMAP success criterion 1 |

**Deprecated/outdated:**
- `flask run --host=0.0.0.0` for production: the VM migration guide documents this for reference, but Phase 2 adopts Gunicorn. Phase 1 does not start any server.

---

## Open Questions

1. **Does the VM have Python 3.10 available via `apt` without PPAs?**
   - What we know: VM is Ubuntu (confirmed by migration guide using `apt`). Ubuntu 22.04 ships Python 3.10 in main repos. Ubuntu 20.04 ships 3.8 and would require a PPA (`deadsnakes`).
   - What's unclear: Which Ubuntu version the VM runs.
   - Recommendation: Check `lsb_release -a` immediately after first SSH. If Ubuntu 20.04, add `deadsnakes` PPA: `sudo add-apt-repository ppa:deadsnakes/ppa`. If 22.04+, `apt install python3.10` works directly.

2. **Will `psycopg2-binary` wheel be available for the VM's architecture?**
   - What we know: `psycopg2-binary` provides pre-built wheels for Linux x86_64 on most Ubuntu versions. The VM is almost certainly x86_64.
   - What's unclear: Exact OS and architecture without SSHing in.
   - Recommendation: Attempt `pip install -r requirements.txt`; if `psycopg2-binary` fails, install `libpq-dev` + `python3-dev` and use `pip install psycopg2` (source build). Document the fallback in the plan.

3. **Is the Supabase database reachable from the VM's network?**
   - What we know: Supabase is a public cloud service; the VM has outbound internet access (cloning from GitHub implies this). The connection uses `sslmode=require`.
   - What's unclear: Whether the university network has any outbound firewall rules blocking PostgreSQL port 5432 (Supabase's transaction pooler uses 6543; session pooler uses 5432).
   - Recommendation: The connectivity test (`python -m common.database.test_connection`) will definitively answer this. If it fails with a timeout rather than an auth error, the port may be blocked. In that case, switch to Supabase's connection pooler on port 6543.

---

## Sources

### Primary (HIGH confidence)

- `/Users/tjcla/Dev/CollegeDev/context-of-code/common/settings.py` — exact required env var names, validation logic, `lru_cache` behavior
- `/Users/tjcla/Dev/CollegeDev/context-of-code/common/database/db_operations.py` — connection string format, `NullPool`, `sslmode=require`
- `/Users/tjcla/Dev/CollegeDev/context-of-code/common/database/test_connection.py` — the exact connectivity check command the planner should use
- `/Users/tjcla/Dev/CollegeDev/context-of-code/requirements.txt` — exact package list including `psycopg2-binary`, `SQLAlchemy==2.0.46`, `python-dotenv==1.2.1`
- `/Users/tjcla/Dev/CollegeDev/context-of-code/zTjLocalFiles/IseVm/VM_Migration_Guide.md` — SSH command, apt packages, venv steps, scp method, git clone URL
- `/Users/tjcla/Dev/CollegeDev/context-of-code/zTjLocalFiles/IseVm/VmConfirmationEmail.md` — VM IP (200.69.13.70), SSH port (2214), VM name (Student-vm-13)
- `/Users/tjcla/Dev/CollegeDev/context-of-code/zTjLocalFiles/IseVm/studentVMAccessGuide.md` — passwordless sudo, key-only auth, scp `-P` port flag

### Secondary (MEDIUM confidence)

- `.env` key names extracted via grep (keys only, no values) — confirms exactly 6 keys: `user`, `password`, `host`, `port`, `dbname`, `AGGREGATOR_API_URL`

### Tertiary (LOW confidence)

- Ubuntu 22.04 Python 3.10 availability via apt — assumed from common knowledge; should be confirmed with `lsb_release -a` and `apt show python3.10` on first SSH session.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — all tools are either stdlib, pinned in requirements.txt, or documented in existing VM guide
- Architecture: HIGH — project structure, required env keys, and verification commands all read directly from source code
- Pitfalls: MEDIUM — psycopg2-binary and Ubuntu version pitfalls are based on well-known patterns; specific VM behavior unconfirmed until first SSH

**Research date:** 2026-02-24
**Valid until:** 2026-04-24 (stable toolchain; revisit if VM OS or Supabase connection pooler configuration changes)
