from banking_assistant.core.config import Settings
from banking_assistant.domain.llm_port import LLMProvider
from banking_assistant.infrastructure.groq_provider import (
    GroqLLMProvider,
)


def create_llm_provider(settings: Settings) -> LLMProvider:

    if settings.llm_provider == "groq":
        return GroqLLMProvider(
            api_key=settings.groq_api_key,
            model=settings.groq_model,
            max_tokens=settings.max_tokens,
        )

    if settings.llm_provider == "openai":
        raise NotImplementedError("OpenAI adapter has not been implemented yet")

    if settings.llm_provider == "anthropic":
        raise NotImplementedError("Anthropic adapter has not been implemented yet")

    raise ValueError(f"Unsupported LLM provider: {settings.llm_provider}")
