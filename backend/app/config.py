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
    cors_origins: str = "http://localhost:5173"

    rag_top_k: int = 5
    rag_match_threshold: float = 0.7
    max_upload_bytes: int = 10_485_760
    chunk_size: int = 1000
    chunk_overlap: int = 200

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
