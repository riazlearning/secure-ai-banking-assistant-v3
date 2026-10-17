import asyncio
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langchain_core.tools import tool
from langgraph.checkpoint.memory import InMemorySaver

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.tools.interest_tool import calculate_simple_interest
from banking_assistant.agents.tools.registry import ToolRegistry


def test_registry_requires_explicit_permission():
    registry = ToolRegistry([calculate_simple_interest])
    assert registry.resolve_allowed([]) == []
    assert registry.resolve_allowed([calculate_simple_interest.name]) == [calculate_simple_interest]
    with pytest.raises(ValueError, match="not registered"):
        registry.resolve_allowed(["transfer_money"])
    with pytest.raises(ValueError, match="unique"):
        registry.resolve_allowed([calculate_simple_interest.name] * 2)
    with pytest.raises(ValueError, match="duplicate"):
        ToolRegistry([calculate_simple_interest] * 2)


@pytest.mark.parametrize("requested_name", ["restricted_tool", "unknown_tool"])
def test_graph_rejects_tools_outside_allowlist(requested_name):
    executed = []

    @tool
    def restricted_tool() -> str:
        """A registered tool that has not been granted permission."""
        executed.append(True)
        return "executed"

    async def run():
        fake = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": requested_name, "args": {}, "id": "blocked",
                "type": "tool_call",
            }]),
            AIMessage(content="That tool is unavailable."),
        ])
        model = MagicMock()
        model.bind_tools.return_value = fake
        agent = BankingAgent(
            model, InMemorySaver(),
            tool_registry=ToolRegistry([calculate_simple_interest, restricted_tool]),
            allowed_tool_names=["calculate_simple_interest"],
        )
        result = await agent.run([HumanMessage(content="Use the tool")], "blocked")
        model.bind_tools.assert_called_once_with([calculate_simple_interest])
        error = next(m for m in result["messages"] if isinstance(m, ToolMessage))
        assert error.status == "error"
        assert error.tool_call_id == "blocked"
        assert executed == []

    asyncio.run(run())


def test_empty_allowlist_does_not_bind_tools():
    model = MagicMock()
    agent = BankingAgent(model, InMemorySaver(), allowed_tool_names=[])
    assert agent.tools == []
    assert agent.model is model
    model.bind_tools.assert_not_called()
