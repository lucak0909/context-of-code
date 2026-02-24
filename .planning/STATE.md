# State

## Project Reference

See: .planning/PROJECT.md (updated 2026-02-24)

**Core value:** Agents on user devices reliably collect and deliver network metrics to a persistent, always-available central server.
**Current focus:** Defining requirements for v1.0 VM Migration

## Current Position

Phase: Not started (defining requirements)
Plan: —
Status: Defining requirements
Last activity: 2026-02-24 — Milestone v1.0 VM Migration started

## Accumulated Context

- Codebase analysis completed: .planning/codebase/ (STACK, ARCHITECTURE, STRUCTURE, INTEGRATIONS, CONCERNS)
- Previously hosted on PythonAnywhere; migrating aggregator to VM
- Supabase PostgreSQL database remains unchanged
- Agents run on end-user devices, not on server
- Serving decision: Gunicorn + systemd (no Nginx — justified by internal-only API scope)
