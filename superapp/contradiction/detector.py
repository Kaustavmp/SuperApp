import json
import uuid
import ollama
import asyncio
from typing import List, Set, FrozenSet, Optional

from superapp.config import settings
from superapp.models import AtomicClaim, ClaimRelation, RelationType
from .prompts import CONTRADICTION_CHECK_SYSTEM_PROMPT, CONTRADICTION_CHECK_USER_PROMPT

class ContradictionDetector:
    def __init__(self, vector_store):
        self.vector_store = vector_store
        self.client = ollama.AsyncClient(host=settings.ollama_host)
        
    async def detect_contradictions(self, claims: List[AtomicClaim]) -> List[ClaimRelation]:
        # 1. Add all claims to vector store
        # Assuming vector_store has a method like add_claims
        # VectorStore methods are synchronous; call directly
        self.vector_store.add_claims(claims)
        
        checked_pairs: Set[FrozenSet[str]] = set()
        candidate_pairs: List[tuple[AtomicClaim, AtomicClaim]] = []
        
        # 2. For each claim, find similar claims via vector store
        for claim in claims:
            # candidate pruning (similarity threshold conceptually handled by vector store)
            similar_claims = self.vector_store.find_similar_claims(claim, n_results=5)
            
            for candidate in similar_claims:
                if claim.id == candidate.id:
                    continue
                    
                pair = frozenset([claim.id, candidate.id])
                if pair in checked_pairs:
                    continue
                    
                checked_pairs.add(pair)
                
                candidate_pairs.append((claim, candidate))

        semaphore = asyncio.Semaphore(max(1, settings.max_concurrent_llm_calls))

        async def check(pair: tuple[AtomicClaim, AtomicClaim]) -> Optional[ClaimRelation]:
            async with semaphore:
                return await self._check_pair(*pair)

        checked = await asyncio.gather(*(check(pair) for pair in candidate_pairs))
        return [relation for relation in checked if relation]
        
    async def _check_pair(self, claim_a: AtomicClaim, claim_b: AtomicClaim) -> Optional[ClaimRelation]:
        messages = [
            {"role": "system", "content": CONTRADICTION_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": CONTRADICTION_CHECK_USER_PROMPT.format(
                claim_a=claim_a.claim_text,
                claim_b=claim_b.claim_text
            )}
        ]
        
        response = await self.client.chat(
            model=settings.get_model_for_stage("contradiction_classification"),
            messages=messages,
            format="json"
        )
        
        try:
            parsed = json.loads(response['message']['content'])
            rel_str = parsed.get("relation", "unrelated")
            confidence = parsed.get("confidence", 0.0)
            reasoning = parsed.get("reasoning", "")
            
            # Map string to RelationType enum if needed
            rel_map = {
                "supports": RelationType.SUPPORTS,
                "contradicts": RelationType.CONTRADICTS,
                "silent_on": RelationType.SILENT_ON,
                "unrelated": RelationType.UNRELATED
            }
            
            rel_type = rel_map.get(rel_str, RelationType.UNRELATED)

            # Create relation object following models.ClaimRelation schema
            return ClaimRelation(
                claim_a_id=claim_a.id,
                claim_b_id=claim_b.id,
                relation=rel_type,
                confidence=float(confidence),
                reasoning=reasoning
            )
            
        except Exception as e:
            print(f"Error checking pair {claim_a.id} and {claim_b.id}: {e}")
            return None
