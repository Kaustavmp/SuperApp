"""Vertical registry for SuperApp."""

from __future__ import annotations

from importlib import import_module
from pathlib import Path

from superapp.models import VerticalConfig


def _available_verticals() -> dict[str, VerticalConfig]:
    return {
        "codebase_docs": VerticalConfig(
            name="codebase_docs",
            display_name="Codebase Docs",
            description="Project documentation and internal knowledge completeness.",
            schema_library_path="superapp/schema_library/codebase_docs",
        ),
        "legal_contracts": VerticalConfig(
            name="legal_contracts",
            display_name="Legal & Contracts",
            description="Legal and contract risk review.",
            schema_library_path="superapp/schema_library/legal_contracts",
        ),
        "company_policy": VerticalConfig(
            name="company_policy",
            display_name="Company Policy",
            description="Policy and compliance review.",
            schema_library_path="superapp/schema_library/company_policy",
        ),
        "engineering_specs": VerticalConfig(
            name="engineering_specs",
            display_name="Engineering Specs",
            description="Engineering and product requirements review.",
            schema_library_path="superapp/schema_library/engineering_specs",
        ),
        "academic_research": VerticalConfig(
            name="academic_research",
            display_name="Academic Research",
            description="Research literature and methodology coverage review.",
            schema_library_path="superapp/schema_library/academic_research",
        ),
    }


def list_verticals() -> list[VerticalConfig]:
    return list(_available_verticals().values())


def get_vertical(name: str) -> VerticalConfig:
    return _available_verticals()[name]


def load_vertical_module(name: str):
    module_name = f"superapp.verticals.{name}"
    try:
        return import_module(module_name)
    except ModuleNotFoundError:
        return None
