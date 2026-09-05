"""SQLAlchemy ORM models for SuperApp persistence."""

from __future__ import annotations

import json
from datetime import datetime
from typing import Any

from sqlalchemy import Column, DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship

from superapp.db.database import Base


class DBUploadedDocument(Base):
    """Uploaded document associated with an upload session."""

    __tablename__ = "uploaded_documents"

    id = Column(String(64), primary_key=True, index=True)
    session_id = Column(String(64), index=True, nullable=False)
    filename = Column(String(255), nullable=False)
    content = Column(Text, nullable=False)
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    @property
    def doc_metadata(self) -> dict[str, Any]:
        try:
            return json.loads(self.metadata_json or "{}")
        except Exception:
            return {}


class DBAnalysis(Base):
    """Persisted analysis run with full stage outputs and metrics."""

    __tablename__ = "analyses"

    id = Column(String(64), primary_key=True, index=True)
    status = Column(String(32), default="pending", index=True)
    domain = Column(String(255), default="")
    vertical = Column(String(64), default="codebase_docs")
    org_id = Column(String(64), nullable=True, index=True)
    workspace_id = Column(String(64), nullable=True, index=True)
    project_id = Column(String(64), nullable=True, index=True)

    # Full stage data stored as JSON strings for deterministic replay & visualization
    documents_json = Column(Text, default="[]")
    schema_json = Column(Text, nullable=True)
    coverage_results_json = Column(Text, default="[]")
    claims_json = Column(Text, default="[]")
    relations_json = Column(Text, default="[]")

    # Day 2: Cost & token tracking
    total_tokens = Column(Integer, default=0)
    estimated_cost_usd = Column(Float, default=0.0)

    created_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    error_message = Column(Text, nullable=True)

    findings = relationship("DBFinding", back_populates="analysis", cascade="all, delete-orphan")


class DBFinding(Base):
    """Persisted coverage gap or contradiction finding."""

    __tablename__ = "findings"

    id = Column(String(64), primary_key=True, index=True)
    analysis_id = Column(String(64), ForeignKey("analyses.id", ondelete="CASCADE"), index=True, nullable=False)
    finding_type = Column(String(32), index=True, nullable=False)  # coverage_gap | contradiction
    title = Column(String(255), nullable=False)
    description = Column(Text, nullable=False)
    severity = Column(String(32), default="medium", index=True)
    confidence = Column(Float, default=0.0)
    reasoning_trace = Column(Text, default="")
    source_references_json = Column(Text, default="[]")
    status = Column(String(32), default="open", index=True)  # open | accepted | dismissed
    metadata_json = Column(Text, default="{}")
    created_at = Column(DateTime, default=datetime.utcnow)

    analysis = relationship("DBAnalysis", back_populates="findings")


# Stable names used by integrations and earlier design documents.
DBDocument = DBUploadedDocument
DBAnalysisResult = DBAnalysis


class DBClaimRelation(Base):
    """Persisted claim relation for direct graph/query access."""

    __tablename__ = "claim_relations"

    id = Column(Integer, primary_key=True, autoincrement=True)
    analysis_id = Column(String(64), ForeignKey("analyses.id", ondelete="CASCADE"), index=True, nullable=False)
    claim_a_id = Column(String(64), nullable=False)
    claim_b_id = Column(String(64), nullable=False)
    relation = Column(String(32), nullable=False)
    confidence = Column(Float, default=0.0)
    reasoning = Column(Text, default="")
