from pathlib import Path
import asyncio

from superapp.models import CoverageSchema, Document


def test_orchestrator_runs_sample_policy_corpus_with_mocked_llm(monkeypatch):
    from superapp.contradiction.claim_extractor import ClaimExtractor
    from superapp.contradiction.detector import ContradictionDetector
    from superapp.coverage.differ import CoverageDiffer
    from superapp.schema_induction.inducer import SchemaInducer
    from superapp.engine.orchestrator import AnalysisOrchestrator

    sample_dir = Path(__file__).parents[1] / "sample_data" / "policy_contradictions"
    documents = [Document(filename=path.name, content=path.read_text(encoding="utf-8")) for path in sample_dir.glob("*.md")]

    async def induce(self, documents, domain=""):
        return CoverageSchema(domain=domain, items=[])

    async def diff(self, schema, documents, chunks):
        return []

    async def claims(self, chunks, documents):
        return []

    async def relations(self, claims):
        return []

    monkeypatch.setattr(SchemaInducer, "induce_schema", induce)
    monkeypatch.setattr(CoverageDiffer, "diff_coverage", diff)
    monkeypatch.setattr(ClaimExtractor, "extract_claims", claims)
    monkeypatch.setattr(ContradictionDetector, "detect_contradictions", relations)

    result = asyncio.run(AnalysisOrchestrator().run_full_analysis(documents, domain="company_policy", vertical="company_policy"))
    assert result.status.value == "completed"
    assert result.documents
    assert result.metadata["token_usage"]["total_tokens"] >= 0
