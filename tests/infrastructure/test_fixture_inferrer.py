"""Tests for fixture/mock inference."""

from pathlib import Path

from testforge.infrastructure.fixture_inferrer import FixtureInferrer


class TestFixtureInferrer:
    def test_infer_http_mocks(self):
        source = '''
import requests

def fetch_data(url):
    response = requests.get(url)
    return response.json()
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "fetch_data")
        assert len(result.mocks) >= 1
        mock_targets = [m.target for m in result.mocks]
        assert "requests.get" in mock_targets

    def test_infer_db_mocks(self):
        source = '''
import sqlite3

def get_users(db_path):
    conn = sqlite3.connect(db_path)
    return conn.execute("SELECT * FROM users").fetchall()
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "get_users")
        mock_targets = [m.target for m in result.mocks]
        assert "sqlite3.connect" in mock_targets

    def test_infer_subprocess_mock(self):
        source = '''
import subprocess

def run_command(cmd):
    return subprocess.run(cmd, capture_output=True)
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "run_command")
        mock_targets = [m.target for m in result.mocks]
        assert "subprocess.run" in mock_targets

    def test_infer_fixtures_from_params(self):
        source = '''
def process_data(db_session, user):
    return db_session.query(user)
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "process_data")
        fixture_names = [f.name for f in result.fixtures]
        assert "db_session" in fixture_names

    def test_generates_patch_decorators(self):
        source = '''
import requests

def api_call():
    return requests.get("http://example.com")
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "api_call")
        assert any("@patch" in d for d in result.patch_decorators)

    def test_no_mocks_for_pure_function(self):
        source = '''
def add(a, b):
    return a + b
'''
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function(source, "add")
        assert len(result.mocks) == 0
        assert len(result.fixtures) == 0

    def test_syntax_error_returns_empty(self):
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function("def broken(:", "broken")
        assert len(result.mocks) == 0

    def test_function_not_found_returns_empty(self):
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_function("def other(): pass", "missing")
        assert len(result.mocks) == 0

    def test_infer_for_module(self, tmp_path: Path):
        source = '''
import requests
import subprocess

def fetch(url):
    return requests.get(url)

def run(cmd):
    return subprocess.run(cmd)

def pure(x):
    return x + 1
'''
        f = tmp_path / "mod.py"
        f.write_text(source)
        inferrer = FixtureInferrer()
        result = inferrer.infer_for_module(f)
        assert "fetch" in result
        assert "run" in result
        assert "pure" not in result  # no mocks needed
