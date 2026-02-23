# Testing Patterns

**Analysis Date:** 2026-02-23

## Test Framework

**Status:** Minimal testing infrastructure

**Test Files Present:**
- `common/database/test_orm.py` - Manual integration test for ORM
- `common/database/test_connection.py` - Manual integration test for database connection

**Runner:**
- No test framework configured (no pytest.ini, setup.py, pyproject.toml found)
- Tests are standalone Python scripts run directly via `python test_file.py`
- Both test files have `if __name__ == "__main__": main()` pattern

**Assertion Library:**
- Standard `assert` statements: `assert user is not None`, `assert user.id == user_id`
- No external assertion library (pytest, unittest)

**Run Commands:**
```bash
# Run individual test file
python common/database/test_orm.py

# Run connection test
python common/database/test_connection.py
```

## Test File Organization

**Location:**
- Tests are **co-located** with source modules in same directory
- Example: `common/database/db_operations.py` paired with `test_orm.py` and `test_connection.py`

**Naming:**
- Test files prefix with `test_`: `test_orm.py`, `test_connection.py`
- Test functions prefixed with `test_`: Not used; uses `main()` function instead
- Single main entry point per test file

**Structure:**
```
common/database/
├── __init__.py
├── db_dataclasses.py
├── db_operations.py
├── test_orm.py          # Tests for ORM functionality
└── test_connection.py   # Tests for database connection
```

## Test Structure

**Suite Organization:**

```python
# From test_orm.py
def main() -> None:
    db = None
    try:
        db = Database()

        # 1. Create a user
        email = f"test_{uuid4().hex[:8]}@example.com"
        logger.info(f"Creating test user with email: {email}")
        user_id = db.create_user(email)
        logger.info(f"Created user with ID: {user_id}")

        # 2. Set password
        # ... more operations ...

        # 8. Clean up (Optional, but let's do it to keep DB clean)
        with db.engine.begin() as conn:
            conn.execute(text("DELETE FROM users WHERE id = :id"), {"id": str(user_id)})

        logger.info("ALL ORM TESTS PASSED SUCCESSFULLY!")

    except Exception:
        logger.exception("Failed ORM tests.")
        raise
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
```

**Patterns:**
- **Setup:** Create Database instance, initialize test data (user, device, etc)
- **Execution:** Call database methods in sequence with inline verification
- **Teardown:** Delete created resources in finally block
- **Assertion:** Inline assertions after operations: `assert user is not None`
- **Logging:** Uses `logger.info()` to show test progress

```python
# From test_connection.py
def main() -> None:
    db = None
    try:
        db = Database()
        with db.engine.connect() as conn:
            conn.execute(text("SELECT 1;")).scalar_one()
        logger.info("Connection successful.")
    except Exception:
        logger.exception("Failed to connect.")
        raise
    finally:
        if db is not None:
            try:
                db.close()
            except Exception:
                pass
```

## Integration Test Characteristics

**What's Tested:**
- Database connection establishment
- CRUD operations on ORM models
- User creation, device creation, sample insertion
- Password hashing and verification
- Device lookup and retrieval

**Test Data:**
- UUIDs generated with `uuid4()` for unique test records
- Email addresses generated: `test_{uuid4().hex[:8]}@example.com`
- Device names: `test_device_{uuid4().hex[:8]}`
- Sample data with realistic network metrics

**Cleanup:**
- Manual SQL delete in transaction: `DELETE FROM users WHERE id = :id`
- Cascade deletions handled by database schema
- Finally block ensures connection closes even on error

## Mocking

**Status:** No mocking framework detected

**What's NOT Mocked:**
- Database connections use real test database (requires running PostgreSQL)
- External APIs not tested (Speedtest CLI, Globalping API)
- File I/O uses real files

**Why:**
- Tests are integration tests, not unit tests
- Tests verify actual database persistence
- Real end-to-end validation important for ORM changes

## Error Handling in Tests

**Pattern:**

```python
try:
    # Test operations
except Exception:
    logger.exception("Failed test.")
    raise
finally:
    # Cleanup
```

**Characteristics:**
- Broad `except Exception` catches any failure
- `logger.exception()` logs full traceback
- Exception re-raised to fail test (exit code non-zero)
- Finally block guarantees cleanup runs

## Test Coverage

**Requirements:** None enforced

**Coverage Status:**
- Only database layer has tests
- No tests for:
  - `DataCollector` class (expensive operations: network speed tests, ping)
  - `UploadQueue` class
  - `GlobalpingLatencyCollector` class
  - Flask API endpoints in `api.py`
  - Authentication functions in `passwords.py`
  - Agent main loop in `main.py`

**Why Gaps Exist:**
- Data collection involves real network I/O (expensive, flaky)
- External APIs (Globalping, Speedtest) require real accounts
- Integration testing more practical than unit mocking for this codebase

## Test Execution Characteristics

**Standalone Scripts:**
- No test runner overhead (pytest, unittest framework)
- Direct execution: `python test_orm.py`
- Exit code 0 on success, non-zero on error
- Output via logging to stdout and file

**Dependencies:**
- Must have active PostgreSQL connection (reads from `.env`)
- Database user/password/host configured
- Schema already exists

**Constraints:**
- Tests use real database (DEV only, not production)
- Network tests are slow (30+ seconds for full speed test)
- External API tests depend on service availability

## Key Testing Gaps

**No Unit Tests:**
- `DataCollector.get_network_metrics()` - Would require mocking subprocess/speedtest
- `GlobalpingLatencyCollector.measure()` - Would require mocking HTTP requests
- `UploadQueue.flush()` - Would require mocking HTTP requests
- `verify_password()` - Could unit test but not currently done

**No Endpoint Tests:**
- `POST /api/ingest` endpoint untested
- JSON validation untested
- Error response codes untested

**No Fixtures/Factories:**
- Test data created inline with hardcoded values
- No reusable test data generators
- No shared database setup/teardown utilities

---

*Testing analysis: 2026-02-23*
