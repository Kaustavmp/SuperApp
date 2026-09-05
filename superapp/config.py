"""SuperApp configuration management using pydantic-settings."""

from typing import Literal

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Application settings loaded from environment variables or .env file."""

    llm_provider: Literal["ollama", "anthropic", "openai"] = "ollama"
    default_model_tier: Literal["fast", "mid", "top"] = "mid"

    ollama_host: str = "http://localhost:11434"
    ollama_reasoning_model: str = "llama3.1"
    ollama_embedding_model: str = "nomic-embed-text"
    ollama_fast_model: str = "llama3.1"
    ollama_mid_model: str = "llama3.1"
    ollama_top_model: str = "llama3.1"

    anthropic_api_key: str = ""
    anthropic_fast_model: str = "claude-haiku-4-5"
    anthropic_mid_model: str = "claude-sonnet-4-5"
    anthropic_top_model: str = "claude-opus-4-5"

    openai_api_key: str = ""
    openai_fast_model: str = "gpt-4o-mini"
    openai_mid_model: str = "gpt-4o"
    openai_top_model: str = "gpt-4o"

    cascade_claim_extraction: str = "fast"
    cascade_coverage_diff: str = "mid"
    cascade_contradiction_classification: str = "mid"
    cascade_schema_induction: str = "top"

    chunk_size: int = 1000
    chunk_overlap: int = 200
    max_concurrent_llm_calls: int = 4

    min_confidence_threshold: float = 0.3
    contradiction_similarity_threshold: float = 0.5

    chroma_persist_dir: str = "./chroma_db"

    db_backend: str = "sqlite"
    database_url: str = "sqlite:///./superapp.db"
    sqlite_path: str = "./superapp.db"

    max_tokens_per_job: int = 500000
    max_cost_per_job_usd: float = 0.0
    input_cost_per_million_tokens: float = 0.0
    output_cost_per_million_tokens: float = 0.0

    auth_provider: str = "none"
    api_key: str = ""
    default_role: str = "admin"
    host: str = "0.0.0.0"
    port: int = 8000
    debug: bool = True

    model_config = {"env_file": ".env", "env_file_encoding": "utf-8"}

    def get_model_for_stage(self, stage: str) -> str:
        """Resolve a cascade stage to the configured provider-specific model."""
        tier = getattr(self, f"cascade_{stage}", self.default_model_tier)
        return getattr(self, f"{self.llm_provider}_{tier}_model")

    def get_model_for_stage(self, stage: str) -> str:
        """Resolve a cascade stage to the configured provider-specific model."""
        tier = getattr(self, f"cascade_{stage}", self.default_model_tier)
        return getattr(self, f"{self.llm_provider}_{tier}_model")


settings = Settings()
