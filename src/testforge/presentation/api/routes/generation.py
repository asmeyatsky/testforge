"""Test generation routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.application.commands import GenerateTestsCommand
from testforge.domain.value_objects import TestLayer
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import GenerateRequest

router = APIRouter(prefix="/api", tags=["generation"])


@router.post("/generate")
def generate_tests(
    body: GenerateRequest,
    session: WebSession = Depends(get_or_create_session),
):
    agent = session.agent
    if agent.strategy is None:
        return {"error": "No strategy available. Run POST /api/strategy first."}

    out = Path(body.output_dir or str(agent.output_dir))
    agent.output_dir = out

    layers: list[TestLayer] | None = None
    if body.layers:
        layers = [TestLayer(l.strip()) for l in body.layers.split(",")]

    generators = agent.container.generators(source_root=agent.project_path.resolve())
    cmd = GenerateTestsCommand(generators, agent.container.event_bus)
    suites = cmd.execute(agent.strategy, out, layers)

    return {
        "session_id": session.id,
        "suites": [
            {"layer": s.layer.value, "size": s.size, "output_dir": str(out)}
            for s in suites
        ],
    }
