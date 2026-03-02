"""Tests for coverage gap analyser."""

from pathlib import Path

from testforge.domain.entities import CodebaseAnalysis
from testforge.domain.value_objects import ClassInfo, FilePath, FunctionSignature, ModuleInfo
from testforge.infrastructure.gap_analyser import GapAnalyser


def _analysis() -> CodebaseAnalysis:
    return CodebaseAnalysis(
        modules=(
            ModuleInfo(
                file_path=FilePath("utils.py"),
                functions=(
                    FunctionSignature(name="format_name", parameters=()),
                    FunctionSignature(name="parse_data", parameters=()),
                    FunctionSignature(name="validate", parameters=()),
                ),
            ),
            ModuleInfo(
                file_path=FilePath("service.py"),
                classes=(
                    ClassInfo(
                        name="UserService",
                        methods=(
                            FunctionSignature(name="__init__", parameters=()),
                            FunctionSignature(name="get_user", parameters=("id",)),
                            FunctionSignature(name="_private", parameters=()),
                        ),
                    ),
                ),
            ),
        ),
    )


class TestGapAnalyser:
    def test_all_untested(self, tmp_path: Path):
        analyser = GapAnalyser()
        report = analyser.analyse(_analysis(), tmp_path)
        # No test files exist, so nothing is tested
        assert report.tested == 0
        assert report.total > 0
        assert report.coverage_percent == 0.0

    def test_partial_coverage(self, tmp_path: Path):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_utils.py").write_text(
            "def test_format_name(): pass\ndef test_validate(): pass\n"
        )
        analyser = GapAnalyser()
        report = analyser.analyse(_analysis(), test_dir)
        assert report.tested >= 2
        assert "parse_data" in str(report.untested)

    def test_full_coverage(self, tmp_path: Path):
        test_dir = tmp_path / "tests"
        test_dir.mkdir()
        (test_dir / "test_utils.py").write_text(
            "def test_format_name(): pass\n"
            "def test_parse_data(): pass\n"
            "def test_validate(): pass\n"
        )
        (test_dir / "test_service.py").write_text(
            "def test_UserService___init__(): pass\n"
            "def test_UserService_get_user(): pass\n"
        )
        analyser = GapAnalyser()
        report = analyser.analyse(_analysis(), test_dir)
        assert report.coverage_percent == 100.0

    def test_skips_private_methods(self, tmp_path: Path):
        analyser = GapAnalyser()
        report = analyser.analyse(_analysis(), tmp_path)
        untested_names = [u.split("::")[-1] for u in report.untested]
        assert "_private" not in untested_names

    def test_empty_analysis(self, tmp_path: Path):
        analyser = GapAnalyser()
        report = analyser.analyse(CodebaseAnalysis(), tmp_path)
        assert report.total == 0
        assert report.coverage_percent == 100.0
