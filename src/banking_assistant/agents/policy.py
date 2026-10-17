"""Server-owned tool policy. Model messages and arguments never grant permission."""

from collections.abc import Iterable, Mapping
from dataclasses import dataclass, field
from enum import StrEnum
import hashlib
import json
from types import MappingProxyType

from langchain_core.messages import ToolCall


class PolicyDecision(StrEnum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ReviewOutcome(StrEnum):
    APPROVED = "approved"
    REJECTED = "rejected"
    EXPIRED = "expired"
    CANCELLED = "cancelled"
    INVALID_RESPONSE = "invalid_response"


def call_fingerprint(call: ToolCall) -> str:
    """Bind approval to an exact call ID, tool name, and argument payload."""
    payload = json.dumps(
        {key: call[key] for key in ("id", "name", "args")},
        sort_keys=True,
        separators=(",", ":"),
        allow_nan=False,
    )
    return hashlib.sha256(payload.encode()).hexdigest()


def review_id(pending) -> str:
    """Sequential interrupts can share an ID; also bind the displayed call."""
    return f"{pending.id}:{pending.value['fingerprint']}"


@dataclass(frozen=True)
class PolicyContext:
    """Trusted per-invocation context supplied only by application code.

    Approval fingerprints must come from a verified approval workflow, never
    chat text, model output, or a client-provided list of approved tools.
    """

    thread_id: str
    approved_calls: frozenset[str] = field(default_factory=frozenset)
    human_review: bool = False

    def __post_init__(self):
        object.__setattr__(self, "approved_calls", frozenset(self.approved_calls))


class PolicyEngine:
    def __init__(
        self,
        allowed_tool_names: Iterable[str],
        rules: Mapping[str, PolicyDecision] | None = None,
    ):
        self.allowed_tool_names = frozenset(allowed_tool_names)
        self.rules = MappingProxyType(
            {
                name: PolicyDecision(decision)
                for name, decision in (
                    DEFAULT_POLICY_RULES if rules is None else rules
                ).items()
            }
        )

    def evaluate(
        self, call: ToolCall, context: PolicyContext | None = None
    ) -> PolicyDecision:
        if call["name"] not in self.allowed_tool_names:
            return PolicyDecision.DENY
        decision = self.rules.get(call["name"], PolicyDecision.DENY)
        if decision == PolicyDecision.REQUIRE_APPROVAL and isinstance(
            context, PolicyContext
        ):
            try:
                approved = call_fingerprint(call) in context.approved_calls
            except (TypeError, ValueError):
                approved = False
            if approved:
                return PolicyDecision.ALLOW
        return decision


DEFAULT_POLICY_RULES = MappingProxyType(
    {
        "calculate_simple_interest": PolicyDecision.ALLOW,
        "get_me": PolicyDecision.ALLOW,
        "get_file_contents": PolicyDecision.ALLOW,
        "openmeteo_search_locations": PolicyDecision.ALLOW,
        "openmeteo_get_forecast": PolicyDecision.ALLOW,
        "get_transactions": PolicyDecision.ALLOW,
        "transfer_money": PolicyDecision.REQUIRE_APPROVAL,
    }
)
