# Phase 4: Systemd Service - Research

**Researched:** 2026-02-25
**Domain:** systemd service unit files, UFW firewall, Ubuntu process management
**Confidence:** HIGH — core findings verified against official systemd docs, systemd.io, and DigitalOcean Ubuntu guides

---

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions

- Keep it as simple and readable as possible while satisfying best practices
- No over-engineering; a clear, standard unit file that anyone familiar with systemd can follow
- Run as the deploy/app user (whoever owns the app files), not root. Avoid creating a new system user unless required — keep it simple.
- Restart=on-failure (restart on crash, not on intentional stop)
- UFW: open port 5000 to all (not IP-restricted)
- Logging: journald is fine — no extra log file setup needed

### Claude's Discretion

- Exact unit file directives (WorkingDirectory, ExecStart path construction, etc.)
- Whether to add WantedBy, After, and other ordering directives (use standard best practices)
- RestartSec and attempt limits: follow standard defaults
- How to pass environment variables: prefer approach already used in project (EnvironmentFile pointing to existing .env)
- UFW rule syntax details

### Deferred Ideas (OUT OF SCOPE)

None — discussion stayed within phase scope.
</user_constraints>

---

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| SRV-02 | Systemd service unit starts the aggregator on boot and restarts it on crash | `[Install] WantedBy=multi-user.target` + `systemctl enable` handles boot start. `Restart=on-failure` handles crash restart. `ExecStart` wraps the confirmed Gunicorn invocation from Phase 2. |
| SRV-03 | Firewall (UFW) permits inbound traffic on the aggregator port | UFW is confirmed inactive on this VM (resolved in Phase 2). The phase must add `sudo ufw allow 5000/tcp` and then either leave UFW inactive (port already accessible) or enable it. Context decision: open port 5000, no IP restriction. |
</phase_requirements>

---

## Summary

Phase 4 is pure OS-level service management — no application code changes. The work splits cleanly into two independent tasks: (1) write and activate a systemd unit file that manages Gunicorn as a managed service, and (2) ensure UFW allows inbound traffic on port 5000.

The Gunicorn invocation is locked in from Phase 2: `gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app` from `/home/student/context-of-code` with the venv active. The systemd unit wraps this exactly, using the absolute venv binary path (`/home/student/context-of-code/venv/bin/gunicorn`) instead of PATH-relative invocation. The project's `.env` file uses a plain `key=value` format that is directly compatible with systemd's `EnvironmentFile` directive — no format translation needed.

UFW is currently inactive on the VM (confirmed in Phase 2, Plan 01). Port 5000 is already accessible without a firewall rule. However, SRV-03 requires the firewall to explicitly permit port 5000 — the correct approach is to add the rule (`sudo ufw allow 5000/tcp`) regardless of whether UFW is active. If UFW is enabled in the future, the rule will be in place. Importantly, before enabling UFW the SSH port (2214) must be allowed first to avoid lockout.

**Primary recommendation:** Write a minimal, well-commented systemd unit file at `/etc/systemd/system/context-of-code.service` using `Restart=on-failure`, `EnvironmentFile` pointing to the project `.env`, and `ExecStart` using the absolute venv gunicorn path. Add the UFW rule for port 5000. `systemctl enable --now context-of-code` activates everything.

---

## Standard Stack

### Core

| Tool | Version | Purpose | Why Standard |
|------|---------|---------|--------------|
| systemd service unit | Ubuntu 22.04 built-in | Manage Gunicorn as a managed OS service | Native Ubuntu process manager; handles start-on-boot, restart-on-crash, dependency ordering, journald logging |
| `/etc/systemd/system/` | — | Location for local admin-created unit files | This directory takes precedence over package-installed units; correct location for custom services |
| `venv/bin/gunicorn` (absolute path) | 25.1.0 | ExecStart binary | Absolute path bypasses PATH; systemd runs in a minimal environment where PATH may not include the venv |
| UFW | Ubuntu 22.04 built-in | Firewall rule management | Ubuntu's standard firewall frontend; `sudo ufw allow 5000/tcp` is the idiomatic command |

