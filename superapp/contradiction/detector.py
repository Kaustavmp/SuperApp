import json
import uuid
import ollama
from typing import List, Set, FrozenSet

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
        await self.vector_store.add_claims(claims)
        
        checked_pairs: Set[FrozenSet[str]] = set()
        relations: List[ClaimRelation] = []
        
        # 2. For each claim, find similar claims via vector store
        for claim in claims:
            # candidate pruning (similarity threshold conceptually handled by vector store)
            similar_claims = await self.vector_store.find_similar_claims(claim, k=5) 
            
            for candidate in similar_claims:
                if claim.id == candidate.id:
                    continue
                    
                pair = frozenset([claim.id, candidate.id])
                if pair in checked_pairs:
                    continue
                    
                checked_pairs.add(pair)
                
                # 3. Call LLM to check for contradiction
                relation = await self._check_pair(claim, candidate)
                if relation:
                    relations.append(relation)
                    
        return relations
        
    async def _check_pair(self, claim_a: AtomicClaim, claim_b: AtomicClaim) -> ClaimRelation:
        messages = [
            {"role": "system", "content": CONTRADICTION_CHECK_SYSTEM_PROMPT},
            {"role": "user", "content": CONTRADICTION_CHECK_USER_PROMPT.format(
                claim_a=claim_a.claim_text,
                claim_b=claim_b.claim_text
            )}
        ]
        
        response = await self.client.chat(
            model=settings.ollama_reasoning_model,
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
            
            # Create relation object
            return ClaimRelation(
                id=str(uuid.uuid4()),
                source_claim_id=claim_a.id,
                target_claim_id=claim_b.id,
                relation=rel_type,
                confidence=float(confidence),
                reasoning=reasoning
            )
            
        except Exception as e:
            print(f"Error checking pair {claim_a.id} and {claim_b.id}: {e}")
            return None
