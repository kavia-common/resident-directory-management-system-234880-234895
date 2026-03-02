from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.core.rbac import require_admin
from src.api.repositories import (
    admin_list_residents,
    get_profile_by_id,
    list_pending_registrations,
    set_user_active,
    set_user_approval_state,
)
from src.api.schemas import AdminPendingResident, AdminResidentRow, OkResponse
from src.api.services.audit_service import write_audit_log

router = APIRouter(prefix="/admin", tags=["Admin"])


@router.get(
    "/registrations/pending",
    response_model=list[AdminPendingResident],
    summary="List pending resident registrations",
    operation_id="admin_pending_registrations",
)
def pending(payload=Depends(require_admin)) -> list[AdminPendingResident]:
    rows = list_pending_registrations()
    return [
        AdminPendingResident(
            id=str(r["id"]),
            name=r["full_name"],
            unitNumber=r["unit_number"],
            email=r.get("email"),
            phone=r.get("phone"),
            createdAt=r["created_at"].isoformat(),
        )
        for r in rows
    ]


@router.post(
    "/registrations/{resident_id}/approve",
    response_model=OkResponse,
    summary="Approve a resident registration",
    operation_id="admin_approve_registration",
)
def approve(resident_id: str, request: Request, payload=Depends(require_admin)) -> OkResponse:
    profile = get_profile_by_id(resident_id)
    if not profile or not profile.get("user_id"):
        raise HTTPException(status_code=404, detail="Resident not found")
    set_user_approval_state(str(profile["user_id"]), "approved")
    write_audit_log(
        actor_user_id=payload.sub,
        action="admin.registration.approve",
        entity_type="app_user",
        entity_id=str(profile["user_id"]),
        request=request,
        details={"resident_id": resident_id},
    )
    return OkResponse(ok=True)


@router.post(
    "/registrations/{resident_id}/reject",
    response_model=OkResponse,
    summary="Reject a resident registration",
    operation_id="admin_reject_registration",
)
def reject(resident_id: str, request: Request, payload=Depends(require_admin)) -> OkResponse:
    profile = get_profile_by_id(resident_id)
    if not profile or not profile.get("user_id"):
        raise HTTPException(status_code=404, detail="Resident not found")
    set_user_approval_state(str(profile["user_id"]), "rejected")
    write_audit_log(
        actor_user_id=payload.sub,
        action="admin.registration.reject",
        entity_type="app_user",
        entity_id=str(profile["user_id"]),
        request=request,
        details={"resident_id": resident_id},
    )
    return OkResponse(ok=True)


@router.get(
    "/residents",
    response_model=list[AdminResidentRow],
    summary="List residents (admin)",
    operation_id="admin_list_residents",
)
def list_residents(payload=Depends(require_admin)) -> list[AdminResidentRow]:
    rows = admin_list_residents()
    out: list[AdminResidentRow] = []
    for r in rows:
        status = "active"
        if r.get("approval_state") == "pending":
            status = "pending"
        elif not bool(r.get("is_active", True)):
            status = "disabled"
        out.append(
            AdminResidentRow(
                id=str(r["id"]),
                name=r["full_name"],
                unitNumber=r["unit_number"],
                email=r.get("email"),
                phone=r.get("phone"),
                status=status,  # type: ignore[arg-type]
            )
        )
    return out


@router.post(
    "/residents/{resident_id}/disable",
    response_model=OkResponse,
    summary="Disable a resident's user account",
    operation_id="admin_disable_resident",
)
def disable(resident_id: str, request: Request, payload=Depends(require_admin)) -> OkResponse:
    profile = get_profile_by_id(resident_id)
    if not profile or not profile.get("user_id"):
        raise HTTPException(status_code=404, detail="Resident not found")
    set_user_active(str(profile["user_id"]), False)
    write_audit_log(
        actor_user_id=payload.sub,
        action="admin.resident.disable",
        entity_type="app_user",
        entity_id=str(profile["user_id"]),
        request=request,
        details={"resident_id": resident_id},
    )
    return OkResponse(ok=True)


@router.post(
    "/residents/{resident_id}/enable",
    response_model=OkResponse,
    summary="Enable a resident's user account",
    operation_id="admin_enable_resident",
)
def enable(resident_id: str, request: Request, payload=Depends(require_admin)) -> OkResponse:
    profile = get_profile_by_id(resident_id)
    if not profile or not profile.get("user_id"):
        raise HTTPException(status_code=404, detail="Resident not found")
    set_user_active(str(profile["user_id"]), True)
    write_audit_log(
        actor_user_id=payload.sub,
        action="admin.resident.enable",
        entity_type="app_user",
        entity_id=str(profile["user_id"]),
        request=request,
        details={"resident_id": resident_id},
    )
    return OkResponse(ok=True)
