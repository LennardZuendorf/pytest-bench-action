---
type: entrypoint
scope: technical
children: []
updated: 2026-07-11
---

# pytest-bench-action — Technical Architecture

## Design Philosophy

1. **Composite action, no Docker.** Pure Python + POSIX shell. Runs on any `ubuntu-latest` runner without a container build step. Faster startup, easier debugging.
2. **Stdlib only in `scripts/`.** `json`, `pathlib`, `sys`, `datetime` — nothing else. Callers must not need `pip install` to run the action internals.
3. **Shell steps are POSIX-safe.** Every `run:` block handles missing files gracefully (`|| true`, conditional checks). No `set -e` surprises.
4. **Idempotency by default.** Baseline save overwrites the same file. Comparison exits with a code, never mutates state. Re-running a step is always safe.
5. **Exit codes are the API.** Scripts communicate success/failure to the shell via exit codes (0 = pass, 1 = fail/update-needed). Parsed outputs are captured via `$GITHUB_OUTPUT`.

## Architecture Overview

```
pytest-bench-action/
├── action.yml                  # Composite action — 20 steps, all orchestration lives here
├── scripts/
│   ├── benchmark_baseline.py   # save | load | list commands (stdlib only)
│   ├── benchmark_compare.py    # compare-json command (stdlib only)
│   └── selftest.sh             # local end-to-end harness (mirrors action.yml pipeline)
├── bench/
│   └── test_sample_benchmark.py # deterministic stdlib suite for dogfooding
├── tests/
│   ├── conftest.py             # subprocess/json helpers
│   ├── fixtures/               # hand-written + captured real pytest-benchmark output
│   └── test_*.py               # 49 unit tests incl. real-output validation
├── .github/workflows/
│   ├── ci.yml                  # unit tests + selftest on push/PR
│   ├── benchmark.yml           # dogfood: uses: ./ against bench/
│   └── release.yml             # manual: gate tests → tags → draft Release
├── docs/
│   ├── example-workflow.yml    # caller reference workflow
│   └── RELEASING.md            # release runbook
├── .spec/                      # Design docs (this directory)
├── CHANGELOG.md                # release notes (source for release.yml)
├── README.md                   # User-facing usage guide
├── AGENTS.md / CLAUDE.md       # Engineering guidelines (symlinked)
└── LICENSE                     # MIT
```

## Tech Stack

**Inherited (caller provides):**
- `pytest-benchmark` — must be installed in the caller's Python environment
- GitHub Actions runner (ubuntu-latest typical)
- Python 3.x (configured via `python-version` input, default 3.14)

**Action dependencies (pinned in `action.yml`):**
- `actions/checkout@v4` — with `fetch-depth: 2`
- `actions/setup-python@v5`
- `EndBug/add-and-commit@v9` — baseline commits
- `actions/github-script@v7` — PR comment via inline JS
- `actions/upload-artifact@v5` — result archiving

**Scripts:**
- Python 3.x stdlib: `json`, `pathlib`, `sys`, `datetime`

## What We Build vs Inherit

| Source | Approx. Lines | What |
|--------|---------------|------|
| **action.yml** (this project) | ~400 | All orchestration logic, input/output wiring, conditional steps |
| **benchmark_baseline.py** (this project) | ~115 | Baseline save/load/list, branch sanitization, metadata injection |
| **benchmark_compare.py** (this project) | ~137 | JSON comparison, node validation, tolerance checks, formatted output |
| **Third-party actions** (inherited) | — | Checkout, Python setup, commit, PR comment, artifact upload |

## Key Patterns

- **Baseline storage:** `<baselines-dir>/<sanitized_branch>.json` committed to the repo. Branch names sanitized: `/\\ .` → `_`.
- **Dual baseline comparison:** Cross-branch (PR vs base-branch baseline) + sequential (current vs HEAD~1 baseline). Each is independently optional. Both gate at `cross-branch-tolerance`.
- **Hardware fingerprint gate, configurable enforcement:** comparability is keyed on `machine_key()` — a fingerprint of `cpu.brand_raw` + `cpu.arch` + `cpu.count` + `system`, **not** the hostname (`node` is randomized per hosted job; it's a fallback only when no `cpu` block exists). Same hardware compares even when the node name changes; genuinely different hardware is rejected. The action **never** emits a cross-machine comparison. `benchmark_compare.py` signals a mismatch with a dedicated exit code (`3` = `NODE_MISMATCH_EXIT`), distinct from a real regression (`1`). `enforce-same-node` (default `"false"`) decides whether the action **hard-fails** on that code or **skips** the comparison with a `::warning::` and `comparison-skipped=true`.
- **Per-PR regression override:** `override-label` (default `benchmark-override`) waives a regression for one PR. `contains(github.event.pull_request.labels.*.name, inputs.override-label)` gates the final fail step; the regression is still reported (`regression-overridden=true`, PR-comment banner) — only the `exit 1` is suppressed. Opt-in per-PR, self-clearing, `pull_request`-only.
- **PR comment deduplication:** `actions/github-script` deletes any prior comment containing `## 📊 Performance Benchmark Results` before posting — exactly one comment per run.
- **Baseline auto-commit:** Only on `push` events AND when `should_update == 'true'`. Message always ends with `[skip ci]`.
- **Threshold map:** JSON string input mapping test-name substrings to max-seconds. First match wins. Default 1.0s fallback. Evaluated in PR comment step only.

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Infinite CI loop from baseline commit | `[skip ci]` in every baseline commit message (enforced by AGENTS.md) |
| Cross-machine noise invalidating baselines | Hardware-fingerprint check in `benchmark_compare.py` (CPU model/arch/cores, not hostname) — mismatch exits `3`; `enforce-same-node` chooses fail vs skip-with-warning; a cross-machine comparison is never emitted |
| A single intentional regression forced repo-wide tolerance loosening | Per-PR `override-label` waives one PR's regression (still reported, non-blocking) instead of weakening detection for everyone |
| PR from fork can't commit baseline | Conditional: only commit on `push`, skip on `pull_request` |
| Large baseline files bloating repo | Strip raw `data` arrays on save (~99% size reduction) |
| Python 3.14 not available on runner | `python-version` is configurable; users can pin to 3.11/3.12/3.13 |
| Missing benchmark causes silent skip | MISSING benchmarks fail the comparison step explicitly |

## Implementation Map

The three feature folders (`composite-action`, `python-scripts`, `self-test-ci`)
were collapsed into this root spec once shipped — **code is the source of
truth**. Where each concern lives:

| Area | Where |
|------|-------|
| Action orchestration, step wiring, input/output contract, PR comment rendering | `action.yml` |
| Baseline save/load/list, JSON format, branch sanitization | `scripts/benchmark_baseline.py` |
| Comparison algorithm, node check, exit-code contract | `scripts/benchmark_compare.py` |
| End-to-end dogfood harness | `scripts/selftest.sh`, `bench/`, `.github/workflows/{ci,benchmark}.yml` |
| Unit + real-output + action-wiring tests | `tests/` |
