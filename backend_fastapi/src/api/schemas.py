from __future__ import annotations

from typing import List, Literal, Optional

from pydantic import BaseModel, Field


UserRole = Literal["resident", "staff", "admin"]
ApprovalState = Literal["pending", "approved", "rejected", "suspended"]


class SessionUser(BaseModel):
    id: str = Field(..., description="User id (uuid).")
    email: Optional[str] = Field(default=None, description="User email.")
    phone: Optional[str] = Field(default=None, description="User phone.")
    name: Optional[str] = Field(default=None, description="Display name.")
    role: UserRole = Field(..., description="User role.")


class AuthRegisterRequest(BaseModel):
    email: Optional[str] = Field(default=None, description="Email address.")
    phone: Optional[str] = Field(default=None, description="Phone number.")
    invitationCode: Optional[str] = Field(default=None, description="Invitation code (optional).")
    password: Optional[str] = Field(default=None, description="Password (optional for OTP-only users).")
    name: str = Field(..., description="Full name.")
    unitNumber: str = Field(..., description="Unit number.")


class AuthLoginRequest(BaseModel):
    identifier: str = Field(..., description="Email or phone.")
    password: Optional[str] = Field(default=None, description="Password (optional).")


class AuthOtpRequest(BaseModel):
    identifier: str = Field(..., description="Email or phone.")


class AuthOtpVerifyRequest(BaseModel):
    identifier: str = Field(..., description="Email or phone.")
    otp: str = Field(..., description="One-time passcode.")


class AuthResponse(BaseModel):
    token: str = Field(..., description="JWT access token.")
    user: SessionUser = Field(..., description="Session user info.")
    approvalStatus: Optional[Literal["pending", "approved", "rejected"]] = Field(
        default=None, description="Approval state (for UI routing)."
    )


class PrivacySettings(BaseModel):
    showEmailToResidents: bool = Field(..., description="Whether email is visible to other residents.")
    showPhoneToResidents: bool = Field(..., description="Whether phone is visible to other residents.")
    showFamilyToResidents: bool = Field(..., description="Whether family member info is visible to other residents.")
    showVehicleToResidents: bool = Field(..., description="Whether vehicle info is visible to other residents.")
    showEmergencyToResidents: bool = Field(..., description="Whether emergency contact info is visible to other residents.")
    showInterestsToResidents: bool = Field(..., description="Whether interests are visible to other residents.")


class ResidentProfile(BaseModel):
    id: str = Field(..., description="Resident profile id.")
    name: str = Field(..., description="Full name.")
    unitNumber: str = Field(..., description="Unit number.")
    building: Optional[str] = Field(default=None, description="Building.")
    floor: Optional[str] = Field(default=None, description="Floor.")

    email: Optional[str] = Field(default=None, description="Email (privacy-aware).")
    phone: Optional[str] = Field(default=None, description="Phone (privacy-aware).")

    familyMembers: Optional[str] = Field(default=None, description="Family members (serialized string for UI).")
    vehicleDetails: Optional[str] = Field(default=None, description="Vehicle details (serialized string for UI).")
    emergencyContact: Optional[str] = Field(default=None, description="Emergency contacts (serialized string for UI).")
    interests: Optional[str] = Field(default=None, description="Interests (serialized string for UI).")

    photoUrl: Optional[str] = Field(default=None, description="Photo URL (privacy-aware).")

    privacy: PrivacySettings = Field(..., description="Privacy settings.")


class UpdateResidentProfileRequest(BaseModel):
    name: str
    unitNumber: str
    building: Optional[str] = None
    floor: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None
    familyMembers: Optional[str] = None
    vehicleDetails: Optional[str] = None
    emergencyContact: Optional[str] = None
    interests: Optional[str] = None
    photoUrl: Optional[str] = None
    privacy: PrivacySettings


class ResidentDirectoryItem(BaseModel):
    id: str
    name: str
    unitNumber: str
    building: Optional[str] = None
    floor: Optional[str] = None
    interests: Optional[List[str]] = None
    photoUrl: Optional[str] = None
    email: Optional[str] = None
    phone: Optional[str] = None


class Announcement(BaseModel):
    id: str
    title: str
    body: str
    createdAt: str


class AnnouncementCreateRequest(BaseModel):
    title: str = Field(..., description="Announcement title.")
    body: str = Field(..., description="Announcement body.")


class AdminPendingResident(BaseModel):
    id: str
    name: str
    unitNumber: str
    email: Optional[str] = None
    phone: Optional[str] = None
    createdAt: str


class AdminResidentRow(BaseModel):
    id: str
    name: str
    unitNumber: str
    email: Optional[str] = None
    phone: Optional[str] = None
    status: Literal["active", "disabled", "pending"]


class OkResponse(BaseModel):
    ok: bool = Field(..., description="Operation success flag.")


class HealthResponse(BaseModel):
    message: str = Field(..., description="Healthcheck message.")
