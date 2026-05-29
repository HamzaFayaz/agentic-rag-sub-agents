from functools import lru_cache

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    supabase_url: str
    supabase_anon_key: str
    openai_api_key: str
    openai_model: str = "gpt-4o-mini"
    openai_embedding_model: str = "text-embedding-3-small"
    langsmith_api_key: str | None = None
    langsmith_project: str = "agentic-rag-module-1"
    langsmith_tracing: bool = False
    langsmith_log_chunk_text: bool = False
    cors_origins: str = "http://localhost:5173"

    rag_top_k: int = 5
    # Cosine similarity floor for match_document_chunks. 0.7 is often too strict
    # for large chunks + text-embedding-3-small (short queries score ~0.45–0.69).
    rag_match_threshold: float = 0.5
    max_upload_bytes: int = 10_485_760
    chunk_size: int = 600
    chunk_overlap: int = 120
    max_chunk_tokens: int = 800
    min_headings_for_section: int = 2

    # Module 4: LLM metadata extraction
    metadata_extraction_enabled: bool = True
    metadata_model: str = "gpt-4o-mini"

    # Module 6: hybrid search + Cohere rerank
    cohere_api_key: str | None = None
    rerank_model: str = "rerank-v3.5"
    rerank_enabled: bool = True
    rerank_top_n: int = 8
    hybrid_candidate_k: int = 40

    system_prompt: str = Field(
        default=(
            "You are a helpful assistant. Answer clearly and concisely using the "
            "provided context when relevant. Cite source filenames when you use "
            "information from the context. If the context does not contain the "
            "answer, say so rather than inventing facts."
        )
    )
    max_history_messages: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]

    def build_rag_system_prompt(self, context_blocks: list[str]) -> str:
        if not context_blocks:
            return self.system_prompt

        context = "\n\n---\n\n".join(context_blocks)
        return (
            f"{self.system_prompt}\n\n"
            "Use the following retrieved document excerpts as context. "
            "When you rely on them, mention the source filename.\n\n"
            f"{context}"
        )


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
