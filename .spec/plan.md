---
type: entrypoint
scope: implementation
covers: milestones, task breakdown, validation criteria, session planning
children: []
updated: 2026-06-11
---

# pytest-bench-action — Implementation Plan

**Parent specs:** [product.md](product.md), [tech.md](tech.md)

---

## Validation Summary

**Spec-vs-implementation audit (2026-06-10):** feature tech specs corrected to match `action.yml` and `scripts/` (baseline file paths, step output names, tolerance usage, sanitization, output format). Three release-blocking bugs found in `action.yml` (invalid YAML, dead exit-code handling under `bash -e`, no fail-on-regression) — all fixed same day under M1 task 0.

**Shipped (2026-06-11):** all M1 work is up as [PR #3](https://github.com/LennardZuendorf/pytest-bench-action/pull/3) (branch `claude/wonderful-volta-jvuhfk`). M2 tagging/release happens after that PR merges to `main`.

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
- [x] Runner support — **resolved 2026-06-11: Linux-only for v1.** Already listed under Known Limitations; the suite and harness are POSIX-validated on Linux only. Windows/macOS stay Post-v1 Candidates.
- [x] Default `python-version` — **resolved 2026-06-10: track latest stable Python (currently `"3.14"`)**; README documents pinning `"3.12"`/`"3.13"` on older runner images
- [x] Integration tests in CI as release gate — **resolved 2026-06-11: yes.** `ci.yml` runs unit tests + selftest on every push/PR, and `release.yml` re-runs both before tagging, so nothing untested can be released.

---

## Implementation Roadmap

| Milestone | Goal | Sessions | Risk |
|-----------|------|----------|------|
| **M1** | Release hardening — tests, docs, changelog | 1–2 | Low |
| **M1.5** | Self-test / dogfood — real end-to-end validation, CI | 1 | Low |
| **M2** | v1 release — tag, GitHub release, announce | 1 | Low |

**M1.5** is detailed in [features/self-test-ci/plan.md](features/self-test-ci/plan.md):
build a real benchmark suite, validate the full pipeline against actual
pytest-benchmark output (closing the open "end-to-end" release criterion), and
add CI + dogfood workflows. Runs between M1 and M2.

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
**Precondition:** PR #3 (M1) merged to `main` — tags must point at a `main` commit.

Tasks:
- [x] Run the action end-to-end on a real pytest-benchmark suite — done via M1.5: `scripts/selftest.sh` + real-output tests prove the pipeline locally; `benchmark.yml` dogfoods the full action on CI
- [x] Add `branding:` block to `action.yml` (`icon: activity`, `color: purple`) — Marketplace requirement (2026-06-11)
- [x] Final review of `action.yml`, scripts, README for any rough edges — subagent review 2026-06-11; fixes applied (base-branch handling, utf-8 I/O), non-issues confirmed
- [x] Automate the mechanical release steps: `.github/workflows/release.yml` (manual `workflow_dispatch` from `main`, runs unit tests + selftest first, then creates the `vX.Y.Z` tag, force-moves the floating major tag, and drafts a GitHub Release with notes extracted from `CHANGELOG.md`); runbook in `docs/RELEASING.md` (2026-06-11)
- [ ] **Human, after PR #3 merges:** run the Release workflow from `main` with `version: v1.0.0` → creates `v1.0.0` + `v1` tags and the draft Release
- [ ] **Human:** publish the draft Release; tick "Publish this Action to the GitHub Marketplace"; set category to CI / Testing
- [ ] **Human:** verify Marketplace listing is live and `uses: lennardzuendorf/pytest-bench-action@v1` resolves
- [x] CI workflow (`.github/workflows/ci.yml`) to run tests on every push (2026-06-11, M1.5)

**Done when:** Action appears on GitHub Marketplace and resolves correctly in a real repo's workflow.

---

## Critical Path

M1 (tests + docs) → M1.5 (dogfood + CI) → M2 (tag + release)

## Spec Lifecycle

Per the spec skill, feature folders are ephemeral: compound to root, then move to
`.spec/archive/<name>/`. All three features (`composite-action`, `python-scripts`,
`self-test-ci`) have had their cross-cutting decisions merged into root
`tech.md` / `lessons.md`; the folders stay live as implementation references
until v1 ships, then archive as part of M2 wrap-up (post PR #3 merge).

---

## Progress

| Milestone | Status | Sessions Used | Estimate |
|-----------|--------|---------------|----------|
| M1 | **COMPLETE** — shipped on PR #3 | 1 | 1–2 |
| M1.5 | **COMPLETE** — dogfood harness + CI, real end-to-end validation (2026-06-11) | 1 | 1 |
| M2 | In progress — branding done; tags/release/Marketplace human-gated on PR #3 merge | 0 | 1 |
