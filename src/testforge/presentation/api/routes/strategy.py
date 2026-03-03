"""Strategy routes."""

from __future__ import annotations

from fastapi import APIRouter, Depends

from testforge.application.commands import GenerateStrategyCommand
from testforge.application.queries import GetStrategy
from testforge.domain.value_objects import TestLayer
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import StrategyRequest

router = APIRouter(prefix="/api", tags=["strategy"])


@router.post("/strategy")
def generate_strategy(
    body: StrategyRequest,
    session: WebSession = Depends(get_or_create_session),
):
    agent = session.agent
    if agent.analysis is None:
        return {"error": "No analysis available. Run POST /api/analyse first."}

    layers_str = (body.layers or "").strip() or "unit"
    layers = [TestLayer(l.strip()) for l in layers_str.split(",")]

    ai = agent.container.ai_strategy()
    cmd = GenerateStrategyCommand(ai, agent.container.event_bus)
    agent.strategy = cmd.execute(agent.analysis, layers, body.prd)

    dto = GetStrategy().execute(agent.strategy)
    return {"session_id": session.id, "strategy": dto.model_dump()}


@router.get("/strategy")
def get_strategy(
    session: WebSession = Depends(get_or_create_session),
):
    if session.agent.strategy is None:
        return {"error": "No strategy available. Run POST /api/strategy first."}

    dto = GetStrategy().execute(session.agent.strategy)
    return {"session_id": session.id, "strategy": dto.model_dump()}
