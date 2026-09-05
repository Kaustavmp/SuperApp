"""Pydantic data models for SuperApp's core data structures."""

from __future__ import annotations

import uuid
from datetime import datetime
from enum import Enum
from typing import Optional

from pydantic import BaseModel, Field


class Document(BaseModel):
    """A source document loaded into the system."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    filename: str
    content: str
    metadata: dict = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class DocumentVersion(BaseModel):
    """Represents a document revision in a version chain."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    version_label: str = "v1"
    source_connector: str = "upload"
    doc_type: str = "document"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Organization(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Workspace(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    organization_id: str
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Project(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    workspace_id: str
    vertical: str = "codebase_docs"
    created_at: datetime = Field(default_factory=datetime.utcnow)
    metadata: dict = Field(default_factory=dict)


class Chunk(BaseModel):
    """A segment of a document produced by the chunker."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    document_id: str
    content: str
    chunk_index: int
    start_char: int
    end_char: int
    metadata: dict = Field(default_factory=dict)


class SchemaItem(BaseModel):
    """A single expected topic/section in the induced coverage schema."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    category: str
    topic: str
    description: str
    importance: str = "medium"
    examples: list[str] = Field(default_factory=list)

    @property
    def name(self) -> str:
        """Backward-compatible alias for topic."""
        return self.topic


class CoverageSchema(BaseModel):
    """The full induced taxonomy of what a document should cover."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    domain: str
    items: list[SchemaItem] = Field(default_factory=list)
    status: str = "draft"
    created_at: datetime = Field(default_factory=datetime.utcnow)


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


class AtomicClaim(BaseModel):
    """A discrete, self-contained factual or policy claim extracted from a chunk."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_text: str
    source_document_id: str
    source_chunk_id: str
    source_filename: str = ""
    source_span: Optional[dict] = None
    doc_version: str = ""
    doc_date: Optional[str] = None
    metadata: dict = Field(default_factory=dict)


class RelationType(str, Enum):
    """The logical relationship between two atomic claims."""

    SUPPORTS = "supports"
    CONTRADICTS = "contradicts"
    SILENT_ON = "silent_on"
    UNRELATED = "unrelated"
    SUPERSEDED = "superseded"


class ClaimNode(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_id: str
    text: str
    document_id: str = ""
    reasoning_trace: str = ""
    metadata: dict = Field(default_factory=dict)


class ClaimEdge(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    claim_a_id: str
    claim_b_id: str
    relation: RelationType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str = ""
    metadata: dict = Field(default_factory=dict)


class ClaimRelation(BaseModel):
    """A detected relationship between two atomic claims."""

    claim_a_id: str
    claim_b_id: str
    relation: RelationType
    confidence: float = Field(ge=0.0, le=1.0)
    reasoning: str
    metadata: dict = Field(default_factory=dict)

    @property
    def source_claim_id(self) -> str:
        """Backward-compatible alias for claim_a_id."""
        return self.claim_a_id

    @property
    def target_claim_id(self) -> str:
        """Backward-compatible alias for claim_b_id."""
        return self.claim_b_id


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


class FindingStatus(str, Enum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DISMISSED = "dismissed"


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
    status: FindingStatus = FindingStatus.OPEN
    metadata: dict = Field(default_factory=dict)


class AnalysisStatus(str, Enum):
    """Status of an analysis run."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class VerticalConfig(BaseModel):
    name: str
    display_name: str
    description: str = ""
    schema_library_path: str = ""
    scoring_rubric: dict = Field(default_factory=dict)
    ui_metadata: dict = Field(default_factory=dict)


class AnalysisResult(BaseModel):
    """Complete output of a SuperApp analysis run."""

    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    status: AnalysisStatus = AnalysisStatus.PENDING
    domain: str = ""
    vertical: str = "codebase_docs"
    documents: list[Document] = Field(default_factory=list)
    coverage_schema: Optional[CoverageSchema] = None
    coverage_results: list[CoverageResult] = Field(default_factory=list)
    claims: list[AtomicClaim] = Field(default_factory=list)
    relations: list[ClaimRelation] = Field(default_factory=list)
    findings: list[Finding] = Field(default_factory=list)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    metadata: dict = Field(default_factory=dict)

    @property
    def token_usage(self) -> dict:
        """Return normalized token usage for API and dashboard consumers."""
        return self.metadata.get("token_usage", {})

    @property
    def cost_estimate(self) -> float:
        """Return the estimated USD cost of this analysis."""
        return float(self.metadata.get("estimated_cost_usd", 0.0))
