---
type: feature-product
scope: product
feature: self-test-ci
parent: ../../product.md
updated: 2026-06-11
---

# self-test-ci — Product

**Parent:** [product.md](../../product.md)

The action ships untested against real `pytest-benchmark` output: the unit tests
use hand-written JSON fixtures, and the action has never run end-to-end because it
was invalid YAML until 2026-06-10. This feature makes the project **dogfood
itself** — a real benchmark suite lives in the repo, and CI both runs the unit
tests and exercises the composite action against that suite. It closes the last
open v1 functionality criterion ("runs end-to-end on a real pytest-benchmark
suite") and guards every future change to the scripts and `action.yml`.

## Why this matters

- **Proves the format contract.** Real `pytest-benchmark` JSON carries far more
  than our fixtures model (`commit_info`, `datetime`, `version`, per-benchmark
  `options`/`extra_info`/`params`, and ~10 extra `stats` keys incl. `outliers`
  as a string). The scripts only read `machine_info.node`, `name`, `stats.mean`
  and strip `stats.data` — but that must be *demonstrated*, not assumed.
- **Satisfies a release gate.** v1 criteria require an end-to-end run; today
  there is no runnable suite, no workflow, and no proof.
- **Regression net for the action itself.** Any change to the scripts or step
  wiring is caught before merge.

## Requirements

- A minimal, deterministic `pytest-benchmark` suite in-repo, runnable with
  `pytest <dir> --benchmark-only --benchmark-json=...`, stdlib-only targets.
- A local end-to-end harness that runs the real benchmark, then drives the full
  script pipeline (extract node → compare → save baseline → list) exactly as
  `action.yml` does — runnable without GitHub, so it validates in-sandbox.
- A CI workflow that runs `python -m pytest tests/` on push and PR.
- A self-test workflow that runs the composite action (`uses: ./`) against the
  in-repo suite, on push and PR.
- Real-output fixtures captured from an actual `pytest-benchmark` run, replacing
  or augmenting the hand-written ones, so unit tests assert against ground truth.

## Non-Goals

- Multi-OS matrix (Linux-only for v1, consistent with the parent non-goals).
- Benchmarking the action's own scripts for performance (the suite exists to
  exercise the pipeline, not to track the action's speed).
- Publishing the self-test results anywhere external.

## Acceptance

- `pytest bench/ --benchmark-only --benchmark-json=out.json` produces valid JSON.
- The local harness runs the full pipeline against that JSON and exits 0 on a
  clean run, non-zero on an injected regression.
- Both scripts pass their unit tests against a real-output fixture.
- `.github/workflows/ci.yml` and `.github/workflows/benchmark.yml` are valid and
  model the intended jobs.
