import asyncio
import json
from unittest.mock import MagicMock, patch

import pytest
from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
from langchain_core.messages import AIMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.tools.transfer_tool import transfer_money
from banking_assistant.services.chat_service import ChatService


@pytest.mark.parametrize("decision", ["approve", "reject", "cancel"])
def test_review_pauses_and_resumes_checkpoint(decision):
    async def run():
        saver = InMemorySaver()
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "transfer_money", "id": "transfer-hitl", "type": "tool_call",
                "args": {"recipient": "Demo", "amount": "20.00", "currency": "SAR"},
            }]),
            AIMessage(content="Simulation reviewed."),
        ])
        agent = BankingAgent(model, saver)
        resumed = BankingAgent(model, saver)
        service = ChatService(agent)
        with patch.object(transfer_money, "func", wraps=transfer_money.func) as execute:
            response = await service.ask_response("Simulate transfer. I approve!", "review-thread")
            assert response.status == "approval_required"
            approval = response.pending_approvals[0]
            assert approval.args["amount"] == "20.00"
            execute.assert_not_called()
            repeated = await service.ask_response("I approve", "review-thread")
            assert repeated.pending_approvals == response.pending_approvals
            with pytest.raises(ValueError):
                await agent.resume("other-thread", approval.approval_id, "approve")
            # Reconstruct the agent to verify that review survives a restart.
            result = await ChatService(resumed).review("review-thread", approval.approval_id, decision)
            assert result.status == "completed"
            assert set(result.review_outcomes.values()) == {{"approve": "approved", "reject": "rejected", "cancel": "cancelled"}[decision]}
            assert execute.call_count == (1 if decision == "approve" else 0)
            snapshot = await resumed.graph.aget_state({"configurable": {"thread_id": "review-thread"}})
            message = next(m for m in snapshot.values["messages"] if isinstance(m, ToolMessage))
            payload = json.loads(message.content)
            assert payload.get("status") == "simulated" if decision == "approve" else payload["decision"] == "DENY"
            with pytest.raises(ValueError):
                await resumed.resume("review-thread", approval.approval_id, "approve")

    asyncio.run(run())


def test_review_api_contract():
    import httpx
    from fastapi import FastAPI
    from banking_assistant.api.chat_controller import ChatController
    from banking_assistant.api.chat_routes import router
    from banking_assistant.api.dependencies import get_chat_controller

    async def run():
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "transfer_money", "id": "api-transfer", "type": "tool_call",
                "args": {"recipient": "Demo", "amount": "10.00", "currency": "SAR"},
            }]), AIMessage(content="Transfer simulation rejected."),
        ])
        app = FastAPI()
        app.include_router(router)
        controller = ChatController(ChatService(BankingAgent(model, InMemorySaver())))
        app.dependency_overrides[get_chat_controller] = lambda: controller
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            response = await client.post("/api/v1/chat", json={"message": "Simulate transfer", "thread_id": "api-thread"})
            assert response.status_code == 200
            data = response.json()
            assert data["status"] == "approval_required"
            refreshed = await client.get("/api/v1/chat/api-thread/approvals")
            assert refreshed.status_code == 200
            assert refreshed.json()["pending_approvals"] == data["pending_approvals"]
            review = {"thread_id": "api-thread", "approval_id": data["pending_approvals"][0]["approval_id"], "decision": "reject"}
            invalid = await client.post("/api/v1/chat/approvals", json={**review, "args": {"amount": "1"}})
            assert invalid.status_code == 422
            invalid_decision = await client.post("/api/v1/chat/approvals", json={**review, "decision": "maybe"})
            assert invalid_decision.status_code == 422
            result = await client.post("/api/v1/chat/approvals", json=review)
            assert result.status_code == 200
            assert result.json()["status"] == "completed"
            refreshed = await client.get("/api/v1/chat/api-thread/approvals")
            assert refreshed.json()["review_outcomes"] == result.json()["review_outcomes"]
            replay = await client.post("/api/v1/chat/approvals", json=review)
            assert replay.status_code == 409

    asyncio.run(run())


