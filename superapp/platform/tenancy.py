"""Multi-tenancy scaffold for organization/workspace/project enforcement."""

from __future__ import annotations

from fastapi import Header
from superapp.models import Organization, Project, Workspace


class TenancyContext:
    def __init__(self, organization_id: str, workspace_id: str, project_id: str):
        self.organization_id = organization_id
        self.workspace_id = workspace_id
        self.project_id = project_id


def get_tenancy_context(
    x_organization_id: str | None = Header(default=None),
    x_workspace_id: str | None = Header(default=None),
    x_project_id: str | None = Header(default=None),
) -> TenancyContext:
    return TenancyContext(
        x_organization_id or "development-org",
        x_workspace_id or "development-workspace",
        x_project_id or "development-project",
    )


def default_tenancy() -> tuple[Organization, Workspace, Project]:
    organization = Organization(id="development-org", name="Development")
    workspace = Workspace(id="development-workspace", name="Default", organization_id=organization.id)
    project = Project(id="development-project", name="Default", workspace_id=workspace.id)
    return organization, workspace, project
