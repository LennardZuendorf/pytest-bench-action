"""Tests for scripts/benchmark_compare.py (compare-json command)."""

import pytest

from benchmark_compare import format_time
from conftest import make_results

SCRIPT = "benchmark_compare.py"


class TestPassFail:
    def test_within_tolerance_passes(self, run_script, fixtures_dir):
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(fixtures_dir / "results.json"),
            "--tolerance=20",
        )
        assert result.returncode == 0
        assert "✅ PASS" in result.stdout
        assert "All benchmarks within 20.0% tolerance." in result.stdout

    def test_regression_fails(self, run_script, fixtures_dir):
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(fixtures_dir / "results_regression.json"),
            "--tolerance=20",
        )
        assert result.returncode == 1
        assert "❌ FAIL" in result.stdout
        assert "+50.0%" in result.stdout
        assert "exceeded 20.0% tolerance" in result.stdout

    def test_improvement_passes(self, run_script, write_json):
        baseline = write_json("baseline.json", make_results(benchmarks={"test_foo": 0.001}))
        current = write_json("current.json", make_results(benchmarks={"test_foo": 0.0005}))
        result = run_script(SCRIPT, "compare-json", str(baseline), str(current), "--tolerance=20")
        assert result.returncode == 0
        assert "-50.0%" in result.stdout

    def test_change_equal_to_tolerance_passes(self, run_script, write_json):
        # change_pct > tolerance fails; exactly equal must pass (100 → 120 at 20%)
        baseline = write_json("baseline.json", make_results(benchmarks={"test_foo": 100.0}))
        current = write_json("current.json", make_results(benchmarks={"test_foo": 120.0}))
        result = run_script(SCRIPT, "compare-json", str(baseline), str(current), "--tolerance=20")
        assert result.returncode == 0
        assert "+20.0%" in result.stdout

    def test_zero_baseline_mean_passes_with_zero_change(self, run_script, write_json):
        baseline = write_json("baseline.json", make_results(benchmarks={"test_foo": 0.0}))
        current = write_json("current.json", make_results(benchmarks={"test_foo": 0.5}))
        result = run_script(SCRIPT, "compare-json", str(baseline), str(current), "--tolerance=20")
        assert result.returncode == 0
        assert "+0.0%" in result.stdout

    def test_default_tolerance_is_20(self, run_script, fixtures_dir):
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(fixtures_dir / "results_regression.json"),
        )
        assert result.returncode == 1
        assert "20.0% tolerance" in result.stdout


class TestNewAndMissing:
    def test_new_benchmark_passes(self, run_script, fixtures_dir):
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(fixtures_dir / "results_new_benchmark.json"),
            "--tolerance=20",
        )
        assert result.returncode == 0
        assert "⚪ NEW" in result.stdout
        assert "test_new_endpoint" in result.stdout

    def test_missing_benchmark_fails(self, run_script, fixtures_dir, write_json):
        current = write_json("current.json", make_results(benchmarks={"test_foo": 0.001}))
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(current),
            "--tolerance=20",
        )
        assert result.returncode == 1
        assert "❌ MISSING" in result.stdout
        assert "test_bar" in result.stdout


class TestNodeCheck:
    def test_node_mismatch_fails(self, run_script, fixtures_dir, write_json):
        current = write_json(
            "current.json", make_results(node="runner-xyz", benchmarks={"test_foo": 0.001, "test_bar": 0.0005})
        )
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(current),
            "--tolerance=20",
        )
        assert result.returncode == 1
        assert "cross-machine comparison is invalid" in result.stderr
        assert "runner-abc" in result.stderr
        assert "runner-xyz" in result.stderr

    def test_missing_node_on_one_side_proceeds(self, run_script, fixtures_dir, write_json):
        current = write_json(
            "current.json", make_results(node="", benchmarks={"test_foo": 0.001, "test_bar": 0.0005})
        )
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(current),
            "--tolerance=20",
        )
        assert result.returncode == 0


class TestErrorHandling:
    def test_missing_baseline_file_exits_1(self, run_script, fixtures_dir, tmp_path):
        result = run_script(
            SCRIPT, "compare-json", str(tmp_path / "nope.json"), str(fixtures_dir / "results.json")
        )
        assert result.returncode == 1
        assert "cannot load baseline file" in result.stderr

    def test_malformed_current_file_exits_1(self, run_script, fixtures_dir, tmp_path):
        bad = tmp_path / "bad.json"
        bad.write_text("{not json")
        result = run_script(SCRIPT, "compare-json", str(fixtures_dir / "baseline.json"), str(bad))
        assert result.returncode == 1
        assert "cannot load current results file" in result.stderr

    def test_invalid_tolerance_exits_1(self, run_script, fixtures_dir):
        result = run_script(
            SCRIPT, "compare-json",
            str(fixtures_dir / "baseline.json"), str(fixtures_dir / "results.json"),
            "--tolerance=lots",
        )
        assert result.returncode == 1
        assert "invalid tolerance" in result.stderr

    def test_no_command_exits_1(self, run_script):
        result = run_script(SCRIPT)
        assert result.returncode == 1
        assert "Usage" in result.stdout

    def test_unknown_command_exits_1(self, run_script):
        result = run_script(SCRIPT, "diff")
        assert result.returncode == 1
        assert "Unknown command" in result.stdout

    def test_missing_args_exits_1(self, run_script):
        result = run_script(SCRIPT, "compare-json", "only-one.json")
        assert result.returncode == 1


class TestFormatTime:
    @pytest.mark.parametrize(
        ("seconds", "expected"),
        [
            (0.0000005, "0.5µs"),
            (0.0005, "500.0µs"),
            (0.001, "1.00ms"),
            (0.04567, "45.67ms"),
            (0.9999, "999.90ms"),
            (1.0, "1.0000s"),
            (1.2345, "1.2345s"),
        ],
    )
    def test_ranges(self, seconds, expected):
        assert format_time(seconds) == expected
