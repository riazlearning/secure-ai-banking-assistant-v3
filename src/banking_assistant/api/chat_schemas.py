from typing import Literal
from pydantic import BaseModel, ConfigDict, Field
from banking_assistant.agents.policy import ReviewOutcome


class ChatRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    message: str = Field(
        min_length=1,
        max_length=4000,
    )

    thread_id: str = Field(
        min_length=1,
        max_length=100,
        pattern=r"^[a-zA-Z0-9_-]+$",
    )


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")

    thread_id: str = Field(min_length=1, max_length=100, pattern=r"^[a-zA-Z0-9_-]+$")
    approval_id: str = Field(min_length=1, max_length=200)
    decision: Literal["approve", "reject", "cancel"]


class PendingApproval(BaseModel):
    approval_id: str
    tool_call_id: str
    tool_name: str
    args: dict[str, object]
    expires_at: float


class ToolTrace(BaseModel):
    tool_call_id: str
    tool_name: str
    args: dict[str, object]
    status: Literal["requested", "success", "error"]


class ChatResponse(BaseModel):
    model_config = ConfigDict(extra="forbid")

    answer: str
    thread_id: str
    status: Literal["completed", "approval_required"] = "completed"
    pending_approvals: list[PendingApproval] = Field(default_factory=list)
    review_outcomes: dict[str, ReviewOutcome] = Field(default_factory=dict)
    tool_traces: list[ToolTrace] = Field(default_factory=list)
