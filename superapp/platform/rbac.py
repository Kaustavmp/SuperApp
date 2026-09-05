"""RBAC stub for admin, reviewer, contributor, and viewer roles."""

from __future__ import annotations

from enum import Enum
from fastapi import Depends, HTTPException, status

from superapp.config import settings
from superapp.platform.auth import get_current_api_key


class Role(str, Enum):
    ADMIN = "admin"
    SCHEMA_REVIEWER = "schema_reviewer"
    CONTRIBUTOR = "contributor"
    VIEWER = "viewer"


class AccessPolicy:
    def __init__(self, role: Role):
        self.role = role

    def can_review_schemas(self):
        return self.role in {Role.ADMIN, Role.SCHEMA_REVIEWER}

    def can_analyze(self):
        return self.role in {Role.ADMIN, Role.CONTRIBUTOR}


def require_roles(*roles: Role):
    allowed = set(roles)

    def dependency(_: str = Depends(get_current_api_key)) -> Role:
        role = Role(settings.default_role)
        if role not in allowed:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Insufficient role")
        return role

    return dependency
