---
type: feature-product
feature: composite-action
sibling: tech.md
parent: ../../product.md
updated: 2026-06-09
---

# composite-action — Product

**Parent:** [../../product.md](../../product.md)
**Architecture:** [tech.md](tech.md)
**Plan:** [plan.md](plan.md)

The composite action is the public interface of pytest-bench-action. It wires together checkout, Python setup, baseline loading, benchmark execution, comparison, baseline commit, PR commenting, and artifact upload into a single reusable workflow step.

---

## Scope

| | |
|---|---|
| **Owns** | `action.yml`, the input/output contract, event-conditional step wiring, PR comment rendering, baseline commit gating, artifact upload |
| **Does not own** | Baseline file format and comparison algorithm ([python-scripts](../python-scripts/product.md)), the caller's benchmark suite, runner provisioning |

---

## Requirements

### Requirement: Minimal adoption surface

The action SHALL run with only `github-token` and `benchmark-run-command` supplied; every other input MUST have a working default.

#### Scenario: Caller supplies only the two required inputs

- **Given** a workflow that sets `github-token` and `benchmark-run-command` and no other inputs
- **When** the action runs
- **Then** it executes end-to-end using defaults for `python-version`, `baselines-dir`, tolerances, and result file path

### Requirement: Event-aware behaviour

The action SHALL behave differently on `push` and `pull_request` events: baseline commits happen only on `push`, PR comments only on `pull_request`.

#### Scenario: Pull request run

- **Given** a `pull_request` event
- **When** the action completes
- **Then** it posts exactly one PR comment and MUST NOT commit a baseline

#### Scenario: Push run

- **Given** a `push` event where the baseline drifted beyond `update-tolerance`
- **When** the action completes
- **Then** it commits an updated baseline and MUST NOT post a PR comment

### Requirement: Single deduplicated PR comment

The action SHALL leave exactly one performance-results comment per PR, replacing any prior one it authored.

#### Scenario: Repeated runs on the same PR

- **Given** a PR that the action has already commented on
- **When** the action runs again
- **Then** it deletes its previous comment and posts a fresh one, so only one results comment remains

### Requirement: Regressions fail loudly

The action SHALL surface a regression as a failing step and MUST leave clean runs quiet.

#### Scenario: A benchmark exceeds tolerance

- **Given** a benchmark whose mean exceeds the baseline by more than the applicable tolerance
- **When** comparison runs
- **Then** the action step fails and the comparison table marks the offending benchmark as failed

---

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
