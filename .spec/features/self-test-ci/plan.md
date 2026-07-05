---
type: feature-plan
scope: implementation
feature: self-test-ci
parent: ../../plan.md
updated: 2026-06-11
---

# self-test-ci — Implementation Plan

**Parent:** [../../plan.md](../../plan.md) · **Specs:** [product.md](product.md), [tech.md](tech.md)

Validatable steps, each with its own checkpoint. Maps to master-plan Phases A–B.

## Phase A — Dogfood harness + real-output validation

- [x] **A2** `bench/test_sample_benchmark.py` — 3 deterministic stdlib benchmarks.
  - Validate: `pytest bench/ --benchmark-only --benchmark-json=/tmp/r.json -q`
    exits 0 and writes parseable JSON with ≥3 benchmarks and `machine_info.node`.
- [x] **A3** Capture `tests/fixtures/real_results.json` from that run (trimmed to
  a stable subset; keep all key groups incl. `options`, `extra_info`, string
  `outliers`, `stats.data`).
  - Validate: `python -c "import json; json.load(...)"`, assert key groups present.
- [x] **A4** `tests/test_real_output.py` — compare real vs real (pass), real vs
  2×-scaled (fail), save strips `data`, node read correct.
  - Validate: `python -m pytest tests/test_real_output.py -v` green.
- [x] **A5** `scripts/selftest.sh` — full pipeline harness (see tech.md).
  - Validate: `bash scripts/selftest.sh` exits 0; flip an assertion to confirm it
    can fail; leaves no artifacts (`git status` clean after).
- [x] **A-checkpoint** full suite green, commit.

## Phase B — CI workflows

- [x] **B1** `.github/workflows/ci.yml` — unit tests + selftest on push/PR.
- [x] **B2** `.github/workflows/benchmark.yml` — dogfood `uses: ./`.
  - Validate B1/B2: YAML parse; subagent review for Actions-syntax correctness
    (job/permission/trigger wiring, `uses: ./`, token, step inputs match
    `action.yml`).
- [x] **B-checkpoint** commit.

## Done when

- [x] `bash scripts/selftest.sh` exits 0 against real output.
- [x] `python -m pytest tests/` green (incl. real-output test).
- [x] Both workflows valid and reviewed.
- [x] Feature compounded into root specs (Phase D, 2026-06-11).

**FEATURE COMPLETE 2026-06-11.** Archives to `.spec/archive/self-test-ci/` at v1
wrap-up (see root plan, "Spec Lifecycle").
