import os
from uuid import uuid4
from sqlalchemy import text
from .db_operations import Database
from .db_dataclasses import User, Device, Sample, Password
from ..utils.logging_setup import setup_logger

logger = setup_logger(name=__name__)

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
        db.set_password(user_id, "test_hash_xyz")
        logger.info(f"Set password for user: {user_id}")
        
        # 3. Get user
        user = db.get_user_by_email(email)
        assert user is not None
        assert user.id == user_id
        logger.info(f"Verified get_user_by_email")
        
        # 4. Verify password
        assert db.get_password_hash(user_id) == "test_hash_xyz"
        logger.info(f"Verified get_password_hash")
        
        # 5. Create device
        device_name = f"test_device_{uuid4().hex[:8]}"
        device = db.create_device(user_id, device_name, "pc")
        logger.info(f"Created device with ID: {device.id}")
        
        # 6. Get device
        fetched_device = db.get_device_by_user_and_name(user_id, device_name)
        assert fetched_device is not None
        assert fetched_device.id == device.id
        logger.info(f"Verified get_device_by_user_and_name")
        
        # 7. Insert Network Sample
        db.insert_desktop_network_sample(
            device_id=device.id,
            latency_ms=15.5,
            packet_loss_pct=0.0,
            down_mbps=150.0,
            up_mbps=50.0
        )
        logger.info("Inserted desktop network sample successfully.")
        
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


if __name__ == "__main__":
    main()
