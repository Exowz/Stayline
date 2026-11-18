"""Model interface and OpenRouter chat completion adapter."""

from time import perf_counter
from typing import Protocol

from openai import AsyncOpenAI
from pydantic import BaseModel

from stayline.config import Settings


class LLMReply(BaseModel):
    """One assistant message and its measured usage."""

    message: dict
    usage: dict


class LLM(Protocol):
    """Complete one turn with the available tool schemas."""

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMReply: ...


class OpenRouterLLM:
    """Use the configured OpenRouter chat completion endpoint."""

    def __init__(self, settings: Settings) -> None:
        self.settings = settings
        self.client = AsyncOpenAI(
            base_url=settings.base_url,
            api_key=settings.api_key.get_secret_value(),
            max_retries=3,
            timeout=settings.model_timeout_s,
        )

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        started = perf_counter()
        reply = await self.client.chat.completions.create(
            model=self.settings.model, messages=messages, tools=tools,
            temperature=0, max_tokens=self.settings.max_tokens,
        )
        elapsed_ms = round((perf_counter() - started) * 1000)
        usage = reply.usage
        return LLMReply(
            message=reply.choices[0].message.model_dump(exclude_none=True),
            usage={
                "model": reply.model,
                "tokens_in": usage.prompt_tokens,
                "tokens_out": usage.completion_tokens,
                "cost_usd": float(getattr(usage, "cost", None) or 0.0),
                "ms": elapsed_ms,
            },
        )
