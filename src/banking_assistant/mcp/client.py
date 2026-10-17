"""Managed MCP session and allowlisted LangChain tool adapters."""

import json
import logging
import sys
from time import perf_counter
from collections.abc import AsyncIterator, Iterable
from contextlib import asynccontextmanager
from datetime import timedelta

from langchain_core.tools import StructuredTool, ToolException
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client

from banking_assistant.agents.tools.registry import ALLOWED_TOOL_NAMES, ToolRegistry

logger = logging.getLogger(__name__)


class BankingMCPClient:
    def __init__(self, session: ClientSession):
        self.session = session

    async def tool_registry(
        self,
        allowed_names: Iterable[str] = ALLOWED_TOOL_NAMES,
    ) -> ToolRegistry:
        names = list(allowed_names)
        if len(names) != len(set(names)):
            raise ValueError("Allowed tool names must be unique")
        discovered = {}
        cursor = None
        while True:
            page = await self.session.list_tools(cursor=cursor)
            for tool in page.tools:
                if tool.name in discovered:
                    raise ValueError(f"Duplicate MCP tool: {tool.name}")
                discovered[tool.name] = tool
            cursor = page.nextCursor
            if not cursor:
                break
        missing = set(names).difference(discovered)
        if missing:
            raise ValueError(f"Allowed MCP tools are unavailable: {sorted(missing)}")

        def adapt(name: str) -> StructuredTool:
            remote = discovered[name]

            async def invoke(**arguments):
                # Decimal input from callers must be JSON serializable.
                arguments = json.loads(json.dumps(arguments, default=str))
                started = perf_counter()
                logger.info("MCP client calling tool: %s", name, extra={"tool_name": name})
                try:
                    result = await self.session.call_tool(name, arguments)
                    if result.isError:
                        raise ToolException("MCP tool rejected the request or failed")
                except Exception as exc:
                    logger.error(
                        "MCP client tool call failed: %s", name,
                        extra={"tool_name": name, "error_type": type(exc).__name__,
                               "duration_ms": round((perf_counter() - started) * 1000, 2)},
                    )
                    raise
                logger.info(
                    "MCP client tool call completed: %s", name,
                    extra={"tool_name": name,
                           "duration_ms": round((perf_counter() - started) * 1000, 2)},
                )
                if result.structuredContent is not None:
                    return result.structuredContent
                text = "\n".join(
                    block.text for block in result.content if block.type == "text"
                )
                try:
                    return json.loads(text)
                except ValueError:
                    return text

            return StructuredTool(
                name=name,
                description=remote.description or name,
                args_schema=remote.inputSchema,
                coroutine=invoke,
            )

        return ToolRegistry(adapt(name) for name in names)


@asynccontextmanager
async def connect_banking_mcp() -> AsyncIterator[BankingMCPClient]:
    """Launch the bundled server and close its session/process on exit."""
    logger.info("Starting MCP banking server via stdio")
    parameters = StdioServerParameters(
        command=sys.executable,
        args=["-m", "banking_assistant.mcp.server"],
    )
    async with stdio_client(parameters) as (read, write):
        async with ClientSession(
            read,
            write,
            read_timeout_seconds=timedelta(seconds=30),
        ) as session:
            await session.initialize()
            logger.info("MCP banking session initialized")
            yield BankingMCPClient(session)
