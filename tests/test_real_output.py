"""Validate the scripts against REAL pytest-benchmark output.

Unlike the hand-written fixtures, ``tests/fixtures/real_results.json`` was
captured from an actual ``pytest bench/ --benchmark-only --benchmark-json`` run
(pytest-benchmark 5.x). It carries the full schema — ``commit_info``,
``datetime``, ``version``, per-benchmark ``options``/``extra_info``/``params``,
and ``stats`` keys like the string-valued ``outliers`` and the raw ``data``
array. This proves the scripts read only what they need and pass everything
else through untouched.
"""

import json

import pytest
from benchmark_baseline import sanitize_branch  # noqa: F401  (import sanity)
from benchmark_compare import NODE_MISMATCH_EXIT

REAL = "real_results.json"


@pytest.fixture
def real_path(fixtures_dir):
    return fixtures_dir / REAL


class TestRealOutputShape:
    def test_carries_full_schema(self, real_path):
        d = json.loads(real_path.read_text())
        assert {"machine_info", "commit_info", "benchmarks", "datetime", "version"} <= set(d)
        b = d["benchmarks"][0]
        assert {
            "group",
            "name",
            "fullname",
            "params",
            "param",
            "extra_info",
            "options",
            "stats",
        } <= set(b)
        # outliers is a "lo;hi" string in real output, not a number
        assert isinstance(b["stats"]["outliers"], str)


class TestCompareOnRealOutput:
    def test_real_vs_self_passes(self, run_script, real_path):
        result = run_script(
            "benchmark_compare.py", "compare-json", str(real_path), str(real_path), "--tolerance=5"
        )
        assert result.returncode == 0, result.stderr
        assert "✅ PASS" in result.stdout

    def test_injected_regression_fails(self, run_script, real_path, write_json):
        d = json.loads(real_path.read_text())
        # Double the mean of the first benchmark — a real 100% regression.
        d["benchmarks"][0]["stats"]["mean"] *= 2
        regressed = write_json("real_regressed.json", d)
        result = run_script(
            "benchmark_compare.py", "compare-json", str(real_path), str(regressed), "--tolerance=10"
        )
        assert result.returncode == 1
        assert "❌ FAIL" in result.stdout

    def test_hardware_fingerprint_not_hostname(self, run_script, real_path, write_json):
        # Real pytest-benchmark output carries a full machine_info.cpu block, so
        # the gate keys on hardware, not the hostname.
        # (a) Same CPU, different node name (the GitHub-hosted-runner case) still
        # compares — the ephemeral hostname must NOT block a valid comparison.
        same_hw = json.loads(real_path.read_text())
        same_hw["machine_info"]["node"] = same_hw["machine_info"]["node"] + "-different-host"
        same_hw_path = write_json("real_same_hw.json", same_hw)
        ok = run_script(
            "benchmark_compare.py",
            "compare-json",
            str(real_path),
            str(same_hw_path),
            "--tolerance=5",
        )
        assert ok.returncode == 0, ok.stderr

        # (b) Different CPU model (hostname unchanged) must hard-fail exit 3.
        other_hw = json.loads(real_path.read_text())
        other_hw["machine_info"]["cpu"]["brand_raw"] = "Some Other CPU @ 9.99GHz"
        other_hw_path = write_json("real_other_hw.json", other_hw)
        result = run_script(
            "benchmark_compare.py",
            "compare-json",
            str(real_path),
            str(other_hw_path),
            "--tolerance=5",
        )
        assert result.returncode == NODE_MISMATCH_EXIT
        assert "cross-machine comparison is invalid" in result.stderr


class TestSaveOnRealOutput:
    def test_save_strips_data_and_injects_info(self, run_script, real_path, tmp_path):
        result = run_script(
            "benchmark_baseline.py", "save", "main", str(real_path), f"--baselines-dir={tmp_path}"
        )
        assert result.returncode == 0, result.stderr
        saved = json.loads((tmp_path / "main.json").read_text())
        # Raw timings stripped from every benchmark...
        for bench in saved["benchmarks"]:
            assert "data" not in bench["stats"]
            # ...but the rest of the rich stats survive untouched.
            assert "mean" in bench["stats"]
            assert isinstance(bench["stats"]["outliers"], str)
        # Full provenance carried through, plus injected baseline_info.
        assert saved["version"] == json.loads(real_path.read_text())["version"]
        assert saved["baseline_info"]["node"] == saved["machine_info"]["node"]
