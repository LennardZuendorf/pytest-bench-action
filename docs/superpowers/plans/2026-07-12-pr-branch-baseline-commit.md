# PR-Branch Baseline Commit Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop committing baseline updates via a post-merge `push`-to-`main` rerun; instead stage the baseline commit on the PR branch itself during the `pull_request` run, so it lands on the target branch automatically when the PR merges.

**Architecture:** The action already loads the target branch's committed baseline during a PR run (`Load cross-branch baseline (PR only)` → `origin/<base_ref>:.../<base_ref>.json`). Today a *second*, separate mechanism reruns benchmarks on `push` to commit an updated baseline directly to `main` — which both duplicates work and gets rejected by any branch ruleset requiring PR-only changes (`GH013`). The fix: check out the PR's own head branch (not the synthetic merge ref), decide `should_update` by comparing this PR's results against the already-loaded target-branch baseline, and — for same-repo PRs only — commit the new baseline file (named after the *target* branch, e.g. `main.json`) directly onto the PR branch with `EndBug/add-and-commit@v9`. No push trigger, no direct commit to a protected branch.

**Tech Stack:** GitHub Actions composite action (`action.yml`), POSIX shell, Python 3.x stdlib (`scripts/benchmark_baseline.py`, `scripts/benchmark_compare.py`), `EndBug/add-and-commit@v9`, `actions/github-script@v7`. Tests: `pytest` text/regex contract tests in `tests/test_action_wiring.py` (no PyYAML available in CI, so `action.yml` is asserted against as plain text — same pattern already used there).

---

## Known Risk — Verify On First Real Use

This design depends on one unverified assumption: that GitHub's CodeQL **default setup** (this repo has no `.github/workflows/codeql.yml` — it's the server-managed "dynamic" kind, confirmed via `gh api repos/.../actions/workflows`) re-analyzes a PR branch after a `[skip ci]`, `GITHUB_TOKEN`-authored commit lands on it (via `EndBug/add-and-commit`), and that the ruleset's `code_scanning` requirement then clears so the PR stays mergeable.

