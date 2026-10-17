"""Local stdio server exposing only the existing demonstration tools."""

import asyncio
import logging
import sys
from time import perf_counter

from pythonjsonlogger.json import JsonFormatter

from mcp import types
from mcp.server import Server
from mcp.server.stdio import stdio_server

from banking_assistant.agents.tools.registry import DEFAULT_TOOL_REGISTRY

server = Server("banking-tools")
logger = logging.getLogger(__name__)


@server.list_tools()
async def list_tools() -> list[types.Tool]:
    return [
        types.Tool(
            name=tool.name,
            description=tool.description,
            inputSchema=tool.get_input_schema().model_json_schema(),
        )
        for tool in DEFAULT_TOOL_REGISTRY.tools.values()
    ]


@server.call_tool()
async def call_tool(name: str, arguments: dict) -> dict:
    started = perf_counter()
    logger.info("MCP server executing tool: %s", name, extra={"tool_name": name})
    try:
        tool = DEFAULT_TOOL_REGISTRY.tools.get(name)
        if tool is None:
            raise ValueError("Unknown banking tool")
        # Reuse local validation and business logic; never implement real transfers here.
        result = await tool.ainvoke(arguments)
    except Exception as exc:
        logger.error(
            "MCP server tool execution failed: %s", name,
            extra={"tool_name": name, "error_type": type(exc).__name__,
                   "duration_ms": round((perf_counter() - started) * 1000, 2)},
        )
        raise
    logger.info(
        "MCP server tool execution completed: %s", name,
        extra={"tool_name": name,
               "duration_ms": round((perf_counter() - started) * 1000, 2)},
    )
    return result


async def serve() -> None:
    async with stdio_server() as (read, write):
        await server.run(read, write, server.create_initialization_options())


def main() -> None:
    # stdout belongs exclusively to MCP JSON-RPC messages.
    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(JsonFormatter("%(asctime)s %(levelname)s %(name)s %(message)s"))
    logging.basicConfig(level=logging.INFO, handlers=[handler], force=True)
    asyncio.run(serve())


if __name__ == "__main__":
    main()
