"""Failures owned by the agent and model integration."""


class AgentError(Exception):
    pass


class LLMError(AgentError):
    pass


class LLMTimeoutError(LLMError):
    pass


class AgentExecutionError(AgentError):
    pass
