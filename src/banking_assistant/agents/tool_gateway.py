"""Enforce trusted policy immediately before every tool invocation."""

import json
import logging
from time import time

from langchain_core.messages import ToolMessage
from langgraph.prebuilt.tool_node import ToolCallRequest

from banking_assistant.agents.policy import PolicyContext, PolicyDecision, PolicyEngine, ReviewOutcome, call_fingerprint

logger = logging.getLogger(__name__)


class ToolExecutionGateway:
    def __init__(self, policy: PolicyEngine):
        self.policy = policy

    def _check(self, request: ToolCallRequest) -> ToolMessage | None:
        context = request.runtime.context
        trusted_context = context if isinstance(context, PolicyContext) else None
        thread_id = request.runtime.config.get("configurable", {}).get("thread_id")
        if trusted_context is not None and trusted_context.thread_id != thread_id:
            trusted_context = None
        decision = self.policy.evaluate(request.tool_call, trusted_context)
        outcome = None
        if request.tool is None:
            decision = PolicyDecision.DENY
        if (
            decision == PolicyDecision.REQUIRE_APPROVAL
            and trusted_context is not None
            and trusted_context.human_review
        ):
            reviewed = request.state.get("reviewed_calls", {}).get(
                call_fingerprint(request.tool_call)
            )
            outcome = reviewed
            if reviewed == ReviewOutcome.APPROVED and time() < request.state.get("review_expires_at", 0):
                decision = PolicyDecision.ALLOW
            elif reviewed is not None:
                decision = PolicyDecision.DENY
                if reviewed == ReviewOutcome.APPROVED:
                    outcome = ReviewOutcome.EXPIRED
        logger.info(
            "Tool policy evaluated",
            extra={
                "tool_name": request.tool_call["name"],
                "policy_decision": decision.value,
                "approval_outcome": outcome,
            },
        )
        if decision != PolicyDecision.ALLOW:
            logger.info(f"decision {decision}")
            return ToolMessage(
                content=json.dumps(
                    {
                        "decision": decision.value,
                        "approval_outcome": outcome,
                        "message": (
                            "Trusted approval is required before this tool can run."
                            if decision == PolicyDecision.REQUIRE_APPROVAL
                            else f"Tool execution was blocked: {outcome or 'denied by policy'}. Do not retry this operation without a new user request."
                        ),
                    }
                ),
                name=request.tool_call["name"],
                tool_call_id=request.tool_call["id"],
                status="error",
            )
        return None

    def execute_sync(self, request: ToolCallRequest, execute):
        blocked = self._check(request)
        return blocked if blocked is not None else execute(request)

    async def execute(self, request: ToolCallRequest, execute):
        blocked = self._check(request)
        return blocked if blocked is not None else await execute(request)
