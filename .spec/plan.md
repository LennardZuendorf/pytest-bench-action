---
type: entrypoint
scope: implementation
covers: milestones, task breakdown, validation criteria, session planning
children: []
updated: 2026-06-10
---

# pytest-bench-action — Implementation Plan

**Parent specs:** [product.md](product.md), [tech.md](tech.md)

---

## Validation Summary

**Spec-vs-implementation audit (2026-06-10):** feature tech specs corrected to match `action.yml` and `scripts/` (baseline file paths, step output names, tolerance usage, sanitization, output format). Three release-blocking bugs found in `action.yml` (invalid YAML, dead exit-code handling under `bash -e`, no fail-on-regression) — all fixed same day under M1 task 0.

Already exists (don't rebuild):
- Full composite action (`action.yml`) with 20 steps — orchestration complete, regression wiring fixed 2026-06-10
- Baseline management script (`scripts/benchmark_baseline.py`) — save/load/list working
- Comparison engine (`scripts/benchmark_compare.py`) — node check, tolerance, exit codes
- PR comment generation with deduplication
- Cross-branch and sequential baseline comparison logic
- Conditional baseline commit with `[skip ci]`
- Artifact upload
- `threshold-map` input support
- Engineering guidelines (`AGENTS.md` / `CLAUDE.md`)
- README with usage example and input/output tables
- MIT LICENSE

Must build (release gates):
- Integration test suite for both Python scripts with real/mock benchmark JSON fixtures
- Example workflow file (`.github/workflows/benchmark-example.yml` or docs)
- `CHANGELOG.md` documenting v1 feature set
- `product-release.md` and `tech-scripts.md` / `tech-action.md` branch docs
- `lessons.md` in `.spec/`
- v1 GitHub release + git tag
- Optional: self-test CI workflow (dogfood the action against itself)

**Timeline:** 2–3 sessions

---

## Critical Architecture Decisions

### Decided
- **Composite action, no Docker:** Faster startup, no container build. Python stdlib only in scripts.
- **Baselines in-repo:** Git-committed, versioned, auditable. No external state.
- **Node lock is hard failure:** Silent cross-machine comparison is worse than no comparison.
- **`[skip ci]` on baseline commits:** Prevents infinite CI loops — non-negotiable.
- **Dual tolerance inputs:** `cross-branch-tolerance` (default 20%) for PR vs main; `update-tolerance` (default 5%) for sequential drift detection.
- **Both regression gates use `cross-branch-tolerance`:** the sequential (vs HEAD~1) comparison also gates at 20%, matching the implementation. `update-tolerance` is only the baseline-update trigger, never a failure gate — 5% would be too noisy for failing CI. (Documented 2026-06-10.)

### To Resolve
- [ ] Should the action support `windows-latest` / `macos-latest` runners, or Linux-only for v1?
- [x] Default `python-version` — **resolved 2026-06-10: track latest stable Python (currently `"3.14"`)**; README documents pinning `"3.12"`/`"3.13"` on older runner images
- [ ] Should integration tests run in CI (self-hosted or GitHub-hosted) as part of the release gate?

---

## Implementation Roadmap

| Milestone | Goal | Sessions | Risk |
|-----------|------|----------|------|
| **M1** | Release hardening — tests, docs, changelog | 1–2 | Low |
| **M2** | v1 release — tag, GitHub release, announce | 1 | Low |

---

## M1: Release Hardening

**Goal:** All release-blocking gaps closed: test suite passes, docs complete, changelog written.
**Sessions:** 1–2 | **Risk:** Low

Tasks:
- [x] **Task 0 — fix `action.yml` regression wiring** (found in 2026-06-10 audit; done, plus a bonus find: `action.yml` was invalid YAML — the PR-comment body template literal terminated the `script: |` block scalar; rebuilt as a joined line array):
  - `shell: bash` steps run under `-eo pipefail`, so `python …; EXIT_CODE=$?` in the compare-main / compare-prev / check-update steps is dead code: a compare exit 1 fails the step immediately. Replace with `EXIT_CODE=0; python … || EXIT_CODE=$?`.
  - Side effect 1: any regression aborts the run before baseline save, outputs, PR comment, and artifact upload (no `if: always()` anywhere).
  - Side effect 2: on push events, drift > `update-tolerance` makes check-update **fail the action** instead of setting `should_update=true` — baseline auto-update is effectively broken.
  - Add a final fail-on-regression step (`exit 1` when `regression-detected == 'true'`) so the comment posts first and the job still fails, per product spec "fail loudly".
- [x] Write `tests/` directory with fixtures (`tests/fixtures/baseline.json`, `tests/fixtures/results.json`, `tests/fixtures/results_regression.json`, `tests/fixtures/results_new_benchmark.json`)
- [x] Write `tests/test_benchmark_baseline.py` — test save, load, list, branch sanitization, metadata injection
- [x] Write `tests/test_benchmark_compare.py` — test pass/fail/new/missing, node mismatch, tolerance boundaries, time formatting
- [x] Verify both scripts pass tests locally (`python -m pytest tests/`)
- [x] Create `docs/example-workflow.yml` — full reference workflow showing typical usage
- [x] Write `CHANGELOG.md` — v1 feature set, known limitations, upgrade notes
- [x] Update `README.md` — add troubleshooting section (first run, node mismatch, fork PRs), fix default python-version mention
- [x] ~~Write `.spec/product-release.md`~~ — dropped: release checklist lives in root `product.md` "v1 Release Criteria"; a separate branch doc would duplicate it
- [x] Write `.spec/features/composite-action/` — action step-by-step reference (corrected against implementation 2026-06-10)
- [x] Write `.spec/features/python-scripts/` — script internals reference (corrected against implementation 2026-06-10)
- [x] Write `.spec/lessons.md` — accumulated decisions and gotchas
- [x] Mark `scripts/benchmark_baseline.py` and `scripts/benchmark_compare.py` executable (`chmod 755`)
- [x] Validate action.yml for shell quoting / logic bugs — audit done 2026-06-10; findings folded into Task 0

**Done when:** `python -m pytest tests/` exits 0, README has troubleshooting section, CHANGELOG exists.

---

## M2: v1 Release + Marketplace

**Goal:** Tagged v1 release published to GitHub Marketplace; action usable via `@v1` by anyone.
**Sessions:** 1 | **Risk:** Low

Tasks:
- [ ] Add `branding:` block to `action.yml` (`icon: activity`, `color: purple`) — Marketplace requirement
- [ ] Final review of `action.yml`, scripts, README for any rough edges
- [ ] Create and push `v1.0.0` git tag: `git tag v1.0.0 && git push origin v1.0.0`
- [ ] Create and push `v1` floating tag: `git tag -f v1 v1.0.0 && git push origin v1 --force`
- [ ] Draft GitHub Release from `v1.0.0` tag with notes from `CHANGELOG.md`
- [ ] Tick "Publish this Action to the GitHub Marketplace" on the release form; set category to CI / Testing
- [ ] Verify Marketplace listing is live and `uses: lennardzuendorf/pytest-bench-action@v1` resolves
- [ ] Optional: add CI workflow (`.github/workflows/ci.yml`) to run tests on every push

**Done when:** Action appears on GitHub Marketplace and resolves correctly in a real repo's workflow.

---

## Critical Path

M1 (tests + docs) → M2 (tag + release)

---

## Progress

| Milestone | Status | Sessions Used | Estimate |
|-----------|--------|---------------|----------|
| M1 | **COMPLETE** (2026-06-10) | 1 | 1–2 |
| M2 | NOT STARTED | 0 | 1 |
