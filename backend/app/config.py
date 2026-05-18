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
    langsmith_api_key: str | None = None
    langsmith_project: str = "agentic-rag-module-1"
    langsmith_tracing: bool = False
    cors_origins: str = "http://localhost:5173"

    system_prompt: str = Field(
        default=(
            "You are a helpful assistant. Answer clearly and concisely. "
            "If you do not know something, say so."
        )
    )
    max_history_messages: int = 50

    @property
    def cors_origin_list(self) -> list[str]:
        return [o.strip() for o in self.cors_origins.split(",") if o.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()


settings = get_settings()
