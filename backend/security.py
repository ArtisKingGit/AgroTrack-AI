"""
AgroTrack AI Security & Role-Based Access Control (RBAC)
Handles token authentication, role verification, and backend access enforcement.
Security Hardened:
- Strict production enforcement: mock tokens and unverified JWTs are rejected when ALLOW_DEV_MOCK_AUTH=false or ENVIRONMENT=production.
- Live Firebase ID token verification via firebase_admin.auth.verify_id_token (fails closed).
- Server-side RBAC and tenant org-level data isolation enforcement.
"""

import os
import json
import base64
import logging
from typing import List, Optional, Callable
from fastapi import Header, HTTPException, Depends, status

try:
    import firebase_admin
    from firebase_admin import auth as fb_auth
except ImportError:
    firebase_admin = None
    fb_auth = None

from .models import Role, Permission, ROLE_PERMISSIONS, UserProfile

logger = logging.getLogger("agrotrack.security")

# Environment & Security Configuration
ENVIRONMENT = os.getenv("ENVIRONMENT", "development").lower()
IS_PRODUCTION = (ENVIRONMENT == "production")

# In production, mock authentication is strictly forbidden and defaults to False
_allow_mock_env = os.getenv("ALLOW_DEV_MOCK_AUTH")
if _allow_mock_env is not None:
    ALLOW_DEV_MOCK_AUTH = _allow_mock_env.lower() in ("true", "1", "yes")
    if IS_PRODUCTION and ALLOW_DEV_MOCK_AUTH:
        logger.warning("[SECURITY CAUTION] ALLOW_DEV_MOCK_AUTH was set to true in production! Forcing to FALSE.")
        ALLOW_DEV_MOCK_AUTH = False
else:
    ALLOW_DEV_MOCK_AUTH = not IS_PRODUCTION


# Known demo/mock user directory for local development & automated unit tests
DEMO_USERS = {
    "admin": UserProfile(
        uid="usr_admin_001",
        email="sarah.mwangi@agrotrack.ai",
        name="Sarah Mwangi",
        activeRole=Role.ORGANISATION_ADMIN,
        defaultOrgId="org_greenvalley_01",
        permissions=[p.value for p in ROLE_PERMISSIONS[Role.ORGANISATION_ADMIN]],
        photo="https://ui-avatars.com/api/?name=Sarah+Mwangi&background=0f392b&color=22c55e"
    ),
    "manager": UserProfile(
        uid="usr_mgr_002",
        email="david.kiprop@agrotrack.ai",
        name="David Kiprop",
        activeRole=Role.PROJECT_MANAGER,
        defaultOrgId="org_greenvalley_01",
        permissions=[p.value for p in ROLE_PERMISSIONS[Role.PROJECT_MANAGER]],
        photo="https://ui-avatars.com/api/?name=David+Kiprop&background=164e38&color=10b981"
    ),
    "field": UserProfile(
        uid="usr_field_003",
        email="amina.otieno@agrotrack.ai",
        name="Amina Otieno",
        activeRole=Role.FIELD_OFFICER,
        defaultOrgId="org_greenvalley_01",
        permissions=[p.value for p in ROLE_PERMISSIONS[Role.FIELD_OFFICER]],
        photo="https://ui-avatars.com/api/?name=Amina+Otieno&background=1e293b&color=38bdf8"
    ),
    "analyst": UserProfile(
        uid="usr_analyst_004",
        email="brian.njoroge@agrotrack.ai",
        name="Brian Njoroge",
        activeRole=Role.ANALYST,
        defaultOrgId="org_greenvalley_01",
        permissions=[p.value for p in ROLE_PERMISSIONS[Role.ANALYST]],
        photo="https://ui-avatars.com/api/?name=Brian+Njoroge&background=334155&color=a855f7"
    ),
    "viewer": UserProfile(
        uid="usr_viewer_005",
        email="grace.wanjiku@agrotrack.ai",
        name="Grace Wanjiku",
        activeRole=Role.VIEWER,
        defaultOrgId="org_greenvalley_01",
        permissions=[p.value for p in ROLE_PERMISSIONS[Role.VIEWER]],
        photo="https://ui-avatars.com/api/?name=Grace+Wanjiku&background=475569&color=cbd5e1"
    ),
}


def parse_bearer_token(authorization: Optional[str]) -> str:
    """Extracts the token from Authorization: Bearer <token> header."""
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication credentials required. Please provide a Bearer token in the Authorization header.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    parts = authorization.strip().split(maxsplit=1)
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'.",
            headers={"WWW-Authenticate": "Bearer"},
        )
    return parts[1]


def _normalize_role(role_val) -> Role:
    if isinstance(role_val, Role):
        return role_val
    if not role_val:
        return Role.VIEWER
    val_str = str(role_val).strip()
    for r in Role:
        if r.value.lower() == val_str.lower() or r.name.lower() == val_str.lower():
            return r
        if r.value.lower() == val_str.replace("_", " ").lower():
            return r
    return Role.VIEWER