### Supporting

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `systemctl daemon-reload` | Reload systemd after unit file changes | Required every time the unit file is edited; forgetting this causes systemd to use a stale version |
| `systemctl enable --now` | Enable for boot + immediately start | Combines `enable` (autostart) and `start` (immediate) in one command — use for initial activation |
| `journalctl -u context-of-code -f` | Follow service logs | Primary diagnostic tool; replaces manual log files since we use journald |
| `systemctl status context-of-code` | Check service state | Shows Active status, last few log lines, PID — the first check after any change |

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| `Restart=on-failure` | `Restart=always` | `always` restarts even after `systemctl stop` — bad for controlled stops. `on-failure` is correct for web services: restart on crash, respect intentional shutdown. |
| `EnvironmentFile` pointing to `.env` | Inline `Environment=KEY=VALUE` per variable | Inline duplicates secrets in the unit file and requires editing the unit to update. `EnvironmentFile` is cleaner and keeps secrets in one place. |
| `After=network.target` | `After=network-online.target` | `network-online.target` adds boot delay and is NOT recommended for server software by systemd.io: "network server software should generally not pull this in." `network.target` is correct. |
| Absolute path `venv/bin/gunicorn` | `ExecStart=/bin/bash -c "source venv/bin/activate && gunicorn ..."` | Shell wrapper is fragile; absolute path is the recommended pattern per all authoritative sources. |

---

## Architecture Patterns

### Unit File Location

```
/etc/systemd/system/
└── context-of-code.service     # The unit file (created in this phase)
```

```
/home/student/context-of-code/
├── venv/
│   └── bin/
│       └── gunicorn            # Absolute path used in ExecStart
├── web_app/
│   └── app.py                  # WSGI entry: web_app.app:app
└── .env                        # Loaded via EnvironmentFile directive
```

### Pattern 1: Standard Systemd Unit File for Gunicorn + Flask

**What:** A minimal, readable unit file covering all three required sections.

**Source:** Synthesized from Miguel Grinberg's Flask+systemd guide (miguelgrinberg.com) and official systemd.service(5) man page (freedesktop.org), cross-referenced with the confirmed project Gunicorn invocation from Phase 2.

```ini
[Unit]
Description=Context of Code - Gunicorn aggregator
After=network.target

[Service]
User=student
WorkingDirectory=/home/student/context-of-code
EnvironmentFile=/home/student/context-of-code/.env
ExecStart=/home/student/context-of-code/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    web_app.app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

**Key decisions in this unit:**
- `User=student` — runs as the deploy user (owns the files), not root
- `WorkingDirectory` — must be repo root so `web_app` resolves as a package (proven in Phase 2)
- `EnvironmentFile` — loads `.env` key=value pairs; systemd natively supports this format
- `ExecStart` — absolute path to venv gunicorn, same flags as Phase 2 foreground verification
- `Restart=on-failure` — locked by user decision
- `RestartSec=5` — 5-second delay before restart attempts (default 100ms is too fast for crash loops)
- `After=network.target` — correct ordering for a server that binds to 0.0.0.0 (does not need network-online.target)
- `WantedBy=multi-user.target` — standard target; enables the service when the system reaches the normal multi-user state (i.e., on boot)

### Pattern 2: UFW Rule for Port 5000

**What:** Adding a firewall rule regardless of whether UFW is currently active.

```bash
# Add the rule (idempotent — safe to run even if rule exists)
sudo ufw allow 5000/tcp

# Verify the rule is registered
sudo ufw status
```

**Critical ordering for enabling UFW (if needed):**
```bash
# MUST do this BEFORE ufw enable — SSH is on non-standard port 2214
sudo ufw allow 2214/tcp

# Then add app port
sudo ufw allow 5000/tcp

# Only then enable (will persist across reboots)
sudo ufw enable

# Confirm
sudo ufw status
```

**Why the ordering matters:** UFW blocks all inbound traffic when enabled. The VM uses SSH on port 2214 (non-standard). Enabling UFW without the SSH rule locks out the session permanently.

### Pattern 3: Systemctl Activation Sequence

```bash
# After creating/editing the unit file
sudo systemctl daemon-reload

