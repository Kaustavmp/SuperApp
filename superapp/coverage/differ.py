"""Coverage Differ implementation."""

import json
from typing import List, Any
import ollama

from superapp.config import settings
from superapp.models import (
    CoverageSchema, 
    SchemaItem, 
    CoverageResult, 
    CoverageStatus, 
    Document, 
    Chunk
)
from superapp.coverage.prompts import (
    COVERAGE_CHECK_SYSTEM_PROMPT,
    COVERAGE_CHECK_USER_PROMPT
)

class CoverageDiffer:
    """Calculates coverage differences between a schema and document content."""

    def __init__(self) -> None:
        """Initialize the differ with the Ollama client."""
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        self.model = settings.ollama_reasoning_model

    async def _check_single_item(self, item: SchemaItem, content: str) -> CoverageResult:
        """Check a single schema item against the content."""
        prompt = COVERAGE_CHECK_USER_PROMPT.format(
            schema_topic=item.name,
            schema_description=item.description or "No description provided.",
            document_content=content
        )
        
        messages = [
            {"role": "system", "content": COVERAGE_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": prompt}
        ]

        try:
            response = await self.client.chat(
                model=self.model,
                messages=messages,
                format="json"
            )
            response_content = response.get("message", {}).get("content", "{}")
            data = json.loads(response_content)
            
            # Map status string to CoverageStatus Enum, default to missing if unknown
            status_str = data.get("status", "missing")
            try:
                status = CoverageStatus(status_str)
            except ValueError:
                status = CoverageStatus.MISSING
                
            return CoverageResult(
                item_id=item.id,
                status=status,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=str(data.get("reasoning", "Failed to parse reasoning.")),
                evidence=data.get("evidence", [])
            )
        except Exception as e:
            # Handle malformed response or API error
            return CoverageResult(
                item_id=item.id,
                status=CoverageStatus.MISSING,
                confidence=0.0,
                reasoning=f"Error analyzing coverage: {str(e)}",
                evidence=[]
            )

    async def diff_coverage(
        self, 
        schema: CoverageSchema, 
        documents: List[Document], 
        chunks: List[Chunk]
    ) -> List[CoverageResult]:
        """
        Assess coverage for all schema items against the documents and chunks.
        """
        # Combine document contents to create the corpus context
        content_parts = [doc.content for doc in documents if doc.content]
        # Also include chunks if document content is missing or for additional context
        content_parts.extend([chunk.content for chunk in chunks if chunk.content])
        
        full_content = "\n\n".join(content_parts)
        
        results = []
        for item in schema.items:
            result = await self._check_single_item(item, full_content)
            results.append(result)
            
        # Sort results: Missing first, then Partially Covered, then Covered.
        # Secondary sort by confidence (ascending - least confident first)
        def sort_key(res: CoverageResult) -> tuple[int, float]:
            order = {
                CoverageStatus.MISSING: 0,
                CoverageStatus.PARTIALLY_COVERED: 1,
                CoverageStatus.COVERED: 2
            }
            return (order.get(res.status, 3), res.confidence)
            
        results.sort(key=sort_key)
        return results