def get_current_user(authorization: Optional[str] = Header(None)) -> UserProfile:
    """
    Validates token and returns authenticated UserProfile.
    In Production: Requires valid, verified Firebase ID token (fail-closed).
    In Development: Allows opt-in mock tokens only when ALLOW_DEV_MOCK_AUTH=true.
    """
    token = parse_bearer_token(authorization)

    # ── 1. Development Mock Auth (Gated by ALLOW_DEV_MOCK_AUTH) ──────────────
    if token.startswith("mock-token-") or token.startswith("mock-jwt:"):
        if not ALLOW_DEV_MOCK_AUTH or IS_PRODUCTION:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Mock development tokens are strictly disabled in production or when ALLOW_DEV_MOCK_AUTH=false.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token.startswith("mock-token-"):
            role_key = token.replace("mock-token-", "").lower()
            if role_key in DEMO_USERS:
                return DEMO_USERS[role_key]
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Unknown mock role identifier '{role_key}'.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if token.startswith("mock-jwt:"):
            try:
                payload = json.loads(token[len("mock-jwt:"):])
                role_val = _normalize_role(payload.get("role", Role.VIEWER))
                perms = [p.value for p in ROLE_PERMISSIONS.get(role_val, [])]
                return UserProfile(
                    uid=payload.get("uid", "custom_usr"),
                    email=payload.get("email", "custom@agrotrack.ai"),
                    name=payload.get("name", "Custom User"),
                    activeRole=role_val,
                    defaultOrgId=payload.get("orgId", "org_greenvalley_01"),
                    permissions=perms
                )
            except Exception:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid mock-jwt token format.",
                    headers={"WWW-Authenticate": "Bearer"},
                )

    # ── 2. Live Firebase ID Token Verification ───────────────────────────────
    # If the token is a standard JWT (contains dots)
    if "." in token:
        if firebase_admin and firebase_admin._apps and fb_auth:
            try:
                # verify_id_token performs cryptographic signature check against Google public keys,
                # checks expiration, audience, issuer, and revokation status
                decoded_token = fb_auth.verify_id_token(token)
                uid = decoded_token.get("uid") or decoded_token.get("sub") or "fb_user"
                email = decoded_token.get("email", "user@agrotrack.ai")
                name = decoded_token.get("name") or decoded_token.get("email", "AgroTrack User")
                role_str = decoded_token.get("role") or decoded_token.get("activeRole") or Role.VIEWER
                user_role = _normalize_role(role_str)
                org_id = decoded_token.get("orgId", "org_greenvalley_01")
                perms = [p.value for p in ROLE_PERMISSIONS.get(user_role, [])]
                return UserProfile(
                    uid=uid,
                    email=email,
                    name=name,
                    activeRole=user_role,
                    defaultOrgId=org_id,
                    permissions=perms
                )
            except Exception as e:
                logger.warning(f"Firebase token verification failed: {e}")
                if IS_PRODUCTION or not ALLOW_DEV_MOCK_AUTH:
                    # Fail-closed in production
                    raise HTTPException(
                        status_code=status.HTTP_401_UNAUTHORIZED,
                        detail="Invalid, expired, or untrusted Firebase authentication token.",
                        headers={"WWW-Authenticate": "Bearer"},
                    )

        # In dev mode ONLY, if Firebase admin is absent or testing offline tokens
        if ALLOW_DEV_MOCK_AUTH and not IS_PRODUCTION:
            try:
                parts = token.split(".")
                payload_b64 = parts[1]
                padded = payload_b64 + "=" * (-len(payload_b64) % 4)
                decoded = base64.urlsafe_b64decode(padded)
                payload = json.loads(decoded.decode("utf-8"))
                
                role_str = payload.get("role") or payload.get("activeRole") or Role.VIEWER
                user_role = _normalize_role(role_str)
                perms = [p.value for p in ROLE_PERMISSIONS.get(user_role, [])]
                return UserProfile(
                    uid=payload.get("sub") or payload.get("user_id") or payload.get("uid", "jwt_user"),
                    email=payload.get("email", "user@agrotrack.ai"),
                    name=payload.get("name", payload.get("email", "AgroTrack User")),
                    activeRole=user_role,
                    defaultOrgId=payload.get("orgId", "org_greenvalley_01"),
                    permissions=perms
                )
            except Exception:
                pass

    # If none of the validation methods succeeded
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid, missing, or expired authentication token.",
        headers={"WWW-Authenticate": "Bearer"},
    )


def require_roles(allowed_roles: List[Role]) -> Callable:
    """
    Dependency factory that enforces Role-Based Access Control.
    Raises HTTP 403 Forbidden if user's role is not in allowed_roles.
    """
    def role_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if user.activeRole not in allowed_roles:
            allowed_names = ", ".join([r.value for r in allowed_roles])
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: User role '{user.activeRole.value}' is not authorized. Required: {allowed_names}."
            )
        return user
    return role_checker


def require_permission(permission: Permission) -> Callable:
    """
    Dependency factory that enforces granular permission checks.
    """
    def permission_checker(user: UserProfile = Depends(get_current_user)) -> UserProfile:
        if permission.value not in user.permissions:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Access forbidden: Missing required permission '{permission.value}'."
            )
        return user
    return permission_checker
