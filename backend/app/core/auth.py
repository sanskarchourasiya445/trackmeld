"""TrackMeld Server-Side Authorization Boundary.

Provides token and API-key verification, role-based access control,
and explicit permission enforcement across TrackMeld API routes.

In demo/prototype mode, unauthenticated requests default to a read-only viewer.
Requests with invalid tokens or API keys are rejected with HTTP 401 Unauthorized.
Requests lacking required permissions are rejected with HTTP 403 Forbidden.
"""

from enum import Enum
from typing import List, Optional, Callable
from pydantic import BaseModel, Field
from fastapi import Request, HTTPException, status, Depends
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials

from backend.app.config import (
    get_settings,
    PROHIBITED_PRODUCTION_TOKENS,
    MIN_PRODUCTION_TOKEN_LENGTH,
)

security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MAINTENANCE_PLANNER = "MAINTENANCE_PLANNER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


ROLE_DEFAULT_PERMISSIONS: dict[UserRole, set[str]] = {
    UserRole.ADMIN: {"*"},
    UserRole.OPERATOR: {"read:reference", "read:operational", "plan:review", "plan:approve", "plan:reject"},
    UserRole.MAINTENANCE_PLANNER: {"read:reference", "read:operational", "write:operational", "plan:review"},
    UserRole.VIEWER: {"read:reference", "read:operational"},
}


class AuthUser(BaseModel):
    user_id: str
    username: str
    role: UserRole
    permissions: List[str] = Field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        if self.role == UserRole.ADMIN or "*" in self.permissions:
            return True
        if permission in self.permissions:
            return True
        if ":" in permission:
            action, res = permission.split(":", 1)
            flipped = f"{res}:{action}"
            if flipped in self.permissions:
                return True
        # Only fallback to role default permissions if no explicit permissions were specified
        if not self.permissions:
            try:
                role_enum = UserRole(self.role) if not isinstance(self.role, UserRole) else self.role
                role_perms = ROLE_DEFAULT_PERMISSIONS.get(role_enum, set())
                if "*" in role_perms or permission in role_perms:
                    return True
            except (ValueError, KeyError):
                pass
        return False


# Pre-configured test/demo tokens and API keys (strictly active only in non-production)
DEMO_CREDENTIALS = {
    "admin-token-2026": AuthUser(
        user_id="USR-ADMIN-01",
        username="chief_operations_admin",
        role=UserRole.ADMIN,
        permissions=["*"],
    ),
    "approver-token-2026": AuthUser(
        user_id="USR-APPR-01",
        username="divisional_operations_manager",
        role=UserRole.OPERATOR,
        permissions=["read:reference", "read:operational", "plan:review", "plan:approve", "plan:reject"],
    ),
    "planner-token-2026": AuthUser(
        user_id="USR-PLAN-01",
        username="senior_planner_dli",
        role=UserRole.MAINTENANCE_PLANNER,
        permissions=["read:reference", "read:operational", "write:operational", "plan:review"],
    ),
    "viewer-token-2026": AuthUser(
        user_id="USR-VIEW-01",
        username="guest_auditor",
        role=UserRole.VIEWER,
        permissions=["read:reference", "read:operational"],
    ),
    "restricted-token-2026": AuthUser(
        user_id="USR-RESTR-01",
        username="restricted_external",
        role=UserRole.VIEWER,
        permissions=["read:reference"],  # Lacks read:operational
    ),
}

# Backwards compatibility alias for tests referencing KNOWN_CREDENTIALS
KNOWN_CREDENTIALS = DEMO_CREDENTIALS

DEFAULT_DEMO_USER = AuthUser(
    user_id="USR-DEMO-VIEWER",
    username="demo_planner_viewer",
    role=UserRole.VIEWER,
    permissions=["read:reference", "read:operational"],
)


def get_active_credentials() -> dict[str, AuthUser]:
    """Retrieve active credentials registry based on environment and configuration."""
    settings = get_settings()
    creds: dict[str, AuthUser] = {}

    # Demo credentials only loaded if explicitly enabled in permitted non-production environment
    if settings.is_demo_auth_active:
        creds.update(DEMO_CREDENTIALS)

    # Apply configuration-driven tokens from environment
    role_tokens = [
        (settings.AUTH_ADMIN_TOKEN, "USR-ADMIN-PROD", "production_admin", UserRole.ADMIN, ["*"]),
        (settings.AUTH_APPROVER_TOKEN, "USR-APPR-PROD", "production_approver", UserRole.OPERATOR, ["read:reference", "read:operational", "plan:review", "plan:approve", "plan:reject"]),
        (settings.AUTH_PLANNER_TOKEN, "USR-PLAN-PROD", "production_planner", UserRole.MAINTENANCE_PLANNER, ["read:reference", "read:operational", "write:operational", "plan:review"]),
        (settings.AUTH_VIEWER_TOKEN, "USR-VIEW-PROD", "production_viewer", UserRole.VIEWER, ["read:reference", "read:operational"]),
    ]

    for token, uid, uname, role, perms in role_tokens:
        if token:
            if settings.is_production:
                clean = token.strip()
                if clean.lower() in PROHIBITED_PRODUCTION_TOKENS or len(clean) < MIN_PRODUCTION_TOKEN_LENGTH:
                    continue
            creds[token] = AuthUser(
                user_id=uid,
                username=uname,
                role=role,
                permissions=perms,
            )

    return creds


async def get_current_user(
    request: Request,
    auth_creds: Optional[HTTPAuthorizationCredentials] = Depends(security),
) -> AuthUser:
    """Extract and validate credentials from Authorization Bearer header or X-API-Key."""
    # 1. Check HTTP Bearer Token
    token = None
    if auth_creds and auth_creds.credentials:
        token = auth_creds.credentials
    elif "X-API-Key" in request.headers:
        token = request.headers.get("X-API-Key")

    if token is not None:
        active_creds = get_active_credentials()
        user = active_creds.get(token)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail={
                    "error": {
                        "code": "UNAUTHORIZED",
                        "message": "Invalid authentication credentials provided.",
                    }
                },
                headers={"WWW-Authenticate": "Bearer"},
            )
        return user

    # 2. Check if anonymous demo user is explicitly permitted and active
    settings = get_settings()
    if settings.is_demo_auth_active:
        return DEFAULT_DEMO_USER

    # 3. Outside explicitly enabled demo mode, unauthenticated access is strictly forbidden (fail closed)
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={
            "error": {
                "code": "AUTHENTICATION_REQUIRED",
                "message": "Authentication credentials are required.",
            }
        },
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_permission(permission: str) -> Callable:
    """Enforce that the authenticated user possesses the required permission."""
    async def permission_dependency(user: AuthUser = Depends(get_current_user)) -> AuthUser:
        if not user.has_permission(permission):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail={
                    "error": {
                        "code": "FORBIDDEN",
                        "message": f"User '{user.username}' lacking required permission '{permission}'.",
                    }
                },
            )
        return user
    return permission_dependency
