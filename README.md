# context-of-code

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
   ```

## Running

Run modules from the project root so package imports resolve correctly:
```bash
python -m common.database.test_connection
```

Run the agent console login/register flow:
```bash
python -m agent.pc_data_collector.cli.console_auth
```

Run the agent (same as login flow, then monitoring):
```bash
python -m agent.pc_data_collector
```
Shortcut:
```bash
python -m agent
```

Run the Flask app (from the project root).

Option 1 (simple):
```bash
python -m web_app.app
```

Option 2 (Flask CLI):
```bash
flask --app web_app.app --debug run
```

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
