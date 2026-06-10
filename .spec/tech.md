---
type: entrypoint
scope: technical
children: []
updated: 2026-06-10
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
│   └── benchmark_compare.py    # compare-json command (stdlib only)
├── .spec/                      # Design docs (this directory)
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

- **Baseline storage:** `<baselines-dir>/<sanitized_branch>.json` committed to the repo. Branch names sanitized: `/\\ .` → `_`. -> [features/python-scripts/tech.md](features/python-scripts/tech.md)
- **Dual baseline comparison:** Cross-branch (PR vs main baseline) + sequential (current vs HEAD~1 baseline). Each is independently optional. -> [features/composite-action/tech.md](features/composite-action/tech.md)
- **Node lock:** `machine_info.node` extracted from benchmark JSON. Mismatched node → `exit 1`. Ensures apples-to-apples comparison. -> [features/python-scripts/tech.md](features/python-scripts/tech.md)
- **PR comment deduplication:** `actions/github-script` deletes any prior comment containing `## 📊 Performance Benchmark Results` before posting. -> [features/composite-action/tech.md](features/composite-action/tech.md)
- **Baseline auto-commit:** Only on `push` events AND when `should_update == 'true'`. Message always ends with `[skip ci]`. -> [features/composite-action/tech.md](features/composite-action/tech.md)
- **Threshold map:** JSON string input mapping test-name substrings to max-seconds. First match wins. Default 1.0s fallback. Evaluated in PR comment step only. -> [features/composite-action/tech.md](features/composite-action/tech.md)

## Risks & Mitigations

| Risk | Mitigation |
|------|------------|
| Infinite CI loop from baseline commit | `[skip ci]` in every baseline commit message (enforced by AGENTS.md) |
| Cross-machine noise invalidating baselines | Hard node check in `benchmark_compare.py` — mismatch exits 1 |
| PR from fork can't commit baseline | Conditional: only commit on `push`, skip on `pull_request` |
| Large baseline files bloating repo | Strip raw `data` arrays on save (~99% size reduction) |
| Python 3.14 not available on runner | `python-version` is configurable; users can pin to 3.11/3.12/3.13 |
| Missing benchmark causes silent skip | MISSING benchmarks fail the comparison step explicitly |

## Feature Specs

| Feature | Covers |
|---------|--------|
| **[features/composite-action/](features/composite-action/tech.md)** | action.yml step-by-step logic, conditional wiring, input/output contracts |
| **[features/python-scripts/](features/python-scripts/tech.md)** | Script internals: baseline format, comparison algorithm, exit codes, test fixtures |
