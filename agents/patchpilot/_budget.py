"""Turn-budget hint injection for LLM agents.

This is the sole file that imports from pydantic_ai._agent_graph.
If pydantic-ai restructures its internals, only this file needs updating.
"""

from __future__ import annotations

# Re-exported so runner.py never imports _agent_graph directly.
from pydantic_ai._agent_graph import CallToolsNode, ModelRequestNode  # noqa: F401

__all__ = ["CallToolsNode", "ModelRequestNode", "hint", "inject"]


def hint(used: int, total: int) -> str:
    """Return the per-turn budget reminder string injected into model requests."""
    remaining_after = total - used
    if remaining_after <= 0:
        return (
            f"[turn-budget] This is the final allowed request ({used} of {total}). "
            "Tool calls, including final_result, need a follow-up request to complete, "
            "so it is too late to safely call tools now. Return immediately with the "
            "best final answer you can without more tool calls."
        )
    if remaining_after == 1:
        return (
            f"[turn-budget] Request {used} of {total}. This is the last request "
            "where a final_result tool call can safely complete. You MUST call "
            "final_result now with whatever you have, and do not call any other tools."
        )
    return (
        f"[turn-budget] Request {used} of {total}. "
        f"{remaining_after} turn(s) remain after this one. "
        "Plan to call final_result while at least one follow-up request remains."
    )


def inject(node, req_count: int, max_req: int) -> None:
    """Append a budget hint to a ModelRequestNode's parts (no-op for other node types)."""
    if not isinstance(node, ModelRequestNode) or req_count <= 1:
        return
    from pydantic_ai.messages import UserPromptPart

    node.request.parts.append(UserPromptPart(content=hint(req_count, max_req)))
