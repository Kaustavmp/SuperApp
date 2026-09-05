try:
    import chromadb
    from chromadb.utils.embedding_functions import OllamaEmbeddingFunction
except Exception:  # pragma: no cover - optional dependency on some Windows setups
    chromadb = None
    OllamaEmbeddingFunction = None

from superapp.config import settings
from superapp.models import Chunk, AtomicClaim


class VectorStore:
    def __init__(self, collection_name: str = 'superapp'):
        self.collection_name = collection_name
        self._available = chromadb is not None and OllamaEmbeddingFunction is not None

        if not self._available:
            self.client = None
            self.embedding_function = None
            self.collection = None
            self.claims_collection = None
            return

        self.client = chromadb.PersistentClient(path=settings.chroma_persist_dir)
        self.embedding_function = OllamaEmbeddingFunction(
            url=settings.ollama_host,
            model_name=settings.ollama_embedding_model,
        )

        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

        self.claims_collection = self.client.get_or_create_collection(
            name='claims',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )

    def add_chunks(self, chunks: list[Chunk]) -> None:
        if not self._available or not self.collection:
            return

        ids = [chunk.id for chunk in chunks]
        documents = [chunk.content for chunk in chunks]
        metadatas = [
            {
                "document_id": chunk.document_id,
                "chunk_index": chunk.chunk_index,
            }
            for chunk in chunks
        ]

        self.collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def add_claims(self, claims: list[AtomicClaim]) -> None:
        if not self._available or not self.claims_collection:
            return

        ids = [claim.id for claim in claims]
        documents = [claim.claim_text for claim in claims]
        metadatas = [
            {
                "source_document_id": claim.source_document_id,
                "source_chunk_id": claim.source_chunk_id,
                "source_filename": claim.source_filename,
            }
            for claim in claims
        ]

        self.claims_collection.add(
            ids=ids,
            documents=documents,
            metadatas=metadatas,
        )

    def find_similar_chunks(self, query: str, n_results: int = 5) -> list[tuple[str, str, float]]:
        if not self._available or not self.collection:
            return []

        results = self.collection.query(
            query_texts=[query],
            n_results=n_results,
        )

        if not results['ids'] or not results['ids'][0]:
            return []

        return [
            (id_, doc, dist)
            for id_, doc, dist in zip(
                results['ids'][0],
                results['documents'][0],
                results['distances'][0],
            )
        ]

    def find_similar_claims(self, claim, n_results: int = 10, threshold: float = None) -> list[AtomicClaim]:
        if not self._available or not self.claims_collection:
            return []

        if threshold is None:
            threshold = getattr(settings, 'contradiction_similarity_threshold', 0.8)

        query_text = claim.claim_text if hasattr(claim, 'claim_text') else str(claim)
        results = self.claims_collection.query(
            query_texts=[query_text],
            n_results=n_results,
        )

        if not results.get('ids') or not results['ids'][0]:
            return []

        ids = results['ids'][0]
        documents = results.get('documents', [[]])[0]
        distances = results.get('distances', [[]])[0]
        metadatas = results.get('metadatas', [[]])[0]

        similar_claims: list[AtomicClaim] = []
        for i, id_ in enumerate(ids):
            doc = documents[i] if i < len(documents) else ""
            dist = distances[i] if i < len(distances) else 1.0
            meta = metadatas[i] if i < len(metadatas) else {}

            similarity = 1.0 - dist
            if similarity < threshold:
                continue

            ac = AtomicClaim(
                id=id_,
                claim_text=doc,
                source_document_id=meta.get('source_document_id', ''),
                source_chunk_id=meta.get('source_chunk_id', ''),
                source_filename=meta.get('source_filename', ''),
                metadata=meta or {},
            )
            similar_claims.append(ac)

        return similar_claims

    def reset(self) -> None:
        if not self._available or not self.client:
            return

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
            metadata={"hnsw:space": "cosine"},
        )

        self.claims_collection = self.client.get_or_create_collection(
            name='claims',
            embedding_function=self.embedding_function,
            metadata={"hnsw:space": "cosine"},
        )
