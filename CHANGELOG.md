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
- Machine node lock: comparisons across different runner hostnames fail hard instead of producing misleading numbers
- Deduplicated PR comment with benchmark table, per-test threshold evaluation (`threshold-map`), and both baseline comparisons
- Final fail-on-regression step: the job fails *after* the PR comment and artifact are published
- Outputs: `regression-detected`, `baseline-updated`, `node`
- Benchmark results uploaded as workflow artifact (30-day retention)
- Test suite for both helper scripts (`python -m pytest tests/`)
- Reference workflow in `docs/example-workflow.yml`

### Fixed (pre-release hardening, 2026-06-10)

- `action.yml` was invalid YAML: the PR-comment script's multiline template literal terminated the `script: |` block scalar
- Exit-code capture in the compare and check-update steps was dead code under GitHub's `bash -e` default; a regression aborted the run before the PR comment, and baseline drift on push events failed the job instead of triggering an update
- Regressions now actually fail the job (previously only reported via output)
- Helper scripts marked executable

### Known limitations

- Validated on `ubuntu-latest` only; Windows/macOS runners untested
- One `benchmark-results-file` per run; no multi-file support
- No historical trending — baselines hold the most recent run only
- Fork PRs skip the baseline commit (no write access by design); the PR comment still posts
- Baselines are tied to runner hostname; GitHub-hosted runners get fresh hostnames per job, so a stable (self-hosted) runner is recommended for cross-run comparison
