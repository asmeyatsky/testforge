"""Tests for LLM-powered test repair."""

from pathlib import Path
from unittest.mock import MagicMock, patch

from testforge.infrastructure.test_repairer import RepairResult, TestRepairer


class TestRepairResult:
    def test_creation(self):
        r = RepairResult(
            test_file="test_foo.py",
            original_code="# orig",
            repaired_code="# fixed",
            attempt=1,
            success=True,
        )
        assert r.success is True
        assert r.attempt == 1


class TestTestRepairer:
    @patch.object(TestRepairer, "_run_test")
    def test_no_repair_needed(self, mock_run_test, tmp_path: Path):
        """If tests already pass, no repair is done."""
        mock_run_test.return_value = ""  # empty = pass
        test_file = tmp_path / "test_ok.py"
        test_file.write_text("def test_pass(): assert True\n")

        ai = MagicMock()
        repairer = TestRepairer(ai_adapter=ai)
        result = repairer.repair_file(test_file)
        assert result.success is True
        assert result.attempt == 1
        ai.assert_not_called()

    @patch.object(TestRepairer, "_run_test")
    @patch.object(TestRepairer, "_ask_llm_to_fix")
    def test_successful_repair(self, mock_fix, mock_run_test, tmp_path: Path):
        """LLM fixes the test on first attempt."""
        # First call: test fails; second call: test passes
        mock_run_test.side_effect = ["AssertionError: expected 1", ""]
        mock_fix.return_value = "def test_fixed(): assert True\n"

        test_file = tmp_path / "test_broken.py"
        test_file.write_text("def test_broken(): assert False\n")

        ai = MagicMock()
        repairer = TestRepairer(ai_adapter=ai, max_attempts=3)
        result = repairer.repair_file(test_file)
        assert result.success is True

    @patch.object(TestRepairer, "_run_test")
    @patch.object(TestRepairer, "_ask_llm_to_fix")
    def test_repair_exhausts_attempts(self, mock_fix, mock_run_test, tmp_path: Path):
        """LLM can't fix the test after max attempts."""
        mock_run_test.return_value = "Error: still broken"
        mock_fix.return_value = "def test_still_broken(): assert False\n"

        test_file = tmp_path / "test_broken.py"
        original = "def test_broken(): assert False\n"
        test_file.write_text(original)

        ai = MagicMock()
        repairer = TestRepairer(ai_adapter=ai, max_attempts=2)
        result = repairer.repair_file(test_file)
        assert result.success is False
        # Original code should be restored
        assert test_file.read_text() == original

    @patch.object(TestRepairer, "_run_test")
    def test_repair_directory_skips_passing(self, mock_run_test, tmp_path: Path):
        """Repair directory skips files that already pass."""
        (tmp_path / "test_ok.py").write_text("def test_pass(): assert True\n")
        mock_run_test.return_value = ""

        ai = MagicMock()
        repairer = TestRepairer(ai_adapter=ai)
        results = repairer.repair_directory(tmp_path)
        assert len(results) == 0

    def test_find_source_code(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "utils.py").write_text("def foo(): pass\n")

        test_file = tmp_path / "tests" / "test_utils.py"
        test_file.parent.mkdir()
        test_file.write_text("def test_foo(): pass\n")

        ai = MagicMock()
        repairer = TestRepairer(ai_adapter=ai, source_root=src)
        source = repairer._find_source_code(test_file)
        assert "def foo" in source
