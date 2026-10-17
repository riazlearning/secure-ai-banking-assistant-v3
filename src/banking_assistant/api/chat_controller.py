from banking_assistant.api.chat_schemas import (
    ChatRequest,
    ChatResponse,
    ApprovalRequest,
)
from banking_assistant.services.chat_service import ChatService


class ChatController:
    def __init__(self, service: ChatService):
        self.service = service

    async def chat(self, request: ChatRequest) -> ChatResponse:
        return await self.service.ask_response(
            message=request.message,
            thread_id=request.thread_id,
        )

    async def review(self, request: ApprovalRequest) -> ChatResponse:
        return await self.service.review(request.thread_id, request.approval_id, request.decision)