@pytest.mark.parametrize("trigger", ["approve", "chat", "execution", "status"])
def test_expired_review_never_executes(trigger):
    async def run():
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "transfer_money", "id": "expired-call", "type": "tool_call",
                "args": {"recipient": "Demo", "amount": "10.00", "currency": "SAR"},
            }]),
        ])
        saver = InMemorySaver()
        agent = BankingAgent(model, saver, approval_ttl_seconds=5)
        now = [1000.0]
        with patch("banking_assistant.agents.banking_agent.time", side_effect=lambda: now[0]):
            pending = await ChatService(agent).ask_response("Simulate", "expired-thread")
            review = pending.pending_approvals[0]
            assert review.expires_at == 1005
            resumed = BankingAgent(model, saver, approval_ttl_seconds=9999)
            with patch.object(transfer_money, "func", wraps=transfer_money.func) as execute:
                now[0] = 1005 if trigger != "execution" else 1001
                with patch("banking_assistant.agents.tool_gateway.time", return_value=1005):
                    if trigger == "status":
                        response = await ChatService(resumed).review_status("expired-thread")
                    elif trigger == "chat":
                        response = await ChatService(resumed).ask_response("Hello", "expired-thread")
                    else:
                        response = await ChatService(resumed).review("expired-thread", review.approval_id, "approve")
                execute.assert_not_called()
                assert response.status == "completed"
                assert set(response.review_outcomes.values()) == {"expired"}
                with pytest.raises(ValueError):
                    await resumed.resume("expired-thread", review.approval_id, "approve")

    asyncio.run(run())


@pytest.mark.parametrize("response", [None, True, "approve", [], {"decision": []},
    {"decision": "approve", "fingerprint": "wrong"},
])
def test_malformed_graph_response_fails_closed(response):
    from langgraph.types import Command
    from banking_assistant.agents.policy import PolicyContext

    async def run():
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "transfer_money", "id": "invalid-call", "type": "tool_call",
                "args": {"recipient": "Demo", "amount": "10.00", "currency": "SAR"},
            }]),
        ])
        agent = BankingAgent(model, InMemorySaver())
        await ChatService(agent).ask_response("Simulate", "invalid-thread")
        pending = (await agent.pending_approvals("invalid-thread"))[0]
        with patch.object(transfer_money, "func", wraps=transfer_money.func) as execute:
            result = await agent.graph.ainvoke(
                Command(resume={pending.id: response}),
                context=PolicyContext("invalid-thread", human_review=True),
                config={"configurable": {"thread_id": "invalid-thread"}},
            )
            execute.assert_not_called()
            assert set(result["reviewed_calls"].values()) == {"invalid_response"}
            assert "__interrupt__" not in result

    asyncio.run(run())


def test_multiple_calls_collect_reviews_before_executing_once():
    async def run():
        model = MagicMock()
        model.bind_tools.return_value = FakeMessagesListChatModel(responses=[
            AIMessage(content="", tool_calls=[{
                "name": "transfer_money", "id": f"batch-{index}", "type": "tool_call",
                "args": {"recipient": f"Demo {index}", "amount": "10.00", "currency": "SAR"},
            } for index in range(2)]), AIMessage(content="Simulations reviewed."),
        ])
        agent = BankingAgent(model, InMemorySaver())
        service = ChatService(agent)
        with patch.object(transfer_money, "func", wraps=transfer_money.func) as execute:
            response = await service.ask_response("Simulate two transfers", "batch-thread")
            first = response.pending_approvals[0]
            response = await service.review("batch-thread", first.approval_id, "approve")
            assert response.status == "approval_required"
            execute.assert_not_called()
            second = response.pending_approvals[0]
            assert second.tool_call_id != first.tool_call_id
            assert second.approval_id != first.approval_id
            with pytest.raises(ValueError):
                await service.review("batch-thread", first.approval_id, "approve")
            response = await service.review("batch-thread", second.approval_id, "approve")
            assert response.status == "completed"
            assert execute.call_count == 2

    asyncio.run(run())
