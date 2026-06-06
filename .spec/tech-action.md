---
type: branch
scope: technical
parent: tech.md
covers: action.yml step-by-step logic, conditional wiring, input/output contracts
updated: 2026-06-06
---

# pytest-bench-action — Action Step Reference

**Parent:** [tech.md](tech.md)

---

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `python-version` | No | `"3.14"` | Python version for `setup-python` |
| `benchmark-run-command` | **Yes** | — | Full pytest-benchmark shell command |
| `setup-command` | No | `""` | Dependency install (e.g. `pip install -e .`) |
| `pre-benchmark-command` | No | `""` | Warm-up step before benchmarks |
| `benchmark-results-file` | No | `benchmark-results.json` | Output path for pytest-benchmark JSON |
| `cross-branch-tolerance` | No | `20` | % increase allowed vs main baseline |
| `update-tolerance` | No | `5` | % drift to trigger baseline update |
| `baselines-dir` | No | `.benchmarks/baselines` | Directory for stored baselines |
| `github-token` | **Yes** | — | Token with `contents:write` + `pull-requests:write` |
| `threshold-map` | No | `""` | JSON map of `test-name-substring → max-seconds` |

## Outputs

| Output | Values | Set by |
|--------|--------|--------|
| `regression-detected` | `"true"` / `"false"` | Step 17 (set-outputs) |
| `baseline-updated` | `"true"` / `"false"` | Step 17 (set-outputs) |
| `node` | hostname string | Step 11 (extract-node) |

---

## Step-by-Step Logic

### Step 1: Checkout
```yaml
uses: actions/checkout@v4
with:
  fetch-depth: 2
  token: ${{ inputs.github-token }}
```
`fetch-depth: 2` required for `git show HEAD~1:...` in sequential baseline loading.

### Step 2: Fetch target branch (PR only)
```bash
git fetch origin ${{ github.base_ref }} --depth=1
```
Only runs on `pull_request` events. Makes `origin/<base_ref>` available for cross-branch baseline lookup.

### Step 3–5: Python setup, dependencies, warm-up
Conditional on non-empty `setup-command` / `pre-benchmark-command`.

### Step 6: Prepare baselines directory
```bash
mkdir -p ${{ inputs.baselines-dir }}
```

### Step 7: Determine branch name
```bash
BRANCH="${{ github.head_ref || github.ref_name }}"
BRANCH_SANITIZED=$(echo "$BRANCH" | tr '/\\ .' '_')
echo "branch=$BRANCH" >> $GITHUB_OUTPUT
echo "branch_sanitized=$BRANCH_SANITIZED" >> $GITHUB_OUTPUT
```

### Step 8: Load cross-branch baseline
```bash
git show origin/${{ github.base_ref }}:${{ inputs.baselines-dir }}/<base_ref>.json > /tmp/cross_baseline.json 2>/dev/null
```
On failure: sets `cross_baseline_available=false`, skips cross-branch comparison.

### Step 9: Load sequential baseline
```bash
git show HEAD~1:${{ inputs.baselines-dir }}/<branch_sanitized>.json > /tmp/seq_baseline.json 2>/dev/null
```
On failure: sets `seq_baseline_available=false`, skips sequential comparison.

### Step 10: Run benchmarks
```bash
${{ inputs.benchmark-run-command }}
```
Runs verbatim. Caller is responsible for ensuring `pytest-benchmark` is installed.

### Step 11: Extract node
```python
import json; print(json.load(open('${{ inputs.benchmark-results-file }}')).get('machine_info', {}).get('node', 'unknown'))
```
Sets `node` output and `$GITHUB_OUTPUT`.

### Steps 12–13: Compare vs baselines
```bash
python scripts/benchmark_compare.py compare-json <baseline> <results> --tolerance=<N> > <output>.txt
```
- Step 12: cross-branch comparison (skipped if `cross_baseline_available != 'true'`)
- Step 13: sequential comparison (skipped if `seq_baseline_available != 'true'`)
- Output files: `/tmp/cross_comparison.txt`, `/tmp/seq_comparison.txt`
- Exit code captured: `cross_failed`, `seq_failed`

### Step 14: Check if baseline needs updating
```bash
python scripts/benchmark_compare.py compare-json /tmp/seq_baseline.json <results> --tolerance=${{ inputs.update-tolerance }}
```
Exit 0 → `should_update=false`. Exit 1 → `should_update=true`.
Skipped if no sequential baseline.

### Step 15: Save baseline
```bash
python scripts/benchmark_baseline.py save "$BRANCH" "${{ inputs.benchmark-results-file }}" --baselines-dir="${{ inputs.baselines-dir }}"
```
Always runs. Overwrites `<baselines-dir>/<branch_sanitized>.json`.

### Step 16: Commit baseline
```yaml
if: github.event_name == 'push' && steps.check-update.outputs.should_update == 'true'
uses: EndBug/add-and-commit@v9
with:
  message: 'chore(benchmark): update baseline for branch "${{ steps.branch.outputs.branch }}" (node: ${{ steps.extract-node.outputs.node }}) [skip ci]'
```
**Only on push events.** `[skip ci]` prevents infinite loop.

### Step 17: Set outputs
Maps step exit codes and flags to `regression-detected`, `baseline-updated`, `node`.

### Step 18: Post PR comment
```yaml
if: github.event_name == 'pull_request'
uses: actions/github-script@v7
```
Inline JavaScript:
1. List all issue comments on the PR
2. Delete any comment whose body contains `## 📊 Performance Benchmark Results`
3. Build new comment body from comparison output files, threshold-map evaluation, and status flags
4. Create new comment

### Step 19: Upload artifact
```yaml
uses: actions/upload-artifact@v5
with:
  name: benchmark-results-${{ github.run_number }}
  path: ${{ inputs.benchmark-results-file }}
  retention-days: 30
```

---

## Conditional Wiring Summary

| Condition | Steps affected |
|-----------|---------------|
| `pull_request` event | Steps 2, 12 (cross), 18 (PR comment) |
| `push` event | Step 16 (commit baseline) |
| `cross_baseline_available == 'true'` | Step 12 |
| `seq_baseline_available == 'true'` | Steps 13, 14 |
| `should_update == 'true'` AND `push` | Step 16 |
| `setup-command != ''` | Step 4 |
| `pre-benchmark-command != ''` | Step 5 |