**Evidence gathered, and why it's not conclusive:**
- `gh api repos/LennardZuendorf/pytest-bench-action/code-scanning/analyses` shows commit `4e2cb79` — the prior `chore(benchmark): ... [skip ci]` bot commit, confirmed via `git log` to be authored by `github-actions` — WAS analyzed by CodeQL (both `python` and `actions` categories). That's reassuring: `[skip ci]` + bot-authorship does **not** universally suppress default-setup scanning.
- But that commit landed via a **push to `main`** (continuous default-branch scanning), not a **`pull_request` synchronize** on a feature branch (a required *check* gating mergeability — the exact thing `GITHUB_TOKEN`-authored pushes are documented to suppress, per `EndBug/add-and-commit`'s own README: *"GitHub sees the push... doesn't run any further checks to avoid unintentional check loops."*). Those are plausibly different code paths inside GitHub's backend. This can only be settled by watching a real PR go through the new mechanism — not by more API introspection from here.

**Fallback if it turns out to block merges:** switch the checkout/commit token from `${{ inputs.github-token }}` (`GITHUB_TOKEN`) to a PAT (documented in `EndBug/add-and-commit`'s README, "About tokens" / "The commit from the action is not triggering CI!"), so the bot commit *does* trigger checks including CodeQL — then add a job-level guard so that commit doesn't also re-trigger an infinite `benchmark.yml` rerun, e.g.:

```yaml
    - name: Skip if this run was triggered by our own baseline commit
      if: startsWith(github.event.pull_request.title, '') # placeholder — see note below
```

(Not filled in because it's contingent on the spike failing — if needed, gate on the head commit message via `github.event.head_commit.message` matching `^chore\(benchmark\): update baseline`, checked in an early step that sets an output the rest of the job's steps `if:` on.)

**Action required:** treat Task 8's verification as passing the unit/wiring suite only — that proves the YAML is wired correctly, not that GitHub's live ruleset behavior cooperates. Before relying on this for anything that matters, open one real PR against this repo that deliberately exceeds `update-tolerance`, and confirm by hand: the staged commit appears on the PR branch, CodeQL re-analyzes that new head SHA, and the PR becomes mergeable. This is called out again as Task 13.

---

## Scope Check

Single subsystem: relocating *where and when* the baseline-update commit happens. Does not touch the sequential/previous-commit comparison feature, the regression-detection/override logic, or the compare script — those are unrelated and explicitly out of scope.

## File Structure

- Modify: `action.yml` — checkout ref, `should_update` comparison target, new staging step, commit step retarget, outputs gate, PR-comment fork-awareness.
- Modify: `tests/test_action_wiring.py` — new contract-test classes for each wiring change above.
- Modify: `.github/workflows/benchmark.yml` — drop `push` trigger.
- Modify: `docs/example-workflow.yml` — drop `push` trigger, update guidance comments.
- Modify: `README.md` — "How It Works", two "Troubleshooting" entries, new "Suggested Usage" table.
- Modify: `AGENTS.md` — hard-constraint wording, Core Logic step 8, edge-case table row, DO/DON'T bullet.

---

### Task 1: Export `sanitized_target_branch` from the cross-branch baseline loader

**Files:**
- Modify: `action.yml:136-157` (`Load cross-branch baseline (PR only)` step)
- Test: `tests/test_action_wiring.py`

Later tasks need the target branch's *sanitized* filename (e.g. `main` for `main`, `release_1_0` for `release/1.0`) to scope the commit's `add:` path to exactly one file. This step already computes it locally as `SANITIZED_TARGET` — just export it.

- [ ] **Step 1: Write the failing test**

Add to `tests/test_action_wiring.py`:

```python
class TestSanitizedTargetBranchOutput:
    def test_sanitized_target_branch_exported(self, action_text):
        assert "sanitized_target_branch=${SANITIZED_TARGET}" in action_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestSanitizedTargetBranchOutput -v`
Expected: FAIL (string not present yet)

- [ ] **Step 3: Edit `action.yml`**

In the `Load cross-branch baseline (PR only)` step, change:

```yaml
        TARGET_BRANCH="${{ github.base_ref }}"
        SANITIZED_TARGET=$(echo "${TARGET_BRANCH}" | tr '/\\. ' '_')
        # Dedicated scratch file (not a branch name) so we never clobber a
        # committed baseline, whatever the base branch is called.
        BASELINE_PATH="${{ inputs.baselines-dir }}/_cross_baseline.json"
```

to:

```yaml
        TARGET_BRANCH="${{ github.base_ref }}"
        SANITIZED_TARGET=$(echo "${TARGET_BRANCH}" | tr '/\\. ' '_')
        echo "sanitized_target_branch=${SANITIZED_TARGET}" >> "$GITHUB_OUTPUT"
        # Dedicated scratch file (not a branch name) so we never clobber a
        # committed baseline, whatever the base branch is called.
        BASELINE_PATH="${{ inputs.baselines-dir }}/_cross_baseline.json"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestSanitizedTargetBranchOutput -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "feat(action): export sanitized_target_branch from cross-branch baseline loader"
```

---

### Task 2: Check out the PR branch tip instead of the synthetic merge ref

**Files:**
- Modify: `action.yml:92-96` (`Checkout` step)
- Test: `tests/test_action_wiring.py`

Committing back requires being on a real, named branch. `actions/checkout` defaults to the `refs/pull/<n>/merge` ref on `pull_request` events, which is detached and not push-able. Same-repo PRs check out `github.head_ref` (an attached branch in this same repo, so `git push` just works); fork PRs check out `github.event.pull_request.head.sha` instead (always resolvable via GitHub's auto-created `refs/pull/<n>/head`, since the fork's branch name doesn't exist in this repo's remote) — fork commits are skipped later anyway (Task 5), so detached is fine there. Non-PR events keep the current `github.ref` behavior.

Accepted trade-off: PR runs now benchmark the branch tip in isolation, not merged-with-target-branch content. Numbers were already documented as best-effort on shared hosted runners (see `.github/workflows/benchmark.yml` comment), so this is not a meaningful regression in practice.

- [ ] **Step 1: Write the failing test**

```python
class TestCheckoutRefForPRs:
    def test_checkout_uses_conditional_ref(self, action_text):
        assert (
            "ref: ${{ github.event_name == 'pull_request' && "
            "(github.event.pull_request.head.repo.full_name == github.repository && "
            "github.head_ref || github.event.pull_request.head.sha) || github.ref }}"
        ) in action_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestCheckoutRefForPRs -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

Change:

```yaml
    - name: Checkout
      uses: actions/checkout@v4
      with:
        fetch-depth: 2
        token: ${{ inputs.github-token }}
```

to:

```yaml
    - name: Checkout
      uses: actions/checkout@v4
      with:
        ref: ${{ github.event_name == 'pull_request' && (github.event.pull_request.head.repo.full_name == github.repository && github.head_ref || github.event.pull_request.head.sha) || github.ref }}
        fetch-depth: 2
        token: ${{ inputs.github-token }}
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestCheckoutRefForPRs -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "fix(action): checkout PR head branch instead of synthetic merge ref"
```

---

### Task 3: Compare `should_update` against the target branch's baseline, not the current branch's own

**Files:**
- Modify: `action.yml:255-278` (`Check whether baseline needs updating` step)
- Test: `tests/test_action_wiring.py`

Today this step decides whether to persist a new baseline by comparing against `${sanitized_current_branch}.json` — which only coincided with the right file when the current branch happened to be `main` on a `push` event. Now that the commit always targets the *base/target* branch's file, the update decision must compare against that same file (`steps.load-main-baseline.outputs.main_baseline_path`), and only makes sense on `pull_request` events.

- [ ] **Step 1: Write the failing test**

```python
class TestCheckUpdateAgainstTargetBaseline:
    def _step_block(self, action_text):
        block = re.search(
            r"- name: Check whether baseline needs updating\n(?:.*\n)+?\n    - name:",
            action_text,
        )
        assert block, "step block not found"
        return block.group(0)

    def test_gated_on_pull_request(self, action_text):
        assert "if: github.event_name == 'pull_request'" in self._step_block(action_text)

    def test_compares_against_main_baseline_path(self, action_text):
        block = self._step_block(action_text)
        assert "steps.load-main-baseline.outputs.main_baseline_exists" in block
        assert "steps.load-main-baseline.outputs.main_baseline_path" in block
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestCheckUpdateAgainstTargetBaseline -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

Replace the whole `Check whether baseline needs updating` step:

```yaml
    - name: Check whether baseline needs updating
      shell: bash
      id: check-update
      run: |
        SCRIPT_DIR="${{ github.action_path }}/scripts"
        SANITIZED="${{ steps.branch.outputs.sanitized_branch }}"
        BASELINE_FILE="${{ inputs.baselines-dir }}/${SANITIZED}.json"

        if [ ! -f "${BASELINE_FILE}" ]; then
          echo "should_update=true" >> "$GITHUB_OUTPUT"
          echo "No existing baseline — will create."
        else
          if python "${SCRIPT_DIR}/benchmark_compare.py" compare-json \
            "${BASELINE_FILE}" \
            "${{ inputs.benchmark-results-file }}" \
            --tolerance="${{ inputs.update-tolerance }}" \
            > /dev/null 2>&1; then
            echo "should_update=false" >> "$GITHUB_OUTPUT"
            echo "Baseline within update tolerance — skipping update."
          else
            echo "should_update=true" >> "$GITHUB_OUTPUT"
            echo "Baseline changed beyond update tolerance — will update."
          fi
        fi
```

with:

```yaml
    - name: Check whether baseline needs updating
      if: github.event_name == 'pull_request'
      shell: bash
      id: check-update
      run: |
        SCRIPT_DIR="${{ github.action_path }}/scripts"

        if [ "${{ steps.load-main-baseline.outputs.main_baseline_exists }}" != "true" ]; then
          echo "should_update=true" >> "$GITHUB_OUTPUT"
          echo "No existing baseline for '${{ github.base_ref }}' — will create."
        else
          if python "${SCRIPT_DIR}/benchmark_compare.py" compare-json \
            "${{ steps.load-main-baseline.outputs.main_baseline_path }}" \
            "${{ inputs.benchmark-results-file }}" \
            --tolerance="${{ inputs.update-tolerance }}" \
            > /dev/null 2>&1; then
            echo "should_update=false" >> "$GITHUB_OUTPUT"
            echo "Baseline within update tolerance — skipping update."
          else
            echo "should_update=true" >> "$GITHUB_OUTPUT"
            echo "Baseline changed beyond update tolerance — will update."
          fi
        fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestCheckUpdateAgainstTargetBaseline -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "fix(action): gate should_update on PR vs target-branch baseline"
```

---

### Task 4: Save the PR's results under the target branch's filename

**Files:**
- Modify: `action.yml` — new step inserted immediately after `Save baseline` (currently `action.yml:280-287`)
- Test: `tests/test_action_wiring.py`

The existing `Save baseline` step is untouched — it still writes `${sanitized_current_branch}.json` to the working tree for the (separate, unaffected) sequential-comparison feature. This new step additionally writes the target branch's file (e.g. `main.json`) from this same PR's results, only when `should_update`, so it's ready to commit in Task 5.

- [ ] **Step 1: Write the failing test**

```python
class TestSaveBaselineForTargetBranch:
    def test_step_present(self, action_text):
        assert "- name: Save baseline for target branch (PR only)" in action_text

    def test_step_gated_and_uses_base_ref(self, action_text):
        block = re.search(
            r"- name: Save baseline for target branch \(PR only\)\n(?:.*\n)+?\n    - name:",
            action_text,
        )
        assert block, "step block not found"
        text = block.group(0)
        assert "if: github.event_name == 'pull_request' && steps.check-update.outputs.should_update == 'true'" in text
        assert 'benchmark_baseline.py" save' in text
        assert '"${{ github.base_ref }}"' in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestSaveBaselineForTargetBranch -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

Immediately after the existing `Save baseline` step (which stays exactly as-is):

```yaml
    - name: Save baseline
      shell: bash
      run: |
        SCRIPT_DIR="${{ github.action_path }}/scripts"
        python "${SCRIPT_DIR}/benchmark_baseline.py" save \
          "${{ steps.branch.outputs.current_branch }}" \
          "${{ inputs.benchmark-results-file }}" \
          --baselines-dir="${{ inputs.baselines-dir }}"
```

insert:

```yaml
    - name: Save baseline for target branch (PR only)
      if: github.event_name == 'pull_request' && steps.check-update.outputs.should_update == 'true'
      shell: bash
      run: |
        SCRIPT_DIR="${{ github.action_path }}/scripts"
        python "${SCRIPT_DIR}/benchmark_baseline.py" save \
          "${{ github.base_ref }}" \
          "${{ inputs.benchmark-results-file }}" \
          --baselines-dir="${{ inputs.baselines-dir }}"
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestSaveBaselineForTargetBranch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "feat(action): stage target-branch baseline file from PR results"
```

---

### Task 5: Commit the staged baseline onto the PR branch (same-repo PRs only)

**Files:**
- Modify: `action.yml:289-298` (`Commit baseline (push events only)` step)
- Test: `tests/test_action_wiring.py`

Replaces the `push`-event commit with one scoped to `pull_request` + same-repo (skips forks — `GITHUB_TOKEN` can't push to a fork's branch, same limitation as before, just now the only path baselines ever update through). `add:` is scoped to exactly the one staged file so this commit never accidentally sweeps in the current branch's own (unrelated, untouched) baseline snapshot from the `Save baseline` step. Since `Checkout` (Task 2) already leaves same-repo PRs on an attached branch, the default `push: true` (`git push origin <current-branch> --set-upstream`) just works — no custom refspec needed.

- [ ] **Step 1: Write the failing test**

```python
class TestBaselineCommitLandsOnPRBranch:
    def test_step_renamed(self, action_text):
        assert "- name: Commit staged baseline to PR branch (same-repo PRs only)" in action_text
        assert "Commit baseline (push events only)" not in action_text

    def test_gated_on_same_repo_pull_request(self, action_text):
        block = re.search(
            r"- name: Commit staged baseline to PR branch \(same-repo PRs only\)\n(?:.*\n)+?\n    - name:",
            action_text,
        )
        assert block, "step block not found"
        text = block.group(0)
        assert "github.event_name == 'pull_request'" in text
        assert "steps.check-update.outputs.should_update == 'true'" in text
        assert "github.event.pull_request.head.repo.full_name == github.repository" in text

    def test_commit_scoped_to_single_baseline_file(self, action_text):
        assert (
            'add: "${{ inputs.baselines-dir }}/${{ steps.load-main-baseline.outputs.sanitized_target_branch }}.json"'
            in action_text
        )
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestBaselineCommitLandsOnPRBranch -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

Replace:

```yaml
    - name: Commit baseline (push events only)
      if: github.event_name == 'push' && steps.check-update.outputs.should_update == 'true'
      uses: EndBug/add-and-commit@v9
      with:
        add: "${{ inputs.baselines-dir }}/"
        default_author: github_actions
        message: >-
          chore(benchmark): update baseline for branch "${{ steps.branch.outputs.current_branch }}"
          (node: ${{ steps.extract-node.outputs.node }}) [skip ci]
        push: true
```

with:

```yaml
    - name: Commit staged baseline to PR branch (same-repo PRs only)
      if: >-
        github.event_name == 'pull_request' &&
        steps.check-update.outputs.should_update == 'true' &&
        github.event.pull_request.head.repo.full_name == github.repository
      uses: EndBug/add-and-commit@v9
      with:
        add: "${{ inputs.baselines-dir }}/${{ steps.load-main-baseline.outputs.sanitized_target_branch }}.json"
        default_author: github_actions
        message: >-
          chore(benchmark): update baseline for branch "${{ github.base_ref }}"
          (node: ${{ steps.extract-node.outputs.node }}) [skip ci]
        push: true
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestBaselineCommitLandsOnPRBranch -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "fix(action): commit staged baseline to the PR branch, not push-to-main"
```

---

### Task 6: Fix the `baseline-updated` output gate

**Files:**
- Modify: `action.yml:300-337` (`Set outputs` step)
- Test: `tests/test_action_wiring.py`

- [ ] **Step 1: Write the failing test**

```python
class TestBaselineUpdatedOutputGate:
    def test_gated_on_same_repo_pull_request(self, action_text):
        assert (
            'SAME_REPO_PR="${{ github.event_name == \'pull_request\' && '
            'github.event.pull_request.head.repo.full_name == github.repository }}"'
        ) in action_text
        assert '[ "${UPDATE}" = "true" ] && [ "${SAME_REPO_PR}" = "true" ]' in action_text

    def test_old_push_gate_removed(self, action_text):
        assert '[ "${{ github.event_name }}" = "push" ] && [ "${UPDATE}" = "true" ]' not in action_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestBaselineUpdatedOutputGate -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

Replace:

```yaml
        UPDATE="${{ steps.check-update.outputs.should_update }}"
        if [ "${{ github.event_name }}" = "push" ] && [ "${UPDATE}" = "true" ]; then
          echo "baseline-updated=true" >> "$GITHUB_OUTPUT"
        else
          echo "baseline-updated=false" >> "$GITHUB_OUTPUT"
        fi
```

with:

```yaml
        UPDATE="${{ steps.check-update.outputs.should_update }}"
        SAME_REPO_PR="${{ github.event_name == 'pull_request' && github.event.pull_request.head.repo.full_name == github.repository }}"
        if [ "${UPDATE}" = "true" ] && [ "${SAME_REPO_PR}" = "true" ]; then
          echo "baseline-updated=true" >> "$GITHUB_OUTPUT"
        else
          echo "baseline-updated=false" >> "$GITHUB_OUTPUT"
        fi
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestBaselineUpdatedOutputGate -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "fix(action): gate baseline-updated output on same-repo PR, not push"
```

---

### Task 7: Make the PR comment fork-aware

**Files:**
- Modify: `action.yml:339-459` (`Post PR comment` step: `env:` block and the `updateNote` logic in the script)
- Test: `tests/test_action_wiring.py`

Without this, a fork PR whose results exceed `update-tolerance` would still show "will be updated on merge" even though the commit is always skipped for forks (Task 5) — misleading.

- [ ] **Step 1: Write the failing test**

```python
class TestForkAwareBaselineNote:
    def test_is_fork_env_wired(self, action_text):
        assert (
            "IS_FORK: ${{ github.event.pull_request.head.repo.full_name != github.repository }}"
            in action_text
        )

    def test_update_note_branches_on_fork(self, action_text):
        assert "process.env.IS_FORK === 'true'" in action_text
        assert "can't be committed back" in action_text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_action_wiring.py::TestForkAwareBaselineNote -v`
Expected: FAIL

- [ ] **Step 3: Edit `action.yml`**

In the `Post PR comment` step's `env:` block, after the `PREV_COMPARISON_SKIPPED` line, add:

```yaml
        PREV_COMPARISON_SKIPPED: ${{ steps.compare-prev.outputs.prev_comparison_skipped }}
        IS_FORK: ${{ github.event.pull_request.head.repo.full_name != github.repository }}
```

(only the new `IS_FORK:` line is added; `PREV_COMPARISON_SKIPPED:` stays where it is.)

Then replace, inside the `script:` block:

```js
          const updateNote = process.env.SHOULD_UPDATE === 'true'
            ? `💾 **Baseline Update:** Will be updated on merge`
            : `⏭️ **Baseline Update:** Skipped (within ${process.env.UPDATE_TOLERANCE}% threshold)`;
```

with:

```js
          const isFork = process.env.IS_FORK === 'true';
          const updateNote = process.env.SHOULD_UPDATE !== 'true'
            ? `⏭️ **Baseline Update:** Skipped (within ${process.env.UPDATE_TOLERANCE}% threshold)`
            : isFork
              ? `⚠️ **Baseline Update:** Change detected, but this PR is from a fork — baselines can't be committed back. Update it manually after merging if needed.`
              : `💾 **Baseline Update:** Staged on this branch — will land on \`${process.env.BASE_REF}\` when this PR merges.`;
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_action_wiring.py::TestForkAwareBaselineNote -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add action.yml tests/test_action_wiring.py
git commit -m "fix(action): make the PR-comment baseline-update note fork-aware"
```

---

### Task 8: Run the full unit + wiring suite and the local self-test harness

**Files:** none (verification only)

- [ ] **Step 1: Run the full test suite**

Run: `python -m pytest tests/ -v`
Expected: all tests PASS, including every new class from Tasks 1-7 and every pre-existing test in `test_action_wiring.py`, `test_benchmark_baseline.py`, `test_benchmark_compare.py`, `test_real_output.py`.

- [ ] **Step 2: Run the local end-to-end harness**

Run: `sh scripts/selftest.sh`
Expected: `SELFTEST FAIL` never printed; every `[n/7] ... ok:` line prints and the script exits 0. (This harness drives the Python scripts directly, not `action.yml`'s GitHub-Actions-only wiring, so it won't catch YAML mistakes — Task 1-7's tests are what cover that surface.)

- [ ] **Step 3: If anything fails**

Stop. Re-open the specific task above whose test now fails, re-diff `action.yml` against the "Edit" block for that task, fix, and re-run just that task's test before moving on. Do not proceed to Task 9 with a red suite.

---

### Task 9: Drop the `push` trigger from the self-test workflow

**Files:**
- Modify: `.github/workflows/benchmark.yml`

- [ ] **Step 1: Edit the trigger and header comment**

Replace:

```yaml
# Dogfoods pytest-bench-action against its own sample suite in bench/.
# Proves action.yml runs end-to-end. Note: GitHub-hosted runners get a fresh
# hostname per job, so cross-run baseline comparison here is best-effort — the
# value is exercising the full step wiring, not stable numbers.

on:
  push:
    branches: [main]
  pull_request:
```

with:

```yaml
# Dogfoods pytest-bench-action against its own sample suite in bench/.
# Proves action.yml runs end-to-end. Note: GitHub-hosted runners get a fresh
# hostname per job, so cross-run baseline comparison here is best-effort — the
# value is exercising the full step wiring, not stable numbers.
#
# PR-only trigger: baseline updates are staged as a commit on the PR branch
# and land on main when the PR merges — no push trigger, no direct commit to
# a (potentially rule-protected) main branch.

on:
  pull_request:
```

- [ ] **Step 2: Verify**

Run: `grep -A2 "^on:" .github/workflows/benchmark.yml`
Expected: only `pull_request:` under `on:`, no `push:` block.

- [ ] **Step 3: Commit**

```bash
git add .github/workflows/benchmark.yml
git commit -m "chore(ci): trigger the self-test workflow on pull_request only"
```

---

### Task 10: Update the copy-paste reference workflow

**Files:**
- Modify: `docs/example-workflow.yml`

- [ ] **Step 1: Replace the whole file**

```yaml
# Reference workflow for pytest-bench-action.
# Copy into your repo as .github/workflows/benchmark.yml and adjust the
# setup/benchmark commands to your project.
#
# Notes:
# - The action performs its own checkout (fetch-depth: 2); you do NOT need
#   an actions/checkout step before it.
# - Trigger on pull_request only. Baseline updates are staged as a commit on
#   the PR branch itself and land on the target branch when the PR merges —
#   no push trigger needed, and a direct push would fail anyway on a branch
#   protected to require PR-only changes.
# - contents:write is needed to push that staged baseline commit onto the PR
#   branch (same-repo PRs only — forks are skipped automatically);
#   pull-requests:write is needed to post the PR comment.
# - Comparability is judged on the CPU fingerprint (machine_info.cpu), not the
#   runner hostname, so hosted runners compare cleanly on the same CPU model.
#   enforce-same-node: "false" (default) skips with a warning on a genuine
#   hardware mismatch; "true" fails on one (use on a stable/self-hosted runner).
# - To merge a PR with an intentional regression, add the "benchmark-override"
#   label to it (configurable via override-label): the regression is still
#   reported in the PR comment but does not fail the job.

name: Benchmarks

on:
  pull_request:

permissions:
  contents: write
  pull-requests: write

jobs:
  benchmark:
    runs-on: ubuntu-latest
    steps:
      - name: Run benchmarks and compare against baselines
        id: bench
        uses: lennardzuendorf/pytest-bench-action@v1
        with:
          github-token: ${{ secrets.GITHUB_TOKEN }}
          python-version: "3.14"
          setup-command: pip install -e ".[dev]"
          benchmark-run-command: >
            pytest tests/benchmarks
            --benchmark-only
            --benchmark-json=benchmark-results.json
            -v
          cross-branch-tolerance: 20
          update-tolerance: 5
          threshold-map: '{"e2e_create": 30.0, "e2e_search": 5.0, "help": 0.5}'
          # Compared on CPU fingerprint, not hostname: same CPU compares even
          # with a fresh node name. "false" skips (don't fail) on a genuine
          # hardware mismatch; "true" fails (use on a stable/self-hosted runner).
          enforce-same-node: "false"
          # PR label that waives a regression for a single PR (default shown).
          override-label: benchmark-override

      # Outputs are available to later steps, e.g. for custom notifications:
      - name: Show outcome
        if: always()
        run: |
          echo "regression-detected:   ${{ steps.bench.outputs.regression-detected }}"
          echo "regression-overridden: ${{ steps.bench.outputs.regression-overridden }}"
          echo "comparison-skipped:    ${{ steps.bench.outputs.comparison-skipped }}"
          echo "baseline-updated:      ${{ steps.bench.outputs.baseline-updated }}"
          echo "node:                  ${{ steps.bench.outputs.node }}"
```

- [ ] **Step 2: Verify**

Run: `grep -c "^  push:" docs/example-workflow.yml`
Expected: `0`

- [ ] **Step 3: Commit**

```bash
git add docs/example-workflow.yml
git commit -m "docs(example-workflow): trigger on pull_request only"
```

---

### Task 11: Update README — How It Works, Troubleshooting, and the new Suggested Usage table

**Files:**
- Modify: `README.md`

- [ ] **Step 1: Update "How It Works" step 4**

Replace:

```markdown
4. **Commits updated baseline** on push events (with `[skip ci]` to prevent loops)
```

with:

```markdown
4. **Stages an updated baseline commit** on your PR branch when the result exceeds `update-tolerance` (same-repo PRs only, with `[skip ci]` to prevent loops) — it lands on the target branch automatically when the PR merges
```

- [ ] **Step 2: Insert the "Suggested Usage" section**

Immediately after the "How It Works" section (after the paragraph ending `...see [docs/example-workflow.yml](docs/example-workflow.yml) for a complete reference workflow.` and before `## Runner hardware and hosted runners`), insert:

````markdown
## Suggested Usage

Trigger on `pull_request` only. A separate `push` trigger for baseline
maintenance isn't needed — the baseline update rides along inside the PR
itself and lands naturally when the PR merges. It also avoids a real failure
mode: repos with a ruleset requiring PR-only changes on the target branch
reject any direct push, including this action's own baseline commit.

| Event | What the action does |
|-------|-----------------------|
| PR opened / synchronized | Runs your benchmark command on the PR branch tip, compares against the target branch's committed baseline (`cross-branch-tolerance`), posts/updates the PR comment. |
| Result differs from the target baseline by more than `update-tolerance` | Stages a baseline-update commit **on the PR branch itself** (`[skip ci]`) — same-repo PRs only, skipped for forks. |
| PR merged | The staged commit is already part of the PR, so it lands on the target branch as part of the normal merge. No separate rerun, no direct push to the target branch. |

```yaml
on:
  pull_request:
```
````

- [ ] **Step 3: Fix the "First run" troubleshooting entry**

Replace:

```markdown
**First run / "No baseline found".** Expected: there is nothing to compare against yet. The action skips the comparison, notes it in the PR comment, and saves a baseline. On the next push to your default branch the baseline is committed and comparisons start working.
```

with:

```markdown
**First run / "No baseline found".** Expected: there is nothing to compare against yet. The action skips the comparison and notes it in the PR comment. Open (or update) a PR against that branch — the action stages a baseline commit on the PR branch, which lands and comparisons start working once that PR merges.
```

- [ ] **Step 4: Fix the "Fork PRs" troubleshooting entry**

Replace:

```markdown
**Fork PRs don't update baselines.** By design: forks have no write access to your repo, so the baseline commit only happens on `push` events. The comparison and PR comment still run.
```

with:

```markdown
**Fork PRs don't update baselines.** By design: the action can't push commits back to a fork, so the baseline-update commit is skipped for fork PRs. The comparison and PR comment still run — update the baseline manually afterward if needed.
```

- [ ] **Step 5: Add a permissions clarification**

After the `Required Permissions` code block (`permissions:\n  contents: write\n  pull-requests: write`), add:

```markdown

`contents: write` pushes the staged baseline commit onto the PR branch (same-repo PRs only); `pull-requests: write` posts the PR comment.
```

- [ ] **Step 6: Verify**

Run: `grep -n "Suggested Usage\|will be updated on merge\|push events" README.md`
Expected: `## Suggested Usage` present; the old literal string `will be updated on merge` gone (superseded by the fork-aware note added in Task 7 and the table above); any remaining `push events` mentions are the unrelated, still-accurate `override-label` note ("regressions on `push` events are always enforced").

- [ ] **Step 7: Commit**

```bash
git add README.md
git commit -m "docs(readme): document PR-only baseline commit flow + suggested usage table"
```

---

### Task 12: Update AGENTS.md to match the new mechanism

**Files:**
- Modify: `AGENTS.md:29` (Critical Constraints)
- Modify: `AGENTS.md:128-131` (Core Logic step 8)
- Modify: `AGENTS.md:166-167` (Edge Cases table)
- Modify: `AGENTS.md:210` (Best Practices DON'T)

- [ ] **Step 1: Reword the hard constraint (line 29)**

Replace:

```markdown
- **NEVER commit baselines on PR events** — only save to working tree on PRs
```

with:

```markdown
- **NEVER push a baseline commit directly to the target/protected branch** — stage it on the PR branch itself (same-repo PRs only) so it lands via the normal PR merge
```

- [ ] **Step 2: Rewrite Core Logic step 8 (lines 128-131)**

Replace:

```markdown
### 8. Commit Baseline
- **Only on `push` events** AND `should_update == 'true'`
- Uses `EndBug/add-and-commit@v9`
- Message: `chore(benchmark): update baseline for branch "..." (node: ...) [skip ci]`
```

with:

```markdown
### 8. Commit Baseline
- **Only on `pull_request` events**, `should_update == 'true'`, and same-repo (not a fork)
- `should_update` compares this PR's results against the **target branch's** committed baseline
- Commits the staged file (named after the **target** branch, e.g. `main.json`) **onto the PR branch** via `EndBug/add-and-commit@v9` — never a direct push to the target/protected branch
- Message: `chore(benchmark): update baseline for branch "..." (node: ...) [skip ci]`
- Lands on the target branch automatically when the PR merges — no separate post-merge rerun
```

- [ ] **Step 3: Fix the Edge Cases table (lines 166-167)**

Replace:

```markdown
| Push to main | Compare HEAD~1; commit new baseline if changed |
| PR from fork | Skip baseline commit, still post comment |
```

with:

```markdown
| PR merges | Staged baseline commit (already part of the PR) lands on the target branch — no rerun |
| PR from fork | Skip baseline commit, still post comment |
```

- [ ] **Step 4: Fix the DON'T bullet (line 210)**

Replace:

```markdown
- NEVER commit baselines on PR events
```

with:

```markdown
- NEVER push a baseline commit directly to a protected/target branch — stage it on the PR branch so it lands via merge
```

- [ ] **Step 5: Verify**

Run: `grep -n "push events\|Push to main" AGENTS.md`
Expected: no remaining references to the old push-triggered commit mechanism.

- [ ] **Step 6: Commit**

```bash
git add AGENTS.md
git commit -m "docs(agents): document PR-branch baseline commit mechanism"
```

---

### Task 13: Live-validate the mechanism on a real PR (do not skip)

**Files:** none (manual GitHub verification)

This is the resolution to the "Known Risk" section above. Tasks 1-12 are locally verifiable (unit tests, text assertions) but cannot prove GitHub's live ruleset/CodeQL behavior cooperates — only a real PR can.

- [ ] **Step 1: Open a real PR that forces a baseline update**

Branch off `main`, tweak `bench/test_sample_benchmark.py` (or any file under `bench/`) so a benchmark's timing measurably changes by more than `update-tolerance` (10% in `.github/workflows/benchmark.yml`'s self-test config) — e.g. add a trivial `time.sleep(0.01)` to one of the benchmarked functions. Push, open a PR against `main`.

- [ ] **Step 2: Watch the `Benchmark (self-test)` job**

Confirm in the Actions log: `should_update=true`, `Save baseline for target branch (PR only)` runs, `Commit staged baseline to PR branch (same-repo PRs only)` runs and pushes.

- [ ] **Step 3: Confirm the commit landed on the PR branch**

Run: `git fetch origin <your-branch> && git log origin/<your-branch> -3 --oneline`
Expected: a new `chore(benchmark): update baseline for branch "main" ... [skip ci]` commit on top, authored by `github-actions`.

- [ ] **Step 4: Confirm CodeQL re-analyzes the new head commit**

Run: `gh api repos/LennardZuendorf/pytest-bench-action/code-scanning/analyses --jq '.[] | select(.commit_sha=="<new-head-sha>")'`
Expected: at least one result (ideally both `python` and `actions` categories) for that exact SHA, within a few minutes of the push.

- [ ] **Step 5: Confirm the PR is mergeable**

Run: `gh pr view <number> --repo LennardZuendorf/pytest-bench-action --json mergeable,mergeStateStatus`
Expected: `mergeable: "MERGEABLE"` (once the required review is also satisfied) — critically, **not** stuck on a `code_scanning` block referencing the old (pre-bot-commit) SHA.

- [ ] **Step 6a: If it works** — merge the PR, confirm `main.json` in the merge commit reflects the new numbers, and close out this plan.

- [ ] **Step 6b: If the PR is stuck on a stale code-scanning check** — this confirms the "Known Risk" section's concern. Do not force-merge or bypass the ruleset to work around it. Come back and re-open the design conversation: the fallback (PAT-based commit + job-level loop guard, sketched in "Known Risk" above) needs its own brainstorming pass rather than a quick patch, since it reintroduces the loop-prevention question from scratch.

---

## Self-Review (run before handing off)

1. **Spec coverage:** Every element of the confirmed design — checkout ref, `should_update` retarget, staged save, commit retarget, outputs gate, fork-aware comment, both workflow files, README, AGENTS.md — has exactly one task above. No gaps.
2. **Placeholder scan:** No `TBD`/`TODO`; every step shows the literal before/after text or literal new file content.
3. **Type/name consistency:** `sanitized_target_branch` (Task 1) is the exact name referenced in Task 5's `add:` path. `IS_FORK` (Task 7) matches `github.event.pull_request.head.repo.full_name != github.repository` used identically in Tasks 5 and 6 (as `==`, inverted correctly for the "is fork" vs "is same-repo" checks). `should_update` (Task 3's output) is the exact id referenced in Tasks 4, 5, 6.
4. **Ordering:** Tasks 1-7 must land before Task 8 (verification) before Tasks 9-12 (docs) — each task's tests depend on the previous task's edits being in place (e.g. Task 5's test references `steps.load-main-baseline.outputs.sanitized_target_branch`, which only exists after Task 1).

---

## Execution Handoff

Two ways to run this:

**1. Subagent-Driven (recommended)** — a fresh subagent per task, with review between tasks, fast iteration. Requires **superpowers:subagent-driven-development**.

**2. Inline Execution** — execute tasks in this session in order, with checkpoints for review. Requires **superpowers:executing-plans**.
