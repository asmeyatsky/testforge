"""Tests for the CLI presentation layer."""

from pathlib import Path

from typer.testing import CliRunner

from testforge.presentation.cli import app

runner = CliRunner()


class TestCLI:
    def test_help(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "analyse" in result.output
        assert "strategise" in result.output
        assert "generate" in result.output
        assert "run" in result.output

    def test_analyse(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def hello(): pass\n")
        result = runner.invoke(app, ["analyse", str(tmp_path)])
        assert result.exit_code == 0
        assert "Codebase Analysis" in result.output
        assert "Modules" in result.output

    def test_analyse_empty_dir(self, tmp_path: Path):
        result = runner.invoke(app, ["analyse", str(tmp_path)])
        assert result.exit_code == 0
        assert "0" in result.output

    def test_strategise(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def greet(name): pass\n")
        result = runner.invoke(app, ["strategise", str(tmp_path)])
        assert result.exit_code == 0
        assert "Test Strategy" in result.output

    def test_strategise_with_layers(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def greet(name): pass\n")
        result = runner.invoke(app, ["strategise", str(tmp_path), "--layers", "unit"])
        assert result.exit_code == 0

    def test_generate(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def handler(): pass\n")
        out = tmp_path / "out"
        result = runner.invoke(app, ["generate", str(src), "--output-dir", str(out), "--layers", "unit"])
        assert result.exit_code == 0

    def test_run_dry_run(self, tmp_path: Path):
        (tmp_path / "mod.py").write_text("def calc(x): return x + 1\n")
        result = runner.invoke(app, ["run", str(tmp_path), "--layers", "unit", "--dry-run"])
        assert result.exit_code == 0
        assert "Pipeline Complete" in result.output
        assert "Dry run: yes" in result.output

    def test_run_generates_files(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "math_utils.py").write_text("def add(a, b): return a + b\n")
        out = tmp_path / "output"
        result = runner.invoke(app, ["run", str(src), "--layers", "unit", "--output-dir", str(out)])
        assert result.exit_code == 0
        assert "Dry run: no" in result.output
