# context-of-code

A distributed network telemetry system. Agents running on team members' machines collect network metrics and transmit them to a central Flask server, which stores the data in Supabase (PostgreSQL).

## Architecture

```
[Agent on your laptop]
  └── pc_data_collector        (local network metrics)
  └── cloud_latency_collector  (Globalping latency)
  └── mobile_data_connector    (polls mobile app Supabase DB)
  └── uploader_queue           (buffers + retries HTTP POST)
         │
         ▼  POST /api/ingest
[VM — Flask + Gunicorn]   http://200.69.13.70:5017
         │
         ▼
[Supabase PostgreSQL]     samples table

[Mobile app Supabase DB]  ──▶  mobile_data_connector (polled every 30s)
```

## Recent Changes (March 2026)

- **VM deployment:** The Flask aggregator is now running on the college VM (not PythonAnywhere). It is managed by a systemd service with Gunicorn on port 5017.
- **ORM migration:** Database inserts now use SQLAlchemy ORM sessions instead of raw SQL.
- **`room_id` removed:** The `rooms` table was dropped from Supabase. All references to `room_id` have been removed from the codebase.
- **`AGGREGATOR_API_URL` env var:** You must update your `.env` to point at the VM (see Setup below).

## Setup

**(Ensure you do the setup while within the project root)**

1. Create a virtual environment:
   ```bash
   python -m venv venv
   ```

2. Activate the virtual environment:
   - Windows:
     ```bash
     venv\Scripts\activate
     ```
   - macOS/Linux:
     ```bash
     source venv/bin/activate
     ```

3. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

4. Create a `.env` file in the project root. All available variables are listed below.

### Root `.env` variables

| Variable | Required | Description |
|---|---|---|
| `user` | Yes | Main Supabase DB user (e.g. `postgres.<project-ref>`) |
| `password` | Yes | Main Supabase DB password |
| `host` | Yes | Main Supabase session pooler host |
| `port` | Yes | Main Supabase pooler port (typically `5432`) |
| `dbname` | Yes | Main Supabase database name (typically `postgres`) |
| `AGGREGATOR_API_URL` | Yes | Full ingest URL (e.g. `http://<vm-ip>:5017/api/ingest`) — without this the agent POSTs to localhost and fails |
| `GLOBALPING_API_TOKEN` | No | Globalping API bearer token — increases rate limits for cloud latency measurements |
| `GLOBALPING_DEBUG` | No | Set to `1` to log raw Globalping API responses |
| `GLOBALPING_INTERVAL_SECONDS` | No | Cloud latency poll interval (default `300`) |
| `GLOBALPING_TARGET` | No | Ping target hostname (default `globalping.io`) |
| `GLOBALPING_LOC_EU` | No | Override EU probe location |
| `GLOBALPING_LOC_US` | No | Override US probe location |
| `GLOBALPING_LOC_ASIA` | No | Override Asia probe location |
| `MOBILE_DB_USER` | No* | Mobile app Supabase DB user (e.g. `postgres.<project-ref>`) |
| `MOBILE_DB_PASSWORD` | No* | Mobile app Supabase DB password |
| `MOBILE_DB_HOST` | No* | Mobile app Supabase pooler host |
| `MOBILE_DB_PORT` | No* | Mobile app Supabase pooler port (`6543` for transaction pooler) |
| `MOBILE_DB_NAME` | No* | Mobile app Supabase database name (typically `postgres`) |
| `LOG_LEVEL` | No | Logging level (e.g. `INFO`, `DEBUG`, `ERROR`) |
| `LOG_FORMAT` | No | Override log format string |
| `LOG_DATE_FORMAT` | No | Override log date format |
| `LOGS_DIR` | No | Directory for log files (default `logs/`) |

\* If any `MOBILE_DB_*` variable is missing the mobile connector thread is skipped gracefully — the rest of the agent continues normally.

### `frontend/.env` variables

| Variable | Required | Description |
|---|---|---|
| `VITE_API_URL` | No | Base URL of the aggregator API (e.g. `http://<vm-ip>:5017`). Leave empty to proxy through Vite to `localhost:5000` during local development. |

---

## Mobile Data — Important Credential Requirement

> **The mobile data connector authenticates against the mobile app's Supabase database using the same email and password you log in with on the dashboard.**
>
> Both accounts must use **identical credentials**. If they differ, the mobile connector will fail to authenticate and no mobile WiFi data will be collected or displayed.

To get mobile data working:
1. Set all `MOBILE_DB_*` vars in your root `.env`
2. Register or log in to the **mobile app** with the **exact same email and password** as your dashboard account
3. Run `python -m agent` — look for `Mobile connector started` in the logs
4. Mobile WiFi metrics appear in the **Mobile WiFi** section of the dashboard

## Running

Run modules from the project root so package imports resolve correctly:
```bash
python -m common.database.test_connection
```

Run the agent (login/register flow, then starts monitoring):
```bash
python -m agent
```

This will prompt you to log in or register, then begin collecting and uploading metrics to the VM.

Globalping cloud latency collector (runs alongside the PC collector):
- Default interval: 300s (`GLOBALPING_INTERVAL_SECONDS`)
- Target: `globalping.io` (`GLOBALPING_TARGET`)
- Locations: EU=Germany, US=Virginia (EST), Asia=China
  - Override with `GLOBALPING_LOC_EU`, `GLOBALPING_LOC_US`, `GLOBALPING_LOC_ASIA`

Run the Flask app locally (from the project root):

Option 1 (simple):
```bash
python -m web_app.app
```

Option 2 (Flask CLI):
```bash
flask --app web_app.app --debug run
```

> Note: The production server runs on the VM under Gunicorn — you only need the above for local development.

## Live Server (VM)

| Endpoint      | URL                                   |
| ------------- | ------------------------------------- |
| Health check  | `http://200.69.13.70:5017/health`     |
| Ingest (POST) | `http://200.69.13.70:5017/api/ingest` |

You can verify the server is up with:
```bash
curl http://200.69.13.70:5017/health
```

## End-to-End Demo

To verify the full pipeline is working:
1. Make sure your `.env` has `AGGREGATOR_API_URL=http://200.69.13.70:5017/api/ingest`
2. Run `python -m agent` and log in
3. Check the `samples` table in Supabase — a new row should appear within ~30 seconds

## Logging

The project uses a custom logging setup via `common/utils/logging_setup.py`.

```python
from common.utils.logging_setup import setup_logger

logger = setup_logger()
logger.info("This is an info message")
logger.error("This is an error message")
logger.critical("This is a critical message")
```

## Running Frontend locally
Step 1:
Install dependencies using:
`pip install -r requirements.txt`
in the project root

Step 2:
For the React frontend:
`cd frontend`
`npm install`

Step 3:
Run both servers in 2 terminals:
Terminal 1 -> Flask (from the project root)
`python -m web_app.app`

Terminal 2 -> Vite dev server (from /frontend)
`npm run dev`

**Features:**
- Logs are written to `common/logs/` by default (override with `LOGS_DIR` or `logs_dir`).
- Log files are named `{HIGHEST_LEVEL}_{timestamp}.log` based on the highest severity logged.
- Console output is colorized (files are plain text).

**Environment overrides (optional):**
- `LOG_LEVEL` (e.g., `INFO`, `DEBUG`, `ERROR` or a number)
- `LOG_FORMAT`
- `LOG_DATE_FORMAT`
- `LOGS_DIR`