# Enable for boot AND start now (combined command)
sudo systemctl enable --now context-of-code

# Verify it came up
sudo systemctl status context-of-code
```

Expected status output when healthy:
```
● context-of-code.service - Context of Code - Gunicorn aggregator
   Loaded: loaded (/etc/systemd/system/context-of-code.service; enabled; ...)
   Active: active (running) since ...
 Main PID: XXXX (gunicorn)
```

### Pattern 4: Workers — nproc Before Committing

The unit file above uses `--workers 2` (same as Phase 2). Before finalizing the unit, run `nproc` on the VM to confirm the vCPU count:

```bash
nproc
# If output is 1: use --workers 3  (formula: (2*1)+1 = 3)
# If output is 2: use --workers 5  (formula: (2*2)+1 = 5)
```

The STATE.md blocker specifically calls this out: "confirm before writing systemd unit; start at 2-3 workers (use `nproc` on VM when writing Phase 4 systemd unit)."

### Anti-Patterns to Avoid

- **Using `ExecStart=gunicorn ...` (relative binary):** systemd runs services in a stripped environment. PATH does not include the venv. The gunicorn binary will not be found or (worse) the system gunicorn will run without the project packages. Always use the absolute venv path.
- **Forgetting `systemctl daemon-reload` after editing the unit file:** systemd caches unit definitions. Without daemon-reload, your edits are invisible and the old version runs.
- **Enabling UFW before allowing SSH on port 2214:** Immediate and unrecoverable lockout from the VM.
- **Running as root:** `User=root` in the unit file runs application code as root. Any security vulnerability in the app becomes a root-level exploit. The `student` user owns the files and is correct.
- **Using `Environment=` for each .env variable:** The project `.env` exists and has the right format. Duplicating variables in the unit file creates a maintenance burden and means secrets live in two places.
- **Using `Restart=always` instead of `Restart=on-failure`:** `always` restarts even after `systemctl stop context-of-code`, which prevents controlled maintenance windows and is explicitly against the user's decision.

---

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Process supervision | Custom bash loop or cron-based restart | systemd `Restart=on-failure` | Handles PID tracking, signal routing, log aggregation, boot ordering automatically |
| Log rotation/capture | Writing Gunicorn logs to a file and configuring logrotate | journald (default when no `--log-file` is passed to Gunicorn) | journald captures stdout/stderr automatically; `journalctl -u context-of-code` provides structured, rotated logs with no configuration |
| Boot ordering | Custom `/etc/rc.local` or init.d script | `WantedBy=multi-user.target` in `[Install]` | systemd handles dependency resolution, ordering, and parallel startup automatically |
| Environment loading | Custom script that sources `.env` before launching gunicorn | systemd `EnvironmentFile=` directive | Native feature; reads `key=value` format (exact format the project's `.env` already uses) |

**Key insight:** This phase writes a single ~15-line text file and runs four shell commands. Zero custom logic needed — every requirement is a built-in systemd or UFW feature.

---

## Common Pitfalls

### Pitfall 1: Absolute Path for ExecStart is Mandatory

**What goes wrong:** The service fails to start with `(code=exited, status=203/EXEC)` or `No such file or directory`.

**Why it happens:** systemd executes ExecStart directly without a shell. It does not search PATH. If `ExecStart=gunicorn ...` is used (no path), systemd cannot find the binary. If `ExecStart=/usr/bin/gunicorn ...` is used (system path), the system Gunicorn runs without the venv packages and fails with `ModuleNotFoundError: No module named 'flask'`.

**How to avoid:** Always use the full absolute path to the venv binary: `ExecStart=/home/student/context-of-code/venv/bin/gunicorn ...`

**Warning signs:** `status=203/EXEC` in `systemctl status` output means binary not found. `ModuleNotFoundError` in `journalctl -u context-of-code` means wrong gunicorn binary.

---

### Pitfall 2: daemon-reload Not Run After Unit File Changes

**What goes wrong:** You edit the unit file (fix a typo, adjust workers), then `systemctl restart` — but the old behavior persists. Confusing because the unit file on disk looks correct.

**Why it happens:** systemd parses and caches unit files at load time. Editing the file on disk does not automatically update systemd's in-memory state.

**How to avoid:** Run `sudo systemctl daemon-reload` after every edit to the unit file, before `systemctl start/restart`.

**Warning signs:** `systemctl status` shows `Loaded: loaded (...)` with a timestamp that predates your edit.

---

### Pitfall 3: WorkingDirectory Wrong or Missing

**What goes wrong:** Gunicorn starts but exits immediately with `ModuleNotFoundError: No module named 'web_app'`.

**Why it happens:** Without `WorkingDirectory=/home/student/context-of-code`, systemd uses `/` as the working directory. Python's module resolution cannot find `web_app` as a package from `/`.

**How to avoid:** Set `WorkingDirectory=/home/student/context-of-code` in `[Service]`. This matches the Phase 2 pattern that was verified to work.

**Warning signs:** `ModuleNotFoundError: No module named 'web_app'` in `journalctl -u context-of-code`.

---

### Pitfall 4: EnvironmentFile Format Incompatibility

**What goes wrong:** Service starts but crashes because environment variables are not loaded or are malformed.

**Why it happens:** systemd `EnvironmentFile` expects bare `KEY=VALUE` per line (no `export`, no shell variable expansion, no quotes unless quoting is intentional). This project's `.env` uses bare `key=value` format (e.g., `user=postgres.vkfy...`) — this IS compatible. However, if anyone adds `export FOO=bar` or `FOO="$(command)"` to the `.env`, systemd will fail.

**How to avoid:** The existing `.env` format is directly compatible. No modification needed. Confirm with `cat .env` that all lines are bare `key=value`. Document that the `.env` must stay in this format.

**Warning signs:** `Failed to load environment files` in journalctl or `systemctl status` output.

---

### Pitfall 5: Crash Loop From Fast Restart

**What goes wrong:** A bad config causes Gunicorn to crash immediately, systemd restarts it instantly (default 100ms), it crashes again — systemd hits the start limit and gives up with `start request repeated too quickly`.

**Why it happens:** Default `RestartSec=100ms` is fast enough to trigger `StartLimitBurst` (5 attempts in 10 seconds by default) before you can diagnose the problem.

**How to avoid:** Set `RestartSec=5` in the unit file. This gives a 5-second window between restart attempts and makes crash loops visible in logs before the limit is hit.

**Warning signs:** `journalctl -u context-of-code` shows rapid repeated startup messages; `systemctl status` shows `(Result: start-limit-hit)`.

---

### Pitfall 6: UFW Enable Lockout (SSH on Non-Standard Port)

**What goes wrong:** `sudo ufw enable` is run before adding the SSH rule. All SSH connections are immediately terminated. The VM becomes inaccessible.

**Why it happens:** UFW blocks all inbound traffic by default when enabled. Port 2214 (the SSH port on this VM) is not a standard port and is not covered by the default SSH profile.

**How to avoid:** If UFW is going to be enabled, ALWAYS add the SSH rule first: `sudo ufw allow 2214/tcp`. Then add the app rule. Then enable. Verify with `sudo ufw status` before `sudo ufw enable`.

**Note:** UFW is currently inactive on this VM (confirmed in Phase 2). SRV-03 only requires the port to be permitted — adding `sudo ufw allow 5000/tcp` satisfies this even without enabling UFW. The rule is stored and will take effect if UFW is ever enabled later.

**Warning signs:** Any time you're about to run `sudo ufw enable`, stop and verify SSH is allowed first.

---

## Code Examples

Verified patterns from official sources and project-specific context:

### Complete Unit File (Project-Specific)

```ini
# /etc/systemd/system/context-of-code.service
# Source: Pattern from miguelgrinberg.com + official systemd.service(5) man page
#         + project-specific paths confirmed in Phase 2

