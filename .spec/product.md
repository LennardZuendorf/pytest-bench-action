---
type: entrypoint
scope: product
children:
  - product-release.md
updated: 2026-06-06
---

# pytest-bench-action — Product

A reusable GitHub Action that automates performance regression detection for Python projects. It runs pytest-benchmark on every push and pull request, stores per-branch baselines in the repository, and posts a formatted comparison table as a PR comment — so slow-downs are caught before they merge.

**One-liner:** Drop-in GitHub Action that catches Python performance regressions before they reach main.

---

## Design Principles

1. **Zero friction to adopt.** One action block, one required input. Works out of the box with any pytest-benchmark suite — no config files, no sidecar services, no external storage.
2. **No false positives from environment drift.** Baselines are tied to machine node identity. Cross-machine comparison is blocked by design, not silently wrong.
3. **Baselines live in the repo.** Committed alongside code, versioned, diffable. No external state to lose or sync.
4. **Fail loudly, pass quietly.** Regressions surface as a failing step with a clear table. A clean run leaves a single PR comment and no noise.
5. **Stdlib-only scripts.** No `pip install` in the action. Python 3.x stdlib is the only dependency — works on any runner image without setup.

## Target User

Python library or application maintainers running pytest who want continuous performance tracking without standing up a dedicated benchmarking service. They're comfortable with GitHub Actions YAML but don't want to own benchmark infrastructure. Primary persona: a solo or small-team open-source maintainer.

## What We Build

| Feature | Priority | Details in |
|---------|----------|------------|
| **Composite action definition** (`action.yml`) | P0 | [tech.md](tech.md) |
| **Baseline management** (`benchmark_baseline.py`) | P0 | [tech.md](tech.md) |
| **Comparison engine** (`benchmark_compare.py`) | P0 | [tech.md](tech.md) |
| **PR comment with results table** | P0 | [tech.md](tech.md) |
| **Per-test threshold map** | P1 | [tech.md](tech.md) |
| **Integration test suite** | P0 (release gate) | [product-release.md](product-release.md) |
| **Example workflow** | P1 | [product-release.md](product-release.md) |

## Implementation Phases

| Phase | Goal | Exit Criteria |
|-------|------|---------------|
| **1: Core action** | Baseline save/load, comparison, PR comment, baseline commit | Manual end-to-end test passes on a real repo |
| **2: Release hardening** | Tests, example workflow, CHANGELOG, v1 tag | CI green, README complete, GitHub release published |

## Non-Goals

- Cross-machine baseline comparison (explicitly blocked)
- Support for non-pytest benchmark runners
- External storage or third-party benchmark services
- Historical trending dashboards or charts
- Slack / webhook notifications (out of scope for v1)

## Product Decisions

1. **Baselines committed to the repo.** Avoids external state and makes baselines auditable via git blame/log. Trade-off: slight repo size growth (mitigated by stripping raw `data` arrays).
2. **Node check is a hard failure.** Silent cross-machine comparison would be worse than no comparison. Users are expected to pin runner types.
3. **Single PR comment, deduplicated.** Previous bot comments are deleted before posting to keep PR threads clean. One comment per run, always fresh.
4. **`[skip ci]` on baseline commits.** Prevents infinite CI loops when the action commits an updated baseline. This is non-negotiable.
5. **`update-tolerance` separate from `cross-branch-tolerance`.** Baseline updates only trigger when performance genuinely shifts (default 5%), not on every noisy run.

## Branch Documents

| Document | Covers |
|----------|--------|
| **[product-release.md](product-release.md)** | Release readiness checklist: tests, docs, example, versioning |
