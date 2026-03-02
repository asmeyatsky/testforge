"""Tests for test validators."""

from pathlib import Path

from testforge.infrastructure.validators import TestValidator


class TestTestValidator:
    def test_validate_syntax_valid(self, tmp_path: Path):
        (tmp_path / "test_ok.py").write_text("def test_foo(): assert True\n")
        validator = TestValidator()
        report = validator.validate_syntax(tmp_path)
        assert report.total == 1
        assert report.passed == 1
        assert report.failed == 0

    def test_validate_syntax_invalid(self, tmp_path: Path):
        (tmp_path / "test_bad.py").write_text("def broken(:\n  pass\n")
        validator = TestValidator()
        report = validator.validate_syntax(tmp_path)
        assert report.total == 1
        assert report.failed == 1
        assert "SyntaxError" in report.results[0].errors[0]

    def test_validate_syntax_mixed(self, tmp_path: Path):
        (tmp_path / "test_good.py").write_text("def test_a(): pass\n")
        (tmp_path / "test_bad.py").write_text("def broken(:\n")
        validator = TestValidator()
        report = validator.validate_syntax(tmp_path)
        assert report.total == 2
        assert report.passed == 1
        assert report.failed == 1
        assert report.success_rate == 0.5

    def test_validate_syntax_empty_dir(self, tmp_path: Path):
        validator = TestValidator()
        report = validator.validate_syntax(tmp_path)
        assert report.total == 0
        assert report.success_rate == 1.0

    def test_validate_collection(self, tmp_path: Path):
        (tmp_path / "test_simple.py").write_text("def test_one(): assert 1 + 1 == 2\n")
        validator = TestValidator()
        report = validator.validate_collection(tmp_path)
        assert report.total >= 1
