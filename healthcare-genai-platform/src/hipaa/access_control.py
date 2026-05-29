"""Role-based access control for HIPAA minimum-necessary standard."""

from enum import Enum
from functools import wraps
from typing import Callable

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel

from src.config.settings import get_settings

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/auth/token")


class Role(str, Enum):
    PHYSICIAN = "physician"
    NURSE = "nurse"
    CARE_MANAGER = "care_manager"
    ADMIN = "admin"
    AUDITOR = "auditor"


# Resource → minimum required role
ROLE_PERMISSIONS: dict[str, list[Role]] = {
    "patient:read": [Role.PHYSICIAN, Role.NURSE, Role.CARE_MANAGER, Role.ADMIN],
    "patient:write": [Role.PHYSICIAN, Role.ADMIN],
    "care_plan:read": [Role.PHYSICIAN, Role.NURSE, Role.CARE_MANAGER, Role.ADMIN],
    "care_plan:write": [Role.PHYSICIAN, Role.CARE_MANAGER, Role.ADMIN],
    "audit:read": [Role.AUDITOR, Role.ADMIN],
    "ai:inference": [Role.PHYSICIAN, Role.NURSE, Role.CARE_MANAGER],
}


class TokenData(BaseModel):
    user_id: str
    role: Role
    organization_id: str


async def get_current_user(token: str = Depends(oauth2_scheme)) -> TokenData:
    settings = get_settings()
    credentials_exc = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, settings.secret_key, algorithms=[settings.jwt_algorithm])
        user_id: str = payload.get("sub")
        role_str: str = payload.get("role")
        org_id: str = payload.get("org")
        if not all([user_id, role_str, org_id]):
            raise credentials_exc
        return TokenData(user_id=user_id, role=Role(role_str), organization_id=org_id)
    except (JWTError, ValueError):
        raise credentials_exc


def require_permission(permission: str):
    """Decorator / dependency factory enforcing HIPAA minimum-necessary."""
    async def _dep(current_user: TokenData = Depends(get_current_user)) -> TokenData:
        allowed_roles = ROLE_PERMISSIONS.get(permission, [])
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail=f"Role '{current_user.role}' lacks permission '{permission}'",
            )
        return current_user
    return _dep
