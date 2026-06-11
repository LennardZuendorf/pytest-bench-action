---
type: feature-product
scope: product
feature: python-scripts
parent: ../../product.md
updated: 2026-06-11
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

## Test Fixtures (as built)

`tests/fixtures/` holds a small set of committed fixtures; the rarer cases are
constructed in-test via the `write_json` / `make_results` helpers in
`tests/conftest.py` (keeps the fixture set minimal and the edge cases explicit).

| File / source | Purpose |
|---------------|---------|
| `baseline.json` | Clean baseline (committed) |
| `results.json` | All benchmarks within tolerance (committed) |
| `results_regression.json` | One benchmark exceeds tolerance (committed) |
| `results_new_benchmark.json` | Adds a benchmark not in baseline (committed) |
| `real_results.json` | **Real** pytest-benchmark 5.x output, full schema (committed) |
| missing-benchmark case | built in-test (drop a benchmark) |
| wrong-node case | built in-test (`make_results(node=...)`) |

Real-output validation and the dogfood harness live in the
[self-test-ci](../self-test-ci/product.md) feature.
