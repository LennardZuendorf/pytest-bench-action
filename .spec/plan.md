---
type: entrypoint
scope: implementation
covers: feature sequence, feature boundaries, release gate, spec-vs-implementation
children:
  - features/composite-action/plan.md
  - features/python-scripts/plan.md
updated: 2026-06-09
---

# pytest-bench-action — Implementation Plan

Single-goal repo: ship v1 of the action to the GitHub Marketplace. The core
ships and runs end-to-end (`action.yml` + `scripts/`); current focus is the v1
release gate — tests, docs, branding, and tagging. Current-only; no long-horizon
backlog (post-v1 ideas live in the issue tracker, not here).

**Parent specs:** [product.md](product.md), [tech.md](tech.md)

**Feature plans (unit-level detail lives here, not duplicated below):**

| Feature | Product | Plan | Status |
|---|---|---|---|
| [composite-action](features/composite-action/product.md) | action interface | [plan.md](features/composite-action/plan.md) | core done; branding open |
| [python-scripts](features/python-scripts/product.md) | baseline + compare engine | [plan.md](features/python-scripts/plan.md) | engine done; tests open |

---

## Feature Boundaries

| Feature | Owns | Does not own |
|---|---|---|
| **composite-action** | `action.yml`, input/output contract, step wiring, PR comment, baseline commit, artifact upload | baseline format, comparison algorithm |
| **python-scripts** | `scripts/benchmark_baseline.py`, `scripts/benchmark_compare.py`, baseline JSON format, `tests/` | action orchestration, PR comment rendering |

---

## Feature Sequence

Single end goal, so the numbered feature list **is** the roadmap. Gates are
binary: a feature starts only when its upstream is `DONE`.

| Order | Feature | Deliverable | Test | Status | Starts when |
|---:|---|---|---|---|---|
| 1 | python-scripts | `scripts/*.py` + `tests/` | `python -m pytest tests/` | ACTIVE — engine DONE, tests open | — |
| 2 | composite-action | `action.yml` end-to-end + `branding:` | real-repo run + Marketplace publish | ACTIVE — core DONE, branding open | python-scripts engine shipped |

Both features' core artifacts ship; each has one open unit (`python-scripts/2`
tests, `composite-action/2` branding). Cross-feature order is only here; feature
plans declare same-feature unit deps only.

---

## Spec vs Implementation

Honest inventory of v1 release gaps. Close via the cited feature unit or release task.

| Gap | Feature / unit | Notes |
|---|---|---|
| No `tests/` suite or fixtures | python-scripts/2 | Blocks the testing release gate |
| No `branding:` block in `action.yml` | composite-action/2 | Required to list on Marketplace |
| No `docs/example-workflow.yml` | release task | Reference workflow for adopters |
| No `CHANGELOG.md` | release task | v1 feature set + known limitations |
| README missing troubleshooting section | release task | First run, node mismatch, fork PRs, `[skip ci]` |
| No `v1.0.0` / `v1` tags or GitHub Release | release task | Marketplace listing + `@v1` pinning |

---

## Current Focus

Land `python-scripts/2` (test suite) and `composite-action/2` (branding block),
then the release tasks: example workflow, CHANGELOG, README troubleshooting, and
the `v1.0.0` / `v1` tags with a GitHub Release published to the Marketplace.
Next human gate: review the test suite and `action.yml` branding before tagging.
