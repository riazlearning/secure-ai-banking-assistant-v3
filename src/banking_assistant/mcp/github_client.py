import os
import httpx

from contextlib import asynccontextmanager
from collections.abc import AsyncIterator
from datetime import timedelta

from dotenv import load_dotenv
from mcp import ClientSession
from mcp.client.streamable_http import streamable_http_client

from banking_assistant.mcp.client import BankingMCPClient

load_dotenv()

GITHUB_MCP_URL = "https://api.githubcopilot.com/mcp/"


@asynccontextmanager
async def connect_github_mcp() -> AsyncIterator[BankingMCPClient]:

    token = os.getenv("GITHUB_TOKEN")

    if not token:
        raise ValueError("GITHUB_TOKEN is required")

    headers = {
        "Authorization": f"Bearer {token}",
        "X-MCP-Readonly": "true",
        "X-MCP-Tools": "get_me,get_file_contents",
    }

    async with httpx.AsyncClient(
        headers=headers,
        timeout=30.0,
    ) as http_client:
        async with streamable_http_client(
            GITHUB_MCP_URL,
            http_client=http_client,
        ) as (read, write, _):
            async with ClientSession(
                read,
                write,
                read_timeout_seconds=timedelta(seconds=30),
            ) as session:
                await session.initialize()

                yield BankingMCPClient(session)
