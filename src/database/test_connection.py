from sqlalchemy import text
from .db_operations import Database
from ..logging_setup import setup_logger

logger = setup_logger(name=__name__)


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


if __name__ == "__main__":
    main()
