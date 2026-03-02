"""Tests for DAG orchestrator."""

import pytest

from testforge.application.orchestrator import DAGOrchestrator, StepStatus, WorkflowStep


class TestDAGOrchestrator:
    def test_single_step(self):
        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=lambda ctx: "result_a"))
        result = orch.run()
        assert result["a"] == "result_a"

    def test_dependency_order(self):
        order = []

        def step_a(ctx):
            order.append("a")
            return 1

        def step_b(ctx):
            order.append("b")
            return ctx["a"] + 1

        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=step_a))
        orch.add_step(WorkflowStep(name="b", execute_fn=step_b, depends_on=["a"]))
        result = orch.run()

        assert order == ["a", "b"]
        assert result["b"] == 2

    def test_parallel_independent_steps(self):
        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=lambda ctx: 1))
        orch.add_step(WorkflowStep(name="b", execute_fn=lambda ctx: 2))
        orch.add_step(
            WorkflowStep(name="c", execute_fn=lambda ctx: ctx["a"] + ctx["b"], depends_on=["a", "b"])
        )
        result = orch.run()
        assert result["c"] == 3

    def test_failed_step_raises(self):
        def failing(ctx):
            raise ValueError("boom")

        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=failing))

        with pytest.raises(ValueError, match="boom"):
            orch.run()

        assert orch._steps["a"].status == StepStatus.FAILED

    def test_skipped_when_dependency_fails(self):
        def failing(ctx):
            raise ValueError("boom")

        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=failing))
        orch.add_step(WorkflowStep(name="b", execute_fn=lambda ctx: 1, depends_on=["a"]))

        with pytest.raises(ValueError):
            orch.run()

        # b never ran because a failed (and raised)
        assert orch._steps["b"].status == StepStatus.PENDING

    def test_context_passed_through(self):
        orch = DAGOrchestrator()
        orch.add_step(WorkflowStep(name="a", execute_fn=lambda ctx: ctx["seed"] * 2))
        result = orch.run(context={"seed": 5})
        assert result["a"] == 10
