---
plan: 01-01
phase: 01-vm-provisioning-and-environment-setup
status: complete
completed: 2026-02-24
---

# Summary: VM Provisioning — Python 3.10 + Repository Clone

## What Was Done

Provisioned Student-vm-13 (200.69.13.70:2214) with Python 3.10, git, and a clone of the context-of-code repository with a working virtual environment containing all project dependencies.

## Tasks Completed

| Task | Description | Status |
|------|-------------|--------|
| 1 | SSH into VM, install system packages, clone repository | ✓ Complete |
| 2 | Create Python 3.10 venv, install all project dependencies | ✓ Complete |

## Key Details

- Ubuntu 20.04 on VM — required deadsnakes PPA (`ppa:deadsnakes/ppa`) to install Python 3.10
- Python 3.10.19 installed successfully
- Repository cloned from https://github.com/lucak0909/context-of-code.git to `/home/student/context-of-code`
- venv created at `/home/student/context-of-code/venv/` using `python3.10 -m venv venv`
- All requirements.txt packages installed (SQLAlchemy 2.0.46, Flask 3.1.2, python-dotenv 1.2.1, psycopg2-binary)

## Artifacts Created

- `/home/student/context-of-code/` — cloned project repository
- `/home/student/context-of-code/venv/` — Python 3.10 virtual environment with all dependencies

## Deviations

- deadsnakes PPA was required (Ubuntu 20.04, not 22.04) — documented in task flow
