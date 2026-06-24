"""AgentRunner — owns the agent execution lifecycle.

Wraps Agent.iter so every agent gets the same treatment: a request budget,
per-turn budget hints, and structured telemetry. Shared by all three agent
tiers (summary, package, vulnerability).
"""

from __future__ import annotations

from typing import Any

from pydantic_ai import Agent
from pydantic_ai.messages import TextPart, ToolCallPart, ToolReturnPart
from pydantic_ai.usage import UsageLimits

from supplyfix import _budget
from supplyfix._budget import CallToolsNode, ModelRequestNode
from supplyfix.telemetry import emit


class AgentRunner:
    """Encapsulates the request budget, turn-budget injection, and telemetry for one agent."""

    def __init__(self, name: str, agent: Agent, max_requests: int) -> None:
        self.name = name
        self.agent = agent
        self.max_requests = max_requests

    async def run(self, prompt: str, *, deps: Any = None) -> Any:
        return await _run_loop(self.agent, self.name, prompt, deps, self.max_requests)


async def _run_loop(agent, name, prompt, deps, max_requests):
    req_count = 0
    run_kwargs: dict = {"usage_limits": UsageLimits(request_limit=max_requests)}
    if deps is not None:
        run_kwargs["deps"] = deps

    async with agent.iter(prompt, **run_kwargs) as agent_run:
        async for node in agent_run:
            if isinstance(node, ModelRequestNode):
                req_count += 1
                _budget.inject(node, req_count, max_requests)
                emit(
                    "agent_request_started",
                    agent=name,
                    message=f"{name} request {req_count}/{max_requests}",
                    request=req_count,
                    max_requests=max_requests,
                )
                for part in node.request.parts:
                    if isinstance(part, ToolReturnPart):
                        emit(
                            "tool_return",
                            agent=name,
                            message=part.model_response_str()[:300],
                            tool_name=part.tool_name,
                            content=part.model_response_str(),
                        )
            elif isinstance(node, CallToolsNode):
                for part in node.model_response.parts:
                    if isinstance(part, TextPart):
                        text = part.content.strip()
                        if text:
                            print(f"  [{name}] {text[:200]}")
                            emit("assistant_text", agent=name, message=text[:500], content=text)
                    elif isinstance(part, ToolCallPart):
                        print(f"  [{name}] → {part.tool_name}")
                        emit(
                            "tool_call",
                            agent=name,
                            message=f"{name} called {part.tool_name}",
                            tool_name=part.tool_name,
                            args=part.args_as_dict(),
                        )

    emit("agent_finished", agent=name, message=f"{name} finished")
    return agent_run.result
