from __future__ import annotations

import getpass
import sys
from typing import Optional

from common.auth.passwords import hash_password
from common.database.db_operations import Database
from common.utils.logging_setup import setup_logger

logger = setup_logger("console_auth")


def _prompt_email() -> Optional[str]:
    email = input("Email: ").strip().lower()
    if not email:
        print("Email is required.")
        return None
    return email


def _prompt_password(confirm: bool = False) -> Optional[str]:
    password = getpass.getpass("Password: ").strip()
    if not password:
        print("Password is required.")
        return None
    if confirm:
        confirm_password = getpass.getpass("Confirm password: ").strip()
        if password != confirm_password:
            print("Passwords do not match.")
            return None
    return password


def register_flow(db: Database) -> None:
    email = _prompt_email()
    if not email:
        return

    if db.get_user_by_email(email):
        print("Account already exists. Please login.")
        return

    password = _prompt_password(confirm=True)
    if not password:
        return

    password_hash = hash_password(password)
    user_id = db.create_user(email)
    db.set_password(user_id, password_hash)
    print(f"Registered. Your user ID is: {user_id}")


def login_flow(db: Database) -> None:
    email = _prompt_email()
    if not email:
        return

    user = db.get_user_by_email(email)
    if not user:
        print("No account found. Please register first.")
        return

    password = _prompt_password(confirm=False)
    if not password:
        return

    if db.verify_user_password(user.id, password):
        print(f"Login successful. Your user ID is: {user.id}")
    else:
        print("Invalid credentials.")


def main() -> None:
    db = Database()
    try:
        while True:
            print("\nChoose an option:")
            print("1. Login")
            print("2. Register")
            print("3. Exit")
            choice = input("Enter choice: ").strip()

            if choice == "1":
                login_flow(db)
            elif choice == "2":
                register_flow(db)
            elif choice == "3":
                print("Goodbye.")
                return
            else:
                print("Invalid choice.")
    except KeyboardInterrupt:
        print("\nGoodbye.")
    except Exception:
        logger.exception("Console auth failed")
        sys.exit(1)
    finally:
        db.close()


if __name__ == "__main__":
    main()
