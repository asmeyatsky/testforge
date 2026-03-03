"""Analysis routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.application.commands import AnalyseCodebaseCommand
from testforge.application.queries import GetAnalysis
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import AnalyseRequest

router = APIRouter(prefix="/api", tags=["analysis"])


@router.post("/analyse")
def analyse(
    body: AnalyseRequest,
    session: WebSession = Depends(get_or_create_session),
):
    agent = session.agent
    scanner = agent.container.scanner()
    cmd = AnalyseCodebaseCommand(scanner, agent.container.event_bus)
    agent.analysis = cmd.execute(Path(body.path).resolve())

    dto = GetAnalysis().execute(agent.analysis)
    return {"session_id": session.id, "analysis": dto.model_dump()}


@router.get("/analysis")
def get_analysis(
    session: WebSession = Depends(get_or_create_session),
):
    if session.agent.analysis is None:
        return {"error": "No analysis available. Run POST /api/analyse first."}

    dto = GetAnalysis().execute(session.agent.analysis)
    return {"session_id": session.id, "analysis": dto.model_dump()}
