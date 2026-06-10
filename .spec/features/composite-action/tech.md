---
type: feature-tech
scope: technical
feature: composite-action
parent: ../../tech.md
updated: 2026-06-10
---

# composite-action — Technical Design

**Parent:** [tech.md](../../tech.md)

## Step-by-Step Logic

Step numbers below match the order of the 19 steps in `action.yml`.

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

### Steps 3–5: Python setup, dependencies, warm-up
`actions/setup-python@v5` with `inputs.python-version`. Install and warm-up steps are conditional on non-empty `setup-command` / `pre-benchmark-command`.

### Step 6: Prepare baselines directory
```bash
mkdir -p "${{ inputs.baselines-dir }}"
```

### Step 7: Determine current branch (`id: branch`)
```bash
# PR: github.head_ref; push: ${GITHUB_REF#refs/heads/}
SANITIZED=$(echo "${CURRENT_BRANCH}" | tr '/\\. ' '_')
```
Outputs: `current_branch`, `sanitized_branch`.

### Step 8: Load cross-branch baseline (PR only, `id: load-main-baseline`)
```bash
git show "origin/${TARGET_BRANCH}:${{ inputs.baselines-dir }}/${SANITIZED_TARGET}.json" \
  > "${{ inputs.baselines-dir }}/main.json" 2>/dev/null || true
```
The baseline is materialized **inside `baselines-dir` as `main.json`** (not `/tmp`). If the file is empty/missing it is removed and `main_baseline_exists=false`; otherwise outputs `main_baseline_exists=true` and `main_baseline_path`.

### Step 9: Load previous-commit baseline (`id: load-prev-baseline`)
```bash
git show "HEAD~1:${{ inputs.baselines-dir }}/${SANITIZED}.json" > "${LOCAL_FILE}" 2>/dev/null || true
```
`LOCAL_FILE` is `<baselines-dir>/<sanitized_branch>.json`, **except on `main` where it is `<baselines-dir>/main_previous.json`** to avoid clobbering the `main.json` written by Step 8. Outputs `prev_baseline_exists`, `prev_baseline_path`.

### Step 10: Run benchmarks
```bash
${{ inputs.benchmark-run-command }}
```
Runs verbatim. Caller is responsible for ensuring `pytest-benchmark` is installed.

### Step 11: Extract node (`id: extract-node`)
Inline `python -c` reads `machine_info.node` from the results file, falling back to `unknown` on any error. Sets `node` output.

### Steps 12–13: Compare vs baselines (`id: compare-main` / `id: compare-prev`)
```bash
python "${SCRIPT_DIR}/benchmark_compare.py" compare-json <baseline> <results> \
  --tolerance="${{ inputs.cross-branch-tolerance }}" > <comparison>.txt 2>&1
```
- Step 12 (cross-branch): PR events only, skipped unless `main_baseline_exists == 'true'`. Output file: `<baselines-dir>/main_comparison.txt`. Sets `main_regression=true|false`.
- Step 13 (sequential): skipped unless `prev_baseline_exists == 'true'`. Output file: `<baselines-dir>/current_comparison.txt`. Sets `prev_regression=true|false`.
- **Both regression gates use `cross-branch-tolerance` (default 20%).** `update-tolerance` is *only* the baseline-update trigger (Step 14), never a regression gate. Using the 5% update tolerance as a failure gate would be too noisy.

### Step 14: Check whether baseline needs updating (`id: check-update`)
Always runs (not conditional on a sequential baseline):
- No `<baselines-dir>/<sanitized_branch>.json` on disk → `should_update=true` (first run creates a baseline).
- Otherwise compare current results against it with `--tolerance=${{ inputs.update-tolerance }}`: exit 0 → `should_update=false`, exit 1 → `should_update=true`.

### Step 15: Save baseline
```bash
python "${SCRIPT_DIR}/benchmark_baseline.py" save "$CURRENT_BRANCH" \
  "${{ inputs.benchmark-results-file }}" --baselines-dir="${{ inputs.baselines-dir }}"
```
Always runs. Overwrites `<baselines-dir>/<sanitized_branch>.json` in the working tree.

### Step 16: Commit baseline
```yaml
if: github.event_name == 'push' && steps.check-update.outputs.should_update == 'true'
uses: EndBug/add-and-commit@v9
with:
  message: 'chore(benchmark): update baseline for branch "..." (node: ...) [skip ci]'
```
**Only on push events.** `[skip ci]` prevents infinite loop.

### Step 17: Set outputs (`id: set-outputs`)
- `regression-detected` = `main_regression == 'true' || prev_regression == 'true'`
- `baseline-updated` = `push` event AND `should_update == 'true'`
- `node` is wired from `extract-node` at the action `outputs:` level.

### Step 18: Post PR comment
```yaml
if: github.event_name == 'pull_request'
uses: actions/github-script@v7
```
Inline JavaScript:
1. List all issue comments on the PR
2. Delete any comment whose body contains `## 📊 Performance Benchmark Results`
3. Build new comment body from `main_comparison.txt` / `current_comparison.txt`, threshold-map evaluation (substring match, first match wins, 1.0s default), and status flags
4. Create new comment

### Step 19: Upload artifact
```yaml
uses: actions/upload-artifact@v5
with:
  name: benchmark-results-${{ github.run_number }}
  path: ${{ inputs.benchmark-results-file }}
  retention-days: 30
```

## Conditional Wiring Summary

| Condition | Steps affected |
|-----------|---------------|
| `pull_request` event | Steps 2, 8, 12 (cross), 18 (PR comment) |
| `push` event AND `should_update == 'true'` | Step 16 (commit baseline) |
| `main_baseline_exists == 'true'` | Step 12 |
| `prev_baseline_exists == 'true'` | Step 13 |
| `setup-command != ''` | Step 4 |
| `pre-benchmark-command != ''` | Step 5 |

Step 14 always runs; a missing on-disk baseline means `should_update=true`.

## Known Implementation Gaps (validated against `action.yml` 2026-06-10)

Tracked as M1 tasks in [.spec/plan.md](../../plan.md):

1. **Exit-code handling is dead code under `bash -e`.** GitHub runs `shell: bash` steps with `-eo pipefail`. In Steps 12, 13, and 14 the pattern `python … ; EXIT_CODE=$?` never reaches the `$?` check when the compare script exits 1 — the step fails immediately. Consequences:
   - On any regression, the action aborts at Step 12/13; Steps 14–19 (baseline save, outputs, **PR comment**, artifact) are skipped — no `if: always()` anywhere.
   - On push events with drift > `update-tolerance`, Step 14's compare exits 1 and **fails the whole action** instead of setting `should_update=true`.
   - Fix shape: `EXIT_CODE=0; python … || EXIT_CODE=$?`, plus `if: always()`-style wiring where downstream steps must still run.
2. **No explicit fail-on-regression step.** Product spec requires "regressions surface as a failing step" *after* the PR comment is posted. Intended design: capture compare exit codes non-fatally, run comment/artifact steps, then a final step exits 1 when `regression-detected == 'true'`.
3. **No `branding:` block** yet (Marketplace requirement, M2).
