"""Settings routes — configure API keys and project target."""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from fastapi import APIRouter, Depends

from pydantic import BaseModel

from testforge.presentation.api.dependencies import WebSession, get_or_create_session

router = APIRouter(prefix="/api", tags=["settings"])


class SetKeysRequest(BaseModel):
    anthropic_key: str | None = None
    gemini_key: str | None = None


class SetTargetRequest(BaseModel):
    path: str  # local path or GitHub URL


@router.post("/settings/keys")
def set_keys(body: SetKeysRequest):
    if body.anthropic_key:
        os.environ["ANTHROPIC_API_KEY"] = body.anthropic_key
    if body.gemini_key:
        os.environ["GEMINI_API_KEY"] = body.gemini_key
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
    }


@router.get("/settings/keys")
def get_keys():
    return {
        "anthropic": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "gemini": bool(os.environ.get("GEMINI_API_KEY")),
    }


@router.post("/settings/target")
def set_target(
    body: SetTargetRequest,
    session: WebSession = Depends(get_or_create_session),
):
    target = body.path.strip()

    # GitHub URL → clone into temp directory
    if target.startswith("https://github.com/") or target.startswith("git@"):
        clone_dir = Path(tempfile.mkdtemp(prefix="testforge_"))
        try:
            subprocess.run(
                ["git", "clone", "--depth", "1", target, str(clone_dir)],
                check=True,
                capture_output=True,
                timeout=120,
            )
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
            shutil.rmtree(clone_dir, ignore_errors=True)
            return {"error": f"Failed to clone: {exc}"}
        target = str(clone_dir)

    resolved = Path(target).resolve()
    if not resolved.exists():
        return {"error": f"Path does not exist: {resolved}"}

    session.agent.project_path = resolved
    return {"session_id": session.id, "path": str(resolved)}
