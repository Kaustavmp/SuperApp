"""Multi-tenancy scaffold for organization/workspace/project enforcement."""

from __future__ import annotations


class TenancyContext:
    def __init__(self, organization_id: str, workspace_id: str, project_id: str):
        self.organization_id = organization_id
        self.workspace_id = workspace_id
        self.project_id = project_id
