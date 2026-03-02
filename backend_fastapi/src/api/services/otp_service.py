from __future__ import annotations

import secrets
from datetime import datetime, timedelta, timezone

from src.api.core.db import execute, fetch_one
from src.api.core.settings import get_settings


def _ensure_table_exists() -> None:
    """Ensure OTP table exists (lightweight safety net).

    The provided migration does not include OTP table. We create it lazily if missing
    to avoid breaking environments where migrations weren't updated yet.
    """
    execute(
        """
        CREATE TABLE IF NOT EXISTS auth_otp (
          id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
          identifier text NOT NULL,
          otp_hash text NOT NULL,
          expires_at timestamptz NOT NULL,
          consumed_at timestamptz,
          created_at timestamptz NOT NULL DEFAULT now()
        );
        """
    )
    execute("CREATE INDEX IF NOT EXISTS idx_auth_otp_identifier ON auth_otp(identifier);")


def _hash_otp(otp: str) -> str:
    # Lightweight hash; OTP is short-lived. Use sha256 to avoid storing plaintext.
    import hashlib

    return hashlib.sha256(otp.encode("utf-8")).hexdigest()


# PUBLIC_INTERFACE
def create_and_store_otp(identifier: str) -> str:
    """Create a new OTP for an identifier and store hashed OTP in DB.

    Args:
        identifier: email or phone string.

    Returns:
        The plaintext OTP (caller decides how to deliver it).
    """
    _ensure_table_exists()
    settings = get_settings()
    otp = f"{secrets.randbelow(1000000):06d}"
    expires_at = datetime.now(timezone.utc) + timedelta(seconds=settings.OTP_TTL_SECONDS)

    execute(
        """
        INSERT INTO auth_otp(identifier, otp_hash, expires_at)
        VALUES (%s, %s, %s)
        """,
        (identifier.lower().strip(), _hash_otp(otp), expires_at),
    )
    return otp


# PUBLIC_INTERFACE
def verify_and_consume_otp(identifier: str, otp: str) -> bool:
    """Verify and consume an OTP for identifier.

    Returns:
        True if valid and consumed; otherwise False.
    """
    _ensure_table_exists()
    row = fetch_one(
        """
        SELECT id, otp_hash, expires_at, consumed_at
        FROM auth_otp
        WHERE identifier = %s
        ORDER BY created_at DESC
        LIMIT 1
        """,
        (identifier.lower().strip(),),
    )
    if not row:
        return False
    if row["consumed_at"] is not None:
        return False
    now = datetime.now(timezone.utc)
    if row["expires_at"] < now:
        return False
    if row["otp_hash"] != _hash_otp(otp.strip()):
        return False

    execute("UPDATE auth_otp SET consumed_at = now() WHERE id = %s", (row["id"],))
    return True
