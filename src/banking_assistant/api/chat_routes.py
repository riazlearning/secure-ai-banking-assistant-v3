from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException, Path

from banking_assistant.api.chat_controller import ChatController
from banking_assistant.api.chat_schemas import (
    ChatRequest,
    ChatResponse,
    ApprovalRequest,
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


@router.post("/approvals", response_model=ChatResponse)
async def review_approval(
    request: ApprovalRequest,
    controller: Annotated[ChatController, Depends(get_chat_controller)],
) -> ChatResponse:
    try:
        return await controller.review(request)
    except ValueError as exc:
        raise HTTPException(status_code=409, detail=str(exc)) from exc


@router.get("/{thread_id}/approvals", response_model=ChatResponse)
async def approval_status(
    thread_id: Annotated[str, Path(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")],
    controller: Annotated[ChatController, Depends(get_chat_controller)],
) -> ChatResponse:
    return await controller.service.review_status(thread_id)
