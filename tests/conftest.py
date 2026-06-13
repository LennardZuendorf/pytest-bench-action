"""Shared helpers for pytest-bench-action script tests."""

import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"

sys.path.insert(0, str(SCRIPTS_DIR))


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def run_script():
    """Run a script CLI as a subprocess; returns CompletedProcess with text output."""

    def _run(script_name: str, *args: str, cwd: Path | None = None) -> subprocess.CompletedProcess:
        return subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / script_name), *args],
            capture_output=True,
            text=True,
            cwd=cwd,
        )

    return _run


@pytest.fixture
def write_json(tmp_path):
    """Write a dict as JSON into tmp_path and return the file path."""

    def _write(name: str, payload: dict) -> Path:
        path = tmp_path / name
        path.write_text(json.dumps(payload, indent=2))
        return path

    return _write


def make_results(node: str = "runner-abc", benchmarks: dict[str, float] | None = None) -> dict:
    """Build a minimal pytest-benchmark results payload from name → mean."""
    benchmarks = benchmarks if benchmarks is not None else {"test_foo": 0.001}
    machine_info = {"node": node, "python_version": "3.14.0"} if node else {}
    return {
        "machine_info": machine_info,
        "benchmarks": [
            {"name": name, "stats": {"mean": mean, "median": mean, "rounds": 10}}
            for name, mean in benchmarks.items()
        ],
    }
