# context-of-code

## Setup Instructions

**Ensure your current working directory is the project root**

1. **Create a virtual environment:**
    ```bash
    python -m venv venv
    ```

2. **Activate the virtual environment:**
    - On Windows:
      ```bash
      venv\Scripts\activate
      ```
    - On macOS/Linux:
      ```bash
      source venv/bin/activate
      ```

3. **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4. **Create a `.env` file:**
    ```bash
    touch .env
    ```

5. **Add database connection fields:**
    Open the `.env` file and add:
    ```
    user=postgres.vkfyssomfhjlddwdaruz
    password=[ASK LUCA FOR PASSWORD]
    host=aws-1-eu-north-1.pooler.supabase.com
    port=5432
    dbname=postgres
    ```