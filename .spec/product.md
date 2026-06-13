---
type: entrypoint
scope: product
children: []
updated: 2026-06-09
---

# pytest-bench-action — Product

A reusable GitHub Action that automates performance regression detection for Python projects. It runs pytest-benchmark on every push and pull request, stores per-branch baselines in the repository, and posts a formatted comparison table as a PR comment — so slow-downs are caught before they merge.

**One-liner:** Drop-in GitHub Action that catches Python performance regressions before they reach main.

---

## Story

Python maintainers who care about performance have no low-friction way to catch regressions in CI. Standing up a benchmarking service is overkill for a single library, and ad-hoc local timing doesn't gate merges. pytest-bench-action turns an existing pytest-benchmark suite into a merge gate: baselines live in the repo, comparisons run on every push and PR, and a regression fails the check with a readable table — no external infrastructure to own.

---

## Requirements

At a project level, pytest-bench-action must:

1. **Adopt with one action block.** Two required inputs (`github-token`, `benchmark-run-command`); everything else defaults.
2. **Compare only like-for-like.** Baselines are tied to runner node identity; cross-machine comparison is blocked, never silently wrong.
3. **Keep state in the repo.** Baselines are committed alongside code — versioned, diffable, no external store.
4. **Fail loudly, pass quietly.** Regressions surface as a failing step with a table; clean runs leave one PR comment and no noise.
5. **Run anywhere without setup.** Action scripts use Python stdlib only — no `pip install` on the runner.

---

## Design Principles

1. **Zero friction to adopt.** One action block, one required command. Works with any pytest-benchmark suite — no config files, no sidecar services, no external storage.
2. **No false positives from environment drift.** Baselines are tied to machine node identity. Cross-machine comparison is blocked by design.
3. **Baselines live in the repo.** Committed alongside code, versioned, diffable. No external state to lose or sync.
4. **Fail loudly, pass quietly.** Regressions surface as a failing step with a clear table. A clean run leaves a single PR comment and no noise.
5. **Stdlib-only scripts.** No `pip install` in the action. Python 3.x stdlib is the only dependency — works on any runner image without setup.

---

## Target User

Python library or application maintainers running pytest who want continuous performance tracking without standing up a dedicated benchmarking service. They're comfortable with GitHub Actions YAML but don't want to own benchmark infrastructure. Primary persona: a solo or small-team open-source maintainer.

---

## Features

| Feature | Covers |
|---|---|
| **[composite-action](features/composite-action/product.md)** | The `action.yml` interface — inputs/outputs, event-aware steps, PR comment, baseline commit, threshold map |
| **[python-scripts](features/python-scripts/product.md)** | Stdlib-only baseline management and the comparison engine, plus their test suite |

---

## Implementation Phases

| Phase | Goal | Exit Criteria |
|---|---|---|
| **1: Core action** | Baseline save/load, comparison, PR comment, baseline commit | Manual end-to-end test passes on a real repo |
| **2: Release hardening** | Tests, example workflow, CHANGELOG, v1 tag, Marketplace listing | CI green, README complete, Marketplace live |

Release-gate sequencing and status live in [plan.md](plan.md).

---

## Product Decisions

1. **Baselines committed to the repo.** Avoids external state and makes baselines auditable via git blame/log. Trade-off: slight repo size growth (mitigated by stripping raw `data` arrays).
2. **Node check is a hard failure.** Silent cross-machine comparison would be worse than no comparison. Users are expected to pin runner types.
3. **Single PR comment, deduplicated.** Previous bot comments are deleted before posting to keep PR threads clean. One comment per run, always fresh.
4. **`[skip ci]` on baseline commits.** Prevents infinite CI loops when the action commits an updated baseline. Non-negotiable.
5. **`update-tolerance` separate from `cross-branch-tolerance`.** Baseline updates only trigger when performance genuinely shifts (default 5%), not on every noisy run.

---

## Non-Goals

- Cross-machine baseline comparison (explicitly blocked)
- Support for non-pytest benchmark runners
- External storage or third-party benchmark services
- Historical trending dashboards or charts
- Slack / webhook notifications

---

## Known Limitations (v1)

- **Linux-only validation.** Tested on `ubuntu-latest` only; Windows/macOS runners untested.
- **Single benchmark file.** Only one `benchmark-results-file` per run; multi-file not in scope.
- **No historical trending.** Baselines track the most recent run only.
- **Fork PRs skip baseline commit.** By design — no write access from forks. Noted in README.
- **Default Python 3.14** may not be available on all runner images; users should pin to a stable version.
