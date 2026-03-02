from __future__ import annotations

from fastapi import Depends, HTTPException, status

from src.api.core.security import TokenPayload, get_current_token_payload
from src.api.core.settings import get_settings


# PUBLIC_INTERFACE
def require_authenticated(payload: TokenPayload = Depends(get_current_token_payload)) -> TokenPayload:
    """Require an authenticated user.

    Returns:
        TokenPayload for the current user.
    """
    # Base checks
    if not payload.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="User is disabled")
    return payload


# PUBLIC_INTERFACE
def require_approved(payload: TokenPayload = Depends(require_authenticated)) -> TokenPayload:
    """Require user to be approved if the system policy is enabled."""
    settings = get_settings()
    if settings.REQUIRE_ADMIN_APPROVAL and payload.approval_state != "approved":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Account pending approval")
    return payload


# PUBLIC_INTERFACE
def require_admin(payload: TokenPayload = Depends(require_authenticated)) -> TokenPayload:
    """Require an admin user."""
    if payload.role != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Admin access required")
    return payload
