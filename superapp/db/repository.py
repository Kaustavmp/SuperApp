"""Repository layer bridging Pydantic domain models and SQLAlchemy ORM models."""

from __future__ import annotations

import json
from datetime import datetime
from typing import List, Optional

from sqlalchemy.orm import Session

from superapp.db.database import SessionLocal
from superapp.db.models import DBAnalysis, DBFinding, DBUploadedDocument
from superapp.models import (
    AnalysisResult,
    AnalysisStatus,
    AtomicClaim,
    ClaimRelation,
    CoverageResult,
    CoverageSchema,
    Document,
    Finding,
    FindingStatus,
    FindingType,
    RelationType,
    SchemaItem,
    Severity,
)


class AnalysisRepository:
    """Repository handling persistence of sessions, analyses, and findings."""

    @staticmethod
    def save_uploaded_documents(session_id: str, documents: List[Document], db: Optional[Session] = None) -> None:
        """Save a batch of uploaded documents for a session."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            for doc in documents:
                db_doc = DBUploadedDocument(
                    id=doc.id,
                    session_id=session_id,
                    filename=doc.filename,
                    content=doc.content,
                    metadata_json=json.dumps(doc.metadata or {}),
                    created_at=doc.created_at or datetime.utcnow(),
                )
                db.merge(db_doc)
            db.commit()
        finally:
            if close:
                db.close()

    @staticmethod
    def get_uploaded_documents(session_id: str, db: Optional[Session] = None) -> List[Document]:
        """Fetch all documents associated with an upload session."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            db_docs = db.query(DBUploadedDocument).filter(DBUploadedDocument.session_id == session_id).all()
            return [
                Document(
                    id=d.id,
                    filename=d.filename,
                    content=d.content,
                    metadata=d.doc_metadata,
                    created_at=d.created_at,
                )
                for d in db_docs
            ]
        finally:
            if close:
                db.close()

    @staticmethod
    def save_analysis(result: AnalysisResult, db: Optional[Session] = None) -> None:
        """Persist or update an AnalysisResult and all associated Findings."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            db_analysis = db.query(DBAnalysis).filter(DBAnalysis.id == result.id).first()
            if not db_analysis:
                db_analysis = DBAnalysis(id=result.id)
                db.add(db_analysis)

            db_analysis.status = result.status.value if isinstance(result.status, AnalysisStatus) else str(result.status)
            db_analysis.domain = result.domain
            db_analysis.vertical = result.vertical
            db_analysis.created_at = result.created_at or datetime.utcnow()
            db_analysis.completed_at = result.completed_at
            db_analysis.error_message = result.error_message

            # Tenancy & cost metadata if present
            extra = getattr(result, "metadata", {}) or {}
            db_analysis.org_id = extra.get("org_id")
            db_analysis.workspace_id = extra.get("workspace_id")
            db_analysis.project_id = extra.get("project_id")
            db_analysis.total_tokens = int(extra.get("total_tokens", 0))
            db_analysis.estimated_cost_usd = float(extra.get("estimated_cost_usd", 0.0))

            # Store serialized representations
            db_analysis.documents_json = json.dumps([d.model_dump(mode="json") for d in result.documents])
            db_analysis.schema_json = json.dumps(result.coverage_schema.model_dump(mode="json")) if result.coverage_schema else None
            db_analysis.coverage_results_json = json.dumps([c.model_dump(mode="json") for c in result.coverage_results])
            db_analysis.claims_json = json.dumps([c.model_dump(mode="json") for c in result.claims])
            db_analysis.relations_json = json.dumps([r.model_dump(mode="json") for r in result.relations])

            # Persist findings
            existing_findings = {f.id: f for f in db.query(DBFinding).filter(DBFinding.analysis_id == result.id).all()}
            current_finding_ids = set()

            for f in result.findings:
                current_finding_ids.add(f.id)
                db_f = existing_findings.get(f.id)
                if not db_f:
                    db_f = DBFinding(id=f.id, analysis_id=result.id)
                    db.add(db_f)

                db_f.finding_type = f.finding_type.value if isinstance(f.finding_type, FindingType) else str(f.finding_type)
                db_f.title = f.title
                db_f.description = f.description
                db_f.severity = f.severity.value if isinstance(f.severity, Severity) else str(f.severity)
                db_f.confidence = float(f.confidence)
                db_f.reasoning_trace = f.reasoning_trace or ""
                db_f.source_references_json = json.dumps(f.source_references or [])
                db_f.status = f.status.value if isinstance(f.status, FindingStatus) else str(f.status)
                db_f.metadata_json = json.dumps(f.metadata or {})

            # Remove findings that are no longer present
            for old_id, old_f in existing_findings.items():
                if old_id not in current_finding_ids:
                    db.delete(old_f)

            db.commit()
        finally:
            if close:
                db.close()

    @staticmethod
    def get_analysis(analysis_id: str, db: Optional[Session] = None) -> Optional[AnalysisResult]:
        """Load an AnalysisResult from the database with all claims, relations, and findings."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            db_analysis = db.query(DBAnalysis).filter(DBAnalysis.id == analysis_id).first()
            if not db_analysis:
                return None

            # Reconstruct domain objects
            documents = []
            if db_analysis.documents_json:
                try:
                    documents = [Document(**d) for d in json.loads(db_analysis.documents_json)]
                except Exception:
                    pass

            coverage_schema = None
            if db_analysis.schema_json:
                try:
                    coverage_schema = CoverageSchema(**json.loads(db_analysis.schema_json))
                except Exception:
                    pass

            coverage_results = []
            if db_analysis.coverage_results_json:
                try:
                    coverage_results = [CoverageResult(**c) for c in json.loads(db_analysis.coverage_results_json)]
                except Exception:
                    pass

            claims = []
            if db_analysis.claims_json:
                try:
                    claims = [AtomicClaim(**c) for c in json.loads(db_analysis.claims_json)]
                except Exception:
                    pass

            relations = []
            if db_analysis.relations_json:
                try:
                    relations = [ClaimRelation(**r) for r in json.loads(db_analysis.relations_json)]
                except Exception:
                    pass

            findings = []
            for db_f in db_analysis.findings:
                source_refs = []
                try:
                    source_refs = json.loads(db_f.source_references_json or "[]")
                except Exception:
                    pass
                meta = {}
                try:
                    meta = json.loads(db_f.metadata_json or "{}")
                except Exception:
                    pass

                findings.append(
                    Finding(
                        id=db_f.id,
                        finding_type=FindingType(db_f.finding_type),
                        title=db_f.title,
                        description=db_f.description,
                        severity=Severity(db_f.severity),
                        confidence=db_f.confidence,
                        reasoning_trace=db_f.reasoning_trace or "",
                        source_references=source_refs,
                        status=FindingStatus(db_f.status) if db_f.status in FindingStatus._value2member_map_ else FindingStatus.OPEN,
                        metadata=meta,
                    )
                )

            metadata = {
                "total_tokens": db_analysis.total_tokens or 0,
                "estimated_cost_usd": db_analysis.estimated_cost_usd or 0.0,
                "org_id": db_analysis.org_id,
                "workspace_id": db_analysis.workspace_id,
                "project_id": db_analysis.project_id,
            }

            status_val = AnalysisStatus(db_analysis.status) if db_analysis.status in AnalysisStatus._value2member_map_ else AnalysisStatus.PENDING

            result = AnalysisResult(
                id=db_analysis.id,
                status=status_val,
                domain=db_analysis.domain or "",
                vertical=db_analysis.vertical or "codebase_docs",
                documents=documents,
                coverage_schema=coverage_schema,
                coverage_results=coverage_results,
                claims=claims,
                relations=relations,
                findings=findings,
                created_at=db_analysis.created_at,
                completed_at=db_analysis.completed_at,
                error_message=db_analysis.error_message,
            )
            # Attach extra runtime tracking
            result.metadata = metadata
            return result
        finally:
            if close:
                db.close()

    @staticmethod
    def list_analyses(db: Optional[Session] = None) -> List[dict]:
        """Return summaries of all stored analyses for the dashboard."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            rows = db.query(DBAnalysis).order_by(DBAnalysis.created_at.desc()).all()
            summaries = []
            for a in rows:
                doc_count = 0
                if a.documents_json:
                    try:
                        doc_count = len(json.loads(a.documents_json))
                    except Exception:
                        pass
                summaries.append(
                    {
                        "id": a.id,
                        "status": a.status,
                        "domain": a.domain,
                        "doc_count": doc_count,
                        "finding_count": len(a.findings),
                        "created_at": a.created_at.isoformat() if a.created_at else datetime.utcnow().isoformat(),
                        "total_tokens": a.total_tokens or 0,
                        "estimated_cost_usd": a.estimated_cost_usd or 0.0,
                    }
                )
            return summaries
        finally:
            if close:
                db.close()

    @staticmethod
    def update_finding_status(finding_id: str, new_status: str, db: Optional[Session] = None) -> bool:
        """Update reviewer workflow status of a specific finding."""
        close = False
        if db is None:
            db = SessionLocal()
            close = True
        try:
            db_f = db.query(DBFinding).filter(DBFinding.id == finding_id).first()
            if not db_f:
                return False
            db_f.status = new_status
            db.commit()
            return True
        finally:
            if close:
                db.close()
