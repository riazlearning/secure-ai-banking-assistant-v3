from fastapi import FastAPI
from contextlib import AsyncExitStack, asynccontextmanager
from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.api.dependencies import get_chat_model
from banking_assistant.core.config import get_settings
from banking_assistant.infrastructure.checkpointer import create_checkpointer
from banking_assistant.infrastructure.logging_config import configure_logging

from banking_assistant.api.banking_routes import router as banking_router

from banking_assistant.api.exception_handlers import (
    transfer_rejected_handler,
    application_error_handler,
    request_validation_handler,
    http_error_handler,
)
from fastapi.exceptions import RequestValidationError
from starlette.exceptions import HTTPException
from banking_assistant.agents.exceptions import AgentError
from banking_assistant.services.exceptions import ApplicationError
from banking_assistant.domain.exceptions import TransferRejectedError
from dotenv import load_dotenv

from banking_assistant.api.chat_routes import (
    router as chat_router,
)

from banking_assistant.agents.tools.registry import (
    DEFAULT_TOOL_REGISTRY,
    ALLOWED_TOOL_NAMES,
    ToolRegistry,
)

load_dotenv()  # Load environment variables from .env file


@asynccontextmanager
async def lifespan(app: FastAPI):
    configure_logging()
    settings = get_settings()
    async with AsyncExitStack() as stack:
        checkpointer = await stack.enter_async_context(create_checkpointer(settings))

        registry = DEFAULT_TOOL_REGISTRY
        allowed_names = list(ALLOWED_TOOL_NAMES)
        if settings.mcp_enabled:
            from banking_assistant.mcp.client import connect_banking_mcp

            banking_client = await stack.enter_async_context(connect_banking_mcp())
            banking_registry = await banking_client.tool_registry()

            from banking_assistant.mcp.github_client import connect_github_mcp

            github_client = await stack.enter_async_context(connect_github_mcp())
            github_registry = await github_client.tool_registry(
                allowed_names=["get_me", "get_file_contents"]
            )

            from banking_assistant.mcp.weather_client import connect_weather_mcp, WEATHER_TOOL_NAMES

            weather_client = await stack.enter_async_context(connect_weather_mcp())
            weather_registry = await weather_client.tool_registry(WEATHER_TOOL_NAMES)

            combined_tools = [
                *banking_registry.tools.values(),
                *github_registry.tools.values(),
                *weather_registry.tools.values(),
            ]

            registry = ToolRegistry(combined_tools)

            allowed_names = [
                *ALLOWED_TOOL_NAMES,
                "get_me",
                "get_file_contents",
                *WEATHER_TOOL_NAMES,
            ]
        app.state.banking_agent = BankingAgent(
            model=get_chat_model(),
            checkpointer=checkpointer,
            tool_registry=registry,
            allowed_tool_names=allowed_names,
        )
        print(
            "Agent registered tools:",
            [tool.name for tool in app.state.banking_agent.tools],
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
app.add_exception_handler(AgentError, application_error_handler)
app.add_exception_handler(ApplicationError, application_error_handler)
app.add_exception_handler(RequestValidationError, request_validation_handler)
app.add_exception_handler(HTTPException, http_error_handler)
app.add_exception_handler(Exception, application_error_handler)
app.include_router(banking_router)

app.include_router(chat_router)


@app.get("/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}
