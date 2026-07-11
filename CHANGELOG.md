# Changelog

All notable changes to pytest-bench-action are documented here.
Format follows [Keep a Changelog](https://keepachangelog.com/); versions follow [SemVer](https://semver.org/).

## [1.0.0] — Unreleased

First public release.

### Added

- Composite GitHub Action (no Docker) that runs any `pytest-benchmark` suite via `benchmark-run-command`
- Per-branch baselines committed to the repo (`baselines-dir`, default `.benchmarks/baselines`), stripped of raw `data` arrays (~99% smaller) and stamped with `baseline_info` (branch, node, created_at)
- Dual baseline comparison: cross-branch (PR vs target branch baseline, `cross-branch-tolerance`, default 20%) and sequential (vs `HEAD~1` baseline)
- Baseline auto-update on push events when drift exceeds `update-tolerance` (default 5%), committed with `[skip ci]` to prevent CI loops
- Hardware-aware comparison gate: comparability is judged on a CPU/system fingerprint (`machine_info.cpu.brand_raw` + arch + core count + `system`), **not** the hostname — so the same machine compares cleanly even when the runner's `node` name changes between jobs (as it does on GitHub-hosted runners), while genuinely different hardware is still rejected. Falls back to `node` for minimal/legacy payloads with no `cpu` block. `enforce-same-node` (default `"false"`) controls the response to a hardware mismatch — skip that comparison with a `::warning::` + `comparison-skipped` output, or hard-fail (`"true"`, for stable/self-hosted runners). `benchmark_compare.py` signals a mismatch with a dedicated exit code (`3`) so the action can tell "cannot compare" from "regressed"
- Per-PR regression override via the `benchmark-override` label (configurable with `override-label`): a labelled PR still shows the regression in its comment but the job does not fail — an opt-in, self-clearing, per-PR escape hatch instead of loosening tolerances repo-wide
- Deduplicated PR comment with benchmark table, per-test threshold evaluation (`threshold-map`), and both baseline comparisons; comparison sections render a skip note on node mismatch and the regression banner reflects an active override
- Final fail-on-regression step: the job fails *after* the PR comment and artifact are published, and is bypassed when the regression is overridden by the label
- Outputs: `regression-detected`, `baseline-updated`, `node`, `comparison-skipped`, `regression-overridden`
- Benchmark results uploaded as workflow artifact (30-day retention)
- Marketplace `branding` (icon `activity`, colour `purple`)
- Test suite for both helper scripts (`python -m pytest tests/`)
- Reference workflow in `docs/example-workflow.yml`
- **Self-test / dogfood harness:** a real `pytest-benchmark` suite (`bench/`),
  a captured real-output fixture, a local end-to-end harness
  (`scripts/selftest.sh`) that drives the full pipeline against actual
  pytest-benchmark JSON, and CI workflows (`.github/workflows/ci.yml` for unit
  tests + self-test, `.github/workflows/benchmark.yml` dogfooding `uses: ./`)
- **Release automation:** `.github/workflows/release.yml` (manual dispatch from
  `main`; re-runs all tests, creates the version tag, moves the floating major
  tag, drafts a GitHub Release from this changelog) plus the
  `docs/RELEASING.md` runbook

### Fixed (pre-release hardening, 2026-06-10)

- `action.yml` was invalid YAML: the PR-comment script's multiline template literal terminated the `script: |` block scalar
- Exit-code capture in the compare and check-update steps was dead code under GitHub's `bash -e` default; a regression aborted the run before the PR comment, and baseline drift on push events failed the job instead of triggering an update
- Regressions now actually fail the job (previously only reported via output)
- Helper scripts marked executable
- Cross-branch comparison no longer assumes the base branch is `main`: uses the
  PR's real `base_ref`, a dedicated scratch file, and a base-ref-labelled comment
- All script file I/O uses explicit `encoding="utf-8"` (non-ASCII test ids safe
  regardless of runner locale)
- Proved end-to-end against real pytest-benchmark 5.x output, not just
  hand-written fixtures

### Known limitations

- Validated on `ubuntu-latest` only; Windows/macOS runners untested
- One `benchmark-results-file` per run; no multi-file support
- No historical trending — baselines hold the most recent run only
- Fork PRs skip the baseline commit (no write access by design); the PR comment still posts
- Comparisons are gated on a CPU fingerprint, not the hostname, so hosted runners compare on the same CPU model — but GitHub rotates its pool across CPU generations, so some runs still skip, and shared-VM noise is not removed by fingerprinting (absorbed by `cross-branch-tolerance`). A stable/self-hosted runner with `enforce-same-node: "true"` remains recommended for the most reliable cross-run comparison
