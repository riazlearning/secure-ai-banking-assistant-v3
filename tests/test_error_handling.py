import asyncio
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi.testclient import TestClient
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage
from langgraph.checkpoint.memory import InMemorySaver

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.agents.exceptions import AgentExecutionError, LLMError, LLMTimeoutError
from banking_assistant.api.dependencies import get_chat_controller
from banking_assistant.main import app
from banking_assistant.services.chat_service import ChatService
from banking_assistant.services.exceptions import InvalidInterestInputError, MissingAnswerError, CalculationError


@pytest.mark.parametrize('cause,expected', [
    (RuntimeError('private provider detail'), LLMError),
    (httpx.ReadTimeout('private timeout'), LLMTimeoutError),
])
def test_agent_wraps_model_errors(cause, expected):
    async def run():
        model = MagicMock()
        model.bind_tools.return_value.ainvoke = AsyncMock(side_effect=cause)
        agent = BankingAgent(model, InMemorySaver())
        with pytest.raises(expected) as caught:
            await agent.run([], 'failure')
        assert caught.value.__cause__ is cause
    asyncio.run(run())


def test_agent_wraps_graph_errors():
    async def run():
        agent = BankingAgent(MagicMock(), InMemorySaver())
        cause = RuntimeError('private database detail')
        agent.graph = MagicMock()
        agent.graph.aget_state = AsyncMock(return_value=MagicMock(tasks=()))
        agent.graph.ainvoke = AsyncMock(side_effect=cause)
        with pytest.raises(AgentExecutionError) as caught:
            await agent.run([], 'failure')
        assert caught.value.__cause__ is cause
    asyncio.run(run())


def test_service_does_not_return_stale_answer():
    async def run():
        agent = MagicMock()
        agent.run = AsyncMock(return_value={'messages': [AIMessage(content='old'), AIMessage(content='')]})
        with pytest.raises(MissingAnswerError):
            await ChatService(agent).ask('new', 'thread')
    asyncio.run(run())


@pytest.mark.parametrize("tail", [
    [],
    [HumanMessage(content="Failed request")],
    [HumanMessage(content="Failed request"), AIMessage(content="")],
    [HumanMessage(content="Read README"),
     AIMessage(content="", tool_calls=[{"id": "read", "name": "get_file_contents", "args": {}}]),
     ToolMessage(content="result", tool_call_id="read")],
])
def test_review_status_handles_incomplete_turn_without_replaying_tools(tail):
    async def run():
        agent = MagicMock()
        agent.review_status = AsyncMock(return_value={"messages": tail})
        response = await ChatService(agent).review_status("thread")
        assert response.status == "completed"
        assert response.pending_approvals == []
        assert "No pending approval" in response.answer
        agent.run.assert_not_called()
        agent.resume.assert_not_called()
    asyncio.run(run())


def test_review_status_does_not_return_answer_from_previous_turn():
    result = {"messages": [AIMessage(content="Old answer"), HumanMessage(content="Failed request")]}
    response = ChatService.response(result, "thread", status_only=True)
    assert "Old answer" not in response.answer
    with pytest.raises(MissingAnswerError):
        ChatService.response(result, "thread")


@pytest.mark.parametrize('error,status,code', [
    (LLMError('secret'), 502, 'LLM_UNAVAILABLE'),
    (LLMTimeoutError('secret'), 504, 'LLM_TIMEOUT'),
    (AgentExecutionError('secret'), 500, 'AGENT_EXECUTION_FAILED'),
    (MissingAnswerError('secret'), 500, 'MISSING_ANSWER'),
    (CalculationError('secret'), 500, 'APPLICATION_ERROR'),
    (InvalidInterestInputError('Invalid principal'), 422, 'INVALID_INTEREST_INPUT'),
    (RuntimeError('secret'), 500, 'INTERNAL_ERROR'),
])
def test_http_error_mapping(error, status, code):
    controller = MagicMock()
    controller.chat = AsyncMock(side_effect=error)
    app.dependency_overrides[get_chat_controller] = lambda: controller
    try:
        client = TestClient(app, raise_server_exceptions=False)
        response = client.post('/api/v1/chat', json={'message': 'hello', 'thread_id': 'test'})
        assert response.status_code == status
        assert response.json()['error']['code'] == code
        assert 'secret' not in response.text
    finally:
        app.dependency_overrides.clear()


def test_http_validation_and_not_found():
    app.dependency_overrides[get_chat_controller] = lambda: MagicMock()
    try:
        client = TestClient(app)
        response = client.post('/api/v1/chat', json={})
        assert response.status_code == 422
        assert response.json()['error']['code'] == 'INVALID_REQUEST'
        response = client.get('/does-not-exist')
        assert response.status_code == 404
        assert response.json()['error']['code'] == 'HTTP_ERROR'
    finally:
        app.dependency_overrides.clear()


def test_invalid_tool_input_is_recoverable():
    from langchain_core.language_models.fake_chat_models import FakeMessagesListChatModel
    from langchain_core.messages import ToolMessage

    async def run():
        fake = FakeMessagesListChatModel(responses=[
            AIMessage(content='', tool_calls=[{
                'name': 'calculate_simple_interest',
                'args': {'principal': -1, 'annual_rate': 5, 'years': 2},
                'id': 'invalid-input', 'type': 'tool_call',
            }]),
            AIMessage(content='Please provide a non-negative principal.'),
        ])
        model = MagicMock()
        model.bind_tools.return_value = fake
        agent = BankingAgent(model, InMemorySaver())
        assert await ChatService(agent).ask('calculate', 'invalid') == 'Please provide a non-negative principal.'
        state = await agent.graph.aget_state({'configurable': {'thread_id': 'invalid'}})
        result = next(m for m in state.values['messages'] if isinstance(m, ToolMessage))
        assert result.status == 'error'
        assert 'Invalid tool inputs' in result.content
    asyncio.run(run())
