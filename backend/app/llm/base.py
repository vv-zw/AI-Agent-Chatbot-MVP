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


class LLMProvider(Protocol):
    def complete(self, messages: list[dict[str, str]]) -> LLMResult:
        """Return text or one normalized tool call."""

    def complete_with_tool_result(
        self,
        messages: list[dict[str, str]],
        tool_name: str,
        result: dict[str, Any],
    ) -> str:
        """Return the final assistant text after a tool execution."""