"""Base class for vertical schema modules."""

from __future__ import annotations

from abc import ABC, abstractmethod


class BaseVertical(ABC):
    """Common interface for vertical-specific domain modules."""

    name: str = "base"
    display_name: str = "Base Vertical"
    description: str = ""

    @property
    @abstractmethod
    def schema_library(self):
        return []

    @property
    @abstractmethod
    def scoring_rubric(self):
        return {}

    @property
    @abstractmethod
    def ui_metadata(self):
        return {}