[Unit]
Description=Context of Code - Gunicorn aggregator
After=network.target

[Service]
User=student
WorkingDirectory=/home/student/context-of-code
EnvironmentFile=/home/student/context-of-code/.env
ExecStart=/home/student/context-of-code/venv/bin/gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 2 \
    web_app.app:app
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Note: `--workers 2` is a placeholder pending `nproc` on the VM. Update to `(2 * nproc_output) + 1` before writing the file.

### Activation Sequence (on VM)

```bash
# 1. Write the unit file (sudo required — /etc/systemd/system is root-owned)
sudo nano /etc/systemd/system/context-of-code.service
# (or copy via scp / heredoc)

# 2. Reload systemd to pick up the new file
sudo systemctl daemon-reload

# 3. Enable (autostart on boot) and start now
sudo systemctl enable --now context-of-code

# 4. Verify it's running
sudo systemctl status context-of-code
# Expected: Active: active (running)
```

### Crash Recovery Verification

```bash
# Find the main Gunicorn PID
systemctl status context-of-code | grep "Main PID"

# Kill the process
sudo kill <PID>

# Wait ~5-10 seconds (RestartSec=5), then check
sudo systemctl status context-of-code
# Expected: Active: active (running) — with a new PID and a restart count
```

### Log Inspection

