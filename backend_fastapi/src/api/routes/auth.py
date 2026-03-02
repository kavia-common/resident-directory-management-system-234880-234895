from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException, Request

from src.api.core.rbac import require_authenticated
from src.api.core.security import create_access_token, hash_password, verify_password
from src.api.core.settings import get_settings
from src.api.repositories import create_resident_profile_for_user, create_user, find_user_by_identifier, get_profile_by_user_id, get_user_by_id
from src.api.schemas import AuthLoginRequest, AuthOtpRequest, AuthOtpVerifyRequest, AuthRegisterRequest, AuthResponse, SessionUser
from src.api.services.audit_service import write_audit_log
from src.api.services.otp_service import create_and_store_otp, verify_and_consume_otp

router = APIRouter(prefix="/auth", tags=["Auth"])


def _session_user_from_user_row(user_row: dict, profile_row: dict | None) -> SessionUser:
    return SessionUser(
        id=str(user_row["id"]),
        email=user_row.get("email"),
        phone=user_row.get("phone"),
        name=profile_row["full_name"] if profile_row else None,
        role=user_row["role"],
    )


@router.post(
    "/register",
    response_model=AuthResponse,
    summary="Register a new resident account",
    description="Creates app_user + resident_profile. New account may be pending approval based on policy.",
    operation_id="auth_register",
)
def register(payload: AuthRegisterRequest, request: Request) -> AuthResponse:
    settings = get_settings()

    if not payload.email and not payload.phone:
        raise HTTPException(status_code=400, detail="Email or phone required")

    existing = find_user_by_identifier(payload.email or payload.phone or "")
    if existing:
        raise HTTPException(status_code=409, detail="User already exists")

    pw_hash = hash_password(payload.password) if payload.password else None
    user = create_user(email=payload.email, phone=payload.phone, password_hash=pw_hash)
    profile = create_resident_profile_for_user(
        user_id=str(user["id"]),
        full_name=payload.name,
        unit_number=payload.unitNumber,
        email=payload.email,
        phone=payload.phone,
    )

    write_audit_log(
        actor_user_id=str(user["id"]),
        action="auth.register",
        entity_type="app_user",
        entity_id=str(user["id"]),
        request=request,
        details={"approval_state": user["approval_state"]},
    )

    token = create_access_token(
        user_id=str(user["id"]),
        role=user["role"],
        approval_state=user["approval_state"],
        is_active=bool(user["is_active"]),
    )
    approval_status = user["approval_state"] if settings.REQUIRE_ADMIN_APPROVAL else "approved"

    return AuthResponse(
        token=token,
        user=_session_user_from_user_row(user, profile),
        approvalStatus=approval_status if approval_status in ("pending", "approved", "rejected") else "pending",
    )


@router.post(
    "/login",
    response_model=AuthResponse,
    summary="Login with identifier + password (or identifier-only if OTP-only account)",
    operation_id="auth_login",
)
def login(payload: AuthLoginRequest, request: Request) -> AuthResponse:
    user = find_user_by_identifier(payload.identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="User is disabled")

    # Password login requires stored password_hash
    if payload.password:
        if not user.get("password_hash"):
            raise HTTPException(status_code=401, detail="Password not set; use OTP")
        if not verify_password(payload.password, user["password_hash"]):
            raise HTTPException(status_code=401, detail="Invalid credentials")
    else:
        # No password provided; force OTP path (frontend uses separate endpoints)
        raise HTTPException(status_code=400, detail="Password required for /auth/login. Use OTP endpoints.")

    profile = get_profile_by_user_id(str(user["id"]))
    token = create_access_token(
        user_id=str(user["id"]),
        role=user["role"],
        approval_state=user["approval_state"],
        is_active=bool(user["is_active"]),
    )

    write_audit_log(
        actor_user_id=str(user["id"]),
        action="auth.login",
        entity_type="app_user",
        entity_id=str(user["id"]),
        request=request,
        details={},
    )

    return AuthResponse(
        token=token,
        user=_session_user_from_user_row(user, profile),
        approvalStatus=user["approval_state"] if user["approval_state"] in ("pending", "approved", "rejected") else "pending",
    )


@router.post(
    "/otp/request",
    summary="Request an OTP for identifier",
    description="Generates an OTP for email/phone. Delivery via SMS/Email is out of scope; optional test bypass can return OTP.",
    operation_id="auth_request_otp",
)
def request_otp(payload: AuthOtpRequest, request: Request) -> dict:
    settings = get_settings()
    # We allow requesting OTP even if user doesn't exist (privacy), but verify will fail.
    otp = create_and_store_otp(payload.identifier)

    write_audit_log(
        actor_user_id=None,
        action="auth.otp.request",
        entity_type="auth_otp",
        entity_id=None,
        request=request,
        details={"identifier": payload.identifier},
    )

    if settings.OTP_TEST_BYPASS:
        return {"sent": True, "otp": otp}
    return {"sent": True}


@router.post(
    "/otp/verify",
    response_model=AuthResponse,
    summary="Verify OTP and create session",
    operation_id="auth_verify_otp",
)
def verify_otp(payload: AuthOtpVerifyRequest, request: Request) -> AuthResponse:
    user = find_user_by_identifier(payload.identifier)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid OTP")

    if not user["is_active"]:
        raise HTTPException(status_code=403, detail="User is disabled")

    if not verify_and_consume_otp(payload.identifier, payload.otp):
        raise HTTPException(status_code=401, detail="Invalid OTP")

    profile = get_profile_by_user_id(str(user["id"]))
    token = create_access_token(
        user_id=str(user["id"]),
        role=user["role"],
        approval_state=user["approval_state"],
        is_active=bool(user["is_active"]),
    )

    write_audit_log(
        actor_user_id=str(user["id"]),
        action="auth.otp.verify",
        entity_type="app_user",
        entity_id=str(user["id"]),
        request=request,
        details={},
    )

    return AuthResponse(
        token=token,
        user=_session_user_from_user_row(user, profile),
        approvalStatus=user["approval_state"] if user["approval_state"] in ("pending", "approved", "rejected") else "pending",
    )


@router.get(
    "/me",
    response_model=SessionUser,
    summary="Get current session user",
    operation_id="auth_me",
)
def me(payload=Depends(require_authenticated)) -> SessionUser:
    user = get_user_by_id(payload.sub)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    profile = get_profile_by_user_id(payload.sub)
    return _session_user_from_user_row(user, profile)
