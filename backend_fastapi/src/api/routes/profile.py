from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.core.rbac import require_approved
from src.api.repositories import get_profile_by_user_id, update_profile_and_privacy
from src.api.schemas import ResidentProfile, UpdateResidentProfileRequest
from src.api.services.audit_service import write_audit_log
from src.api.transform import _string_to_list_csv, row_to_profile

router = APIRouter(prefix="/profile", tags=["Profile"])


@router.get(
    "/me",
    response_model=ResidentProfile,
    summary="Get current user's resident profile",
    operation_id="profile_me_get",
)
def get_my_profile(payload=Depends(require_approved)) -> ResidentProfile:
    row = get_profile_by_user_id(payload.sub)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")
    return row_to_profile(row, viewer_role=payload.role, viewer_is_self=True)


@router.put(
    "/me",
    response_model=ResidentProfile,
    summary="Update current user's resident profile and privacy settings",
    operation_id="profile_me_put",
)
def update_my_profile(body: UpdateResidentProfileRequest, request: Request, payload=Depends(require_approved)) -> ResidentProfile:
    row = get_profile_by_user_id(payload.sub)
    if not row:
        raise HTTPException(status_code=404, detail="Profile not found")

    updated = update_profile_and_privacy(
        resident_id=str(row["id"]),
        full_name=body.name,
        unit_number=body.unitNumber,
        building=body.building,
        floor=body.floor,
        email=body.email,
        phone=body.phone,
        family_members=_string_to_list_csv(body.familyMembers),
        vehicles=_string_to_list_csv(body.vehicleDetails),
        emergency_contacts=_string_to_list_csv(body.emergencyContact),
        interests=_string_to_list_csv(body.interests),
        photo_url=body.photoUrl,
        show_email=body.privacy.showEmailToResidents,
        show_phone=body.privacy.showPhoneToResidents,
        show_family_members=body.privacy.showFamilyToResidents,
        show_vehicles=body.privacy.showVehicleToResidents,
        show_emergency_contacts=body.privacy.showEmergencyToResidents,
        show_interests=body.privacy.showInterestsToResidents,
    )

    write_audit_log(
        actor_user_id=payload.sub,
        action="profile.update",
        entity_type="resident_profile",
        entity_id=str(row["id"]),
        request=request,
        details={},
    )

    return row_to_profile(updated, viewer_role=payload.role, viewer_is_self=True)
