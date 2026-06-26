from functools import lru_cache
from typing import Annotated

from pydantic import field_validator
from pydantic_settings import BaseSettings, NoDecode, SettingsConfigDict


class Settings(BaseSettings):
    app_name: str = "AI Agent Chatbot MVP"
    app_env: str = "development"
    app_host: str = "127.0.0.1"
    app_port: int = 8000
    database_url: str = "sqlite:///./data/chatbot.db"
    cors_origins: Annotated[list[str], NoDecode] = [
        "http://localhost:5173",
        "http://127.0.0.1:5173",
    ]
    max_context_messages: int = 20
    max_user_message_length: int = 10_000

    llm_provider: str = "mock"
    openai_api_key: str | None = None
    openai_base_url: str | None = "https://api.openai.com/v1"
    openai_model: str | None = "gpt-4.1-mini"

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @field_validator("cors_origins", mode="before")
    @classmethod
    def parse_cors_origins(cls, value: object) -> object:
        if isinstance(value, str):
            return [item.strip() for item in value.split(",") if item.strip()]
        return value

    @field_validator("llm_provider")
    @classmethod
    def normalize_provider(cls, value: str) -> str:
        return value.strip().lower()

    @field_validator("openai_api_key", "openai_base_url", "openai_model", mode="before")
    @classmethod
    def normalize_optional_openai_value(cls, value: object) -> object:
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


@lru_cache
def get_settings() -> Settings:
    return Settings()
