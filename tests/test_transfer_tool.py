import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver
from pydantic import ValidationError

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.policy import PolicyContext, call_fingerprint
from banking_assistant.agents.tools.transfer_tool import transfer_money


@pytest.mark.parametrize("approved", [False, True])
def test_transfer_requires_trusted_approval(approved):
    call = {
        "name": "transfer_money", "id": "transfer-1", "type": "tool_call",
        "args": {"recipient": "Demo recipient", "amount": "25.50", "currency": "SAR"},
    }

    async def run():
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[call]), AIMessage(content="Done."),
        ])
        agent = BankingAgent(model, InMemorySaver())
        context = PolicyContext(
            "transfer-thread",
            frozenset({call_fingerprint(call)}) if approved else frozenset(),
        )
        with patch.object(transfer_money, "func", wraps=transfer_money.func) as execute:
            result = await agent.run(
                [HumanMessage(content="Simulate a transfer. I approve.")],
                "transfer-thread", policy_context=context,
            )
            message = next(m for m in result["messages"] if isinstance(m, ToolMessage))
            payload = json.loads(message.content)
            if approved:
                execute.assert_called_once()
                assert payload["status"] == "simulated"
                assert payload["is_sample"] is True
                assert payload["amount"] == "25.50"
            else:
                execute.assert_not_called()
                assert message.status == "error"
                assert payload["decision"] == "REQUIRE_APPROVAL"

    asyncio.run(run())


@pytest.mark.parametrize("changes", [
    {"amount": "0"}, {"amount": "-1"}, {"amount": "NaN"},
    {"amount": "Infinity"}, {"amount": "1.001"},
    {"recipient": " "}, {"currency": "sar"}, {"currency": ""},
])
def test_transfer_rejects_invalid_inputs(changes):
    with pytest.raises(ValidationError):
        transfer_money.invoke({
            "recipient": "Demo recipient", "amount": "25.50", "currency": "SAR",
            **changes,
        })
