"""Pydantic data models for SuperApp's core data structures."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Document & Chunk Models
# ---------------------------------------------------------------------------

class Document(BaseModel):
    """A source document loaded into the system."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class Chunk(BaseModel):
    """A segment of a document produced by the chunker."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Schema Induction Models
# ---------------------------------------------------------------------------

class SchemaItem(BaseModel):
    """A single expected topic/section in the induced coverage schema."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    topic: str
    description: str
    importance: str = "medium"  # low, medium, high, critical


class CoverageSchema(BaseModel):
    """The full induced taxonomy of what a document should cover."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str
    items: list[SchemaItem] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)


# ---------------------------------------------------------------------------
# Coverage Diffing Models
# ---------------------------------------------------------------------------

class CoverageStatus(str, Enum):
    """Whether a schema item is covered in the corpus."""

    COVERED = "covered"
    PARTIALLY_COVERED = "partially_covered"
    MISSING = "missing"


class CoverageResult(BaseModel):
    """Result of checking one schema item against the corpus."""

    schema_item: SchemaItem
    status: CoverageStatus
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    evidence_chunks: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Atomic Claim & Contradiction Models
# ---------------------------------------------------------------------------

class AtomicClaim(BaseModel):
    """A discrete, self-contained factual or policy claim extracted from a chunk."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str
    source_document_id: str
    source_chunk_id: str
    source_filename: str = ""
    metadata: dict = Field(default_factory=dict)


class RelationType(str, Enum):
    """The logical relationship between two atomic claims."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SILENT_ON = "silent_on"
    UNRELATED = "unrelated"


class ClaimRelation(BaseModel):
    """A detected relationship between two atomic claims."""

    claim_a_id: str
    claim_b_id: str
    relation: RelationType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str


# ---------------------------------------------------------------------------
# Finding Models (unified output)
# ---------------------------------------------------------------------------

class FindingType(str, Enum):
    """The type of finding surfaced by SuperApp."""

    COVERAGE_GAP = "coverage_gap"
    CONTRADICTION = "contradiction"


class Severity(str, Enum):
    """Severity level of a finding."""

    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class Finding(BaseModel):
    """A single gap or contradiction finding with full reasoning trace."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    finding_type: FindingType
    title: str
    description: str
    severity: Severity = Severity.MEDIUM
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning_trace: str
    source_references: list[str] = Field(default_factory=list)
    metadata: dict = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Analysis Result (top-level container)
# ---------------------------------------------------------------------------

class AnalysisStatus(str, Enum):
    """Status of an analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class AnalysisResult(BaseModel):
    """Complete output of a SuperApp analysis run."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: AnalysisStatus = AnalysisStatus.PENDING
    domain: str = ""
    documents: list[Document] = Field(default_factory=list)
    coverage_schema: Optional[CoverageSchema] = None
    coverage_results: list[CoverageResult] = Field(default_factory=list)
    claims: list[AtomicClaim] = Field(default_factory=list)
    relations: list[ClaimRelation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
