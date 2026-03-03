"""Tests for incremental diff detector."""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from testforge.infrastructure.diff_detector import DiffDetector, DiffResult


class TestDiffResult:
    def test_all_changed(self):
        dr = DiffResult(modified=("a.py",), added=("b.py",), deleted=("c.py",))
        assert dr.all_changed == ("a.py", "b.py")

    def test_has_changes_true(self):
        dr = DiffResult(modified=("a.py",), added=(), deleted=())
        assert dr.has_changes is True

    def test_has_changes_false(self):
        dr = DiffResult(modified=(), added=(), deleted=())
        assert dr.has_changes is False


class TestDiffDetector:
    def test_detect_git_changes(self, tmp_path: Path):
        detector = DiffDetector(tmp_path)
        # Without a git repo, returns empty
        result = detector.detect_git_changes()
        assert not result.has_changes

    def test_is_source_file(self):
        assert DiffDetector._is_source_file("app.py") is True
        assert DiffDetector._is_source_file("app.ts") is True
        assert DiffDetector._is_source_file("readme.md") is False
        assert DiffDetector._is_source_file("data.json") is False

    @patch("testforge.infrastructure.diff_detector.subprocess.run")
    def test_detect_git_changes_with_mock(self, mock_run, tmp_path: Path):
        mock_diff = MagicMock()
        mock_diff.returncode = 0
        mock_diff.stdout = "M\tapp.py\nA\tnew_file.py\nD\told.py\n"

        mock_untracked = MagicMock()
        mock_untracked.returncode = 0
        mock_untracked.stdout = ""

        mock_run.side_effect = [mock_diff, mock_untracked]

        detector = DiffDetector(tmp_path)
        result = detector.detect_git_changes()
        assert "app.py" in result.modified
        assert "new_file.py" in result.added
        assert "old.py" in result.deleted

    def test_filter_analysis_to_changed(self, tmp_path: Path):
        from testforge.domain.entities import CodebaseAnalysis
        from testforge.domain.value_objects import FilePath, FunctionSignature, ModuleInfo

        analysis = CodebaseAnalysis(
            modules=(
                ModuleInfo(file_path=FilePath("app.py"), functions=(FunctionSignature(name="foo", parameters=()),)),
                ModuleInfo(file_path=FilePath("utils.py"), functions=(FunctionSignature(name="bar", parameters=()),)),
            ),
        )
        diff = DiffResult(modified=("app.py",), added=(), deleted=())
        detector = DiffDetector(tmp_path)
        filtered = detector.filter_analysis_to_changed(analysis, diff)
        assert filtered.total_modules == 1
        assert str(filtered.modules[0].file_path) == "app.py"
