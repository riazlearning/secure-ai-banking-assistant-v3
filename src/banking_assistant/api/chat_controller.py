from banking_assistant.api.chat_schemas import (
    ChatRequest,
    ChatResponse,
)
from banking_assistant.services.chat_service import ChatService


class ChatController:
    def __init__(self, service: ChatService):
        self.service = service

    async def chat(self, request: ChatRequest) -> ChatResponse:
        answer = await self.service.ask(
            message=request.message,
            thread_id=request.thread_id,
        )

        return ChatResponse(
            answer=answer,
            thread_id=request.thread_id,
        )
