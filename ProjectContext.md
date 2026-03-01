Here is a comprehensive `ProjectContext.md` file that synthesizes all the lecture materials, architectural requirements, project status, and grading criteria. 

You can copy and paste this directly into Claude to give it a complete "brain dump" of everything your professor expects.

***

```markdown
# Project Context: Distributed System Monitoring Tool
**Course:** Immersive Software Engineering (ISE) - Context of the Code
**Professor:** John Savage

## 1. Project Overview & Target Architecture
The goal is to build a distributed telemetry system that reads hardware metrics from various devices and transmits them to a central cloud server for storage and visualization. For my teams case we will be focussed on Network Metrics.

**Target Architecture Components:**
*   **Collector Agents:** Local scripts running on specific devices (PC Data Collector, Mobile Data Collector, 3rd Party APIs). They gather data and pass it to an internal **Uploader Queue**.
*   **Uploader Queue:** A safety buffer inside the agent to handle offline scenarios and batch network requests.
*   **Web Application (Cloud Server):** 
    *   **Aggregator API:** A REST endpoint (Flask) that catches incoming JSON payloads from the agents.
    *   **Database:** Persistent storage (PostgreSQL/Supabase) updated via SQLAlchemy ORM.
    *   **Reporting API:** An endpoint that fetches historical data from the database.
*   **System Reports / Dashboard:** A web UI that queries the Reporting API to display live and historical metric graphs to the end-user.

## 2. Core Engineering Principles (Lecture Concepts)
Code generated for this project MUST adhere to these specific principles taught in the module:

*   **No Magical Thinking:** All code must be fully understood by the team. Avoid over-engineered AI solutions; prefer explicit, readable code that demonstrates an understanding of the underlying OS, networks, and databases.
*   **Resource Management & RAII:** Resource Acquisition Is Initialization (RAII) must be used. Use Python Context Managers (`with` statements) to guarantee that sockets, database sessions, memory, and files are safely closed and cleaned up to prevent leaks and port exhaustion (e.g., handling TCP `TIME_WAIT` states).
*   **Structured Logging:** Do not use basic `print()` statements. Use a configured logging framework (e.g., `logger.info()`, `logger.error()`) for logic flow and debugging.
*   **Configuration Management:** Avoid magic strings. Use `.env` files and human-readable config formats (JSON) for environment setups. 
*   **Caching Strategy:** Implement in-memory caching (e.g., 5-minute TTL) for slower data reads or heavy reporting endpoints to optimize performance.
*   **Serialization:** Serialize objects into JSON at the "last responsible moment" before network transmission.
*   **ORM Integration:** Use an Object-Relational Mapper (SQLAlchemy) rather than raw SQL for database inserts/queries. Database logic should include session management (commit/rollback).

## 3. Lecture Progression & Expected Knowledge
The project builds upon these specific weekly milestones:
*   **Day 1 (PoC 1.0):** Data Model design, Process isolation, reading local PC data. Replacing print statements with structured logging.
*   **Day 2 (Transmission):** IPC, TCP/IP mechanics (connections, sockets), Resource Management, and RAII BlockTimers.
*   **Day 3 (Web/Cache):** Flask Web Server basics, JSON HTTP responses, Execution flow (`__main__`), and Caching principles.
*   **Day 4 (Networks/Data):** Command-line arguments (`argparse`), DNS/Ping/Ports, and Database schema normalization (1:1, 1:N, N:M).
*   **Day 5 (SQL/ORM):** SQL indexing, transactions, connecting to the database, and mapping tables to Python classes using SQLAlchemy ORM (`sqlacodegen`).

## 4. Current Project Status (~85% Complete)
*   **What Works:**
    *   Data collection is fully modularised (`agent/pc_data_collector/` and `agent/cloud_latency_collector/`), gathering local network metrics and 3rd-party Globalping cloud latency.
    *   An internal **Uploader Queue** (`agent/uploader_queue/queue.py`) buffers metrics offline and transmits them via HTTP POST to the aggregator.
    *   The Flask web app is deployed on a college-provisioned VM (Ubuntu), running under **Gunicorn** (5 workers, port 5017) managed by a **systemd** service that auto-restarts on failure.
    *   The **Aggregator API** (`POST /api/ingest`) is live and externally reachable at `http://200.69.13.70:5017/api/ingest`. It receives JSON payloads from agents and persists them to Supabase PostgreSQL using **SQLAlchemy ORM** sessions.
    *   A **health endpoint** (`GET /health`) exists at `http://200.69.13.70:5017/health` for uptime verification.
    *   The database schema uses a normalised `samples` table (no `rooms` table — removed). ORM models (`Sample`, `Device`, `User`, `Password`) are defined in `common/database/db_dataclasses.py`.
    *   End-to-end pipeline verified: agent runs → data POSTed to VM → rows confirmed in Supabase.
    *   Configuration (`settings.py`, `.env`) and structured logging are properly set up throughout.
*   **Critical Flaws to Fix:**
    *   No error handling on Flask startup (if the network drops, the app crashes).
    *   The local PC agent's entrypoint currently defaults to `run()` (a test function with a hardcoded `device_id`). Production use requires switching the default to `run_with_user()` to dynamically register the device and use a real database ID.
*   **Missing Features:** The Reporting API and Dashboard UI do not exist yet.

## 5. Immediate Development Priorities
When assisting with code generation, prioritize these tasks in order:
1.  **Build Reporting API:** Create Flask endpoints to fetch historical metric data from the database, broken down by `sample_type` (`desktop_network`, `cloud_latency`).
2.  **Build Dashboard UI:** Create the web interface to query the Reporting API and display live and historical metric graphs to the end-user.
3.  **Switch agent default to `run_with_user()`:** Update `agent/__main__.py` so that the production entry point prompts for user login and registers the device dynamically instead of using a hardcoded test ID.
4.  **Add Flask Startup Error Handling:** Ensure the Flask app doesn't crash on startup if the network or database is temporarily unavailable.
5.  **Device Commands (Stretch Goal):** Implement bidirectional communication allowing the server to dynamically change the PC agent's polling interval.

## 6. Assessment Constraints
*   **Format:** 70% of the module grade. Examined via a strict 20-minute team interview.
*   **Deliverables:** Code submission and a maximum 3-slide presentation. No written reports.
*   **Rubric Focus:** Marks are awarded heavily for "Understanding of Code Built". Complex AI-generated code that the team cannot explain will result in a failure. Code must be clean, modular, and defensible.
*   **Stretch Goal:** Once the base pipeline is working, a stretch goal is to implement "Device Commands" (e.g., bidirectional communication where the server tells the PC agent to change its polling interval).

# 7. Please Note! 
*   Before Merging/Pushing to main please update this project context file to reflect the current state of the project! Also, ensure to stage this file before pushing.
*   In your IDE Chat inside Cursor/Antigravity You can run something like `Please look at @ProjectContext.md and update the current project status and immediate Development priorites if needed`
```

*** 
