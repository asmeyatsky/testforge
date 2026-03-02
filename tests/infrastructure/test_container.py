"""Tests for the DI container."""

from unittest.mock import patch

from testforge.domain.events import AnalysisCompleted
from testforge.domain.value_objects import TestLayer
from testforge.infrastructure.container import Container, SimpleEventBus
from testforge.infrastructure.scanners.python_scanner import PythonScanner


class TestSimpleEventBus:
    def test_publish_calls_handler(self):
        bus = SimpleEventBus()
        received = []
        bus.subscribe(AnalysisCompleted, lambda e: received.append(e))
        event = AnalysisCompleted(aggregate_id="a1", module_count=5)
        bus.publish(event)
        assert len(received) == 1
        assert received[0].module_count == 5

    def test_publish_no_handlers(self):
        bus = SimpleEventBus()
        # Should not raise
        bus.publish(AnalysisCompleted())

    def test_multiple_handlers(self):
        bus = SimpleEventBus()
        counts = {"a": 0, "b": 0}
        bus.subscribe(AnalysisCompleted, lambda e: counts.__setitem__("a", counts["a"] + 1))
        bus.subscribe(AnalysisCompleted, lambda e: counts.__setitem__("b", counts["b"] + 1))
        bus.publish(AnalysisCompleted())
        assert counts == {"a": 1, "b": 1}


class TestContainer:
    def test_default_config(self):
        container = Container()
        assert "project" in container.config
        assert "layers" in container.config

    def test_custom_config(self):
        container = Container(config={"project": {"name": "test"}})
        assert container.config["project"]["name"] == "test"

    def test_scanner_returns_python_scanner(self):
        container = Container()
        assert isinstance(container.scanner(), PythonScanner)

    def test_generators_returns_all_layers(self):
        container = Container()
        gens = container.generators()
        assert TestLayer.UNIT in gens
        assert TestLayer.INTEGRATION in gens
        assert TestLayer.SOAK in gens
        assert TestLayer.PERFORMANCE in gens
        assert TestLayer.UAT in gens

    def test_event_bus(self):
        container = Container()
        assert isinstance(container.event_bus, SimpleEventBus)

    def test_ai_strategy_none_without_key(self):
        container = Container()
        with patch.dict("os.environ", {}, clear=True):
            assert container.ai_strategy() is None

    def test_filesystem(self):
        container = Container()
        assert container.filesystem is not None
