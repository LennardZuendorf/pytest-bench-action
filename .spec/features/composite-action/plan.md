---
type: feature-plan
feature: composite-action
sibling: tech.md
parent: ../../plan.md
updated: 2026-06-09
---

# composite-action — Implementation Plan

The public `action.yml` interface. Orchestration ships and runs end-to-end; the
open slice is the Marketplace `branding:` block required to list the action. This
feature is a closed, deliverable, testable box.

**Parent:** [../../plan.md](../../plan.md)
**Requirements:** [product.md](product.md)
**Architecture:** [tech.md](tech.md)

**Feature gate:** Consumes `python-scripts` as a shipped artifact (`scripts/*.py`); no mid-arc unit coupling. See root [plan.md](../../plan.md) Feature Sequence.

---

## Requirements Trace

| ID | Requirement | Units |
|---|---|---|
| R1 | [Minimal adoption surface](product.md#requirement-minimal-adoption-surface) | composite-action/1 |
| R2 | [Event-aware behaviour](product.md#requirement-event-aware-behaviour) | composite-action/1 |
| R3 | [Single deduplicated PR comment](product.md#requirement-single-deduplicated-pr-comment) | composite-action/1 |
| R4 | [Regressions fail loudly](product.md#requirement-regressions-fail-loudly) | composite-action/1 |

---

### composite-action/1 — Orchestration in action.yml

**Goal:** Ship the full composite action: input/output contract, event-conditional steps, dual baseline comparison, deduplicated PR comment, gated baseline commit, artifact upload.

**Requirements:** R1, R2, R3, R4

**Dependencies:** —

**Files:**

```
action.yml     # composite action, all orchestration (delivered)
```

**Verification:** Action runs end-to-end on a real pytest-benchmark suite; PR run posts one deduplicated comment and skips commit; push run commits a `[skip ci]` baseline when drift exceeds `update-tolerance`. DONE — shipped in `action.yml`.

---

### composite-action/2 — Marketplace branding block

**Goal:** Add the `branding:` block (`icon: activity`, `color: purple`) so the action is listable on the GitHub Marketplace.

**Requirements:** —

**Dependencies:** composite-action/1

**Files:**

```
action.yml     # add top-level branding: block
```

**Verification:** `action.yml` contains a valid `branding:` block; Marketplace publish form accepts the action.

---

## Progress

| Unit | Status |
|---|---|
| composite-action/1 | DONE |
| composite-action/2 | NOT STARTED |
