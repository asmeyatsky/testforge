"""Data transfer objects for layer boundaries."""

from __future__ import annotations

from pydantic import BaseModel

from testforge.domain.value_objects import TestLayer


class ModuleDTO(BaseModel):
    file_path: str
    function_count: int
    class_count: int
    endpoint_count: int


class AnalysisDTO(BaseModel):
    id: str
    root_path: str
    modules: list[ModuleDTO]
    languages: list[str]
    total_functions: int
    total_classes: int
    total_modules: int


class TestCaseDTO(BaseModel):
    __test__ = False

    name: str
    description: str
    layer: str
    target_function: str
    target_module: str
    priority: int


class TestSuiteDTO(BaseModel):
    __test__ = False

    layer: str
    test_cases: list[TestCaseDTO]
    size: int


class StrategyDTO(BaseModel):
    id: str
    analysis_id: str
    suites: list[TestSuiteDTO]
    total_test_cases: int
    layers_covered: list[str]
