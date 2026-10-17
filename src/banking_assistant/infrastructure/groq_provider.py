from langchain_core.language_models import BaseChatModel
from langchain_groq import ChatGroq


class GroqLLMProvider:
    def __init__(self, api_key: str, model: str, max_tokens: int):
        if not api_key:
            raise ValueError("Groq API key is required")

        if not model:
            raise ValueError("Groq model is required")

        self.api_key = api_key
        self.model = model
        self.max_tokens = max_tokens  # Default value, can be overridden by settings

    def get_chat_model(self) -> BaseChatModel:
        return ChatGroq(
            api_key=self.api_key,
            model=self.model,
            temperature=0,
            timeout=20,
            max_retries=0,
            max_tokens=self.max_tokens,
        )
