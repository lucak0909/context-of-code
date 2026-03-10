from __future__ import annotations

import getpass
import sys
from typing import Optional
from uuid import UUID

from common.auth.passwords import hash_password
from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger
from agent.pc_data_collector.main import run_with_user

logger = setup_logger("console_auth")


def _prompt_email() -> Optional[str]:
    email = input("Email: ").strip().lower()
    if not email:
        logger.warning("Email is required")
        return None
    return email


def _prompt_password(confirm: bool = False) -> Optional[str]:
    password = getpass.getpass("Password: ").strip()
    if not password:
        logger.warning("Password is required")
        return None
    if confirm:
        confirm_password = getpass.getpass("Confirm password: ").strip()
        if password != confirm_password:
            logger.warning("Passwords do not match")
            return None
    return password


def register_flow(db: Database) -> Optional[tuple]:
    """Returns (user_id, email, password) on success, else None."""
    email = _prompt_email()
    if not email:
        return None

    if db.get_user_by_email(email):
        logger.warning("Account already exists for %s", email)
        return None

    password = _prompt_password(confirm=True)
    if not password:
        return None

    password_hash = hash_password(password)
    user_id = db.create_user(email)
    db.set_password(user_id, password_hash)
    logger.info("Registered user %s", user_id)
    return user_id, email, password


def login_flow(db: Database) -> Optional[tuple]:
    """Returns (user_id, email, password) on success, else None."""
    email = _prompt_email()
    if not email:
        return None

    user = db.get_user_by_email(email)
    if not user:
        logger.warning("No account found for %s", email)
        return None

    password = _prompt_password(confirm=False)
    if not password:
        return None

    if db.verify_user_password(user.id, password):
        logger.info("Login successful for user %s", user.id)
        return user.id, email, password

    logger.warning("Invalid credentials for %s", email)
    return None


def main() -> None:
    db = Database()
    result: Optional[tuple] = None
    try:
        while True:
            print("\nChoose an option:")
            print("1. Login")
            print("2. Register")
            print("3. Exit")
            choice = input("Enter choice: ").strip()

            if choice == "1":
                result = login_flow(db)
            elif choice == "2":
                result = register_flow(db)
            elif choice == "3":
                logger.info("Exiting")
                return
            else:
                logger.warning("Invalid menu choice: %s", choice)

            if result:
                break
    except KeyboardInterrupt:
        logger.info("Exiting")
    except Exception:
        logger.exception("Console auth failed")
        sys.exit(1)
    finally:
        db.close()

    if result:
        user_id, email, password = result
        run_with_user(user_id, email=email, password=password)


if __name__ == "__main__":
    main()
