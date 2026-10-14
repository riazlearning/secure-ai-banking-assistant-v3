import asyncio
from contextlib import asynccontextmanager
from unittest.mock import AsyncMock, MagicMock, patch

from langchain_core.language_models.fake_chat_models import FakeListChatModel
from langchain_core.messages import HumanMessage
from langgraph.checkpoint.memory import InMemorySaver
from psycopg.conninfo import conninfo_to_dict

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.core.config import Settings
from banking_assistant.infrastructure.checkpointer import create_checkpointer
from banking_assistant.services.chat_service import ChatService


def test_conversation_history_and_thread_isolation():
    async def run():
        saver = InMemorySaver()
        agent = BankingAgent(FakeListChatModel(responses=["one", "two", "three"]), saver)
        service = ChatService(agent)
        assert await service.ask("first", "thread-a") == "one"
        assert await service.ask("second", "thread-a") == "two"
        resumed = BankingAgent(FakeListChatModel(responses=["resumed"]), saver)
        assert await ChatService(resumed).ask("third", "thread-a") == "resumed"
        state = await resumed.graph.aget_state({"configurable": {"thread_id": "thread-a"}})
        assert [m.content for m in state.values["messages"] if isinstance(m, HumanMessage)] == [
            "first", "second", "third",
        ]
        await service.ask("separate", "thread-b")
        other = await agent.graph.aget_state({"configurable": {"thread_id": "thread-b"}})
        assert len(other.values["messages"]) == 2

    asyncio.run(run())


def test_checkpointer_setup_and_pool_cleanup():
    async def run():
        pool = MagicMock()
        pool.wait = AsyncMock()
        pool.__aenter__ = AsyncMock(return_value=pool)
        pool.__aexit__ = AsyncMock(return_value=False)
        saver = MagicMock()
        saver.setup = AsyncMock()
        settings = Settings(_env_file=None, postgres_password="quote' and space")
        with patch("banking_assistant.infrastructure.checkpointer.AsyncConnectionPool", return_value=pool) as factory:
            with patch("banking_assistant.infrastructure.checkpointer.AsyncPostgresSaver", return_value=saver):
                async with create_checkpointer(settings) as result:
                    assert result is saver
                    saver.setup.assert_awaited_once()
                pool.__aexit__.assert_awaited_once()
                conninfo = conninfo_to_dict(factory.call_args.kwargs["conninfo"])
                assert conninfo["password"] == settings.postgres_password
                assert conninfo["port"] == "5433"

    asyncio.run(run())


def test_api_lifespan_cleans_up_agent():
    from banking_assistant.main import app, lifespan

    saver = InMemorySaver()
    closed = []

    @asynccontextmanager
    async def storage(settings):
        try:
            yield saver
        finally:
            closed.append(True)

    async def run():
        with patch("banking_assistant.main.create_checkpointer", storage):
            with patch("banking_assistant.main.get_chat_model", return_value=FakeListChatModel(responses=["answer"])):
                async with lifespan(app):
                    assert app.state.banking_agent.checkpointer is saver
                assert not hasattr(app.state, "banking_agent")
                assert closed == [True]

    asyncio.run(run())
