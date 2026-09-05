"""RBAC stub for admin, reviewer, contributor, and viewer roles."""

from __future__ import annotations

from enum import Enum


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
