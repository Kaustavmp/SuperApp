import json
import ollama
import uuid
from typing import List, Dict

from superapp.config import settings
from superapp.models import Document, Chunk, AtomicClaim
from .prompts import CLAIM_EXTRACTION_SYSTEM_PROMPT, CLAIM_EXTRACTION_USER_PROMPT

class ClaimExtractor:
    def __init__(self):
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        
    async def extract_claims(self, chunks: List[Chunk], documents: List[Document]) -> List[AtomicClaim]:
        # Build lookup dict for document filenames
        doc_lookup: Dict[str, str] = {doc.id: doc.filename for doc in documents}
        
        all_claims = []
        for chunk in chunks:
            source_filename = doc_lookup.get(chunk.document_id, "unknown")
            claims = await self._extract_from_chunk(chunk, source_filename)
            all_claims.extend(claims)
            
        return all_claims
        
    async def _extract_from_chunk(self, chunk: Chunk, source_filename: str) -> List[AtomicClaim]:
        messages = [
            {"role": "system", "content": CLAIM_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": CLAIM_EXTRACTION_USER_PROMPT.format(chunk_content=chunk.content)}
        ]
        
        response = await self.client.chat(
            model=settings.ollama_reasoning_model,
            messages=messages,
            format="json"
        )
        
        claims_data = []
        try:
            parsed = json.loads(response['message']['content'])
            if isinstance(parsed, list):
                claims_data = parsed
            elif isinstance(parsed, dict) and 'claims' in parsed:
                claims_data = parsed['claims']
        except Exception as e:
            print(f"Error parsing JSON from LLM: {e}")
            
        atomic_claims = []
        for c in claims_data:
            if isinstance(c, dict) and "claim_text" in c:
                claim_id = str(uuid.uuid4())
                ac = AtomicClaim(
                    id=claim_id,
                    claim_text=c["claim_text"],
                    source_chunk_id=chunk.id,
                    source_document_id=chunk.document_id,
                    source_filename=source_filename
                )
                atomic_claims.append(ac)
                
        return atomic_claims
