"""Coverage Differ implementation."""

import json
import asyncio
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
        self.model = settings.get_model_for_stage("coverage_diff")

    async def _check_single_item(self, item: SchemaItem, content: str) -> CoverageResult:
        """Check a single schema item against the content."""
        topic_name = getattr(item, "topic", getattr(item, "name", "General Topic"))
        prompt = COVERAGE_CHECK_USER_PROMPT.format(
            schema_topic=topic_name,
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
                schema_item=item,
                status=status,
                confidence=float(data.get("confidence", 0.0)),
                reasoning=str(data.get("reasoning", "Failed to parse reasoning.")),
                evidence_chunks=data.get("evidence", [])
            )
        except Exception as e:
            # Handle malformed response or API error
            return CoverageResult(
                schema_item=item,
                status=CoverageStatus.MISSING,
                confidence=0.0,
                reasoning=f"Error analyzing coverage: {str(e)}",
                evidence_chunks=[]
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
        
        semaphore = asyncio.Semaphore(max(1, settings.max_concurrent_llm_calls))

        async def check(item: SchemaItem) -> CoverageResult:
            async with semaphore:
                return await self._check_single_item(item, full_content)

        results = list(await asyncio.gather(*(check(item) for item in schema.items)))
            
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
