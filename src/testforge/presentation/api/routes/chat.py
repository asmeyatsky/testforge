"""Chat routes — SSE streaming via AgentSession tool-use loop."""

from __future__ import annotations

import json
import logging
from typing import Any, AsyncIterator

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from testforge.presentation.agent import (
    TOOLS,
    AgentSession,
    _HANDLERS,
    _trim_messages,
    build_system_prompt,
)
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import ChatRequest

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["chat"])

# Per-session message history.
_chat_histories: dict[str, list[dict[str, Any]]] = {}


def _sse_event(event: str, data: Any) -> str:
    return f"event: {event}\ndata: {json.dumps(data)}\n\n"


def _stream_chat(session: WebSession, message: str) -> str:
    """Synchronous generator that yields SSE events for one user turn."""
    import anthropic

    client = anthropic.Anthropic()
    agent = session.agent

    history = _chat_histories.setdefault(session.id, [])
    history.append({"role": "user", "content": message})

    model = agent.container.config.get("ai", {}).get("model", "claude-sonnet-4-6-20250514")
    chunks: list[str] = []

    while True:
        system_prompt = build_system_prompt(agent)
        trimmed = _trim_messages(history)

        response = client.messages.create(
            model=model,
            max_tokens=4096,
            system=system_prompt,
            tools=TOOLS,
            messages=trimmed,
        )

        assistant_content: list[dict[str, Any]] = []
        tool_results: list[dict[str, Any]] = []

        for block in response.content:
            if block.type == "text":
                assistant_content.append({"type": "text", "text": block.text})
                chunks.append(_sse_event("text", {"text": block.text}))
            elif block.type == "tool_use":
                assistant_content.append({
                    "type": "tool_use",
                    "id": block.id,
                    "name": block.name,
                    "input": block.input,
                })
                chunks.append(_sse_event("tool_call", {"name": block.name, "input": block.input}))

                result = agent.execute_tool(block.name, block.input)

                chunks.append(_sse_event("tool_result", {"name": block.name, "result": result}))
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": block.id,
                    "content": result,
                })

        history.append({"role": "assistant", "content": assistant_content})

        if response.stop_reason == "end_turn":
            break

        if response.stop_reason == "tool_use" and tool_results:
            history.append({"role": "user", "content": tool_results})
        else:
            break

    chunks.append(_sse_event("done", {}))
    return "".join(chunks)


@router.post("/chat")
def chat(
    body: ChatRequest,
    session: WebSession = Depends(get_or_create_session),
):
    content = _stream_chat(session, body.message)

    return StreamingResponse(
        iter([content]),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Session-Id": session.id,
        },
    )
