import asyncio
from decimal import Decimal
from unittest.mock import MagicMock

import pytest
from langchain_core.tools import ToolException
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.policy import review_id
from banking_assistant.mcp.client import connect_banking_mcp
from banking_assistant.mcp.server import server


def test_server_advertises_tools_only():
    capabilities = server.create_initialization_options().capabilities
    assert capabilities.tools is not None
    assert capabilities.resources is None
    assert capabilities.prompts is None


def test_stdio_tools_round_trip():
    async def run():
        async with connect_banking_mcp() as client:
            registry = await client.tool_registry()
            assert set(registry.tools) == {
                "calculate_simple_interest", "get_transactions", "transfer_money",
            }
            interest = registry.tools["calculate_simple_interest"]
            calculation = await interest.ainvoke({
                "principal": 1000, "annual_rate": 5, "years": 2,
            })
            assert Decimal(calculation["simple_interest"]) == 100
            assert Decimal(calculation["total_amount"]) == 1100
            with pytest.raises(ToolException):
                await interest.ainvoke({
                    "principal": -1, "annual_rate": 5, "years": 2,
                })
            history = await registry.tools["get_transactions"].ainvoke({})
            assert history["is_sample"] is True
            transfer = await registry.tools["transfer_money"].ainvoke({
                "recipient": "Demo", "amount": "12.50", "currency": "SAR",
            })
            assert transfer["status"] == "simulated"
            assert transfer["amount"] == "12.50"
            with pytest.raises(ValueError, match="unavailable"):
                await client.tool_registry(["unknown"])
            with pytest.raises(ValueError, match="unique"):
                await client.tool_registry(["get_transactions"] * 2)
            empty = await client.tool_registry([])
            assert not empty.tools

            model = MagicMock()
            model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
                AIMessage(content="", tool_calls=[{
                    "name": "transfer_money", "id": "mcp-transfer",
                    "args": {"recipient": "Demo", "amount": "12.50", "currency": "SAR"},
                }]),
                AIMessage(content="Fictional simulation completed."),
            ])
            agent = BankingAgent(model, InMemorySaver(), tool_registry=registry)
            paused = await agent.run([HumanMessage(content="Simulate a transfer")], "mcp")
            assert paused["__interrupt__"]
            assert not any(isinstance(m, ToolMessage) for m in paused["messages"])
            completed = await agent.resume(
                "mcp", review_id(paused["__interrupt__"][0]), "approve",
            )
            assert any(isinstance(m, ToolMessage) and m.status == "success"
                       for m in completed["messages"])

    asyncio.run(run())
