from __future__ import annotations

from fastapi import APIRouter, Depends, Request

from src.api.core.rbac import require_admin, require_approved
from src.api.repositories import create_announcement, list_announcements
from src.api.schemas import Announcement, AnnouncementCreateRequest
from src.api.services.audit_service import write_audit_log
from src.api.transform import row_to_announcement

router = APIRouter(prefix="/announcements", tags=["Announcements"])


@router.get(
    "",
    response_model=list[Announcement],
    summary="List published announcements",
    operation_id="announcements_list",
)
def list_all(payload=Depends(require_approved)) -> list[Announcement]:
    return [row_to_announcement(r) for r in list_announcements()]


@router.post(
    "",
    response_model=Announcement,
    summary="Create a new announcement (admin)",
    operation_id="announcements_create",
)
def create(body: AnnouncementCreateRequest, request: Request, payload=Depends(require_admin)) -> Announcement:
    row = create_announcement(title=body.title, body=body.body, created_by=payload.sub)
    write_audit_log(
        actor_user_id=payload.sub,
        action="announcement.create",
        entity_type="announcement",
        entity_id=str(row["id"]),
        request=request,
        details={"title": body.title},
    )
    return row_to_announcement(row)
