from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from superapp.db import database, repository
from superapp.db.models import Base
from superapp.db.repository import AnalysisRepository
from superapp.models import AnalysisResult, AnalysisStatus, Document, Finding, FindingType


def test_analysis_and_finding_status_persist(tmp_path, monkeypatch):
    engine = create_engine(f"sqlite:///{tmp_path / 'test.db'}", connect_args={"check_same_thread": False})
    session_factory = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    Base.metadata.create_all(bind=engine)
    monkeypatch.setattr(database, "SessionLocal", session_factory)
    monkeypatch.setattr(repository, "SessionLocal", session_factory)

    document = Document(filename="policy.md", content="Retention is seven years.")
    finding = Finding(
        finding_type=FindingType.COVERAGE_GAP,
        title="Retention",
        description="Missing retention details.",
        confidence=0.8,
        reasoning_trace="test",
    )
    result = AnalysisResult(
        id="analysis-test",
        status=AnalysisStatus.COMPLETED,
        documents=[document],
        findings=[finding],
        created_at=datetime.utcnow(),
    )
    AnalysisRepository.save_analysis(result)

    loaded = AnalysisRepository.get_analysis(result.id)
    assert loaded is not None
    assert loaded.findings[0].status.value == "open"
    assert AnalysisRepository.update_finding_status(finding.id, "accepted") is True
    assert AnalysisRepository.get_analysis(result.id).findings[0].status.value == "accepted"
