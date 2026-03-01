# context-of-code

A distributed network telemetry system. Agents running on team members' machines collect network metrics and transmit them to a central Flask server, which stores the data in Supabase (PostgreSQL).

## Architecture

```
[Agent on your laptop]
  └── pc_data_collector   (local network metrics)
  └── cloud_latency_collector  (Globalping latency)
  └── uploader_queue      (buffers + retries HTTP POST)
         │
         ▼  POST /api/ingest
[VM — Flask + Gunicorn]   http://200.69.13.70:5017
         │
         ▼
[Supabase PostgreSQL]     samples table
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

4. Create a `.env` file in the project root with:
   ```
   user=postgres.vkfyssomfhjlddwdaruz
   password=[ASK LUCA FOR PASSWORD]
   host=aws-1-eu-north-1.pooler.supabase.com
   port=5432
   dbname=postgres

   AGGREGATOR_API_URL=http://200.69.13.70:5017/api/ingest
   ```

   > **Important:** The `AGGREGATOR_API_URL` line is new. Without it the agent will try to POST to localhost and fail.

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

**Features:**
- Logs are written to `common/logs/` by default (override with `LOGS_DIR` or `logs_dir`).
- Log files are named `{HIGHEST_LEVEL}_{timestamp}.log` based on the highest severity logged.
- Console output is colorized (files are plain text).

**Environment overrides (optional):**
- `LOG_LEVEL` (e.g., `INFO`, `DEBUG`, `ERROR` or a number)
- `LOG_FORMAT`
- `LOG_DATE_FORMAT`
- `LOGS_DIR`
