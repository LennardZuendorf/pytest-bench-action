---
type: lessons
updated: 2026-06-09
---

# pytest-bench-action — Lessons & Gotchas

Mistakes made and rules to prevent repeating them. Review at the start of every
session. Tags make entries retrievable — scan for tags matching the work in hand.

---

### `[skip ci]` is non-negotiable on baseline commits
**Pattern:** The action commits baselines back to the repo. Without `[skip ci]` in the message, the push triggers another CI run, which commits another baseline — forever.
**Rule:** Every baseline commit message must end with `[skip ci]`. Never remove it.
**Tags:** ci, baseline, commit, action.yml, loop
**Date:** 2026-06-06

### Never compare benchmarks across machines
**Pattern:** `machine_info.node` is the runner hostname. Comparing a baseline from `runner-abc` against results from `runner-xyz` produces meaningless numbers — runner specs vary.
**Rule:** The node check in `benchmark_compare.py` is a hard `exit 1`, not a warning. Do not soften it.
**Tags:** node, comparison, benchmark_compare, machine_info
**Date:** 2026-06-06

### Stdlib only in `scripts/`
**Pattern:** The action scripts run inside the caller's environment, which we don't control. Any `import requests` or similar silently breaks every caller that lacks it.
**Rule:** Scripts use Python stdlib only — `json`, `pathlib`, `sys`, `datetime`. No third-party imports, no `pip install` in the action.
**Tags:** scripts, stdlib, dependencies, python
**Date:** 2026-06-06

### `fetch-depth: 2` on checkout
**Pattern:** Sequential baseline loading uses `git show HEAD~1:...`, which needs at least two commits of history. The default shallow clone (`fetch-depth: 1`) makes it fail silently.
**Rule:** Always set `fetch-depth: 2` on `actions/checkout`.
**Tags:** checkout, git, baseline, action.yml, fetch-depth
**Date:** 2026-06-06

### PR from fork can't commit a baseline
**Pattern:** Forks have no write access to the upstream repo, so the baseline commit step cannot run on fork PRs.
**Rule:** Gate the baseline commit on `github.event_name == 'push'`, never `pull_request`. Never remove that condition.
**Tags:** fork, pull_request, commit, baseline, permissions
**Date:** 2026-06-06

### Default `python-version: "3.14"` may not exist on a runner
**Pattern:** Python 3.14 may be missing on older runner images, causing setup to fail in ways that look unrelated.
**Rule:** `python-version` is configurable; when debugging caller failures, first check whether it needs pinning to `"3.12"` / `"3.13"`.
**Tags:** python-version, runner, setup-python, debugging
**Date:** 2026-06-06

---

## Design Decisions That Felt Weird But Are Correct

- **Two tolerance inputs** (`cross-branch-tolerance` vs `update-tolerance`): the first catches regressions on PRs; the second decides when to update the baseline. Merging them caused false baseline churn in early iterations.
- **Deleting the old PR comment before posting a new one**: just editing the existing comment leaves stale results when the benchmark set changes. Delete + create is cleaner and avoids races with the old body.
- **Stripping `data` arrays on baseline save**: pytest-benchmark stores every sample in `data`. We only need the aggregates (`mean`, `median`, …); stripping reduces file size by ~99%.
