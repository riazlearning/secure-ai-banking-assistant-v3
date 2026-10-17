from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from datetime import timedelta

from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from banking_assistant.mcp.client import BankingMCPClient


WEATHER_MCP_URL = "https://open-meteo.caseyjhand.com/mcp"
WEATHER_TOOL_NAMES = ("openmeteo_search_locations", "openmeteo_get_forecast")


@asynccontextmanager
async def connect_weather_mcp() -> AsyncIterator[BankingMCPClient]:

    async with streamable_http_client(
        WEATHER_MCP_URL,
    ) as (read, write, _):
        async with ClientSession(
            read,
            write,
            read_timeout_seconds=timedelta(seconds=30),
        ) as session:
            await session.initialize()

            yield BankingMCPClient(session)
