from superapp.config import settings
from superapp.models import (
    FindingStatus,
    ClaimRelation,
    RelationType,
    VerticalConfig,
    DocumentVersion,
    Project,
    Workspace,
    Organization,
)
from superapp.llm.providers import LLMProvider, OllamaProvider
from superapp.verticals import list_verticals


def test_settings_expose_provider_and_budget_config():
    assert hasattr(settings, "llm_provider")
    assert hasattr(settings, "default_model_tier")
    assert hasattr(settings, "max_cost_per_job_usd")
    assert settings.llm_provider in {"ollama", "anthropic", "openai"}


def test_core_models_support_vertical_and_versioning():
    org = Organization(name="Acme")
    workspace = Workspace(name="Legal", organization_id=org.id)
    project = Project(name="Policy Review", workspace_id=workspace.id)
    version = DocumentVersion(document_id="doc-1", version_label="v2")

    assert org.name == "Acme"
    assert workspace.organization_id == org.id
    assert project.workspace_id == workspace.id
    assert version.version_label == "v2"

    relation = ClaimRelation(
        claim_a_id="a",
        claim_b_id="b",
        relation=RelationType.SUPERSEDED,
        confidence=0.9,
        reasoning="A newer rule supersedes the older one.",
    )
    assert relation.relation == RelationType.SUPERSEDED

    finding_status = FindingStatus.ACCEPTED
    assert finding_status.value == "accepted"

    vertical = VerticalConfig(name="legal_contracts", display_name="Legal & Contracts")
    assert vertical.display_name == "Legal & Contracts"


def test_llm_provider_base_and_default_ollama_provider():
    assert issubclass(OllamaProvider, LLMProvider)
    provider = OllamaProvider()
    assert provider.name == "ollama"


def test_vertical_registry_discovers_known_modules():
    verticals = list_verticals()
    names = {v.name for v in verticals}
    assert "codebase_docs" in names
    assert "legal_contracts" in names
