import networkx as nx
from typing import List, Tuple, Dict, Any

from superapp.models import AtomicClaim, ClaimRelation, RelationType

class ContradictionGraphBuilder:
    def __init__(self):
        self.graph = nx.DiGraph()
        
    def build_graph(self, claims: List[AtomicClaim], relations: List[ClaimRelation]) -> nx.DiGraph:
        for claim in claims:
            self.graph.add_node(
                claim.id,
                claim_text=claim.claim_text,
                source_document_id=claim.source_document_id,
                source_filename=claim.source_filename
            )
            
        for relation in relations:
            relation_val = relation.relation.value if isinstance(relation.relation, RelationType) else relation.relation
            claim_a = getattr(relation, "claim_a_id", getattr(relation, "source_claim_id", None))
            claim_b = getattr(relation, "claim_b_id", getattr(relation, "target_claim_id", None))
            self.graph.add_edge(
                claim_a,
                claim_b,
                relation_type=relation_val,
                confidence=relation.confidence,
                reasoning=relation.reasoning
            )
            
        return self.graph
        
    def get_contradictions(self) -> List[Tuple[str, str, dict]]:
        contradictions = []
        for u, v, data in self.graph.edges(data=True):
            if data.get('relation_type') == 'contradicts' or data.get('relation_type') == RelationType.CONTRADICTS.value:
                contradictions.append((u, v, data))
        return contradictions
        
    def get_contradiction_clusters(self) -> List[List[str]]:
        # Create subgraph with only contradiction edges
        edge_list = []
        for u, v, data in self.graph.edges(data=True):
            if data.get('relation_type') == 'contradicts' or data.get('relation_type') == RelationType.CONTRADICTS.value:
                edge_list.append((u, v))
                
        contradiction_subgraph = self.graph.edge_subgraph(edge_list).to_undirected()
        
        # Find connected components
        components = list(nx.connected_components(contradiction_subgraph))
        return [list(comp) for comp in components]
        
    def export_graph_data(self) -> Dict[str, Any]:
        data = {
            "nodes": [],
            "edges": []
        }
        for node, attrs in self.graph.nodes(data=True):
            data["nodes"].append({
                "id": node,
                **attrs
            })
        for u, v, attrs in self.graph.edges(data=True):
            data["edges"].append({
                "source": u,
                "target": v,
                **attrs
            })
        return data
