from typing import Annotated, NotRequired, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages
from banking_assistant.agents.policy import ReviewOutcome


class BankingState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
    reviewed_calls: NotRequired[dict[str, ReviewOutcome]]
    review_expires_at: NotRequired[float]
