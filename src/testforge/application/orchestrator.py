"""DAG-based pipeline orchestrator."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable

logger = logging.getLogger(__name__)


class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    SKIPPED = "skipped"


@dataclass
class WorkflowStep:
    name: str
    execute_fn: Callable[..., Any]
    depends_on: list[str] = field(default_factory=list)
    status: StepStatus = StepStatus.PENDING
    result: Any = None
    error: Exception | None = None


class DAGOrchestrator:
    """Executes workflow steps respecting dependency order."""

    def __init__(self) -> None:
        self._steps: dict[str, WorkflowStep] = {}

    def add_step(self, step: WorkflowStep) -> None:
        self._steps[step.name] = step

    def run(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        ctx = dict(context or {})
        execution_order = self._topological_sort()
        logger.info("Executing pipeline: %s", " -> ".join(execution_order))

        for step_name in execution_order:
            step = self._steps[step_name]
            deps_met = all(
                self._steps[d].status == StepStatus.COMPLETED
                for d in step.depends_on
            )
            if not deps_met:
                step.status = StepStatus.SKIPPED
                continue

            step.status = StepStatus.RUNNING
            logger.info("Running step: %s", step_name)
            try:
                step.result = step.execute_fn(ctx)
                ctx[step.name] = step.result
                step.status = StepStatus.COMPLETED
                logger.info("Step completed: %s", step_name)
            except Exception as exc:
                step.error = exc
                step.status = StepStatus.FAILED
                logger.error("Step failed: %s — %s", step_name, exc)
                raise

        return ctx

    def _topological_sort(self) -> list[str]:
        visited: set[str] = set()
        order: list[str] = []

        def visit(name: str) -> None:
            if name in visited:
                return
            visited.add(name)
            step = self._steps[name]
            for dep in step.depends_on:
                visit(dep)
            order.append(name)

        for name in self._steps:
            visit(name)

        return order
