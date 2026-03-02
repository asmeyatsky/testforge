"""Tests for filesystem adapter."""

from pathlib import Path

from testforge.infrastructure.filesystem import FileSystemAdapter


class TestFileSystemAdapter:
    def test_write_and_read(self, tmp_path: Path):
        fs = FileSystemAdapter()
        target = tmp_path / "sub" / "file.txt"
        fs.write_text(target, "hello")
        assert fs.read_text(target) == "hello"

    def test_list_files(self, tmp_path: Path):
        (tmp_path / "a.py").write_text("a")
        (tmp_path / "b.txt").write_text("b")
        sub = tmp_path / "sub"
        sub.mkdir()
        (sub / "c.py").write_text("c")

        fs = FileSystemAdapter()
        all_files = fs.list_files(tmp_path)
        assert len(all_files) == 3

        py_files = fs.list_files(tmp_path, "**/*.py")
        assert len(py_files) == 2

    def test_exists(self, tmp_path: Path):
        fs = FileSystemAdapter()
        assert fs.exists(tmp_path) is True
        assert fs.exists(tmp_path / "nope") is False

    def test_mkdir(self, tmp_path: Path):
        fs = FileSystemAdapter()
        new_dir = tmp_path / "a" / "b" / "c"
        fs.mkdir(new_dir)
        assert new_dir.is_dir()
