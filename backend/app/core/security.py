"""Module: security."""

import hashlib
import hmac
import os

# Shared password hashing format/version marker.
PASSWORD_SCHEME = "pbkdf2_sha256"
PASSWORD_ITERATIONS = 390000


def hash_password(password: str) -> str:
    """
    Create a PBKDF2-SHA256 password hash string.

    Stored format:
      pbkdf2_sha256$<iterations>$<salt_hex>$<hash_hex>
    """
    salt = os.urandom(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        salt,
        PASSWORD_ITERATIONS,
    )
    return f"{PASSWORD_SCHEME}${PASSWORD_ITERATIONS}${salt.hex()}${digest.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """
    Verify password against hashed or legacy plaintext value.

    Legacy plaintext fallback is kept for backward compatibility with existing
    seeded data until all users are migrated to hashed storage.
    """
    if not stored:
        return False

    if stored.startswith(f"{PASSWORD_SCHEME}$"):
        try:
            _, iterations_raw, salt_hex, hash_hex = stored.split("$", 3)
            iterations = int(iterations_raw)
            salt = bytes.fromhex(salt_hex)
            expected = bytes.fromhex(hash_hex)
        except Exception:
            return False

        computed = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            salt,
            iterations,
        )
        return hmac.compare_digest(computed, expected)

    # Legacy plaintext compare path.
    return hmac.compare_digest(stored, password)

