from functools import lru_cache
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    llm_provider: Literal["groq", "openai", "anthropic"] = "groq"

    groq_api_key: str = Field(default="", repr=False)
    groq_model: str = ""
    max_tokens: int = Field(default=100, gt=0)

    postgres_host: str = "localhost"
    postgres_port: int = Field(default=5433, gt=0, le=65535)
    postgres_db: str = "banking_db"
    postgres_user: str = "banking"
    postgres_password: str = Field(default="", repr=False)

    # openai_api_key: str = Field(default="", repr=False)
    # openai_model: str = ""

    # anthropic_api_key: str = Field(default="", repr=False)
    # anthropic_model: str = ""


@lru_cache
def get_settings() -> Settings:
    return Settings()
