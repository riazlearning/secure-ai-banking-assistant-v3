from langchain_core.language_models import BaseChatModel
from langchain_core.messages import SystemMessage
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.graph import END, START, StateGraph

from banking_assistant.agents.banking_state import BankingState


SYSTEM_PROMPT = """
You are a banking education assistant.

Explain general banking concepts clearly and accurately.

You do not have access to customer accounts, balances,
personal banking records, or transaction systems.

Never invent customer balances, account details,
or completed transactions.

If a customer requests account-specific information,
explain that authenticated banking integration
is not available yet.

Do not claim to execute transfers or payments.
"""


class BankingAgent:
    def __init__(self, model: BaseChatModel, checkpointer: BaseCheckpointSaver):
        self.model = model
        self.checkpointer = checkpointer
        self.graph = self._build_graph()

    def _build_graph(self):

        builder = StateGraph(BankingState)

        builder.add_node(
            "generate_answer",
            self._generate_answer,
        )

        builder.add_edge(
            START,
            "generate_answer",
        )

        builder.add_edge(
            "generate_answer",
            END,
        )

        return builder.compile(checkpointer=self.checkpointer)

    async def _generate_answer(
        self,
        state: BankingState,
    ) -> dict:

        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            *state["messages"],
        ]

        response = await self.model.ainvoke(messages)

        return {"messages": [response]}

    async def run(
        self,
        messages: list,
        thread_id: str,
    ) -> BankingState:

        return await self.graph.ainvoke(
            {"messages": messages},
            config={"configurable": {"thread_id": thread_id}},
        )
