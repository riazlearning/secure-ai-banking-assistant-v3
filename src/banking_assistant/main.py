from fastapi import FastAPI
from contextlib import asynccontextmanager
from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.api.dependencies import get_chat_model
from banking_assistant.core.config import get_settings
from banking_assistant.infrastructure.checkpointer import create_checkpointer

from banking_assistant.api.banking_routes import router as banking_router

from banking_assistant.api.exception_handlers import transfer_rejected_handler
from banking_assistant.domain.exceptions import TransferRejectedError
from dotenv import load_dotenv

from banking_assistant.api.chat_routes import (
    router as chat_router,
)

load_dotenv()  # Load environment variables from .env file


@asynccontextmanager
async def lifespan(app: FastAPI):
    async with create_checkpointer(get_settings()) as checkpointer:
        app.state.banking_agent = BankingAgent(
            model=get_chat_model(), checkpointer=checkpointer,
        )
        try:
            yield
        finally:
            del app.state.banking_agent


app = FastAPI(
    lifespan=lifespan,
    title="Secure AI Banking Assistant V3",
    version="0.1.0",
    description="Production-oriented AI Banking Assistant learning project",
)

app.add_exception_handler(
    TransferRejectedError,
    transfer_rejected_handler,
)
app.include_router(banking_router)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
