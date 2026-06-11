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

Step numbers below match the order of the 20 steps in `action.yml`.

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
  > "${{ inputs.baselines-dir }}/_cross_baseline.json" 2>/dev/null || true
```
The base branch is `github.base_ref` (any branch, not just `main`). The baseline
is materialized **inside `baselines-dir` as the scratch file `_cross_baseline.json`**
— a dedicated non-branch name so a committed baseline is never clobbered, whatever
the base branch is called. If the file is empty/missing it is removed and
`main_baseline_exists=false`; otherwise outputs `main_baseline_exists=true` and
`main_baseline_path`. (The output names retain the `main_*` prefix for historical
reasons; they refer to the base/target branch, not literally `main`.)

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
3. Build new comment body from `main_comparison.txt` / `current_comparison.txt`, threshold-map evaluation (substring match, first match wins, 1.0s default), and status flags. The cross-branch section is labelled with the actual base ref (`github.base_ref`, e.g. "vs Base Branch `develop`"), not a hardcoded "Main".
4. Create new comment

### Step 19: Upload artifact
```yaml
uses: actions/upload-artifact@v5
with:
  name: benchmark-results-${{ github.run_number }}
  path: ${{ inputs.benchmark-results-file }}
  retention-days: 30
```

### Step 20: Fail on regression
```yaml
if: steps.set-outputs.outputs.regression-detected == 'true'
run: exit 1   # with ::error:: annotation
```
Last step by design: the PR comment (Step 18) and artifact (Step 19) always publish before the job fails. Compare steps (12–13) capture exit codes non-fatally (`EXIT_CODE=0; … || EXIT_CODE=$?`) because GitHub runs `shell: bash` with `-eo pipefail`.

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

## Known Implementation Gaps

None blocking v1.

Resolved 2026-06-10 (M1 task 0): dead exit-code handling under `bash -eo pipefail` in Steps 12–14 (now `EXIT_CODE=0; … || EXIT_CODE=$?` / `if python …; then`), missing fail-on-regression step (now Step 20), and an invalid-YAML bug — the PR-comment body was a multiline JS template literal whose column-0 lines terminated the `script: |` block scalar (now built as a joined array of lines).

Resolved 2026-06-11 (Phase C, pre-release review): added the `branding:` block (`icon: activity`, `color: purple`, Marketplace requirement); the cross-branch scratch file is now `_cross_baseline.json` and the PR-comment label uses the real base ref, so non-`main` default branches are handled correctly; scripts now read/write with explicit `encoding="utf-8"`.
