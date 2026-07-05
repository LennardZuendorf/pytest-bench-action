---
type: feature-tech
scope: technical
feature: self-test-ci
parent: ../../tech.md
updated: 2026-06-11
---

# self-test-ci — Technical Design

**Parent:** [tech.md](../../tech.md)

## Layout

```
bench/
  test_sample_benchmark.py     # real pytest-benchmark suite, stdlib targets only
tests/
  fixtures/
    real_results.json          # captured from an actual pytest-benchmark run
  test_real_output.py          # asserts scripts handle real-output shape
scripts/
  selftest.sh                  # local end-to-end harness (mirrors action.yml steps)
.github/workflows/
  ci.yml                       # unit tests on push/PR
  benchmark.yml                # dogfood: uses: ./ against bench/
```

## Real pytest-benchmark JSON (ground truth, v3.x–5.x stable)

Top-level: `machine_info`, `commit_info`, `benchmarks[]`, `datetime`, `version`.
`machine_info.node` = `platform.node()` (hostname). Each `benchmarks[]` entry:
`group, name, fullname, params, param, extra_info, options, stats`. `stats` keys:
`min, max, mean, stddev, rounds, median, iqr, q1, q3, iqr_outliers,
stddev_outliers, outliers (string "lo;hi"), ld15iqr, hd15iqr, ops, total,
iterations, data (raw timings, stripped on baseline save)`.

The scripts depend only on `machine_info.node`, `benchmarks[].name`,
`benchmarks[].stats.mean`, and pop `stats.data`. Everything else is carried
through untouched on save. The real-output fixture exists to prove this.

## Sample suite (`bench/test_sample_benchmark.py`)

Targets must be:
- **stdlib-only** (no third-party imports), so the suite runs on any runner.
- **deterministic & fast** — pure CPU work (e.g. sum over a range, string join,
  list sort) with small inputs so CI stays quick and node-locked comparisons are
  meaningful run-to-run on the same runner.
- Named distinctly (`test_sum_range`, `test_sort_list`, `test_str_join`) so the
  comparison table and threshold-map substring matching can be exercised.

## Local harness (`scripts/selftest.sh`)

POSIX shell, mirrors the relevant `action.yml` steps so the pipeline is validated
without GitHub. Steps:
1. Run `pytest bench/ --benchmark-only --benchmark-json=$TMP/results.json -q`.
2. Extract node via the same `python -c` snippet `action.yml` uses.
3. `benchmark_compare.py compare-json` results vs itself → must exit 0 (sanity:
   zero drift passes).
4. `benchmark_baseline.py save` → assert baseline written, `stats.data` stripped,
   `baseline_info` injected.
5. `benchmark_baseline.py list` → assert the saved branch appears.
6. Inject a synthetic regression (scale one mean by 2×) and re-compare with a low
   tolerance → must exit 1. Proves the failure path on real-shaped data.

Exit 0 only if every assertion holds. Runs under `set -eu`; uses a temp dir so it
leaves no artifacts in the working tree.

## CI workflows

### `ci.yml`
- Triggers: `push`, `pull_request`.
- Job `unit-tests`: checkout → setup-python `3.14` → `pip install pytest
  pytest-benchmark` → `python -m pytest tests/ -v` → run `scripts/selftest.sh`.
- No special permissions needed (read-only).

### `benchmark.yml` (dogfood)
- Triggers: `push` to default branch, `pull_request`.
- `permissions: contents: write, pull-requests: write` (the action commits
  baselines on push and comments on PRs).
- Single step `uses: ./` with:
  - `setup-command: pip install pytest pytest-benchmark`
  - `benchmark-run-command: pytest bench/ --benchmark-only
    --benchmark-json=benchmark-results.json -q`
  - `github-token: ${{ secrets.GITHUB_TOKEN }}`
  - a `threshold-map` exercising substring matching against the sample tests.
- This is the in-repo proof that `action.yml` runs end-to-end. Note: on
  GitHub-hosted runners the node hostname changes per job, so cross-run baseline
  comparison is best-effort here — the workflow's value is exercising the full
  step wiring, not stable numbers (documented limitation in parent product.md).

## Validation strategy (in-sandbox)

GitHub Actions can't run here, so workflows are validated by: (a) YAML parse,
(b) `scripts/selftest.sh` reproducing the action's pipeline against real output,
(c) the new unit test against the captured real-output fixture. The workflows
themselves are reviewed by a subagent for action-syntax correctness.

## Open decisions

- Directory name `bench/` vs `benchmarks/` — chose `bench/` to avoid colliding
  with the `tests/` tree and to keep the caller example (`tests/benchmarks`)
  distinct from our own suite. (Decided 2026-06-11.)
- Keep hand-written fixtures? Yes — they're minimal and make failure-mode tests
  (missing/wrong-node) easy to construct. The real-output fixture augments them.
