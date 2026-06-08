---
type: lessons
updated: 2026-06-06
---

# pytest-bench-action — Lessons & Gotchas

Read this at the start of each session to avoid repeating past mistakes.

---

## Hard-Learned Rules

### 1. `[skip ci]` is non-negotiable
The action commits baselines back to the repo. Without `[skip ci]` in the commit message, the push triggers another CI run, which triggers another baseline commit, forever. This has burned us before. Every baseline commit message must end with `[skip ci]`.

### 2. Never compare across machines
`machine_info.node` in the benchmark JSON is the runner hostname. If you compare a baseline from `runner-abc` against results from `runner-xyz`, the numbers mean nothing — runner specs vary. The node check in `benchmark_compare.py` is a hard exit, not a warning. Do not soften it.

### 3. Stdlib only in `scripts/`
The action scripts run inside the caller's environment. We have no control over what's installed. Adding any `import requests` or similar will silently break every caller that doesn't have it. `json`, `pathlib`, `sys`, `datetime` — that's the full list.

### 4. `fetch-depth: 2` on checkout
`git show HEAD~1:...` for sequential baseline loading requires at least 2 commits of history. The default `fetch-depth: 1` (shallow clone) will cause `git show HEAD~1` to fail silently. Always specify `fetch-depth: 2`.

### 5. PR from fork can't commit
Forks don't have write access to the upstream repo. The baseline commit step is conditional on `github.event_name == 'push'`, not `pull_request`. Never remove that condition.

### 6. Default `python-version: "3.14"` may break
Python 3.14 may not be available on older runner images. When helping users debug, the first thing to check is whether `python-version` needs to be pinned to `"3.12"` or `"3.13"`.

---

## Design Decisions That Felt Weird But Are Correct

- **Two tolerance inputs** (`cross-branch-tolerance` vs `update-tolerance`): The first is for catching regressions on PRs; the second is for deciding when to update the baseline. They serve different purposes. Merging them into one caused false baseline churn in early iterations.
- **Deleting the old PR comment before posting a new one**: Just updating the existing comment leaves stale results if the benchmark set changes. Deleting + creating is cleaner and avoids race conditions with the old comment body.
- **Stripping `data` arrays on baseline save**: pytest-benchmark stores every individual sample in `data`. For a 100-round benchmark this can be 100 floats. We only need the aggregates (`mean`, `median`, etc.). Stripping reduces file size by ~99%.
