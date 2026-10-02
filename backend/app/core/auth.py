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

security = HTTPBearer(auto_error=False)


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    MAINTENANCE_PLANNER = "MAINTENANCE_PLANNER"
    OPERATOR = "OPERATOR"
    VIEWER = "VIEWER"


class AuthUser(BaseModel):
    user_id: str
    username: str
    role: UserRole
    permissions: List[str] = Field(default_factory=list)

    def has_permission(self, permission: str) -> bool:
        if self.role == UserRole.ADMIN or "*" in self.permissions:
            return True
        return permission in self.permissions


# Pre-configured test/demo tokens and API keys
KNOWN_CREDENTIALS = {
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

DEFAULT_DEMO_USER = AuthUser(
    user_id="USR-DEMO-VIEWER",
    username="demo_planner_viewer",
    role=UserRole.VIEWER,
    permissions=["read:reference", "read:operational"],
)


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
        user = KNOWN_CREDENTIALS.get(token)
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

    # 2. In prototype environment, default to safe read-only demo user
    return DEFAULT_DEMO_USER


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
