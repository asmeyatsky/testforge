"""Request/response models for the API."""

from __future__ import annotations

from pydantic import BaseModel


class AnalyseRequest(BaseModel):
    path: str = "."


class StrategyRequest(BaseModel):
    path: str = "."
    layers: str | None = None
    prd: str | None = None


class GenerateRequest(BaseModel):
    layers: str | None = None
    output_dir: str | None = None


class ExecuteRequest(BaseModel):
    test_dir: str | None = None


class GapsRequest(BaseModel):
    path: str = "."
    test_dir: str | None = None


class ValidateRequest(BaseModel):
    test_dir: str | None = None


class RepairRequest(BaseModel):
    test_dir: str | None = None
    max_attempts: int = 3


class MutateRequest(BaseModel):
    source: str = "."
    test_dir: str = "tests"


class ChatRequest(BaseModel):
    message: str
