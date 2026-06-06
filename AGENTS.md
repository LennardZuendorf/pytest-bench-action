# AGENTS.md - pytest-bench-action Engineering Guide

**Last Updated:** 2026-06-06
**Repository:** pytest-bench-action (reusable GitHub Action)

## Core Operating Principles

### 1. ASK → PLAN → CONFIRM → EXECUTE

**NEVER write code without approval.**

1. **ASK**: Clarify requirements, understand constraints, avoid assumptions
2. **PLAN**: Break down tasks, research patterns, present approach with reasoning
3. **CONFIRM**: Get explicit user approval before any implementation
4. **EXECUTE**: Implement step-by-step with clear explanations

### 2. Quality-First Engineering

- **KISS**: Keep It Simple, Stupid - prefer simplicity over complexity
- **Stdlib Only**: Scripts use Python 3.x stdlib only (`json`, `pathlib`, `sys`) — no third-party packages
- **Shell Safety**: All shell steps must be POSIX-compatible and handle missing files gracefully
- **Idempotency**: Baseline saves and comparisons must be safe to re-run

### 3. Critical Constraints

- **ALWAYS test with a real `pytest-benchmark` JSON** before pushing
- **ALWAYS include `[skip ci]` in baseline commit messages** — prevents infinite CI loops
- **NEVER compare across machines** — node mismatch must exit with a clear error
- **NEVER commit baselines on PR events** — only save to working tree on PRs
- **NEVER use third-party Python packages in `scripts/`** — stdlib only
- **NEVER proceed without user confirmation**

## Tech Stack

```yaml
# Action Runtime
composite action         # Pure Python + shell, no Docker required
actions/checkout@v4      # With fetch-depth: 2
EndBug/add-and-commit@v9 # Baseline commits
actions/github-script@v7 # PR comments
actions/upload-artifact@v5 # Result archiving

# Scripting
Python 3.x stdlib        # json, pathlib, sys, datetime
POSIX shell              # All action steps

# Caller Requirements
pytest-benchmark         # In the caller's environment
```

## Project Structure

```
pytest-bench-action/
├── AGENTS.md                   # You are here
├── CLAUDE.md                   # Symlink → AGENTS.md
├── README.md                   # Usage documentation
├── action.yml                  # Composite action definition
└── scripts/
    ├── benchmark_baseline.py   # Baseline save/load/list
    └── benchmark_compare.py    # Comparison engine (compare-json)
```

## Action Design

### Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `python-version` | No | `"3.14"` | Python version |
| `benchmark-run-command` | **Yes** | — | Full pytest-benchmark shell command |
| `setup-command` | No | `""` | Dependency install command |
| `pre-benchmark-command` | No | `""` | Warm-up command |
| `benchmark-results-file` | No | `benchmark-results.json` | JSON output path |
| `cross-branch-tolerance` | No | `20` | % tolerance vs main baseline |
| `update-tolerance` | No | `5` | % threshold to trigger baseline update |
| `baselines-dir` | No | `.benchmarks/baselines` | Baseline storage path |
| `github-token` | **Yes** | — | Token with contents + pull-requests write |
| `threshold-map` | No | `""` | JSON map of test-name-substring → max-seconds |

### Outputs

| Output | Description |
|--------|-------------|
| `regression-detected` | `"true"` / `"false"` |
| `baseline-updated` | `"true"` / `"false"` |
| `node` | Hostname from `machine_info.node` |

## Core Logic (Step by Step)

### 1. Checkout
- `fetch-depth: 2` required for `git show HEAD~1:...`
- On PRs, also `git fetch origin $base_ref --depth=1`

### 2. Load Baselines
- **Baseline A** (cross-branch): `git show origin/<base_ref>:.benchmarks/baselines/<base_ref>.json`
- **Baseline B** (sequential): `git show HEAD~1:.benchmarks/baselines/<current_branch>.json`
- If either missing → set flag, skip that comparison

### 3. Run Benchmarks
- Execute `benchmark-run-command` verbatim

### 4. Extract Node
```python
NODE=$(python -c "import json; print(json.load(open('benchmark-results.json')).get('machine_info', {}).get('node', 'unknown'))")
```

### 5. Compare Against Baselines
```bash
python scripts/benchmark_compare.py compare-json \
  <baseline.json> <results.json> --tolerance=<N>
```
- Node mismatch → `exit 1` with clear error
- MISSING benchmarks → fail
- NEW benchmarks → pass
- `change_pct > tolerance` → fail
- Output captured to `*_comparison.txt` for PR comment

### 6. Check Update Needed
- Compare current branch baseline to results with `update-tolerance`
- `exit 0` → no update; `exit 1` → update needed

### 7. Save Baseline
- Strip raw `data` arrays from stats (~99% size reduction)
- Inject `baseline_info: {branch, node, created_at}`
- Write to `<baselines-dir>/<sanitized_branch>.json`

### 8. Commit Baseline
- **Only on `push` events** AND `should_update == 'true'`
- Uses `EndBug/add-and-commit@v9`
- Message: `chore(benchmark): update baseline for branch "..." (node: ...) [skip ci]`

### 9. Post PR Comment
- **Only on `pull_request` events**
- Deduplicates: deletes previous bot comment containing `## 📊 Performance Benchmark Results`
- Threshold: substring match on test name, first match wins, default 1.0s

### 10. Upload Artifact
- `benchmark-results-${{ github.run_number }}`
- Retention: 30 days

## Baseline File Format

```json
{
  "machine_info": { "node": "runner-abc", "python_version": "3.14.0" },
  "benchmarks": [
    { "name": "test_foo", "stats": { "mean": 0.001234, "median": 0.001200, "rounds": 100 } }
  ],
  "baseline_info": {
    "branch": "main",
    "node": "runner-abc",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

## Edge Cases

| Case | Behaviour |
|------|-----------|
| No baseline (first run) | Skip comparison, save baseline, note in PR comment |
| Different node than baseline | Fail with clear error, do not compare |
| Benchmark removed from suite | Mark MISSING, fail |
| New benchmark not in baseline | Mark NEW, pass |
| Push to main | Compare HEAD~1; commit new baseline if changed |
| PR from fork | Skip baseline commit, still post comment |
| `[skip ci]` loop | Commit message includes `[skip ci]` |

## Git Commit Standards

```
[type](optional-scope): imperative subject

# Examples:
feat(action): add threshold-map input
fix(compare): handle missing node in machine_info
chore(baseline): update baseline for branch "main" [skip ci]
```

**Rules:**
- Imperative mood, lowercase
- Max 72 characters
- No trailing period

## Development Workflow

```bash
# Test scripts locally
python scripts/benchmark_compare.py compare-json baseline.json results.json --tolerance=20
python scripts/benchmark_baseline.py save main results.json
python scripts/benchmark_baseline.py list .benchmarks/baselines/

# Validate action.yml structure
cat action.yml
```

## Best Practices

### DO ✅
- Use Python stdlib only in scripts
- Handle missing baseline files gracefully with clear messages
- Always include `[skip ci]` in baseline commit messages
- Sanitize branch names before using as filenames
- Deduplicate PR comments before posting
- Validate node consistency before comparing

### DON'T ❌
- NEVER use third-party packages in `scripts/` — no `pip install` in the action
- NEVER commit baselines on PR events
- NEVER compare benchmarks across different machines
- NEVER fail the action when a baseline doesn't exist yet (first run)
- NEVER use `actions/upload-artifact@v4` or older — use v5
- NEVER skip the `[skip ci]` tag in baseline commits

---

**Remember:** ASK → PLAN → CONFIRM → EXECUTE. Stdlib only. KISS principle always.
