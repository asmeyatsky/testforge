"""Dependency injection for FastAPI routes."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from fastapi import Header, Request

from testforge.infrastructure.container import Container
from testforge.presentation.agent import AgentSession


@dataclass
class WebSession:
    """Per-user session state, mirrors AgentSession for tool reuse."""

    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    agent: AgentSession = field(default_factory=AgentSession)


# In-memory session store — appropriate for single-user dev tool.
_sessions: dict[str, WebSession] = {}


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_or_create_session(
    request: Request,
    x_session_id: str | None = Header(default=None),
) -> WebSession:
    container: Container = request.app.state.container

    if x_session_id and x_session_id in _sessions:
        return _sessions[x_session_id]

    session_id = x_session_id or str(uuid.uuid4())
    session = WebSession(
        id=session_id,
        agent=AgentSession(container=container),
    )
    _sessions[session_id] = session
    return session