```bash
# Follow live logs
journalctl -u context-of-code -f

# Last 50 lines
journalctl -u context-of-code -n 50

# Since last boot
journalctl -u context-of-code -b
```

### UFW Commands (safe sequence)

```bash
# Add rule for app port (always safe to run; does not enable UFW)
sudo ufw allow 5000/tcp

# Verify the rule is registered
sudo ufw status

# If enabling UFW in the future (not required for SRV-03):
# Step 1: allow SSH on the non-standard port FIRST
sudo ufw allow 2214/tcp
# Step 2: add app port
sudo ufw allow 5000/tcp
# Step 3: verify both rules are listed
sudo ufw status
# Step 4: enable
sudo ufw enable
```

### Health Check After Service Start

```bash
# From an agent machine (not the VM) — same test pattern as Phase 2/3
curl http://200.69.13.70:5000/health
# Expected: {"status": "ok", "ts": "..."}  HTTP 200
```

---

## State of the Art

| Old Approach | Current Approach | Notes |
|---|---|---|
| Upstart (`/etc/init/`) | systemd (`/etc/systemd/system/`) | Ubuntu switched from Upstart to systemd in 15.04 (2015). Upstart tutorials are obsolete. All Ubuntu 22.04 service management uses systemd. |
| `start on runlevel [2345]` (Upstart syntax) | `WantedBy=multi-user.target` (systemd) | Equivalent concept, different syntax. Any tutorial using Upstart syntax is inapplicable. |
| `iptables` rules for firewall | `ufw` commands | UFW wraps iptables. Direct iptables manipulation is rarely needed on Ubuntu. |
| `Restart=always` (common older tutorials) | `Restart=on-failure` (best practice for web services) | `always` prevents controlled stops; `on-failure` correctly distinguishes crashes from intentional shutdowns. |

**Deprecated/outdated:**
- Upstart configuration guides: obsolete on Ubuntu 22.04; ignore entirely
- `sudo service context-of-code start` (SysV-style): still works as a compatibility shim but `systemctl` is the correct interface
- `Environment="PATH=/path/to/venv/bin"` approach: some older tutorials set PATH so gunicorn can be invoked without full path. This is fragile and unnecessary — use the absolute path in ExecStart directly.

---

## Open Questions

1. **VM vCPU count (affects --workers value)**
   - What we know: `nproc` on the VM returns the vCPU count. Formula is `(2 * vCPUs) + 1`. STATE.md flags this as an open concern.
   - What's unclear: Whether the university VM has 1 or 2 vCPUs allocated.
   - Recommendation: Run `nproc` as the first task of this phase. Use the result to set `--workers` in the unit file. If `nproc` returns 1, use `--workers 3`. If it returns 2, use `--workers 5`. Default to 2 if nproc is unavailable for some reason.

