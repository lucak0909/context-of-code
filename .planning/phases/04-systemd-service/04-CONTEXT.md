# Phase 4: Systemd Service - Context

**Gathered:** 2026-02-25
**Status:** Ready for planning

<domain>
## Phase Boundary

Create a systemd unit file for the Gunicorn aggregator so it starts automatically on boot and restarts on crash. Configure UFW to allow inbound traffic on port 5000. No new application features — this is purely OS-level service management.

</domain>

<decisions>
## Implementation Decisions

### Overall Approach
- Keep it as simple and readable as possible while satisfying best practices
- No over-engineering; a clear, standard unit file that anyone familiar with systemd can follow

### Service Identity
- Claude's discretion: run as the deploy/app user (whoever owns the app files), not root
- Avoid creating a new system user unless required — keep it simple

### Restart Behavior
- Restart on failure (not always) — best practice for a web service: restart on crash, not on intentional stop
- RestartSec and attempt limits: Claude's discretion, follow standard defaults

### Environment & Config
- Claude's discretion on how to pass environment variables; prefer the approach already used in the project (e.g., EnvironmentFile pointing to existing .env)

### Network Exposure
- UFW: open port 5000 to all (not IP-restricted) — satisfies SRV-03, keeps it simple

### Claude's Discretion
- Exact unit file directives (WorkingDirectory, ExecStart path construction, etc.)
- Whether to add WantedBy, After, and other ordering directives (use standard best practices)
- Logging approach (journald is fine — no extra log file setup needed)
- UFW rule syntax details

</decisions>

<specifics>
## Specific Ideas

- The user explicitly wants this to be easy to understand — unit file should be well-commented or self-evident
- "Best practices" over cleverness: standard systemd patterns, not exotic configurations

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 04-systemd-service*
*Context gathered: 2026-02-25*
