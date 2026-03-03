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
        assert "validate" in result.output
        assert "gaps" in result.output
        assert "watch" in result.output

    def test_analyse(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def hello(): pass\n")
        result = runner.invoke(app, ["analyse", str(tmp_path)])
        assert result.exit_code == 0
        assert "Codebase Analysis" in result.output
        assert "Modules" in result.output

    def test_analyse_json(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def hello(): pass\n")
        result = runner.invoke(app, ["analyse", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        assert '"total_functions"' in result.output

    def test_analyse_yaml(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def hello(): pass\n")
        result = runner.invoke(app, ["analyse", str(tmp_path), "--format", "yaml"])
        assert result.exit_code == 0
        assert "total_functions:" in result.output

    def test_analyse_empty_dir(self, tmp_path: Path):
        result = runner.invoke(app, ["analyse", str(tmp_path)])
        assert result.exit_code == 0
        assert "0" in result.output

    def test_strategise(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def greet(name): pass\n")
        result = runner.invoke(app, ["strategise", str(tmp_path)])
        assert result.exit_code == 0
        assert "Test Strategy" in result.output

    def test_strategise_json(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def greet(name): pass\n")
        result = runner.invoke(app, ["strategise", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        assert '"total_test_cases"' in result.output

    def test_strategise_with_layers(self, tmp_path: Path):
        (tmp_path / "sample.py").write_text("def greet(name): pass\n")
        result = runner.invoke(app, ["strategise", str(tmp_path), "--layers", "unit"])
        assert result.exit_code == 0

    def test_generate(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "app.py").write_text("def handler(): pass\n")
        out = tmp_path / "out"
        result = runner.invoke(app, ["generate", str(src), "--output-dir", str(out), "--layers", "unit", "--no-dedup"])
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

    def test_validate(self, tmp_path: Path):
        (tmp_path / "test_ok.py").write_text("def test_foo(): assert True\n")
        result = runner.invoke(app, ["validate", str(tmp_path)])
        assert result.exit_code == 0
        assert "PASS" in result.output

    def test_gaps(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "utils.py").write_text("def foo(): pass\ndef bar(): pass\n")
        tests = src / "tests"
        tests.mkdir()
        (tests / "test_utils.py").write_text("def test_foo(): pass\n")
        result = runner.invoke(app, ["gaps", str(src), "--test-dir", str(tests)])
        assert result.exit_code == 0
        assert "Coverage Gap" in result.output

    def test_gaps_json(self, tmp_path: Path):
        src = tmp_path / "src"
        src.mkdir()
        (src / "utils.py").write_text("def foo(): pass\n")
        result = runner.invoke(app, ["gaps", str(src), "--format", "json"])
        assert result.exit_code == 0
        assert '"coverage_percent"' in result.output

    def test_help_shows_new_commands(self):
        result = runner.invoke(app, ["--help"])
        assert result.exit_code == 0
        assert "execute" in result.output
        assert "incremental" in result.output
        assert "repair" in result.output
        assert "mutate" in result.output
        assert "interactive" in result.output
        assert "plugins" in result.output

    def test_execute(self, tmp_path: Path):
        (tmp_path / "test_ok.py").write_text("def test_pass(): assert True\n")
        result = runner.invoke(app, ["execute", str(tmp_path)])
        assert result.exit_code == 0
        assert "Execution Report" in result.output

    def test_execute_json(self, tmp_path: Path):
        (tmp_path / "test_ok.py").write_text("def test_pass(): assert True\n")
        result = runner.invoke(app, ["execute", str(tmp_path), "--format", "json"])
        assert result.exit_code == 0
        assert '"total"' in result.output

    def test_plugins_command(self):
        result = runner.invoke(app, ["plugins"])
        assert result.exit_code == 0

    def test_incremental_no_git(self, tmp_path: Path):
        result = runner.invoke(app, ["incremental", str(tmp_path)])
        assert result.exit_code == 0
        assert "No source file changes" in result.output
