from __future__ import annotations

import json
from typing import Any, Dict, List, Optional

from src.api.core.db import execute, execute_returning_one, fetch_all, fetch_one


# --------------------
# Users
# --------------------
def find_user_by_identifier(identifier: str) -> Optional[Dict[str, Any]]:
    ident = identifier.strip().lower()
    return fetch_one(
        """
        SELECT id, email, phone, password_hash, role::text AS role, approval_state::text AS approval_state, is_active
        FROM app_user
        WHERE (email = %s OR phone = %s)
        """,
        (ident, ident),
    )


def get_user_by_id(user_id: str) -> Optional[Dict[str, Any]]:
    return fetch_one(
        """
        SELECT id, email, phone, password_hash, role::text AS role, approval_state::text AS approval_state, is_active
        FROM app_user
        WHERE id = %s
        """,
        (user_id,),
    )


def create_user(*, email: Optional[str], phone: Optional[str], password_hash: Optional[str]) -> Dict[str, Any]:
    return execute_returning_one(
        """
        INSERT INTO app_user(email, phone, password_hash)
        VALUES (%s, %s, %s)
        RETURNING id, email, phone, role::text AS role, approval_state::text AS approval_state, is_active, created_at
        """,
        (email.lower().strip() if email else None, phone.strip() if phone else None, password_hash),
    )  # type: ignore[return-value]


def set_user_approval_state(user_id: str, new_state: str) -> None:
    execute("UPDATE app_user SET approval_state = %s WHERE id = %s", (new_state, user_id))


def set_user_active(user_id: str, is_active: bool) -> None:
    execute("UPDATE app_user SET is_active = %s WHERE id = %s", (is_active, user_id))


# --------------------
# Resident profiles + privacy
# --------------------
def create_resident_profile_for_user(
    *,
    user_id: str,
    full_name: str,
    unit_number: str,
    email: Optional[str],
    phone: Optional[str],
) -> Dict[str, Any]:
    profile = execute_returning_one(
        """
        INSERT INTO resident_profile(user_id, full_name, unit_number, email, phone)
        VALUES (%s, %s, %s, %s, %s)
        RETURNING id, user_id, full_name, unit_number, building, floor, photo_url, email, phone,
                  family_members, vehicles, emergency_contacts, interests, bio, created_at, updated_at
        """,
        (user_id, full_name, unit_number, email.lower().strip() if email else None, phone.strip() if phone else None),
    )
    # Create default privacy row
    execute(
        """
        INSERT INTO resident_privacy_settings(resident_id)
        VALUES (%s)
        ON CONFLICT (resident_id) DO NOTHING
        """,
        (profile["id"],),
    )
    return profile  # type: ignore[return-value]


def get_profile_by_user_id(user_id: str) -> Optional[Dict[str, Any]]:
    return fetch_one(
        """
        SELECT rp.*,
               ps.show_email, ps.show_phone, ps.show_photo, ps.show_family_members, ps.show_vehicles,
               ps.show_emergency_contacts, ps.show_interests, ps.allow_in_app_messages_only
        FROM resident_profile rp
        JOIN resident_privacy_settings ps ON ps.resident_id = rp.id
        WHERE rp.user_id = %s
        """,
        (user_id,),
    )


def get_profile_by_id(resident_id: str) -> Optional[Dict[str, Any]]:
    return fetch_one(
        """
        SELECT rp.*,
               ps.show_email, ps.show_phone, ps.show_photo, ps.show_family_members, ps.show_vehicles,
               ps.show_emergency_contacts, ps.show_interests, ps.allow_in_app_messages_only
        FROM resident_profile rp
        JOIN resident_privacy_settings ps ON ps.resident_id = rp.id
        WHERE rp.id = %s
        """,
        (resident_id,),
    )


