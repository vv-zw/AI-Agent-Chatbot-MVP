class MockLLMProvider:
    async def complete(self, messages: list[dict[str, str]]) -> str:
        latest = messages[-1]["content"] if messages else ""
        return f"[Mock] I received: {latest}"

