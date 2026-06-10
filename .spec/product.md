---
type: entrypoint
scope: product
children: []
updated: 2026-06-10
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
| **Composite action definition** (`action.yml`) | P0 | [features/composite-action/](features/composite-action/product.md) |
| **Baseline management** (`benchmark_baseline.py`) | P0 | [features/python-scripts/](features/python-scripts/product.md) |
| **Comparison engine** (`benchmark_compare.py`) | P0 | [features/python-scripts/](features/python-scripts/product.md) |
| **PR comment with results table** | P0 | [features/composite-action/](features/composite-action/product.md) |
| **Per-test threshold map** | P1 | [features/composite-action/](features/composite-action/product.md) |
| **Integration test suite** | P0 (release gate) | See Release Criteria below |
| **Example workflow** | P1 | See Release Criteria below |

## Implementation Phases

| Phase | Goal | Exit Criteria |
|-------|------|---------------|
| **1: Core action** | Baseline save/load, comparison, PR comment, baseline commit | Manual end-to-end test passes on a real repo |
| **2: Release hardening** | Tests, example workflow, CHANGELOG, v1 tag, Marketplace listing | CI green, README complete, Marketplace live |

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

---

## v1 Release Criteria

A release is ready when ALL of the following are true.

### Functionality
- [x] Composite action runs end-to-end on a real pytest-benchmark suite
- [x] Baseline save/load/list works correctly
- [x] Comparison detects regressions and new/missing benchmarks
- [x] PR comment posts and deduplicates correctly
- [x] Baseline commits include `[skip ci]`
- [x] Node mismatch fails with a clear error message
- [x] Threshold map evaluated per-test in PR comment

### Testing
- [x] `tests/` directory with realistic JSON fixtures exists
- [x] `tests/test_benchmark_baseline.py` covers save, load, list, sanitization
- [x] `tests/test_benchmark_compare.py` covers pass/fail/new/missing/node-mismatch/tolerance
- [x] All tests pass: `python -m pytest tests/` (43 tests, 2026-06-10)

### Documentation
- [x] `README.md` with inputs/outputs table and basic usage
- [x] `README.md` troubleshooting section (first run, node mismatch, fork PRs, `[skip ci]`)
- [x] `docs/example-workflow.yml` — complete reference workflow
- [x] `CHANGELOG.md` — v1 feature set documented

### Release Infrastructure
- [ ] `branding:` block added to `action.yml` (`icon: activity`, `color: purple`) — required for Marketplace listing
- [ ] `v1.0.0` git tag created and pushed
- [ ] `v1` floating tag pointing to same commit — enables `@v1` pinning convention
- [ ] GitHub Release drafted with notes drawn from `CHANGELOG.md`
- [ ] "Publish this Action to the GitHub Marketplace" checkbox ticked on release form; category set to CI / Testing
- [ ] Marketplace listing verified live
- [ ] Action reachable via `uses: lennardzuendorf/pytest-bench-action@v1`

---

## Known Limitations (v1)

- **Linux-only validation.** Tested on `ubuntu-latest` only; Windows/macOS runners untested.
- **Single benchmark file.** Only one `benchmark-results-file` per run; multi-file not in scope.
- **No historical trending.** Baselines track the most recent run only.
- **Fork PRs skip baseline commit.** By design — no write access from forks. Noted in README.
- **Default Python 3.14** may not be available on all runner images; users should pin to a stable version.

## Post-v1 Candidates

- Windows / macOS runner support
- Multiple benchmark result files in a single run
- Historical baseline storage (keep N past baselines)
- Trend chart in PR comment (ASCII or linked image)
- Slack / webhook notification on regression
- Self-test CI workflow (dogfooding)
- Configurable comment header string (to support multiple action instances per repo)
