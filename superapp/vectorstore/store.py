import chromadb
from chromadb.utils.embedding_functions import OllamaEmbeddingFunction

from superapp.config import settings
from superapp.models import Chunk, AtomicClaim

class VectorStore:
    def __init__(self, collection_name: str = 'superapp'):
        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.embedding_function = OllamaEmbeddingFunction(
            url=settings.ollama_host,
            model_name=settings.ollama_embedding_model
        )
        self.collection_name = collection_name
        
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.claims_collection = self.client.get_or_create_collection(
            name='claims',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not chunks:
            return
            
        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index
            }
            for chunk in chunks
        ]
        
        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def add_claims(self, claims: list[AtomicClaim]) -> None:
        if not claims:
            return
            
        ids = [claim.id for claim in claims]
        documents = [claim.claim_text for claim in claims]
        metadatas = [
            {
                "source_document_id": claim.source_document_id,
                "source_chunk_id": claim.source_chunk_id,
                "source_filename": claim.source_filename
            }
            for claim in claims
        ]
        
        self.claims_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas
        )

    def find_similar_chunks(self, query: str, n_results: int = 5) -> list[tuple[str, str, float]]:
        results = self.collection.query(
            query_texts=[query],
            n_results=n_results
        )
        
        if not results['ids'] or not results['ids'][0]:
            return []
            
        return [
            (id_, doc, dist)
            for id_, doc, dist in zip(
                results['ids'][0],
                results['documents'][0],
                results['distances'][0]
            )
        ]

    def find_similar_claims(self, claim_text: str, n_results: int = 10, threshold: float = None) -> list[tuple[str, str, float]]:
        if threshold is None:
            threshold = getattr(settings, 'contradiction_similarity_threshold', 0.8)
            
        results = self.claims_collection.query(
            query_texts=[claim_text],
            n_results=n_results
        )
        
        if not results['ids'] or not results['ids'][0]:
            return []
            
        similar_claims = []
        for id_, doc, dist in zip(
            results['ids'][0],
            results['documents'][0],
            results['distances'][0]
        ):
            # ChromaDB with cosine space returns distance = 1 - cosine_similarity
            similarity = 1.0 - dist
            if similarity >= threshold:
                similar_claims.append((id_, doc, dist))
                
        return similar_claims

    def reset(self) -> None:
        try:
            self.client.delete_collection(name=self.collection_name)
        except Exception:
            pass
            
        try:
            self.client.delete_collection(name='claims')
        except Exception:
            pass
            
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
        
        self.claims_collection = self.client.get_or_create_collection(
            name='claims',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"}
        )
