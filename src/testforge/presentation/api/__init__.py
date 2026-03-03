"""Web API presentation layer — FastAPI backend for the TestForge dashboard."""

from __future__ import annotations

import uvicorn


def serve(host: str = "0.0.0.0", port: int = 8000) -> None:
    """Start the API server."""
    from testforge.presentation.api.app import create_app

    app = create_app()
    uvicorn.run(app, host=host, port=port)
