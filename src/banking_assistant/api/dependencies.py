from banking_assistant.api.banking_controller import BankingController
from banking_assistant.services.banking_service import BankingService
from functools import lru_cache
from fastapi import Request

from langchain_core.language_models import BaseChatModel

from banking_assistant.core.config import get_settings
from banking_assistant.infrastructure.provider_factory import (
    create_llm_provider,
)


from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.api.chat_controller import ChatController
from banking_assistant.services.chat_service import ChatService

# from dotenv import load_dotenv

# load_dotenv()


def get_banking_service() -> BankingService:
    return BankingService()


def get_banking_controller() -> BankingController:
    service = get_banking_service()
    return BankingController(service)


@lru_cache
def get_chat_model() -> BaseChatModel:
    settings = get_settings()

    provider = create_llm_provider(settings)

    return provider.get_chat_model()


def get_banking_agent(request: Request) -> BankingAgent:
    return request.app.state.banking_agent


def get_chat_service(request: Request) -> ChatService:
    return ChatService(agent=get_banking_agent(request))


def get_chat_controller(request: Request) -> ChatController:
    return ChatController(service=get_chat_service(request))
