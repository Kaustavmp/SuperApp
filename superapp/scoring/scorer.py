import uuid
from superapp.models import (
    Finding,
    FindingType,
    Severity,
    CoverageResult,
    CoverageStatus,
    ClaimRelation,
    RelationType,
    AtomicClaim
)

class Scorer:
    """Scorer module for generating and ranking findings."""
    
    def generate_findings(
        self,
        coverage_results: list[CoverageResult],
        claim_relations: list[ClaimRelation],
        claims: list[AtomicClaim]
    ) -> list[Finding]:
        """
        Generate, rank, and return a list of findings from coverage and contradiction results.
        """
        findings: list[Finding] = []
        
        # 1. Convert coverage gaps
        for result in coverage_results:
            if result.status != CoverageStatus.COVERED:
                finding = self._build_gap_finding(result)
                findings.append(finding)
                
        # 2. Convert contradiction relations
        for relation in claim_relations:
            if relation.relation == RelationType.CONTRADICTS:
                finding = self._build_contradiction_finding(relation, claims)
                findings.append(finding)
                
        # 4. Rank all findings by (severity_weight * confidence) descending
        findings.sort(
            key=lambda f: (self._severity_weight(f.severity) * f.confidence),
            reverse=True
        )
        
        # 5. Return the sorted list
        return findings

    def _severity_from_coverage(self, result: CoverageResult) -> Severity:
        """Map coverage result to severity."""
        importance = result.schema_item.importance.lower()
        
        if result.status == CoverageStatus.MISSING:
            if importance == "critical" or importance == "high":
                return Severity.CRITICAL
            elif importance == "medium":
                return Severity.HIGH
            else:
                return Severity.MEDIUM
        elif result.status == CoverageStatus.PARTIALLY_COVERED:
            if importance == "critical":
                return Severity.HIGH
            elif importance == "high":
                return Severity.MEDIUM
            else:
                return Severity.LOW
        
        return Severity.LOW

    def _severity_from_contradiction(self, relation: ClaimRelation) -> Severity:
        """Map contradiction confidence to severity."""
        if relation.confidence > 0.8:
            return Severity.CRITICAL
        elif relation.confidence >= 0.5:
            return Severity.HIGH
        else:
            return Severity.MEDIUM

    def _severity_weight(self, severity: Severity) -> float:
        """Assign numerical weight to severity for ranking."""
        if severity == Severity.CRITICAL:
            return 4.0
        elif severity == Severity.HIGH:
            return 3.0
        elif severity == Severity.MEDIUM:
            return 2.0
        elif severity == Severity.LOW:
            return 1.0
        return 1.0

    def _build_gap_finding(self, result: CoverageResult) -> Finding:
        """Create a Finding from a CoverageResult."""
        severity = self._severity_from_coverage(result)
        return Finding(
            id=str(uuid.uuid4()),
            finding_type=FindingType.COVERAGE_GAP,
            title=f"Coverage Gap: {result.schema_item.topic}",
            description=f"Topic '{result.schema_item.topic}' in category '{result.schema_item.category}' is {result.status.value}.",
            severity=severity,
            confidence=result.confidence,
            reasoning_trace=result.reasoning,
            source_references=result.evidence_chunks
        )

    def _build_contradiction_finding(self, relation: ClaimRelation, claims: list[AtomicClaim]) -> Finding:
        """Create a Finding from a ClaimRelation (contradiction)."""
        severity = self._severity_from_contradiction(relation)
        
        claim_map = {c.id: c for c in claims}
        claim_a = claim_map.get(relation.claim_a_id)
        claim_b = claim_map.get(relation.claim_b_id)
        
        claim_a_text = claim_a.claim_text if claim_a else "Unknown claim A"
        claim_b_text = claim_b.claim_text if claim_b else "Unknown claim B"
        
        source_refs = []
        if claim_a:
            source_refs.append(f"{claim_a.source_filename} (Chunk {claim_a.source_chunk_id})")
        if claim_b:
            source_refs.append(f"{claim_b.source_filename} (Chunk {claim_b.source_chunk_id})")
            
        return Finding(
            id=str(uuid.uuid4()),
            finding_type=FindingType.CONTRADICTION,
            title="Contradiction Found",
            description=f"Claim A: '{claim_a_text}' contradicts Claim B: '{claim_b_text}'.",
            severity=severity,
            confidence=relation.confidence,
            reasoning_trace=relation.reasoning,
            source_references=source_refs
        )
