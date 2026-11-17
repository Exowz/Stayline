"""Scripted model and fault wrapper for graph tests."""

import json

from stayline.agent.llm import LLMReply
from stayline.servers.results import ToolError, ToolResult


class ScriptedLLM:
    """Return scripted model replies and retain each input transcript."""

    def __init__(self, steps: list[dict]) -> None:
        self.steps = list(steps)
        self.seen: list[list[dict]] = []
        self.calls = 0

    async def complete(self, messages: list[dict], tools: list[dict]) -> LLMReply:
        self.seen.append(list(messages))
        step = self.steps.pop(0) if self.steps else {"tool": "finish", "args": {"summary": "done"}}
        self.calls += 1
        if "text" in step:
            message = {"role": "assistant", "content": step["text"]}
        else:
            arguments = step.get("raw_arguments", json.dumps(step.get("args", {})))
            message = {"role": "assistant", "content": None, "tool_calls": [{
                "id": f"call-{self.calls}", "type": "function",
                "function": {"name": step["tool"], "arguments": arguments},
            }]}
        return LLMReply(message=message, usage={
            "model": "scripted", "tokens_in": 10, "tokens_out": 5,
            "cost_usd": 0.001, "ms": 1,
        })


class FlakyHarness:
    """Lose a selected write response after forwarding the call."""

    def __init__(self, inner, tool: str, times: int = 1) -> None:
        self.inner = inner
        self.tool = tool
        self.times = times

    def tool_specs(self) -> list[dict]:
        return self.inner.tool_specs()

    async def call(self, tool: str, args: dict, run_id: str) -> ToolResult:
        result = await self.inner.call(tool, args, run_id)
        if tool == self.tool and self.times > 0:
            self.times -= 1
            return ToolResult(ok=False, error=ToolError(
                code="timeout", message="lost", retryable=True, outcome_unknown=True,
            ))
        return result
