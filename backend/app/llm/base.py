from dataclasses import dataclass
from typing import Any, Protocol


@dataclass(frozen=True)
class ToolCallRequest:
    name: str
    arguments: dict[str, Any]


@dataclass(frozen=True)
class LLMResult:
    content: str | None = None
    tool_call: ToolCallRequest | None = None
    tool_calls: tuple[ToolCallRequest, ...] = ()

    def normalized_tool_calls(self) -> tuple[ToolCallRequest, ...]:
        """Return the multi-call shape while accepting the legacy single call."""
        if self.tool_calls:
            return self.tool_calls
        return (self.tool_call,) if self.tool_call is not None else ()


class LLMProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        """Return text or zero, one, or multiple normalized tool calls."""

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        """Return the final assistant text after a tool execution."""

    def complete_with_tool_results(
        self,
        messages: list[dict[str, str]],
        results: list[dict[str, Any]],
    ) -> str:
        """Return the final assistant text after all tool executions."""
