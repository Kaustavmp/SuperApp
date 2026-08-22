"""FastAPI routes for SuperApp — API endpoints and dashboard UI routes."""

from __future__ import annotations

import os
import uuid
from datetime import datetime
from typing import Optional

import aiofiles
from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from superapp.config import settings
from superapp.models import (
    AnalysisResult,
    AnalysisStatus,
    Document,
)

# ---------------------------------------------------------------------------
# Template setup
# ---------------------------------------------------------------------------
base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
templates = Jinja2Templates(
    directory=os.path.join(base_dir, "dashboard", "templates")
)

# ---------------------------------------------------------------------------
# In-memory storage for analysis results (swap for DB in production)
# ---------------------------------------------------------------------------
_analyses: dict[str, AnalysisResult] = {}
_uploaded_docs: dict[str, list[Document]] = {}

# ---------------------------------------------------------------------------
# API Router
# ---------------------------------------------------------------------------
router = APIRouter()


@router.post("/upload")
async def upload_documents(
    files: list[UploadFile] = File(...),
    domain: str = Form("open-source documentation"),
):
    """Upload documents for analysis."""
    session_id = str(uuid.uuid4())
    documents: list[Document] = []

    upload_dir = os.path.join(base_dir, "uploads", session_id)
    os.makedirs(upload_dir, exist_ok=True)

    for f in files:
        content = await f.read()
        text = content.decode("utf-8", errors="replace")

        doc = Document(
            filename=f.filename or "unknown",
            content=text,
            metadata={"domain": domain, "size_bytes": len(content)},
        )
        documents.append(doc)

        # Save to disk
        file_path = os.path.join(upload_dir, f.filename or "unknown")
        async with aiofiles.open(file_path, "wb") as out:
            await out.write(content)

    _uploaded_docs[session_id] = documents

    return {
        "session_id": session_id,
        "document_count": len(documents),
        "documents": [
            {"id": d.id, "filename": d.filename, "size": len(d.content)}
            for d in documents
        ],
    }


@router.post("/analyze")
async def run_analysis(
    session_id: str = Form(...),
    domain: str = Form("open-source documentation"),
):
    """Trigger the full SuperApp analysis pipeline on uploaded documents."""
    if session_id not in _uploaded_docs:
        raise HTTPException(status_code=404, detail="Session not found. Upload documents first.")

    documents = _uploaded_docs[session_id]
    analysis_id = str(uuid.uuid4())

    # Create initial result
    result = AnalysisResult(
        id=analysis_id,
        status=AnalysisStatus.RUNNING,
        domain=domain,
        documents=documents,
    )
    _analyses[analysis_id] = result

    # Run pipeline
    try:
        # Step 1: Chunk documents
        from superapp.ingestion.chunker import DocumentChunker

        chunker = DocumentChunker()
        all_chunks = []
        for doc in documents:
            chunks = chunker.chunk_document(doc)
            all_chunks.extend(chunks)

        # Step 2: Schema induction
        from superapp.schema_induction.inducer import SchemaInducer

        inducer = SchemaInducer()
        schema = await inducer.induce_schema(documents, domain)
        result.coverage_schema = schema

        # Step 3: Coverage diffing
        from superapp.coverage.differ import CoverageDiffer

        differ = CoverageDiffer()
        coverage_results = await differ.diff_coverage(schema, documents, all_chunks)
        result.coverage_results = coverage_results

        # Step 4: Atomic claim extraction
        from superapp.contradiction.claim_extractor import ClaimExtractor

        extractor = ClaimExtractor()
        claims = await extractor.extract_claims(all_chunks, documents)
        result.claims = claims

        # Step 5: Contradiction detection (with vector store pruning)
        from superapp.vectorstore.store import VectorStore
        from superapp.contradiction.detector import ContradictionDetector

        vector_store = VectorStore(collection_name=f"analysis_{analysis_id}")
        detector = ContradictionDetector(vector_store)
        relations = await detector.detect_contradictions(claims)
        result.relations = relations

        # Step 6: Build contradiction graph
        from superapp.contradiction.graph_builder import ContradictionGraphBuilder

        graph_builder = ContradictionGraphBuilder()
        graph_builder.build_graph(claims, relations)

        # Step 7: Scoring & ranking
        from superapp.scoring.scorer import Scorer

        scorer = Scorer()
        findings = scorer.generate_findings(coverage_results, relations, claims)
        result.findings = findings

        # Mark complete
        result.status = AnalysisStatus.COMPLETED
        result.completed_at = datetime.utcnow()

    except Exception as e:
        result.status = AnalysisStatus.FAILED
        result.error_message = str(e)
        raise HTTPException(status_code=500, detail=f"Analysis failed: {e}")

    return {
        "analysis_id": analysis_id,
        "status": result.status.value,
        "total_findings": len(result.findings),
        "coverage_gaps": len(
            [f for f in result.findings if f.finding_type.value == "coverage_gap"]
        ),
        "contradictions": len(
            [f for f in result.findings if f.finding_type.value == "contradiction"]
        ),
    }


