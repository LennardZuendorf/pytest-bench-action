---
type: feature-product
scope: product
feature: composite-action
parent: ../../product.md
updated: 2026-06-06
---

# composite-action — Product

**Parent:** [product.md](../../product.md)

The composite action is the public interface of pytest-bench-action. It wires together checkout, Python setup, baseline loading, benchmark execution, comparison, baseline commit, PR commenting, and artifact upload into a single reusable workflow step.

## Requirements

- Accepts 10 inputs (2 required, 8 optional with sensible defaults)
- Exposes 3 outputs: `regression-detected`, `baseline-updated`, `node`
- Works on `push` and `pull_request` events with different behaviour per event type
- Requires only `github-token` and `benchmark-run-command` to get started
- Posts exactly one PR comment per run (deduplicates previous bot comment)
- Commits updated baselines only on `push` events, never on `pull_request`
- Surfaces regressions as a failing step; clean runs pass silently

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `python-version` | No | `"3.14"` | Python version for `setup-python` |
| `benchmark-run-command` | **Yes** | — | Full pytest-benchmark shell command |
| `setup-command` | No | `""` | Dependency install (e.g. `pip install -e .`) |
| `pre-benchmark-command` | No | `""` | Warm-up step before benchmarks |
| `benchmark-results-file` | No | `benchmark-results.json` | Output path for pytest-benchmark JSON |
| `cross-branch-tolerance` | No | `20` | % increase allowed vs main baseline |
| `update-tolerance` | No | `5` | % drift to trigger baseline update |
| `baselines-dir` | No | `.benchmarks/baselines` | Directory for stored baselines |
| `github-token` | **Yes** | — | Token with `contents:write` + `pull-requests:write` |
| `threshold-map` | No | `""` | JSON map of `test-name-substring → max-seconds` |

## Outputs

| Output | Values | Description |
|--------|--------|-------------|
| `regression-detected` | `"true"` / `"false"` | Whether any benchmark exceeded tolerance |
| `baseline-updated` | `"true"` / `"false"` | Whether a baseline commit was made |
| `node` | hostname string | Runner node from `machine_info.node` |
