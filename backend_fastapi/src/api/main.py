import os

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


def _csv_env(name: str, default: str) -> list[str]:
    """Parse a comma-separated env var into a list."""
    raw = os.getenv(name, default).strip()
    if not raw:
        return []
    return [part.strip() for part in raw.split(",") if part.strip()]


app = FastAPI(
    title="Resident Directory Backend API",
    description=(
        "Secure resident directory backend with RBAC, privacy controls, announcements, and audit logging.\n\n"
        "Auth: Use `Authorization: Bearer <token>` header."
    ),
    version="1.0.0",
    openapi_tags=openapi_tags,
)

# CORS configuration:
# - Browsers disallow `Access-Control-Allow-Origin: *` when credentials are allowed.
# - We therefore default to explicit localhost origins and allow overriding via ALLOWED_ORIGINS.
allowed_origins = _csv_env("ALLOWED_ORIGINS", "http://localhost:3000")
allowed_headers = _csv_env("ALLOWED_HEADERS", "Content-Type,Authorization")
allowed_methods = _csv_env("ALLOWED_METHODS", "GET,POST,PUT,DELETE,PATCH,OPTIONS")

app.add_middleware(
    CORSMiddleware,
    allow_origins=allowed_origins,
    allow_credentials=True,
    allow_methods=allowed_methods,
    allow_headers=allowed_headers,
)


@app.get("/", response_model=HealthResponse, tags=["Auth"], summary="Health check", operation_id="health_check_root")
def health_check() -> HealthResponse:
    """Health check endpoint.

    Returns:
        HealthResponse: service status message.
    """
    return HealthResponse(message="Healthy")


@app.get(
    "/healthz",
    response_model=HealthResponse,
    tags=["Auth"],
    summary="Health check (compat)",
    description="Alias for `/` used by some deployments/frontends.",
    operation_id="health_check_healthz",
)
def health_check_healthz() -> HealthResponse:
    """Health check endpoint (compat alias).

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
