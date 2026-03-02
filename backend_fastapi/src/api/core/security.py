from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any, Dict, Optional

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from passlib.context import CryptContext
from pydantic import BaseModel, Field

from src.api.core.settings import get_settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
bearer_scheme = HTTPBearer(auto_error=False)


class TokenPayload(BaseModel):
    """Decoded JWT payload."""
    sub: str = Field(..., description="User id (uuid).")
    role: str = Field(..., description="User role: resident|staff|admin.")
    approval_state: str = Field(..., description="User approval_state.")
    is_active: bool = Field(..., description="Whether user is active.")
    exp: int = Field(..., description="Expiry (epoch seconds).")


# PUBLIC_INTERFACE
def hash_password(password: str) -> str:
    """Hash a plaintext password.

    Args:
        password: Plaintext password.

    Returns:
        Password hash suitable for storage.
    """
    return pwd_context.hash(password)


# PUBLIC_INTERFACE
def verify_password(password: str, password_hash: str) -> bool:
    """Verify plaintext password against stored hash."""
    return pwd_context.verify(password, password_hash)


# PUBLIC_INTERFACE
def create_access_token(*, user_id: str, role: str, approval_state: str, is_active: bool) -> str:
    """Create a signed JWT access token."""
    settings = get_settings()
    exp_dt = datetime.now(timezone.utc) + timedelta(minutes=settings.JWT_EXPIRES_MINUTES)
    payload: Dict[str, Any] = {
        "sub": user_id,
        "role": role,
        "approval_state": approval_state,
        "is_active": is_active,
        "exp": int(exp_dt.timestamp()),
    }
    return jwt.encode(payload, settings.JWT_SECRET, algorithm=settings.JWT_ALGORITHM)


# PUBLIC_INTERFACE
def decode_token(token: str) -> TokenPayload:
    """Decode and validate a JWT."""
    settings = get_settings()
    try:
        data = jwt.decode(token, settings.JWT_SECRET, algorithms=[settings.JWT_ALGORITHM])
        return TokenPayload(**data)
    except jwt.ExpiredSignatureError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Token expired") from exc
    except jwt.PyJWTError as exc:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid token") from exc


# PUBLIC_INTERFACE
def get_current_token_payload(
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(bearer_scheme),
) -> TokenPayload:
    """FastAPI dependency: extract and validate Bearer token.

    Raises:
        HTTPException(401) if missing/invalid.
    """
    if not credentials or not credentials.credentials:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Not authenticated")
    return decode_token(credentials.credentials)
