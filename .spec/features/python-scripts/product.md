---
type: feature-product
feature: python-scripts
sibling: tech.md
parent: ../../product.md
updated: 2026-06-09
---

# python-scripts — Product

**Parent:** [../../product.md](../../product.md)
**Architecture:** [tech.md](tech.md)
**Plan:** [plan.md](plan.md)

The Python scripts are the stdlib-only engine behind pytest-bench-action. They handle all baseline file I/O and benchmark comparison logic, keeping this work out of shell and away from GitHub Actions YAML. Both scripts are invoked by `action.yml` steps and communicate results via exit codes and stdout.

---

## Scope

| | |
|---|---|
| **Owns** | `scripts/benchmark_baseline.py`, `scripts/benchmark_compare.py`, the baseline JSON format, comparison algorithm, exit-code contract, and `tests/` fixtures for both |
| **Does not own** | Action orchestration and step wiring ([composite-action](../composite-action/product.md)), PR comment rendering, the caller's benchmark suite |

---

## Requirements

### Requirement: Stdlib-only execution

The scripts SHALL depend on the Python standard library only and MUST NOT import any third-party package.

#### Scenario: Run on a bare runner

- **Given** a runner with Python installed but no extra packages
- **When** either script is invoked
- **Then** it runs without `pip install` and without import errors

### Requirement: Baseline lifecycle commands

`benchmark_baseline.py` SHALL provide `save`, `load`, and `list` for per-branch baselines.

#### Scenario: Save strips raw samples

- **Given** a pytest-benchmark results file with raw `data` sample arrays
- **When** `save` runs
- **Then** the written baseline drops the `data` arrays and injects a `baseline_info` block with branch, node, and UTC timestamp

#### Scenario: Load of a missing baseline

- **Given** no baseline exists for the requested branch
- **When** `load` runs
- **Then** it exits non-zero so the caller can skip comparison

### Requirement: Tolerance-bounded comparison

`benchmark_compare.py` SHALL compare two benchmark files against a configurable tolerance and report per-benchmark status.

#### Scenario: Regression beyond tolerance

- **Given** a benchmark whose mean exceeds the baseline by more than `--tolerance`
- **When** comparison runs
- **Then** the benchmark is marked FAIL and the script exits 1

#### Scenario: New and missing benchmarks

- **Given** a results file that adds a benchmark and drops another relative to baseline
- **When** comparison runs
- **Then** the added benchmark is NEW (pass) and the dropped benchmark is MISSING (fail)

### Requirement: Exit codes are the API

The scripts SHALL communicate outcome through exit codes: `0` for pass / no-change, `1` for fail / update-needed / node mismatch.

#### Scenario: Node mismatch

- **Given** a baseline and results file with different `machine_info.node`
- **When** comparison runs
- **Then** the script prints a clear node-mismatch error and exits 1 without comparing numbers

---

## Test Fixtures Needed

For `tests/fixtures/`:

| File | Purpose |
|------|---------|
| `baseline.json` | Clean baseline with 3–5 benchmarks |
| `results_pass.json` | All benchmarks within tolerance |
| `results_regression.json` | One benchmark exceeds tolerance |
| `results_new_benchmark.json` | Adds a benchmark not in baseline |
| `results_missing_benchmark.json` | Drops a benchmark from baseline |
| `results_wrong_node.json` | Different `machine_info.node` than baseline |
