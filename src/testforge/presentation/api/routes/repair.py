"""Test repair routes."""

from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends

from testforge.presentation.api.dependencies import WebSession, get_or_create_session
from testforge.presentation.api.schemas import RepairRequest

router = APIRouter(prefix="/api", tags=["repair"])


@router.post("/repair")
def repair_tests(
    body: RepairRequest,
    session: WebSession = Depends(get_or_create_session),
):
    from testforge.infrastructure.test_repairer import TestRepairer

    ai = session.agent.container.ai_strategy()
    if not ai:
        return {"error": "ANTHROPIC_API_KEY required for test repair."}

    test_dir = Path(body.test_dir or str(session.agent.output_dir))
    repairer = TestRepairer(ai_adapter=ai, max_attempts=body.max_attempts)
    results = repairer.repair_directory(test_dir)

    if not results:
        return {"session_id": session.id, "repair": {"message": "All tests passing.", "results": []}}

    return {
        "session_id": session.id,
        "repair": {
            "fixed": sum(1 for r in results if r.success),
            "total": len(results),
            "results": [
                {
                    "file": Path(r.test_file).name,
                    "success": r.success,
                    "attempt": r.attempt,
                    "error": r.error if not r.success else None,
                }
                for r in results
            ],
        },
    }
