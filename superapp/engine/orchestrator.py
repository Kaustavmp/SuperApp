"""Service orchestrator for the SuperApp analysis pipeline."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from superapp.config import settings
from superapp.models import AnalysisResult, AnalysisStatus, Document
from superapp.platform.billing import BillingTracker


class AnalysisOrchestrator:
    """Minimal orchestrator that preserves the existing pipeline while enabling future expansion."""

    def __init__(self, analysis_id: str | None = None, billing: BillingTracker | None = None):
        self.analysis_id = analysis_id
        self.billing = billing or BillingTracker()

    async def run_full_analysis(self, documents: list[Document], *, domain: str = "", vertical: str = "codebase_docs") -> AnalysisResult:
        analysis = AnalysisResult(
            id=self.analysis_id or __import__("uuid").uuid4().hex,
            status=AnalysisStatus.RUNNING,
            domain=domain,
            vertical=vertical,
            documents=documents,
            created_at=datetime.utcnow(),
        )
        self.billing.add_usage(documents_processed=len(documents))

        try:
            from superapp.ingestion.chunker import DocumentChunker
            from superapp.schema_induction.inducer import SchemaInducer
            from superapp.coverage.differ import CoverageDiffer
            from superapp.contradiction.claim_extractor import ClaimExtractor
            from superapp.vectorstore.store import VectorStore
            from superapp.contradiction.detector import ContradictionDetector
            from superapp.contradiction.graph_builder import ContradictionGraphBuilder
            from superapp.scoring.scorer import Scorer

            chunker = DocumentChunker()
            all_chunks = []
            for document in documents:
                all_chunks.extend(chunker.chunk_document(document))

            schema = await SchemaInducer().induce_schema(documents, domain)
            self.billing.add_usage(tokens_consumed=sum(len(d.content) for d in documents) // 4)
            analysis.coverage_schema = schema

            differ = CoverageDiffer()
            analysis.coverage_results = await differ.diff_coverage(schema, documents, all_chunks)

            extractor = ClaimExtractor()
            analysis.claims = await extractor.extract_claims(all_chunks, documents)

            vector_store = VectorStore(collection_name=f"analysis_{analysis.id}")
            detector = ContradictionDetector(vector_store)
            analysis.relations = await detector.detect_contradictions(analysis.claims)

            graph_builder = ContradictionGraphBuilder()
            graph_builder.build_graph(analysis.claims, analysis.relations)

            scorer = Scorer()
            analysis.findings = scorer.generate_findings(analysis.coverage_results, analysis.relations, analysis.claims)
            analysis.findings = [
                finding for finding in analysis.findings
                if finding.confidence >= settings.min_confidence_threshold
            ]
            usage = self.billing.snapshot()
            analysis.metadata = {
                "token_usage": usage,
                "total_tokens": usage["total_tokens"],
                "estimated_cost_usd": usage["estimated_cost_usd"],
            }

            analysis.status = AnalysisStatus.COMPLETED
            analysis.completed_at = datetime.utcnow()
        except Exception as exc:  # pragma: no cover - runtime integration path
            analysis.status = AnalysisStatus.FAILED
            analysis.error_message = str(exc)
            raise

        return analysis