2. **Whether to enable UFW or just add the rule**
   - What we know: UFW is inactive on this VM. SRV-03 says "UFW allows inbound traffic on port 5000 (`sudo ufw status` lists the rule)." The success criterion checks that the rule is listed, not that UFW is active.
   - What's unclear: The phase success criterion says "`sudo ufw status` lists the rule" — if UFW is inactive, `sudo ufw status` shows `Status: inactive` and does NOT list rules.
   - Recommendation: The phase should enable UFW to satisfy the literal success criterion. If enabling, the SSH allow rule on port 2214 MUST be added first. This makes UFW active and listing the rule satisfies SRV-03 exactly.

3. **EnvironmentFile — .env on the VM vs this repo's .env**
   - What we know: The project `.env` in the repo is a `key=value` file used for local development. The VM has its own `.env` at `/home/student/context-of-code/.env` configured in Phase 1 (SETUP-03).
   - What's unclear: Whether the VM's `.env` uses the same bare `key=value` format (likely yes, since SETUP-03 copies/creates it).
   - Recommendation: Verify with `cat .env` on the VM before writing the unit file. If the format is bare `key=value` (no `export`, no shell expansion), `EnvironmentFile` works directly. If there are any `export` prefixes, they must be removed before using EnvironmentFile.

---

## Sources

### Primary (HIGH confidence)

- Official systemd.service(5) man page — https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html — `Restart=` options and definitions, `RestartSec=` default (100ms), `ExecStart` behavior, `EnvironmentFile` directive
- systemd.io official docs on network targets — https://systemd.io/NETWORK_ONLINE/ — authoritative guidance that server software should use `After=network.target` NOT `After=network-online.target`
- Phase 2 RESEARCH.md + SUMMARY.md — confirmed Gunicorn invocation (`gunicorn --bind 0.0.0.0:5000 --workers 2 web_app.app:app`), working directory (`/home/student/context-of-code`), venv location (`venv/bin/gunicorn`), UFW inactive status
- Project `.env` file — confirmed bare `key=value` format, directly compatible with `EnvironmentFile` directive

### Secondary (MEDIUM confidence)

- Miguel Grinberg — Running a Flask Application as a Service with Systemd — https://blog.miguelgrinberg.com/post/running-a-flask-application-as-a-service-with-systemd — complete unit file structure pattern; Flask-specific guidance
- DigitalOcean — How To Serve Flask Applications with Gunicorn and Nginx on Ubuntu 22.04 — https://www.digitalocean.com/community/tutorials/how-to-serve-flask-applications-with-gunicorn-and-nginx-on-ubuntu-22-04 — unit file structure confirmed; UFW commands verified
- DigitalOcean — How To Set Up a Firewall with UFW on Ubuntu — https://www.digitalocean.com/community/tutorials/how-to-set-up-a-firewall-with-ufw-on-ubuntu — UFW command syntax, SSH lockout prevention sequence
- WebSearch results on RestartSec defaults — cross-verified: default 100ms is from official man page; `RestartSec=5` is a widely-cited practical recommendation; `StartLimitBurst` default is 5 per official systemd-system.conf defaults

### Tertiary (LOW confidence)

- WebSearch result that `StartLimitIntervalSec` and `StartLimitBurst` belong in `[Unit]` section not `[Service]` — this is reported across multiple community sources; the official man page reference was confirmed to exist in systemd.unit(5) (not systemd.service(5)) but not directly fetched. Accept as likely correct; the unit file in Code Examples omits these since the defaults (5 attempts in 10 seconds with 100ms RestartSec, overridden to 5s here) are safe for a college project.

---

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH — systemd is built into Ubuntu 22.04; UFW is built-in; all commands verified against official man page and Ubuntu docs
- Architecture: HIGH — unit file pattern synthesized from official systemd.service(5) + verified project-specific paths from Phase 2 summaries + project source read directly
- Pitfalls: HIGH for ExecStart path, daemon-reload, UFW lockout (all from official docs); MEDIUM for EnvironmentFile format (format confirmed from project .env, systemd behavior from official docs)

**Research date:** 2026-02-25
**Valid until:** 2026-08-25 (systemd and UFW are extremely stable; revisit only if Ubuntu version changes)
