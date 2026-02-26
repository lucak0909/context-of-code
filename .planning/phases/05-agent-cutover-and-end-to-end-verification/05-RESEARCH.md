# Phase 5: Agent Cutover and End-to-End Verification - Research

**Researched:** 2026-02-26
**Domain:** `.env` configuration management, Gunicorn port rebinding, systemd unit editing, end-to-end HTTP verification
**Confidence:** HIGH — findings based directly on reading the project source code, codebase docs, and established patterns from prior phases

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

**Rollout strategy:**
- Multiple agent machines are in use (different people's laptops)
- Each person updates their own `.env` independently — no central update
- All machines must switch on the same coordinated day (not staggered)
- No per-machine tracking required — verifying the end result is sufficient
- PythonAnywhere is NOT kept as a fallback — everyone cuts over at once

**Pre-cutover VM checks:**
- Before any agent switches, verify the VM endpoint is ready via SSH tunnel
- Test sequence: hit `/health` for 200, then send a test POST to `/api/ingest` and confirm 200/201
- SSH tunnel from laptop is the test method (established pattern from prior phases)
- A 200/201 response from the VM is sufficient — no need to verify a test Supabase row

**Verification rigor:**
- Minimum bar: one agent run that logs a 200 or 201 response, plus a new row appearing in Supabase
- Supabase checked manually via the browser dashboard (no scripted query needed)
- Evidence to capture for presentation: screenshot of new Supabase row + terminal output showing the 200/201 agent log
- Agent queue/retry behavior is unknown — researcher should investigate (see findings below)

**Fallback plan:**
- Fix forward — no revert to PythonAnywhere
- If cutover fails (wrong port, Gunicorn config issue, etc.), investigate and fix on the VM
- Failure risks are unknown — researcher should assess the most likely failure modes (see findings below)

### Claude's Discretion

- How to structure the step-by-step cutover instructions for other team members (format, medium)
- Exact curl command format for the pre-cutover test POST
- How to document that the cutover day has been coordinated (whether to note it anywhere)

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CUTOVER-01 | `AGGREGATOR_API_URL` updated on all agent machines to point to the VM | Each agent machine has a `.env` file in the repo root. The setting is loaded by `common/settings.py` via `python-dotenv`. Update the value to `http://200.69.13.70:<ASSIGNED_PORT>/api/ingest`. The `lru_cache` on `get_settings()` means the agent must be restarted after `.env` is edited. |
| CUTOVER-02 | End-to-end verified — agents successfully POST metrics that appear in Supabase | The `UploadQueue.flush()` method returns the count of successfully sent payloads. A log line "Uploaded N queued sample(s)." confirms a 200 response was received. New rows in the `samples` table in Supabase (visible in dashboard) confirm end-to-end persistence. |
</phase_requirements>

---

## Summary

Phase 5 has three distinct sub-tasks that must be done in order: (1) reconfigure Gunicorn on the VM to bind to the college-assigned external port instead of port 5000, (2) verify the VM endpoint is reachable and accepting valid POSTs via SSH tunnel, and (3) update `AGGREGATOR_API_URL` in every agent machine's `.env` and verify one successful end-to-end run.

The phase cannot begin until the college ISE admin responds with port assignments — 2 ports were requested on 2026-02-26 and the email is pending. Once the ports arrive, the Gunicorn bind address in the systemd unit file must be changed from `--bind 0.0.0.0:5000` to `--bind 0.0.0.0:<ASSIGNED_PORT>`. This requires editing the unit file, running `sudo systemctl daemon-reload`, and restarting the service. The VM `.env` does not need to change for the server side — the port is set in the ExecStart directive of the unit file, not in `.env`.

On the agent side, the change is a single `.env` line per machine. The agents use `lru_cache(maxsize=1)` on `get_settings()` which means settings are frozen at process start — every agent must be restarted after editing `.env`. The `UploadQueue._send_payload()` function only returns `True` on HTTP 200 (not 201), but the `/api/ingest` endpoint returns 200 on success, so this is not a problem. Failed payloads stay in `agent_queue.jsonl` and are retried on the next `flush()` — there is no data loss risk from a failed first attempt.

**Primary recommendation:** Wait for port assignment email. Reconfigure systemd unit to new port first. Pre-verify via SSH tunnel (health check + test POST with curl). Distribute a single-line `.env` change instruction to all team members for a coordinated cutover on one agreed day. Verify one agent run end-to-end and capture the Supabase screenshot.

---

## Standard Stack

### Core

| Component | Version/Location | Purpose | Why Standard |
|-----------|-----------------|---------|--------------|
| systemd unit file | `/etc/systemd/system/context-of-code.service` | Controls Gunicorn bind port | Already in place from Phase 4; the only change for Phase 5 is the `--bind` flag value |
| `common/settings.py` — `ENV_AGGREGATOR_API_URL` | Project source | Agent reads `AGGREGATOR_API_URL` env var | Established in the codebase; no code change needed — only a `.env` value change |
| `.env` file | Repo root on each agent machine | Holds `AGGREGATOR_API_URL` | Already used by all agents; the current value is the PythonAnywhere URL |
| `UploadQueue._send_payload()` | `agent/uploader_queue/queue.py` | Makes the HTTP POST to the aggregator | Existing implementation; uses `urllib.request`, 10s timeout, retries via JSONL queue |
| SSH tunnel | `-L <PORT>:localhost:<PORT>` pattern | Pre-cutover endpoint testing | Established pattern from Phase 2/3/4; the only way to reach the VM from outside |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `sudo systemctl daemon-reload` | Required after editing the unit file | Every time the unit file is modified |
| `sudo systemctl restart context-of-code` | Applies the new port binding | After daemon-reload; service picks up the new ExecStart |
| `journalctl -u context-of-code -n 50` | Diagnose service startup failures | If the service fails to start on the new port |
| `curl -X POST` with JSON body | Pre-cutover test POST to `/api/ingest` | Verifies the endpoint accepts valid payloads before agents are switched |

---

## Architecture Patterns

### Pattern 1: Reconfiguring Gunicorn's Bind Port (VM-side)

The Gunicorn bind port is set in the systemd unit file's `ExecStart` directive — not in `.env`. The current configuration is:

```ini
ExecStart=/home/student/context-of-code/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 5 \
    web_app.app:app
```

To rebind to an assigned port (e.g., `XXXX`):

```bash
# Step 1 — Edit the unit file
sudo nano /etc/systemd/system/context-of-code.service
# Change --bind 0.0.0.0:5000 to --bind 0.0.0.0:XXXX

# Step 2 — Reload systemd (required after any unit file edit)
sudo systemctl daemon-reload

# Step 3 — Restart the service to apply the new port
sudo systemctl restart context-of-code

# Step 4 — Verify it came up on the new port
sudo systemctl status context-of-code --no-pager
curl http://localhost:XXXX/health
```

**Critical:** `daemon-reload` is required before `restart`. Without it, systemd uses the cached old unit and the port does not change.

### Pattern 2: Pre-Cutover Endpoint Verification via SSH Tunnel

The assigned port is only reachable from outside the college network if the ISE admin has opened it at the gateway level. Before instructing agents to switch, verify this via the established SSH tunnel pattern:

```bash
# Terminal 1 — open SSH tunnel for the new port
ssh -i /Users/tjcla/.ssh/tj_vm_key \
    -L XXXX:localhost:XXXX \
    student@200.69.13.70 -p 2214

# Terminal 2 — health check
curl http://localhost:XXXX/health
# Expected: {"status": "ok", "ts": "..."} HTTP 200

# Terminal 2 — test POST to /api/ingest
curl -X POST http://localhost:XXXX/api/ingest \
    -H "Content-Type: application/json" \
    -d '{"device_id": "647fb7f6-9988-4656-b3db-49f19e834f63", "sample_type": "desktop_network", "latency_ms": 10.0, "packet_loss_pct": 0.0, "down_mbps": 100.0, "up_mbps": 50.0}'
# Expected: {"status": "ok", "sample_type": "desktop_network"} HTTP 200
```

The `device_id` `647fb7f6-9988-4656-b3db-49f19e834f63` is already used in the standalone test mode in `agent/pc_data_collector/main.py` — it exists in the development database and will pass the FK constraint. For a clean presentation, use any valid registered device UUID from the Supabase `devices` table instead.

**Note on tunnel vs direct access:** The SSH tunnel tests from Timothy's laptop only. To verify the port is accessible directly (no tunnel) from outside, a direct `curl http://200.69.13.70:XXXX/health` from any device can be attempted. If it succeeds, the college gateway has opened the port. If it fails (connection refused/timeout), the port has not yet been opened at the gateway level — in this case Timothy should contact the ISE admin to confirm the port was configured, not just assigned.

### Pattern 3: Agent `.env` Update

Each agent machine needs exactly one line changed in its `.env` file:

```bash
# Before (PythonAnywhere):
AGGREGATOR_API_URL=https://tazo.pythonanywhere.com/api/ingest

# After (VM):
AGGREGATOR_API_URL=http://200.69.13.70:XXXX/api/ingest
```

The gateway IP is `200.69.13.70` and port `XXXX` is the college-assigned external port (pending email confirmation).

**Important:** `common/settings.py` uses `@lru_cache(maxsize=1)` on `get_settings()`. This means settings are loaded once at process startup and never re-read from disk. After editing `.env`, the agent process must be fully restarted (not just a soft reload) for the new URL to take effect.

### Pattern 4: Agent Queue Retry Behavior

The `UploadQueue.flush()` in `agent/uploader_queue/queue.py` works as follows:

1. Reads all lines from `agent_queue.jsonl`
2. For each payload, calls `_send_payload()` which does `urllib.request.urlopen()` with a 10s timeout
3. `_send_payload()` returns `True` only on HTTP 200 — any other status, HTTP error, or network error returns `False`
4. Payloads where `_send_payload()` returns `False` are written back to `agent_queue.jsonl` via `_rewrite_queue()`
5. `flush()` returns the count of successfully sent payloads

**What "no queue retention" means:** When the POST succeeds (HTTP 200), the payload is removed from `agent_queue.jsonl`. If the queue is empty after a successful agent run, it means all payloads were delivered. If `agent_queue.jsonl` is non-empty (or keeps growing), payloads are being retained — indicating the POST is failing.

**Note on HTTP 200 vs 201:** The agent's `_send_payload()` only checks for HTTP 200 (`if resp.status == 200`). The `/api/ingest` endpoint in `web_app/blueprints/api.py` returns HTTP 200 on success (`return jsonify(...), 200`). There is no mismatch. If the endpoint ever returns 201, the agent would treat it as a failure and retry — but the current implementation returns 200.

**Implication for verification:** A log line `"Uploaded N queued sample(s)."` in the agent output confirms HTTP 200 was received. If the log shows `"Locally queued payload. Will retry on next flush."` (from standalone `run()` mode), it means the POST failed. In production mode (`run_with_user()`), failed POSTs are silent at INFO level — check for `WARNING` level logs showing `"Aggregator unreachable"` or `"Aggregator HTTP error"`.

### Pattern 5: Supabase Verification (Manual Dashboard Check)

After a successful agent run:
1. Open the Supabase dashboard at `https://supabase.com` and log in
2. Navigate to Table Editor → `samples` table
3. Sort by `ts` (timestamp) descending
4. A new row should appear with a timestamp matching the agent run time

The `samples` table has columns: `device_id`, `sample_type`, `ts`, `latency_ms`, `packet_loss_pct`, `down_mbps`, `up_mbps`, `test_method`, `ip`, `latency_eu_ms`, `latency_us_ms`, `latency_asia_ms`, `room_id` (from reading `web_app/blueprints/api.py` and `common/database/db_dataclasses.py`).

### Anti-Patterns to Avoid

- **Switching agents before verifying the VM endpoint:** If the VM is not ready, all agents immediately start failing and queuing. Fix the VM first, then switch agents.
- **Forgetting `daemon-reload` after editing the unit file:** The port will not change. The service will restart on port 5000 and external connections on the new port will fail.
- **Editing `.env` while the agent is running and expecting it to pick up the change:** The `lru_cache` freezes settings at startup. The agent must be restarted.
- **Testing via SSH tunnel and assuming direct access works too:** The tunnel routes through the SSH session. Direct external access depends on the college gateway opening the assigned port. Both must be tested — tunnel first, then direct.
- **Using port 5000 in the agent URL:** Port 5000 is not accessible externally. The college gateway only forwards SSH (2214→22) and the newly assigned port(s). Direct connections to port 5000 from outside the VM will always fail.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Agent retry logic | Custom retry loop around the HTTP POST | Existing `UploadQueue` JSONL queue | Already implemented; payloads stay in `agent_queue.jsonl` until a 200 is received — zero code changes needed |
| Port configuration | New env var or config file for port | Edit the systemd unit file's `ExecStart` flag | Port is already parameterized in the unit file; changing `--bind 0.0.0.0:5000` to the new port is a one-line edit |
| External reachability verification | Scripted poll loop | Manual `curl` via SSH tunnel, then without tunnel | Two curl commands answer the question; a script adds no value here |
| Supabase row verification | Scripted DB query | Supabase browser dashboard | Sufficient for the presentation; screenshot is the artifact needed |

---

## Common Pitfalls

### Pitfall 1: Port Not Open at College Gateway Level

**What goes wrong:** The ISE admin assigns a port number but the college gateway firewall rule is not yet active. Direct `curl http://200.69.13.70:XXXX/health` times out even though the service is running on that port on the VM.

**Why it happens:** The port assignment email may be separate from the gateway firewall configuration. The email confirms "you have been assigned port XXXX" but the gateway rule may take additional time to propagate.

**How to avoid:** Test via SSH tunnel first (this always works if the service is running on the port). Then test direct access from outside the tunnel. If direct access fails, contact the ISE admin to confirm the gateway rule is active — don't assume the port is open just because it was assigned.

**Warning signs:** SSH tunnel curl succeeds; direct curl times out or is refused.

---

### Pitfall 2: Gunicorn Still Running on Port 5000 After Unit File Edit

**What goes wrong:** Edit the unit file, restart the service — but the service still responds on port 5000 and not on the new port.

**Why it happens:** `daemon-reload` was skipped. systemd is still using the cached old unit file that specifies port 5000.

**How to avoid:** Always run `sudo systemctl daemon-reload` after any edit to the unit file, before restarting. The sequence is: edit → daemon-reload → restart → verify.

**Warning signs:** `curl http://localhost:5000/health` still works after a restart; `curl http://localhost:XXXX/health` returns connection refused.

---

### Pitfall 3: Agent Settings Cached from Old URL

**What goes wrong:** `.env` is updated with the new VM URL but the agent keeps posting to PythonAnywhere. Supabase rows appear on PythonAnywhere's side (old system), not from the VM.

**Why it happens:** `common/settings.py` uses `@lru_cache(maxsize=1)` on `get_settings()`. Once the agent process starts, the URL is frozen in memory. Editing `.env` while the process is running has no effect.

**How to avoid:** After updating `.env`, fully stop and restart the agent process. On macOS/Linux: `Ctrl+C` to stop, then `python -m agent` to restart. Don't assume a soft reload or signal is sufficient.

**Warning signs:** Agent logs show the old PythonAnywhere URL in warning messages; or Supabase rows do not appear with expected timestamps despite the agent running.

---

### Pitfall 4: device_id FK Constraint Failure on Test POST

**What goes wrong:** A manual `curl` test to `/api/ingest` gets back HTTP 400 or 500 with a database error about a foreign key constraint violation.

**Why it happens:** The `samples` table has a FK constraint on `device_id` linking to the `devices` table. A random UUID in the test `curl` command will not exist in the `devices` table and the insert will fail.

**How to avoid:** Use a real `device_id` that exists in the `devices` table. Options:
1. The development UUID `647fb7f6-9988-4656-b3db-49f19e834f63` (used in standalone test mode in `main.py`) — confirmed to exist in the development database
2. Look up a real device UUID in the Supabase `devices` table in the browser dashboard

**Warning signs:** The `/api/ingest` curl returns `{"error": "Internal server error while persisting sample."}` with HTTP 500, and `journalctl -u context-of-code -n 20` shows a FK violation error.

---

### Pitfall 5: HTTP 200-Only Success Check in Agent

**What goes wrong:** The VM endpoint returns an unexpected HTTP status (e.g., a temporary 503 during a restart) and payloads pile up in `agent_queue.jsonl`. The agent appears to run but no new rows appear in Supabase.

**Why it happens:** `UploadQueue._send_payload()` returns `True` only on HTTP 200. Any other status code causes the payload to be retained in the queue. If the service is mid-restart when the agent flushes, it may receive a 502 or connection refused.

**How to avoid:** Verify the service is running and healthy before starting an agent run. Check `agent_queue.jsonl` is empty (or shrinking) during the first run. The log line `"Uploaded N queued sample(s)."` is the positive confirmation.

**Warning signs:** `agent_queue.jsonl` grows in size across runs; agent logs show `"Aggregator HTTP error"` or `"Aggregator unreachable"` warnings.

---

## Code Examples

### Editing the Systemd Unit File for New Port

```bash
# On the VM via SSH:

# Step 1 — Edit the unit file
sudo nano /etc/systemd/system/context-of-code.service
# Find the line:  --bind 0.0.0.0:5000 \
# Change to:      --bind 0.0.0.0:XXXX \

# Step 2 — Reload and restart
sudo systemctl daemon-reload
sudo systemctl restart context-of-code

# Step 3 — Verify
sudo systemctl status context-of-code --no-pager
curl http://localhost:XXXX/health
# Expected: {"status": "ok", "ts": "..."} HTTP 200
```

### Pre-Cutover Test: Health Check via SSH Tunnel

```bash
# Terminal 1 — open SSH tunnel (one tunnel per port)
ssh -i /Users/tjcla/.ssh/tj_vm_key \
    -L XXXX:localhost:XXXX \
    student@200.69.13.70 -p 2214

# Terminal 2 — from laptop
curl http://localhost:XXXX/health
# Expected: {"status": "ok", "ts": "2026-..."} HTTP 200
```

### Pre-Cutover Test: Validate /api/ingest via SSH Tunnel

```bash
# Terminal 2 — from laptop (while tunnel from Terminal 1 is open)
curl -s -w "\nHTTP %{http_code}\n" \
    -X POST http://localhost:XXXX/api/ingest \
    -H "Content-Type: application/json" \
    -d '{
        "device_id": "647fb7f6-9988-4656-b3db-49f19e834f63",
        "sample_type": "desktop_network",
        "ts": "2026-02-26T12:00:00+00:00",
        "latency_ms": 10.0,
        "packet_loss_pct": 0.0,
        "down_mbps": 100.0,
        "up_mbps": 50.0,
        "test_method": "http_fallback",
        "ip": "127.0.0.1"
    }'
# Expected: {"status": "ok", "sample_type": "desktop_network"}  HTTP 200
```

### Agent `.env` Change (Each Machine)

```bash
# In repo root on each agent machine, open .env in any text editor
# Find the line:
AGGREGATOR_API_URL=https://tazo.pythonanywhere.com/api/ingest
# Replace with:
AGGREGATOR_API_URL=http://200.69.13.70:XXXX/api/ingest
```

After editing, restart the agent process (Ctrl+C and re-run).

### Direct Reachability Test (No Tunnel — From Agent Machine)

```bash
# From any laptop that is NOT on the VM (no tunnel needed):
curl -s -w "\nHTTP %{http_code}\n" http://200.69.13.70:XXXX/health
# If HTTP 200: port is open at college gateway level — agents can reach the VM directly
# If timeout/refused: gateway rule not yet active — contact ISE admin
```

---

## Failure Mode Assessment

The three most likely failure modes for this cutover, in order of probability:

### Failure Mode 1: College Gateway Port Not Yet Active (HIGHEST RISK)

**Scenario:** Port is assigned in the email, service is rebound, but direct external connections fail.
**Diagnosis:** SSH tunnel curl works; direct curl fails.
**Fix:** Contact ISE admin to confirm the gateway forwarding rule has been applied. This may take additional time after the assignment email.

### Failure Mode 2: Wrong Port in Agent `.env` (MEDIUM RISK)

**Scenario:** Agent URL uses port 5000 (forgotten to update), or uses a typo, or old URL was not replaced completely.
**Diagnosis:** Agent logs show `"Aggregator unreachable"` or the URL in warning logs still shows PythonAnywhere.
**Fix:** Correct the `.env` on that machine and restart the agent.

### Failure Mode 3: Gunicorn Not Rebound to New Port (MEDIUM RISK)

**Scenario:** Unit file was edited but `daemon-reload` was forgotten. Service restarts on port 5000 instead of the new port.
**Diagnosis:** `curl http://localhost:XXXX/health` from inside the VM fails; port 5000 still responds.
**Fix:** Run `sudo systemctl daemon-reload && sudo systemctl restart context-of-code`.

### Failure Mode 4: device_id FK Violation on Agent Run (LOW RISK — Existing Agents)

**Scenario:** An agent runs with a `device_id` that doesn't exist in the `devices` table (e.g., new machine that hasn't registered). The POST succeeds (HTTP 200 from the queue's perspective — wait, no: the `/api/ingest` endpoint returns 500 on DB error).
**Diagnosis:** Supabase rows don't appear; agent logs show HTTP 500 or the queue grows.
**Fix:** Ensure the agent has properly registered via `run_with_user()` (which calls `get_or_create_device()`) rather than the standalone `run()` function with a hardcoded UUID.

---

## Phase Sequencing (What Order to Plan Things)

This phase needs two plans:

**Plan 01 — VM Port Rebinding:**
- Prerequisite: Port assignment email received
- Task: Edit systemd unit file to bind to assigned port, reload, restart, verify health responds on new port
- Done when: `curl http://localhost:XXXX/health` returns 200 from inside the VM
- Also verify direct external access: `curl http://200.69.13.70:XXXX/health` from outside

**Plan 02 — Agent Cutover and End-to-End Verification:**
- Prerequisite: Plan 01 complete (VM accepting connections on new port)
- Task 1: Pre-cutover endpoint test via SSH tunnel (health + test POST)
- Task 2: Coordinate and distribute `.env` update instructions to all team members
- Task 3: Run one agent and verify logs show "Uploaded N queued sample(s)."
- Task 4: Check Supabase dashboard for new rows; screenshot for presentation
- Done when: New Supabase row visible with timestamp matching the agent run

---

## Open Questions

1. **Which port number will be assigned?**
   - What we know: 2 ports were requested 2026-02-26. Port assignments come via email from ISE admin.
   - What's unclear: The actual port number(s). All plan steps use `XXXX` as a placeholder.
   - Recommendation: Plans must be written with the placeholder and filled in once the email arrives. Do not begin Plan 01 until the port number is known.

2. **Is the assigned port also opened at the college gateway, or just assigned?**
   - What we know: The college gateway controls external port access. The ISE port request form says the email will notify of assigned ports.
   - What's unclear: Whether the email implies the gateway rule is already active, or whether that requires a separate step.
   - Recommendation: After rebinding Gunicorn, test both via SSH tunnel AND direct external curl. If direct fails, follow up with ISE admin.

3. **Does the VM's `.env` (on the server) need `AGGREGATOR_API_URL` updated?**
   - What we know: The server's `.env` is loaded by the Flask app via `EnvironmentFile` in the systemd unit. The server does NOT use `AGGREGATOR_API_URL` — only agents do. The server reads DB credentials from `.env`.
   - What's unclear: Nothing — this is clear. The server `.env` does not need the `AGGREGATOR_API_URL` variable.
   - Recommendation: No change to the VM's `.env`. Only the agent machines' `.env` files need updating.

4. **How many agent machines need to be updated?**
   - What we know: "Multiple agent machines (different people's laptops)" — each person updates their own `.env` independently. No per-machine tracking required.
   - What's unclear: The exact count and whether all team members are available on the same day.
   - Recommendation: Plan 02 should include a brief coordination step — agree on a cutover day and send the one-line `.env` change to all teammates before that day.

---

## Sources

### Primary (HIGH confidence)

- `agent/uploader_queue/queue.py` — read directly; confirms `_send_payload()` checks HTTP 200 only, JSONL retry behavior
- `agent/pc_data_collector/main.py` — read directly; confirms `UploadQueue()` reads `AGGREGATOR_API_URL` from settings, `lru_cache` freeze behavior
- `common/settings.py` — read directly; confirms `@lru_cache(maxsize=1)` on `get_settings()`, `AGGREGATOR_API_URL` default, `load_dotenv()` at call time
- `web_app/blueprints/api.py` — read directly; confirms `/api/ingest` returns HTTP 200 on success
- `web_app/app.py` — read directly; confirms Flask app structure and route registration
- `.env` (repo root) — read directly; confirms current `AGGREGATOR_API_URL=https://tazo.pythonanywhere.com/api/ingest`
- `.planning/phases/04-systemd-service/04-01-SUMMARY.md` — confirms current systemd unit binds to `0.0.0.0:5000`, UFW disabled, `--workers 5`
- `.planning/STATE.md` — confirms Phase 4 complete, port assignment pending, UFW disabled (Petr ran `sudo ufw disable`)
- `zTjLocalFiles/IseVm/ssh-tunnel-notes.md` — confirms tunnel pattern, gateway IP `200.69.13.70`, SSH port 2214
- `.planning/codebase/ARCHITECTURE.md` + `INTEGRATIONS.md` — confirms data flow, queue retry behavior documentation

### Secondary (MEDIUM confidence)

- `.planning/codebase/STACK.md` — environment variable list (cross-referenced against settings.py source)
- `zTjLocalFiles/uploader_queue_refactor_walkthrough.md` — confirms "offline-safe" design intent

---

## Metadata

**Confidence breakdown:**
- Port rebinding procedure: HIGH — based on established pattern from Phase 4 systemd research; unit file structure is known
- Agent `.env` update: HIGH — read directly from source code; `lru_cache` behavior is standard Python, confirmed in settings.py
- Queue retry behavior: HIGH — read directly from `queue.py` source
- College gateway port activation timing: LOW — unknown; depends on ISE admin process; flagged as open question

**Research date:** 2026-02-26
**Valid until:** 2026-03-26 (stable domain; only invalidated if codebase changes or port numbers change)
