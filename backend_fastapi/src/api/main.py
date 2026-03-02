from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from src.api.routes.admin import router as admin_router
from src.api.routes.announcements import router as announcements_router
from src.api.routes.auth import router as auth_router
from src.api.routes.directory import router as directory_router
from src.api.routes.profile import router as profile_router
from src.api.schemas import HealthResponse

openapi_tags = [
    {"name": "Auth", "description": "Authentication (password + OTP) and session user endpoints."},
    {"name": "Directory", "description": "Resident directory search and resident profile view (privacy enforced)."},
    {"name": "Profile", "description": "Current user profile management."},
    {"name": "Announcements", "description": "Announcements feed and admin publishing."},
    {"name": "Admin", "description": "Admin approvals and resident account management."},
]

app = FastAPI(
    title="Resident Directory Backend API",
    description=(
        "Secure resident directory backend with RBAC, privacy controls, announcements, and audit logging.\n\n"
        "Auth: Use `Authorization: Bearer <token>` header."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=HealthResponse, tags=["Auth"], summary="Health check", operation_id="health_check")
def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse: service status message.
    """
    return HealthResponse(message="Healthy")


# Routers (aligned to frontend expectations under src/lib/api.ts)
app.include_router(auth_router)
app.include_router(directory_router)
app.include_router(profile_router)
app.include_router(announcements_router)
app.include_router(admin_router)
