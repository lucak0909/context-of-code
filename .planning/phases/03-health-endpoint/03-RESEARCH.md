# Phase 3: Health Endpoint - Research

**Researched:** 2026-02-24
**Domain:** Flask Routing & Health Checks
**Confidence:** HIGH

## Summary

This phase requires adding a simple HTTP liveness probe to the aggregator application. The endpoint `GET /health` must return HTTP 200 with a JSON payload containing the string "ok" and an ISO 8601 UTC timestamp. This endpoint will be used by external agents (and potentially future monitoring systems) to verify the service is running.

**Primary recommendation:** Add a `@app.route('/health', methods=['GET'])` directly in `web_app/app.py` and use Python's `datetime.now(timezone.utc).isoformat()` for the timestamp.

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| HEALTH-01 | `GET /health` endpoint returns `{"status": "ok", "ts": "<utc-iso>"}` at HTTP 200 | Implementation requires adding a root-level route in Flask returning JSON with a UTC ISO timestamp. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| Flask | Current | Web Framework | Existing project standard for the aggregator app |
| datetime | Built-in | Timestamp generation | Native Python library for robust timezone-aware dates |

## Architecture Patterns

### Recommended Project Structure
The endpoint should be placed directly in the main app file since it is an app-level liveness check, not a business API resource.

```text
web_app/
├── app.py             # Add /health route here
└── blueprints/
    └── api.py         # Keep domain logic (ingest) separate
```

### Pattern 1: App-level Health Check
**What:** A simple liveness endpoint registered at the application root.
**When to use:** For basic uptime monitoring and load-balancer health checks.
**Example:**
```python
from flask import Flask, jsonify
from datetime import datetime, timezone

app = Flask(__name__)

@app.route('/health', methods=['GET'])
def health():
    return jsonify({
        "status": "ok",
        "ts": datetime.now(timezone.utc).isoformat()
    }), 200
```

### Anti-Patterns to Avoid
- **Adding to `api_bp`:** The API blueprint is prefixed with `/api`. Adding the health check there would expose it as `/api/health`, failing the `GET /health` requirement.
- **Using `datetime.utcnow()`:** This is deprecated in Python 3.12 and produces a naive datetime object without timezone information (`+00:00` suffix).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| JSON serialization | Manual `json.dumps` | Flask `jsonify` (or native dict return) | Automatically handles proper `Content-Type: application/json` headers and edge cases. |
| Timezone management | Manual string formatting | `datetime.now(timezone.utc).isoformat()` | Ensures strict ISO 8601 compliance including the timezone designator. |

**Key insight:** Python's standard library and Flask provide all necessary tools for a robust, standards-compliant health check.

## Common Pitfalls

### Pitfall 1: Incorrect Endpoint Path
**What goes wrong:** The health check is placed inside a blueprint that has a URL prefix (e.g., `/api`).
**Why it happens:** Attempting to group all routes in a single blueprint to keep `app.py` clean.
**How to avoid:** Explicitly define `@app.route('/health')` in `app.py` before or after blueprint registration.
**Warning signs:** `curl http://<VM_IP>:5000/health` returns 404, but `/api/health` returns 200.

### Pitfall 2: Non-ISO Timestamp format
**What goes wrong:** The `ts` field does not contain timezone information or uses an invalid format.
**Why it happens:** Using `datetime.now().isoformat()` (local time, no timezone indicator) or `datetime.utcnow().isoformat()` (UTC time, but naive/missing `+00:00` or `Z` indicator).
**How to avoid:** Always use `datetime.now(timezone.utc).isoformat()`.

## Code Examples

Verified patterns from official sources:

### Robust ISO 8601 Timestamp Generation
```python
from datetime import datetime, timezone

# Correct: Includes +00:00 timezone indicator
iso_ts = datetime.now(timezone.utc).isoformat()
# Output: '2026-02-24T12:00:00.000000+00:00'
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `datetime.utcnow()` | `datetime.now(timezone.utc)` | Python 3.12 (deprecated) | Requires updating timezone handling to avoid warnings and ensure correct timezone serialization. |

## Sources

### Primary (HIGH confidence)
- Flask Documentation - Routing and `jsonify` behaviour.
- Python `datetime` Module Documentation - Best practices for UTC and ISO formatting.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - Built-in features of the existing framework.
- Architecture: HIGH - Standard microservice pattern.
- Pitfalls: HIGH - Known common mistakes with Flask routing and Python datetimes.

**Research date:** 2026-02-24
**Valid until:** 2026-08-24
