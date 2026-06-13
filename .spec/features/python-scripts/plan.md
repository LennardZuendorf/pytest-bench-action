---
type: feature-plan
feature: python-scripts
sibling: tech.md
parent: ../../plan.md
updated: 2026-06-09
---

# python-scripts — Implementation Plan

The stdlib-only baseline + comparison engine. The engine ships in `scripts/`; the
open slice is an automated test suite that locks the exit-code contract. This
feature is a closed, deliverable, testable box.

**Parent:** [../../plan.md](../../plan.md)
**Requirements:** [product.md](product.md)
**Architecture:** [tech.md](tech.md)

**Feature gate:** No upstream feature gate — the engine is independent of `composite-action`; the action consumes it as a shipped artifact (`scripts/*.py`).

---

## Requirements Trace

| ID | Requirement | Units |
|---|---|---|
| R1 | [Stdlib-only execution](product.md#requirement-stdlib-only-execution) | python-scripts/1, python-scripts/2 |
| R2 | [Baseline lifecycle commands](product.md#requirement-baseline-lifecycle-commands) | python-scripts/1, python-scripts/2 |
| R3 | [Tolerance-bounded comparison](product.md#requirement-tolerance-bounded-comparison) | python-scripts/1, python-scripts/2 |
| R4 | [Exit codes are the API](product.md#requirement-exit-codes-are-the-api) | python-scripts/1, python-scripts/2 |

---

### python-scripts/1 — Baseline + comparison engine

**Goal:** Ship the stdlib-only `save`/`load`/`list` baseline tooling and the tolerance-bounded comparison engine.

**Requirements:** R1, R2, R3, R4

**Dependencies:** —

**Files:**

```
scripts/benchmark_baseline.py     # save | load | list (delivered)
scripts/benchmark_compare.py      # compare-json (delivered)
```

**Verification:** `python scripts/benchmark_compare.py compare-json baseline.json results.json --tolerance=20` exits 0/1 as expected; `benchmark_baseline.py save|load|list` round-trips a real pytest-benchmark JSON. DONE — shipped in `scripts/`.

---

### python-scripts/2 — Test suite + fixtures

**Goal:** Lock the exit-code contract with realistic fixtures so behaviour can't silently regress.

**Requirements:** R1, R2, R3, R4

**Dependencies:** python-scripts/1

**Files:**

```
tests/fixtures/baseline.json
tests/fixtures/results_pass.json
tests/fixtures/results_regression.json
tests/fixtures/results_new_benchmark.json
tests/fixtures/results_missing_benchmark.json
tests/fixtures/results_wrong_node.json
tests/test_benchmark_baseline.py     # save, load, list, sanitization, metadata
tests/test_benchmark_compare.py      # pass/fail/new/missing/node-mismatch/tolerance/time-format
```

**Test scenarios:**

- Save strips `data` arrays and injects `baseline_info`
- Load of a missing baseline exits non-zero
- Comparison: pass within tolerance, fail beyond tolerance, NEW, MISSING, node mismatch
- Time formatting across µs / ms / s ranges

**Verification:** `python -m pytest tests/` exits 0.

---

## Progress

| Unit | Status |
|---|---|
| python-scripts/1 | DONE |
| python-scripts/2 | NOT STARTED |
