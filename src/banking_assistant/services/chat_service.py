from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from banking_assistant.agents.banking_agent import BankingAgent
from banking_assistant.services.exceptions import MissingAnswerError
from banking_assistant.api.chat_schemas import ChatResponse, PendingApproval, ToolTrace
from banking_assistant.agents.policy import review_id


class ChatService:
    def __init__(self, agent: BankingAgent):
        self.agent = agent

    async def ask(self, message: str, thread_id: str) -> str:
        return (await self.ask_response(message, thread_id)).answer

    async def ask_response(self, message: str, thread_id: str) -> ChatResponse:
        result = await self.agent.run(
            messages=[HumanMessage(content=message)],
            thread_id=thread_id,
        )
        return self.response(result, thread_id)

    async def review(
        self, thread_id: str, approval_id: str, decision: str
    ) -> ChatResponse:
        result = await self.agent.resume(thread_id, approval_id, decision)
        print("\n========== LANGGRAPH FINAL STATE ==========")
        print("State keys:", list(result.keys()))

        for index, message in enumerate(result.get("messages", [])):
            print(f"\nMessage {index}")
            print("Type:", type(message).__name__)
            print("Content:", repr(message.content)[:1000])
            print("Tool calls:", getattr(message, "tool_calls", None))
            print("Tool call ID:", getattr(message, "tool_call_id", None))

            print("==========================================")
        return self.response(result, thread_id)

    async def review_status(self, thread_id: str) -> ChatResponse:
        result = await self.agent.review_status(thread_id)
        return self.response(result, thread_id, status_only=True)

    @staticmethod
    def response(result: dict, thread_id: str, *, status_only: bool = False) -> ChatResponse:
        # Trace only the latest user turn, including all of its tool rounds.
        messages = result.get("messages", [])
        start = next((i + 1 for i in range(len(messages) - 1, -1, -1)
                      if isinstance(messages[i], HumanMessage)), 0)
        current = messages[start:]
        results = {item.tool_call_id: item for item in current
                   if isinstance(item, ToolMessage)}
        traces = [
            ToolTrace(
                tool_call_id=call["id"], tool_name=call["name"], args=call["args"],
                status=results[call["id"]].status if call["id"] in results else "requested",
            )
            for item in current if isinstance(item, AIMessage)
            for call in item.tool_calls
        ]
        pending = result.get("__interrupt__", ())
        if pending:
            return ChatResponse(
                answer="Review the pending operation and choose Approve, Reject, or Cancel.",
                thread_id=thread_id,
                status="approval_required",
                tool_traces=traces,
                pending_approvals=[
                    PendingApproval(
                        approval_id=review_id(item),
                        tool_call_id=item.value["tool_call_id"],
                        tool_name=item.value["tool_name"],
                        args=item.value["args"],
                        expires_at=item.value.get("expires_at", 0),
                    )
                    for item in pending
                ],
            )

        for item in reversed(current):
            if isinstance(item, AIMessage):
                if (
                    isinstance(item.content, str)
                    and item.content.strip()
                    and not item.tool_calls
                ):
                    return ChatResponse(
                        answer=item.content,
                        thread_id=thread_id,
                        review_outcomes=result.get("reviewed_calls", {}),
                        tool_traces=traces,
                    )
                break

        if status_only:
            return ChatResponse(
                answer="No pending approval in this conversation. The latest request has no completed text answer.",
                thread_id=thread_id,
                tool_traces=traces,
                review_outcomes=result.get("reviewed_calls", {}),
            )
        raise MissingAnswerError("The banking agent did not return a text answer")
