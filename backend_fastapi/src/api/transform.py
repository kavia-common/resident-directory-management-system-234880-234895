from __future__ import annotations

from datetime import datetime
from typing import Any, Dict, List, Optional

from src.api.schemas import Announcement, ResidentDirectoryItem, ResidentProfile, PrivacySettings


def _iso(dt: Any) -> str:
    if isinstance(dt, datetime):
        return dt.isoformat()
    return str(dt)


def _json_list_to_string(value: Any) -> Optional[str]:
    """Frontend expects string fields for complex info (MVP)."""
    if value is None:
        return None
    if isinstance(value, list):
        return ", ".join([str(x) for x in value])
    # value may be jsonb already decoded by psycopg to python object
    return str(value)


def _string_to_list_csv(value: Optional[str]) -> List[str]:
    if not value:
        return []
    return [v.strip() for v in value.split(",") if v.strip()]


# PUBLIC_INTERFACE
def row_to_announcement(row: Dict[str, Any]) -> Announcement:
    """Convert announcement DB row to API model."""
    return Announcement(
        id=str(row["id"]),
        title=row["title"],
        body=row["body"],
        createdAt=_iso(row["created_at"]),
    )


def _privacy_from_row(row: Dict[str, Any]) -> PrivacySettings:
    return PrivacySettings(
        showEmailToResidents=bool(row.get("show_email", False)),
        showPhoneToResidents=bool(row.get("show_phone", False)),
        showFamilyToResidents=bool(row.get("show_family_members", False)),
        showVehicleToResidents=bool(row.get("show_vehicles", False)),
        showEmergencyToResidents=bool(row.get("show_emergency_contacts", False)),
        showInterestsToResidents=bool(row.get("show_interests", False)),
    )


# PUBLIC_INTERFACE
def row_to_profile(row: Dict[str, Any], *, viewer_role: str, viewer_is_self: bool) -> ResidentProfile:
    """Convert full resident+privacy row to ResidentProfile with privacy enforced."""
    privacy = _privacy_from_row(row)

    allow_full = viewer_is_self or viewer_role in ("staff", "admin")

    email = row.get("email")
    phone = row.get("phone")
    photo_url = row.get("photo_url")

    if not allow_full:
        if not privacy.showEmailToResidents:
            email = None
        if not privacy.showPhoneToResidents:
            phone = None
        # photo controlled by show_photo (defaults true)
        if not bool(row.get("show_photo", True)):
            photo_url = None

    family_members = row.get("family_members")
    vehicles = row.get("vehicles")
    emergency_contacts = row.get("emergency_contacts")
    interests = row.get("interests")

    if not allow_full:
        if not privacy.showFamilyToResidents:
            family_members = None
        if not privacy.showVehicleToResidents:
            vehicles = None
        if not privacy.showEmergencyToResidents:
            emergency_contacts = None
        if not privacy.showInterestsToResidents:
            interests = None

    return ResidentProfile(
        id=str(row["id"]),
        name=row["full_name"],
        unitNumber=row["unit_number"],
        building=row.get("building"),
        floor=row.get("floor"),
        email=email,
        phone=phone,
        familyMembers=_json_list_to_string(family_members) if family_members is not None else None,
        vehicleDetails=_json_list_to_string(vehicles) if vehicles is not None else None,
        emergencyContact=_json_list_to_string(emergency_contacts) if emergency_contacts is not None else None,
        interests=",".join(interests) if isinstance(interests, list) else (_json_list_to_string(interests) if interests is not None else None),
        photoUrl=photo_url,
        privacy=privacy,
    )


# PUBLIC_INTERFACE
def row_to_directory_item(row: Dict[str, Any], *, viewer_role: str, viewer_is_self: bool) -> ResidentDirectoryItem:
    """Convert directory search row to ResidentDirectoryItem with privacy enforced."""
    allow_full = viewer_is_self or viewer_role in ("staff", "admin")
    email = row.get("email")
    phone = row.get("phone")
    photo_url = row.get("photo_url")

    if not allow_full:
        if not bool(row.get("show_email", False)):
            email = None
        if not bool(row.get("show_phone", False)):
            phone = None
        if not bool(row.get("show_photo", True)):
            photo_url = None

    return ResidentDirectoryItem(
        id=str(row["id"]),
        name=row["full_name"],
        unitNumber=row["unit_number"],
        building=row.get("building"),
        floor=row.get("floor"),
        interests=row.get("interests"),
        photoUrl=photo_url,
        email=email,
        phone=phone,
    )
