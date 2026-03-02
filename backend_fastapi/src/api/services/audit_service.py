from __future__ import annotations

from typing import Any, Dict, Optional

from fastapi import Request

from src.api.core.db import execute


# PUBLIC_INTERFACE
def write_audit_log(
    *,
    actor_user_id: Optional[str],
    action: str,
    entity_type: str,
    entity_id: Optional[str],
    request: Optional[Request],
    details: Optional[Dict[str, Any]] = None,
) -> None:
    """Write an audit log entry.

    Args:
        actor_user_id: User id performing action (nullable for anonymous actions).
        action: Action string (e.g., "auth.register").
        entity_type: Entity type (e.g., "app_user", "resident_profile").
        entity_id: Entity id (uuid) if applicable.
        request: FastAPI Request for IP/user-agent (optional).
        details: Arbitrary JSON-serializable details.
    """
    ip = None
    ua = None
    if request is not None:
        ip = request.client.host if request.client else None
        ua = request.headers.get("user-agent")

    execute(
        """
        INSERT INTO audit_log(actor_user_id, action, entity_type, entity_id, ip_address, user_agent, details)
        VALUES (%s, %s, %s, %s, %s, %s, %s::jsonb)
        """,
        (
            actor_user_id,
            action,
            entity_type,
            entity_id,
            ip,
            ua,
            "{}" if not details else __import__("json").dumps(details),
        ),
    )
