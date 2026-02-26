# Phase 5: Agent Cutover and End-to-End Verification - Context

**Gathered:** 2026-02-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Redirect all agent machines from PythonAnywhere to the VM endpoint, then verify that metrics flow end-to-end: agent → VM → Supabase. Gunicorn must first be reconfigured to bind to the college-assigned external port. This phase does not involve changes to the Supabase schema, agent logic, or monitoring setup.

</domain>

<decisions>
## Implementation Decisions

### Rollout strategy
- Multiple agent machines are in use (different people's laptops)
- Each person updates their own `.env` independently — no central update
- All machines must switch on the same coordinated day (not staggered)
- No per-machine tracking required — verifying the end result is sufficient
- PythonAnywhere is NOT kept as a fallback — everyone cuts over at once

### Pre-cutover VM checks
- Before any agent switches, verify the VM endpoint is ready via SSH tunnel
- Test sequence: hit `/health` for 200, then send a test POST to `/api/ingest` and confirm 200/201
- SSH tunnel from laptop is the test method (established pattern from prior phases)
- A 200/201 response from the VM is sufficient — no need to verify a test Supabase row

### Verification rigor
- Minimum bar: one agent run that logs a 200 or 201 response, plus a new row appearing in Supabase
- Supabase checked manually via the browser dashboard (no scripted query needed)
- Evidence to capture for presentation: screenshot of new Supabase row + terminal output showing the 200/201 agent log
- Agent queue/retry behavior is unknown — researcher should investigate how the agent handles failures and what "no queue retention" means in practice

### Fallback plan
- Fix forward — no revert to PythonAnywhere
- If cutover fails (wrong port, Gunicorn config issue, etc.), investigate and fix on the VM
- Failure risks are unknown — researcher should assess the most likely failure modes for this cutover

### Claude's Discretion
- How to structure the step-by-step cutover instructions for other team members (format, medium)
- Exact curl command format for the pre-cutover test POST
- How to document that the cutover day has been coordinated (whether to note it anywhere)

</decisions>

<specifics>
## Specific Ideas

- Verification evidence is specifically needed for the college presentation — a screenshot of the Supabase dashboard row plus terminal output is the target artifact
- The pre-cutover test should use the same SSH tunnel pattern used in earlier phases

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 05-agent-cutover-and-end-to-end-verification*
*Context gathered: 2026-02-26*
