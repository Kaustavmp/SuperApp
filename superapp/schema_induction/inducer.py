import json
import logging
from typing import List

import ollama

from superapp.config import settings
from superapp.models import Document, CoverageSchema, SchemaItem
from superapp.schema_induction.prompts import (
    SCHEMA_INDUCTION_SYSTEM_PROMPT,
    SCHEMA_INDUCTION_USER_PROMPT,
    SCHEMA_MERGE_PROMPT
)

logger = logging.getLogger(__name__)

class SchemaInducer:
    """
    Induces a comprehensive schema (CoverageSchema) of topics/sections
    from a set of documents using Ollama LLM.
    """
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        self.model = settings.ollama_reasoning_model

    async def _call_llm(self, system_prompt: str, user_prompt: str) -> str:
        """Helper to call Ollama chat with JSON format."""
        try:
            response = await self.client.chat(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                format="json"
            )
            return response["message"]["content"]
        except Exception as e:
            logger.error(f"Error calling LLM: {e}")
            raise RuntimeError(f"Failed to communicate with LLM: {e}")

    def _parse_schema_items(self, raw_json: str) -> List[SchemaItem]:
        """Parse LLM JSON output into SchemaItem list."""
        try:
            data = json.loads(raw_json)
            # Handle potential dict wrapping
            if not isinstance(data, list):
                if isinstance(data, dict) and "schema" in data:
                    data = data["schema"]
                else:
                    data = [data]
            
            items = []
            for item in data:
                items.append(SchemaItem(
                    category=item.get("category", "Uncategorized"),
                    topic=item.get("topic", "Unknown Topic"),
                    description=item.get("description", ""),
                    importance=item.get("importance", "medium")
                ))
            return items
        except json.JSONDecodeError as e:
            logger.error(f"JSON decode error: {e}. Raw response: {raw_json}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error parsing schema items: {e}")
            return []

    async def induce_schema(self, documents: List[Document], domain: str = 'open-source documentation') -> CoverageSchema:
        """
        Induces a schema by prompting the LLM on a sample of the documents.
        Merges results if multiple documents are processed.
        """
        if not documents:
            return CoverageSchema(items=[])

        # Sample up to 5 documents to avoid massive prompt token usage
        sample_docs = documents[:5]
        all_schemas_json = []

        for doc in sample_docs:
            user_prompt = SCHEMA_INDUCTION_USER_PROMPT.format(
                domain=domain,
                document_content=doc.content[:4000]  # Truncate content for sanity
            )
            raw_json = await self._call_llm(SCHEMA_INDUCTION_SYSTEM_PROMPT, user_prompt)
            all_schemas_json.append(raw_json)

        if len(sample_docs) == 1:
            items = self._parse_schema_items(all_schemas_json[0])
            return CoverageSchema(items=items)

        # Merge step
        merge_user_prompt = SCHEMA_MERGE_PROMPT.format(schemas=json.dumps(all_schemas_json))
        merged_json = await self._call_llm(SCHEMA_INDUCTION_SYSTEM_PROMPT, merge_user_prompt)
        merged_items = self._parse_schema_items(merged_json)

        return CoverageSchema(items=merged_items)
