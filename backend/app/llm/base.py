from typing import Protocol


class LLMProvider(Protocol):
    async def complete(self, messages: list[dict[str, str]]) -> str:
        """Return an assistant response for normalized conversation messages."""

