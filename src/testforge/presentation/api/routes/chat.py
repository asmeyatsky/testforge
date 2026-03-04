"""Chat routes — SSE streaming via AgentSession tool-use loop."""

from __future__ import annotations

import json
import logging
import os
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse

from testforge.presentation.agent import (
    TOOLS,
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


def _chat_with_anthropic(system_prompt: str, tools: list, messages: list) -> Any:
    import anthropic

    client = anthropic.Anthropic()
    model = os.environ.get("TESTFORGE_MODEL", "claude-sonnet-4-6-20250514")
    return client.messages.create(
        model=model,
        max_tokens=4096,
        system=system_prompt,
        tools=tools,
        messages=messages,
    )


def _chat_with_gemini(system_prompt: str, messages: list) -> dict:
    """Use Gemini for chat (without tool-use — just text responses)."""
    from google import genai

    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    model = os.environ.get("TESTFORGE_GEMINI_MODEL", "gemini-2.0-flash")

    # Build a conversation string from messages
    parts = [system_prompt, ""]
    for msg in messages:
        role = msg["role"]
        if isinstance(msg["content"], str):
            parts.append(f"{role}: {msg['content']}")
        elif isinstance(msg["content"], list):
            for block in msg["content"]:
                if isinstance(block, dict) and block.get("type") == "text":
                    parts.append(f"{role}: {block['text']}")

    response = client.models.generate_content(
        model=model,
        contents="\n".join(parts),
    )

    # Return a compatible structure
    return {"text": response.text, "stop_reason": "end_turn"}


def _stream_chat(session: WebSession, message: str) -> str:
    """Run chat turn and return SSE events string."""
    agent = session.agent
    has_anthropic = bool(os.environ.get("ANTHROPIC_API_KEY"))
    has_gemini = bool(os.environ.get("GEMINI_API_KEY"))

    if not has_anthropic and not has_gemini:
        return _sse_event("text", {
            "text": "No API key configured. Go to Settings (gear icon) and add an Anthropic or Gemini API key."
        }) + _sse_event("done", {})

    history = _chat_histories.setdefault(session.id, [])
    history.append({"role": "user", "content": message})
    chunks: list[str] = []

    if has_anthropic:
        # Full tool-use loop with Anthropic
        while True:
            system_prompt = build_system_prompt(agent)
            trimmed = _trim_messages(history)

            response = _chat_with_anthropic(system_prompt, TOOLS, trimmed)

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
    else:
        # Gemini fallback — text-only, no tool use
        system_prompt = build_system_prompt(agent)
        trimmed = _trim_messages(history)
        result = _chat_with_gemini(system_prompt, trimmed)
        chunks.append(_sse_event("text", {"text": result["text"]}))
        history.append({"role": "assistant", "content": [{"type": "text", "text": result["text"]}]})

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
