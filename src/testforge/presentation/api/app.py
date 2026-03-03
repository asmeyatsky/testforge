"""FastAPI application factory."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import AsyncIterator

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from testforge.infrastructure.container import Container
from testforge.presentation.api.routes import (
    analysis,
    chat,
    execution,
    gaps,
    generation,
    mutation,
    repair,
    strategy,
    validation,
)


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    app.state.container = Container()
    yield


def create_app() -> FastAPI:
    app = FastAPI(
        title="TestForge API",
        version="0.1.0",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    app.include_router(analysis.router)
    app.include_router(strategy.router)
    app.include_router(generation.router)
    app.include_router(execution.router)
    app.include_router(gaps.router)
    app.include_router(validation.router)
    app.include_router(repair.router)
    app.include_router(mutation.router)
    app.include_router(chat.router)

    return app