def update_profile_and_privacy(
    *,
    resident_id: str,
    full_name: str,
    unit_number: str,
    building: Optional[str],
    floor: Optional[str],
    email: Optional[str],
    phone: Optional[str],
    family_members: List[str],
    vehicles: List[str],
    emergency_contacts: List[str],
    interests: List[str],
    photo_url: Optional[str],
    show_email: bool,
    show_phone: bool,
    show_family_members: bool,
    show_vehicles: bool,
    show_emergency_contacts: bool,
    show_interests: bool,
) -> Dict[str, Any]:
    execute_returning_one(
        """
        UPDATE resident_profile
        SET full_name=%s, unit_number=%s, building=%s, floor=%s, email=%s, phone=%s,
            family_members=%s::jsonb, vehicles=%s::jsonb, emergency_contacts=%s::jsonb, interests=%s,
            photo_url=%s
        WHERE id=%s
        RETURNING *
        """,
        (
            full_name,
            unit_number,
            building,
            floor,
            email.lower().strip() if email else None,
            phone.strip() if phone else None,
            json.dumps(family_members),
            json.dumps(vehicles),
            json.dumps(emergency_contacts),
            interests,
            photo_url,
            resident_id,
        ),
    )
    execute(
        """
        UPDATE resident_privacy_settings
        SET show_email=%s, show_phone=%s, show_family_members=%s, show_vehicles=%s,
            show_emergency_contacts=%s, show_interests=%s
        WHERE resident_id=%s
        """,
        (
            show_email,
            show_phone,
            show_family_members,
            show_vehicles,
            show_emergency_contacts,
            show_interests,
            resident_id,
        ),
    )
    # Return with privacy fields
    return get_profile_by_id(resident_id)  # type: ignore[return-value]


def directory_search(*, q: Optional[str], building: Optional[str], floor: Optional[str], interest: Optional[str]) -> List[Dict[str, Any]]:
    params: List[Any] = []
    where: List[str] = []

    if q:
        where.append("rp.full_name ILIKE %s")
        params.append(f"%{q}%")
    if building:
        where.append("rp.building = %s")
        params.append(building)
    if floor:
        where.append("rp.floor = %s")
        params.append(floor)
    if interest:
        where.append("%s = ANY(rp.interests)")
        params.append(interest)

    where_sql = " AND ".join(where)
    if where_sql:
        where_sql = "WHERE " + where_sql

    return fetch_all(
        f"""
        SELECT rp.id, rp.full_name, rp.unit_number, rp.building, rp.floor, rp.interests, rp.photo_url,
               rp.email, rp.phone,
               ps.show_email, ps.show_phone, ps.show_photo
        FROM resident_profile rp
        JOIN resident_privacy_settings ps ON ps.resident_id = rp.id
        {where_sql}
        ORDER BY rp.full_name ASC
        LIMIT 200
        """,
        params,
    )


# --------------------
# Announcements
# --------------------
def list_announcements() -> List[Dict[str, Any]]:
    return fetch_all(
        """
        SELECT id, title, body, created_at
        FROM announcement
        WHERE is_published = true
        ORDER BY published_at DESC
        LIMIT 100
        """
    )


def create_announcement(*, title: str, body: str, created_by: str) -> Dict[str, Any]:
    return execute_returning_one(
        """
        INSERT INTO announcement(title, body, created_by, is_published, published_at)
        VALUES (%s, %s, %s, true, now())
        RETURNING id, title, body, created_at
        """,
        (title, body, created_by),
    )  # type: ignore[return-value]


# --------------------
# Admin
# --------------------
def list_pending_registrations() -> List[Dict[str, Any]]:
    return fetch_all(
        """
        SELECT rp.id, rp.full_name, rp.unit_number, rp.email, rp.phone, au.created_at
        FROM resident_profile rp
        JOIN app_user au ON au.id = rp.user_id
        WHERE au.approval_state = 'pending'
        ORDER BY au.created_at ASC
        LIMIT 200
        """
    )


def admin_list_residents() -> List[Dict[str, Any]]:
    return fetch_all(
        """
        SELECT rp.id, rp.full_name, rp.unit_number, rp.email, rp.phone,
               au.approval_state::text AS approval_state,
               au.is_active
        FROM resident_profile rp
        LEFT JOIN app_user au ON au.id = rp.user_id
        ORDER BY rp.full_name ASC
        LIMIT 500
        """
    )
