"""Coverage gap analysis routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.infrastructure.gap_analyser import GapAnalyser
from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import GapsRequest

router = APIRouter(prefix="/api", tags=["gaps"])


@router.post("/gaps")
def find_gaps(
    body: GapsRequest,
    session: WebSession = Depends(get_or_create_session),
):
    agent = session.agent
    if agent.analysis:
        analysis = agent.analysis
    else:
        scanner = agent.container.scanner()
        analysis = scanner.scan(Path(body.path).resolve())

    test_dir = Path(body.test_dir) if body.test_dir else Path(body.path).resolve() / "tests"
    analyser = GapAnalyser()
    report = analyser.analyse(analysis, test_dir)

    return {
        "session_id": session.id,
        "gaps": {
            "coverage_percent": report.coverage_percent,
            "tested": report.tested,
            "total": report.total,
            "untested_count": len(report.untested),
            "untested": report.untested[:100],
            "modules": [
                {
                    "file_path": m.file_path,
                    "tested": m.tested,
                    "untested": m.untested,
                    "tested_count": m.tested_count,
                    "total_count": m.total_count,
                }
                for m in report.modules
                if m.untested
            ],
        },
    }
