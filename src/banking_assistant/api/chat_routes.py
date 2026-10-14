from typing import Annotated

from fastapi import APIRouter, Depends

from banking_assistant.api.chat_controller import ChatController
from banking_assistant.api.chat_schemas import (
    ChatRequest,
    ChatResponse,
)
from banking_assistant.api.dependencies import get_chat_controller


router = APIRouter(
    prefix="/api/v1/chat",
    tags=["Banking Chat"],
)


@router.post("", response_model=ChatResponse)
async def chat(
    request: ChatRequest,
    controller: Annotated[
        ChatController,
        Depends(get_chat_controller),
    ],
) -> ChatResponse:
    return await controller.chat(request)
