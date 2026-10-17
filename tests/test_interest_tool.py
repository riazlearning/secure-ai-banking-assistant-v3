import asyncio
import json
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.tools.interest_tool import calculate_simple_interest
from banking_assistant.services.chat_service import ChatService
from banking_assistant.services.interest_service import InterestService


@pytest.mark.parametrize("principal,rate,years,expected", [
    ("1000", "5", "2", "100"),
    ("1250.50", "4.25", "0.5", "26.573125"),
    ("1000", "0", "2", "0"),
    ("1000", "5", "0", "0"),
])
def test_simple_interest(principal, rate, years, expected):
    assert InterestService().calculate_simple_interest(
        Decimal(principal), Decimal(rate), Decimal(years),
    ) == Decimal(expected)


@pytest.mark.parametrize("position", [0, 1, 2])
@pytest.mark.parametrize("invalid", ["-1", "NaN", "Infinity"])
def test_service_rejects_invalid_numbers(position, invalid):
    values = [Decimal("1000"), Decimal("5"), Decimal("2")]
    values[position] = Decimal(invalid)
    with pytest.raises(ValueError):
        InterestService().calculate_simple_interest(*values)


@pytest.mark.parametrize("field", ["principal", "annual_rate", "years"])
@pytest.mark.parametrize("invalid", [-1, float("nan"), float("inf")])
def test_tool_validates_inputs(field, invalid):
    args = {"principal": 1000, "annual_rate": 5, "years": 2}
    args[field] = invalid
    with pytest.raises(ValidationError):
        calculate_simple_interest.invoke(args)


def test_graph_executes_tool_and_returns_final_answer():
    async def run():
        fake = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "calculate_simple_interest",
                "args": {"principal": 1000, "annual_rate": 5, "years": 2},
                "id": "interest-call", "type": "tool_call",
            }]),
            AIMessage(content="Interest is 100 and total amount is 1100."),
        ])
        model = MagicMock()
        model.bind_tools.return_value = fake
        agent = BankingAgent(model, InMemorySaver())
        answer = await ChatService(agent).ask("Interest on 1000 at 5% for 2 years?", "interest")
        assert answer == "Interest is 100 and total amount is 1100."
        model.bind_tools.assert_called_once_with(agent.tools)
        assert {tool.name for tool in agent.tools} == {"calculate_simple_interest", "get_transactions", "transfer_money"}
        state = await agent.graph.aget_state({"configurable": {"thread_id": "interest"}})
        result = next(m for m in state.values["messages"] if isinstance(m, ToolMessage))
        assert result.tool_call_id == "interest-call"
        data = json.loads(result.content)
        assert Decimal(data["simple_interest"]) == Decimal("100")
        assert Decimal(data["total_amount"]) == Decimal("1100")
        assert len(state.values["messages"]) == 4

    asyncio.run(run())
