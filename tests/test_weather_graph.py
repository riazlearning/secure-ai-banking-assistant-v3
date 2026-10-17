import asyncio
from unittest.mock import AsyncMock, MagicMock

from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from mcp.types import CallToolResult, ListToolsResult, TextContent, Tool

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.policy import PolicyDecision, PolicyEngine
from banking_assistant.mcp.client import BankingMCPClient
from banking_assistant.mcp.weather_client import WEATHER_TOOL_NAMES
from banking_assistant.services.chat_service import ChatService


def test_weather_search_then_forecast_runs_through_graph_and_trace():
    async def run():
        session = MagicMock()
        session.list_tools = AsyncMock(return_value=ListToolsResult(tools=[
            Tool(name=name, inputSchema={"type": "object"}) for name in WEATHER_TOOL_NAMES
        ]))
        session.call_tool = AsyncMock(side_effect=[
            CallToolResult(content=[TextContent(type="text", text='{"latitude":24.7,"longitude":46.7}')]),
            CallToolResult(content=[TextContent(type="text", text='{"temperature_2m":30}')]),
        ])
        registry = await BankingMCPClient(session).tool_registry(WEATHER_TOOL_NAMES)
        search = {"name": WEATHER_TOOL_NAMES[0], "id": "search", "args": {"name": "Riyadh"}}
        forecast = {"name": WEATHER_TOOL_NAMES[1], "id": "forecast", "args": {
            "latitude": 24.7, "longitude": 46.7, "current_variables": ["temperature_2m"],
        }}
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[search]),
            AIMessage(content="", tool_calls=[forecast]),
            AIMessage(content="Weather retrieved."),
        ])
        agent = BankingAgent(model, InMemorySaver(), tool_registry=registry,
                             allowed_tool_names=WEATHER_TOOL_NAMES)
        state = await agent.run([HumanMessage(content="Weather in Riyadh?")], "weather")
        assert session.call_tool.await_args_list[0].args == (search["name"], search["args"])
        assert session.call_tool.await_args_list[1].args == (forecast["name"], forecast["args"])
        response = ChatService.response(state, "weather")
        assert [t.status for t in response.tool_traces] == ["success", "success"]
        assert [t.tool_name for t in response.tool_traces] == list(WEATHER_TOOL_NAMES)
    asyncio.run(run())


def test_weather_policy_requires_allowlist_and_denies_unapproved_weather_tools():
    call = {"id": "weather", "name": WEATHER_TOOL_NAMES[0], "args": {}}
    assert PolicyEngine([]).evaluate(call) == PolicyDecision.DENY
    assert PolicyEngine(WEATHER_TOOL_NAMES).evaluate(call) == PolicyDecision.ALLOW
    call["name"] = "openmeteo_get_climate"
    assert PolicyEngine([call["name"]]).evaluate(call) == PolicyDecision.DENY
