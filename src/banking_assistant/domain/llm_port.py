from typing import Protocol

from langchain_core.language_models import BaseChatModel


class LLMProvider(Protocol):
    def get_chat_model(self) -> BaseChatModel: ...
