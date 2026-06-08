---
type: feature-product
scope: product
feature: python-scripts
parent: ../../product.md
updated: 2026-06-06
---

# python-scripts — Product

**Parent:** [product.md](../../product.md)

The Python scripts are the stdlib-only engine behind pytest-bench-action. They handle all baseline file I/O and benchmark comparison logic, keeping this work out of shell and away from GitHub Actions YAML. Both scripts are invoked by `action.yml` steps and communicate results via exit codes and stdout.

## Requirements

- **No third-party dependencies** — Python 3.x stdlib only
- `benchmark_baseline.py`: save, load, list baselines from/to JSON files
- `benchmark_compare.py`: compare two benchmark JSON files with configurable tolerance
- Clear, human-readable output suitable for capture into PR comment body
- Exit codes as the primary API: 0 = pass/no-change, 1 = fail/update-needed
- Graceful handling of missing files, malformed JSON, and mismatched nodes

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
