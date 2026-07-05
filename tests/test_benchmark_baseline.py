"""Tests for scripts/benchmark_baseline.py (save / load / list / sanitization)."""

import json
from datetime import datetime

import pytest

from benchmark_baseline import sanitize_branch
from conftest import make_results

SCRIPT = "benchmark_baseline.py"


class TestSanitizeBranch:
    @pytest.mark.parametrize(
        ("branch", "expected"),
        [
            ("main", "main"),
            ("feature/my-thing", "feature_my-thing"),
            ("release/v1.2.3", "release_v1_2_3"),
            ("fix\\windows path", "fix_windows_path"),
            ("a.b c\\d/e", "a_b_c_d_e"),
        ],
    )
    def test_replaces_unsafe_characters(self, branch, expected):
        assert sanitize_branch(branch) == expected


class TestSave:
    def test_creates_baseline_file_with_sanitized_name(self, run_script, fixtures_dir, tmp_path):
        result = run_script(
            SCRIPT, "save", "feature/my-thing", str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        assert result.returncode == 0
        assert (tmp_path / "feature_my-thing.json").exists()
        assert "Saved baseline" in result.stdout

    def test_strips_data_arrays(self, run_script, fixtures_dir, tmp_path):
        run_script(
            SCRIPT, "save", "main", str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        saved = json.loads((tmp_path / "main.json").read_text())
        for bench in saved["benchmarks"]:
            assert "data" not in bench["stats"]
            assert "mean" in bench["stats"]

    def test_injects_baseline_info(self, run_script, fixtures_dir, tmp_path):
        run_script(
            SCRIPT, "save", "feature/x", str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        saved = json.loads((tmp_path / "feature_x.json").read_text())
        info = saved["baseline_info"]
        assert info["branch"] == "feature/x"
        assert info["node"] == "runner-abc"
        datetime.fromisoformat(info["created_at"])

    def test_node_defaults_to_unknown(self, run_script, write_json, tmp_path):
        results = write_json("no_node.json", make_results(node="", benchmarks={"test_foo": 0.001}))
        result = run_script(SCRIPT, "save", "main", str(results), f"--baselines-dir={tmp_path}")
        assert result.returncode == 0
        saved = json.loads((tmp_path / "main.json").read_text())
        assert saved["baseline_info"]["node"] == "unknown"

    def test_overwrite_is_idempotent(self, run_script, fixtures_dir, tmp_path):
        for _ in range(2):
            result = run_script(
                SCRIPT, "save", "main", str(fixtures_dir / "results.json"),
                f"--baselines-dir={tmp_path}",
            )
            assert result.returncode == 0
        assert len(list(tmp_path.glob("*.json"))) == 1

    def test_unicode_names_round_trip_utf8(self, run_script, write_json, tmp_path):
        # Non-ASCII benchmark names must survive save/load regardless of locale
        # (scripts read/write with explicit utf-8).
        results = write_json("uni.json", make_results(benchmarks={"test_café_ωμέγα": 0.001}))
        save = run_script(SCRIPT, "save", "main", str(results), f"--baselines-dir={tmp_path}")
        assert save.returncode == 0, save.stderr
        load = run_script(SCRIPT, "load", "main", f"--baselines-dir={tmp_path}")
        assert load.returncode == 0
        # JSON may escape non-ASCII (ensure_ascii); assert on the parsed value.
        loaded = json.loads(load.stdout)
        assert loaded["benchmarks"][0]["name"] == "test_café_ωμέγα"

    def test_missing_results_file_exits_1(self, run_script, tmp_path):
        result = run_script(SCRIPT, "save", "main", str(tmp_path / "nope.json"), f"--baselines-dir={tmp_path}")
        assert result.returncode == 1
        assert "not found" in result.stderr

    def test_missing_args_exits_1(self, run_script):
        result = run_script(SCRIPT, "save", "main")
        assert result.returncode == 1


class TestLoad:
    def test_round_trip(self, run_script, fixtures_dir, tmp_path):
        run_script(
            SCRIPT, "save", "feature/y", str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        result = run_script(SCRIPT, "load", "feature/y", f"--baselines-dir={tmp_path}")
        assert result.returncode == 0
        loaded = json.loads(result.stdout)
        assert loaded["baseline_info"]["branch"] == "feature/y"

    def test_missing_baseline_exits_1(self, run_script, tmp_path):
        result = run_script(SCRIPT, "load", "ghost", f"--baselines-dir={tmp_path}")
        assert result.returncode == 1
        assert "no baseline" in result.stderr


class TestList:
    def test_no_directory(self, run_script, tmp_path):
        result = run_script(SCRIPT, "list", str(tmp_path / "absent"))
        assert result.returncode == 0
        assert "No baselines directory found." in result.stdout

    def test_empty_directory(self, run_script, tmp_path):
        result = run_script(SCRIPT, "list", str(tmp_path))
        assert result.returncode == 0
        assert "No baselines found." in result.stdout

    def test_lists_saved_baselines(self, run_script, fixtures_dir, tmp_path):
        run_script(
            SCRIPT, "save", "main", str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        result = run_script(SCRIPT, "list", str(tmp_path))
        assert result.returncode == 0
        assert "main" in result.stdout
        assert "runner-abc" in result.stdout

    def test_malformed_baseline_reported_not_fatal(self, run_script, tmp_path):
        (tmp_path / "broken.json").write_text("{not json")
        result = run_script(SCRIPT, "list", str(tmp_path))
        assert result.returncode == 0
        assert "ERROR" in result.stdout


class TestCli:
    def test_no_command_exits_1(self, run_script):
        result = run_script(SCRIPT)
        assert result.returncode == 1
        assert "Usage" in result.stdout

    def test_unknown_command_exits_1(self, run_script):
        result = run_script(SCRIPT, "frobnicate")
        assert result.returncode == 1
        assert "Unknown command" in result.stdout
