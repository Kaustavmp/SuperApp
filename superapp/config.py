"""SuperApp configuration management using pydantic-settings."""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    # Ollama
    ollama_host: str = "http://localhost:11434"
    ollama_reasoning_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"

    # Chunking
    chunk_size: int = 1000
    chunk_overlap: int = 200

    # Confidence thresholds
    min_confidence_threshold: float = 0.3
    contradiction_similarity_threshold: float = 0.5

    # ChromaDB
    chroma_persist_dir: str = "./chroma_db"

    # Server
    host: str = "0.0.0.0"
    port: int = 8000

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}


# Singleton settings instance
settings = Settings()
