from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Query

from src.api.core.rbac import require_approved
from src.api.repositories import directory_search, get_profile_by_id
from src.api.schemas import ResidentDirectoryItem, ResidentProfile
from src.api.transform import row_to_directory_item, row_to_profile

router = APIRouter(tags=["Directory"])


@router.get(
    "/directory",
    response_model=list[ResidentDirectoryItem],
    summary="Search resident directory",
    description="Search/filter residents. Privacy is enforced based on viewer role and resident privacy settings.",
    operation_id="directory_search",
)
def search_directory(
    q: str | None = Query(default=None, description="Search query (name)."),
    building: str | None = Query(default=None, description="Building filter."),
    floor: str | None = Query(default=None, description="Floor filter."),
    interest: str | None = Query(default=None, description="Interest filter (exact match)."),
    payload=Depends(require_approved),
) -> list[ResidentDirectoryItem]:
    rows = directory_search(q=q, building=building, floor=floor, interest=interest)
    items: list[ResidentDirectoryItem] = []
    for row in rows:
        is_self = False  # directory rows do not include user_id; self view is handled by /profile/me
        items.append(row_to_directory_item(row, viewer_role=payload.role, viewer_is_self=is_self))
    return items


@router.get(
    "/residents/{resident_id}",
    response_model=ResidentProfile,
    summary="Get a resident profile by id",
    description="Returns privacy-filtered resident profile details.",
    operation_id="residents_get",
)
def get_resident(resident_id: str, payload=Depends(require_approved)) -> ResidentProfile:
    row = get_profile_by_id(resident_id)
    if not row:
        raise HTTPException(status_code=404, detail="Resident not found")
    # Determine self by resolving resident_profile.user_id vs payload.sub
    viewer_is_self = str(row.get("user_id")) == payload.sub
    return row_to_profile(row, viewer_role=payload.role, viewer_is_self=viewer_is_self)
