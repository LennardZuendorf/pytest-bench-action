---
type: feature-tech
scope: technical
feature: python-scripts
parent: ../../tech.md
updated: 2026-06-10
---

# python-scripts — Technical Design

**Parent:** [tech.md](../../tech.md)

## benchmark_baseline.py

Entry point: `python scripts/benchmark_baseline.py <command> [args]`

### Commands

| Command | Args | Effect |
|---------|------|--------|
| `save` | `<branch> <results-file> [--baselines-dir=PATH]` | Strips `data` arrays, injects `baseline_info`, writes `<dir>/<sanitized>.json` |
| `load` | `<branch> [--baselines-dir=PATH]` | Prints JSON to stdout, exits 1 if not found |
| `list` | `[baselines-dir]` | Prints formatted table: Branch / Node / Created |

### Baseline JSON Format

```json
{
  "machine_info": { "node": "runner-abc", "python_version": "3.14.0" },
  "benchmarks": [
    {
      "name": "test_foo",
      "stats": { "mean": 0.001234, "median": 0.001200, "rounds": 100 }
    }
  ],
  "baseline_info": {
    "branch": "main",
    "node": "runner-abc",
    "created_at": "2026-01-01T00:00:00Z"
  }
}
```

**Key transformations on save:**
- Raw `data` arrays removed from every benchmark's `stats` block (~99% size reduction)
- `baseline_info` block injected with branch, node, UTC timestamp
- Branch name sanitized: `/\\ .` → `_` (used as filename)

### Branch Sanitization

```python
def sanitize_branch(branch: str) -> str:
    for ch in "/\\ .":
        branch = branch.replace(ch, "_")
    return branch
```

Examples: `feature/my-thing` → `feature_my-thing`, `main` → `main`

### Graceful fallbacks (save / list)

- Missing `machine_info.node` on save → recorded as `"unknown"`
- `list` with no baselines dir → prints "No baselines directory found."; empty dir → "No baselines found."
- `list` with malformed JSON → prints `ERROR: …` per file, continues
- `list` with missing `baseline_info` → branch falls back to filename stem, node/created to `"unknown"`

---

## benchmark_compare.py

Entry point: `python scripts/benchmark_compare.py compare-json <baseline> <current> [--tolerance=N]`

`--tolerance` defaults to `20` when omitted.

### Algorithm

1. Load both JSON files; exit 1 with message on parse error or missing file
2. **Node check:** compare `machine_info.node` in baseline vs current. Mismatch → exit 1 with an error explaining that cross-machine comparison is invalid (names both nodes). **Only enforced when both files carry a node** — if either side lacks `machine_info.node`, comparison proceeds.
3. Build `name → mean` maps from both files
4. For each benchmark:
   - In current but not baseline → **NEW** (⚪, pass)
   - In baseline but not current → **MISSING** (❌, fail)
   - In both → compute `change_pct = ((current - baseline) / baseline) * 100` if baseline > 0, else 0
     - `change_pct > tolerance` → **FAIL** (❌)
     - Otherwise → **PASS** (✅)
5. Print formatted table (dynamic column widths)
6. Exit 0 if no failures/missing, exit 1 otherwise

### Time Formatting

| Range | Format | Example |
|-------|--------|---------|
| < 0.001s | microseconds | `1.23µs` |
| < 1s | milliseconds | `45.67ms` |
| ≥ 1s | seconds | `1.2345s` |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | All benchmarks passed within tolerance (or NEW) |
| `1` | One or more regressions, MISSING benchmarks, or node mismatch |

### Output Format (stdout)

```
Benchmark                                   Baseline      Current       Change       Status
--------------------------------------------------------------------------------------------
test_foo                                    1.23ms        1.30ms        +5.7%        ✅ PASS
test_bar                                    0.45ms        0.60ms        +33.3%       ❌ FAIL
test_baz                                    N/A           0.10ms        N/A          ⚪ NEW
test_gone                                   0.80ms        MISSING       N/A          ❌ MISSING
```

Column widths are dynamic (first column min 42 chars). Absent values render as `N/A` / `MISSING`. The summary is a single line: either `All benchmarks within N% tolerance.` or `One or more benchmarks exceeded N% tolerance or are MISSING.`