@router.get("/results/{analysis_id}")
async def get_results(analysis_id: str):
    """Get full analysis results."""
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    result = _analyses[analysis_id]
    return result.model_dump()


@router.get("/results/{analysis_id}/gaps")
async def get_gaps(analysis_id: str):
    """Get coverage gap findings."""
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    result = _analyses[analysis_id]
    gaps = [f for f in result.findings if f.finding_type.value == "coverage_gap"]
    return [g.model_dump() for g in gaps]


@router.get("/results/{analysis_id}/contradictions")
async def get_contradictions(analysis_id: str):
    """Get contradiction findings."""
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")
    result = _analyses[analysis_id]
    contradictions = [
        f for f in result.findings if f.finding_type.value == "contradiction"
    ]
    return [c.model_dump() for c in contradictions]


@router.get("/graph/{analysis_id}")
async def get_graph(analysis_id: str):
    """Get contradiction graph data for visualization."""
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    result = _analyses[analysis_id]

    # Rebuild graph for export
    from superapp.contradiction.graph_builder import ContradictionGraphBuilder

    builder = ContradictionGraphBuilder()
    builder.build_graph(result.claims, result.relations)
    return builder.export_graph_data()


# ---------------------------------------------------------------------------
# UI Router (serves dashboard HTML pages)
# ---------------------------------------------------------------------------
ui_router = APIRouter()


@ui_router.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    """Render the main dashboard / upload page."""
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "analyses": [
                {
                    "id": a.id,
                    "status": a.status.value,
                    "domain": a.domain,
                    "doc_count": len(a.documents),
                    "finding_count": len(a.findings),
                    "created_at": a.created_at.isoformat(),
                }
                for a in _analyses.values()
            ],
        },
    )


@ui_router.get("/results/{analysis_id}", response_class=HTMLResponse)
async def dashboard_results(request: Request, analysis_id: str):
    """Render the results dashboard for a specific analysis."""
    if analysis_id not in _analyses:
        raise HTTPException(status_code=404, detail="Analysis not found.")

    result = _analyses[analysis_id]
    gaps = [f for f in result.findings if f.finding_type.value == "coverage_gap"]
    contradictions = [
        f for f in result.findings if f.finding_type.value == "contradiction"
    ]

    # Build graph data for visualization
    graph_data = {"nodes": [], "edges": []}
    if result.claims and result.relations:
        from superapp.contradiction.graph_builder import ContradictionGraphBuilder

        builder = ContradictionGraphBuilder()
        builder.build_graph(result.claims, result.relations)
        graph_data = builder.export_graph_data()

    return templates.TemplateResponse(
        "results.html",
        {
            "request": request,
            "analysis": result,
            "gaps": gaps,
            "contradictions": contradictions,
            "graph_data": graph_data,
            "total_findings": len(result.findings),
            "avg_confidence": (
                sum(f.confidence for f in result.findings) / len(result.findings)
                if result.findings
                else 0
            ),
        },
    )
