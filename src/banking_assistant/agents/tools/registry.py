"""Explicit tool registration and a default-deny execution policy."""

from collections.abc import Iterable
from types import MappingProxyType

from langchain_core.tools import BaseTool

from banking_assistant.agents.tools.interest_tool import calculate_simple_interest
from banking_assistant.agents.tools.transactions_tool import get_transactions
from banking_assistant.agents.tools.transfer_tool import transfer_money


class ToolRegistry:
    """A snapshot of available tools; registration alone grants no permission."""

    def __init__(self, tools: Iterable[BaseTool]):
        registered: dict[str, BaseTool] = {}
        for tool in tools:
            if not tool.name or tool.name in registered:
                raise ValueError(f"Empty or duplicate tool name: {tool.name!r}")
            registered[tool.name] = tool
        self.tools = MappingProxyType(registered)

    def resolve_allowed(self, allowed_names: Iterable[str]) -> list[BaseTool]:
        """Resolve only explicitly allowed names, failing on policy mistakes."""
        names = list(allowed_names)
        if len(names) != len(set(names)):
            raise ValueError("Allowed tool names must be unique")
        unknown = set(names).difference(self.tools)
        if unknown:
            raise ValueError(f"Allowed tools are not registered: {sorted(unknown)}")
        return [self.tools[name] for name in names]


DEFAULT_TOOL_REGISTRY = ToolRegistry(
    [calculate_simple_interest, get_transactions, transfer_money]
)
ALLOWED_TOOL_NAMES = frozenset(
    {
        "calculate_simple_interest",
        "get_transactions",
        "transfer_money",
    }
)
