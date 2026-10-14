from langchain_core.messages import AIMessage, HumanMessage

from banking_assistant.agents.banking_agent import BankingAgent


class ChatService:
    def __init__(self, agent: BankingAgent):
        self.agent = agent

    async def ask(self, message: str, thread_id: str) -> str:
        result = await self.agent.run(
            messages=[HumanMessage(content=message)],
            thread_id=thread_id,
        )

        for item in reversed(result["messages"]):
            if isinstance(item, AIMessage):
                if isinstance(item.content, str):
                    return item.content

        raise RuntimeError("The banking agent did not return a text answer")
