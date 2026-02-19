from __future__ import annotations

import base64
import hashlib
import hmac
import os
from typing import Tuple

DEFAULT_ITERATIONS = 200_000
DEFAULT_SALT_BYTES = 16
ALGORITHM = "pbkdf2_sha256"


def _pbkdf2(password: str, salt: bytes, iterations: int) -> bytes:
    return hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, iterations)


def _encode_bytes(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).decode("ascii").rstrip("=")


def _decode_bytes(encoded: str) -> bytes:
    padding = "=" * (-len(encoded) % 4)
    return base64.urlsafe_b64decode(encoded + padding)


def hash_password(
    password: str,
    *,
    iterations: int = DEFAULT_ITERATIONS,
    salt_bytes: int = DEFAULT_SALT_BYTES,
) -> str:
    if not password:
        raise ValueError("Password cannot be empty.")

    salt = os.urandom(salt_bytes)
    digest = _pbkdf2(password, salt, iterations)
    return (
        f"{ALGORITHM}${iterations}${_encode_bytes(salt)}${_encode_bytes(digest)}"
    )


def _parse_hash(stored: str) -> Tuple[int, bytes, bytes]:
    try:
        algorithm, iterations_str, salt_b64, digest_b64 = stored.split("$", 3)
    except ValueError as exc:
        raise ValueError("Invalid password hash format.") from exc

    if algorithm != ALGORITHM:
        raise ValueError("Unsupported password hash algorithm.")

    iterations = int(iterations_str)
    salt = _decode_bytes(salt_b64)
    digest = _decode_bytes(digest_b64)
    return iterations, salt, digest


def verify_password(password: str, stored_hash: str) -> bool:
    if not password or not stored_hash:
        return False

    try:
        iterations, salt, digest = _parse_hash(stored_hash)
    except ValueError:
        return False

    candidate = _pbkdf2(password, salt, iterations)
    return hmac.compare_digest(candidate, digest)
