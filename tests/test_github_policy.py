import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.policy import PolicyDecision, PolicyEngine
from banking_assistant.mcp.client import BankingMCPClient


@pytest.mark.parametrize("name", ["get_me", "get_file_contents"])
def test_registered_github_read_tool_reaches_mcp_session(name):
    async def run():
        arguments = (
            {"owner": "example", "repo": "demo", "path": "README.md"}
            if name == "get_file_contents" else {}
        )
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=ListToolsResult(tools=[
            Tool(name=name, inputSchema={"type": "object"}),
        ]))
        session.call_tool = AsyncMock(return_value=CallToolResult(
            content=[TextContent(type="text", text="# Example\n\n")],
        ))
        registry = await BankingMCPClient(session).tool_registry([name])
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": name, "args": arguments, "id": "github-read",
            }]),
            AIMessage(content="Read completed."),
        ])
        agent = BankingAgent(model, InMemorySaver(), tool_registry=registry,
                             allowed_tool_names=[name])
        result = await agent.run([HumanMessage(content="Read from GitHub")], "github")
        session.call_tool.assert_awaited_once_with(name, arguments)
        assert any(isinstance(message, ToolMessage) and message.status == "success"
                   for message in result["messages"])

    asyncio.run(run())


def test_github_permissions_still_require_registration_and_deny_unknown_tools():
    call = {"name": "get_file_contents", "args": {}, "id": "read"}
    assert PolicyEngine([]).evaluate(call) == PolicyDecision.DENY
    unknown = {**call, "name": "delete_repository"}
    assert PolicyEngine(["delete_repository"]).evaluate(unknown) == PolicyDecision.DENY
