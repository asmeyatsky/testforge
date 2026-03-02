"""Domain events."""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import datetime, timezone

from testforge.domain.value_objects import TestLayer


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


def _new_id() -> str:
    return str(uuid.uuid4())


@dataclass(frozen=True)
class DomainEvent:
    event_id: str = field(default_factory=_new_id)
    aggregate_id: str = ""
    occurred_at: datetime = field(default_factory=_utcnow)


@dataclass(frozen=True)
class AnalysisCompleted(DomainEvent):
    root_path: str = ""
    module_count: int = 0
    function_count: int = 0


@dataclass(frozen=True)
class StrategyGenerated(DomainEvent):
    layers: tuple[TestLayer, ...] = ()
    total_test_cases: int = 0


@dataclass(frozen=True)
class TestsGenerated(DomainEvent):
    layer: TestLayer = TestLayer.UNIT
    test_count: int = 0
    output_dir: str = ""
