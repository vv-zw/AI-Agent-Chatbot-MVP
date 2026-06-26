from typing import Literal

from pydantic import BaseModel


LLMProviderName = Literal["mock", "openai"]


class LLMProviderStatus(BaseModel):
    provider: LLMProviderName
    available_providers: list[LLMProviderName]
    openai_configured: bool


class LLMProviderSwitchRequest(BaseModel):
    provider: str


class LLMProviderSwitchResponse(BaseModel):
    provider: LLMProviderName
    openai_configured: bool
