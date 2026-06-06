---
type: branch
scope: product
parent: product.md
covers: release readiness, v1 criteria, user-facing documentation completeness, GitHub Marketplace publication
updated: 2026-06-06
---

# pytest-bench-action — Release Readiness

**Parent:** [product.md](product.md)

This document defines what "release ready" means for pytest-bench-action v1, and tracks the open gaps.

---

## v1 Release Criteria

A release is ready when ALL of the following are true:

### Functionality
- [x] Composite action runs end-to-end on a real pytest-benchmark suite
- [x] Baseline save/load/list works correctly
- [x] Comparison detects regressions and new/missing benchmarks
- [x] PR comment posts and deduplicates correctly
- [x] Baseline commits include `[skip ci]`
- [x] Node mismatch fails with a clear error message
- [x] Threshold map evaluated per-test in PR comment

### Testing
- [ ] `tests/` directory with realistic JSON fixtures exists
- [ ] `tests/test_benchmark_baseline.py` covers save, load, list, sanitization
- [ ] `tests/test_benchmark_compare.py` covers pass/fail/new/missing/node-mismatch/tolerance
- [ ] All tests pass: `python -m pytest tests/`

### Documentation
- [x] `README.md` with inputs/outputs table and basic usage
- [ ] `README.md` troubleshooting section (first run, node mismatch, fork PRs, `[skip ci]`)
- [ ] `docs/example-workflow.yml` — complete reference workflow
- [ ] `CHANGELOG.md` — v1 feature set documented

### Release Infrastructure
- [ ] `branding:` block added to `action.yml` (icon + color) — required for Marketplace listing
- [ ] `v1.0.0` git tag created and pushed
- [ ] `v1` floating tag pointing to same commit — enables `@v1` pinning convention
- [ ] GitHub Release drafted with notes drawn from `CHANGELOG.md`
- [ ] "Publish this Action to the GitHub Marketplace" checkbox ticked on release form
- [ ] Category set (CI / Testing) and Marketplace listing verified live
- [ ] Action reachable via `uses: lennardzuendorf/pytest-bench-action@v1`

---

## Known Limitations (v1)

- **Linux-only validation.** The action has only been tested on `ubuntu-latest`. Windows/macOS runners are untested.
- **Single benchmark file.** Only one `benchmark-results-file` supported per run. Multi-file not in scope.
- **No historical trending.** Baselines track the most recent run only; no time-series data.
- **Fork PRs skip baseline commit.** By design — no write access from forks. Noted in README.
- **Default Python 3.14** may not be available on all runner images. Users should pin to a stable version.

---

## Post-v1 Candidates

These are explicitly out of scope for v1 but may be picked up after:

- Windows / macOS runner support
- Multiple benchmark result files in a single run
- Historical baseline storage (keep N past baselines)
- Trend chart in PR comment (ASCII or linked image)
- Slack / webhook notification on regression
- Self-test CI workflow (dogfooding)
- Configurable comment header string (to support multiple action instances per repo)
