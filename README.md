# pytest-bench-action

A reusable GitHub Action that runs `pytest-benchmark`, manages per-branch baselines committed to your repository, compares results against those baselines, and posts a formatted summary comment on every PR.

## Usage

Add the action as a step in a workflow file in your repository — create
`.github/workflows/benchmark.yml` (any name works) and drop this step into a
job. The action does its own checkout, so it's the only step you need. For a
complete, copy-pasteable job (triggers, permissions, runner) see
[docs/example-workflow.yml](docs/example-workflow.yml).

```yaml
- uses: lennardzuendorf/pytest-bench-action@v1
  with:
    github-token: ${{ secrets.GITHUB_TOKEN }}
    setup-command: pip install -e ".[dev]"
    benchmark-run-command: >
      pytest tests/benchmarks
      --benchmark-only
      --benchmark-json=benchmark-results.json
      -v
    threshold-map: '{"e2e_create": 30.0, "e2e_search": 5.0, "help": 0.5}'
    cross-branch-tolerance: 20
    update-tolerance: 5
    # Comparability is judged on the CPU fingerprint, not the hostname, so
    # hosted runners compare cleanly on the same CPU. "false" skips (with a
    # warning) on a genuine hardware mismatch; set "true" on a stable/self-hosted
    # runner to fail on one instead.
    enforce-same-node: "false"
```

## Inputs

| Input | Required | Default | Description |
|-------|----------|---------|-------------|
| `python-version` | No | `"3.14"` | Python version for consistent benchmarks (default tracks latest stable; pin an older version if your runner image lacks it) |
| `benchmark-run-command` | **Yes** | — | Full shell command to run benchmarks |
| `setup-command` | No | `""` | Shell command to install dependencies |
| `pre-benchmark-command` | No | `""` | Optional warm-up command run after deps install |
| `benchmark-results-file` | No | `benchmark-results.json` | Path to the JSON output from pytest-benchmark |
| `cross-branch-tolerance` | No | `20` | % increase allowed vs main branch baseline |
| `update-tolerance` | No | `5` | % change threshold that triggers a baseline update |
| `baselines-dir` | No | `.benchmarks/baselines` | Repo-relative path where baseline JSONs are stored |
| `github-token` | **Yes** | — | `${{ secrets.GITHUB_TOKEN }}` |
| `threshold-map` | No | `""` | JSON string mapping test name substrings to max-seconds thresholds |
| `enforce-same-node` | No | `"false"` | Hardware-mismatch handling. Comparability is judged on the CPU fingerprint, not the hostname. `"true"` fails the job on a genuinely different CPU (stable/self-hosted runners); `"false"` skips that comparison with a warning. See [Runner hardware](#runner-hardware-and-hosted-runners). |
| `override-label` | No | `benchmark-override` | PR label that waives a regression for that one PR — the regression is still reported but does not fail the job. See [Accepting a known regression](#accepting-a-known-regression). |

## Outputs

| Output | Description |
|--------|-------------|
| `regression-detected` | `"true"` / `"false"` — a benchmark exceeded tolerance |
| `baseline-updated` | `"true"` / `"false"` — a baseline commit was made |
| `node` | Hostname extracted from `machine_info.node` |
| `comparison-skipped` | `"true"` / `"false"` — a comparison was skipped because it ran on a different runner node (`enforce-same-node: false`) |
| `regression-overridden` | `"true"` / `"false"` — a regression was detected but waived by the override label |

## Required Permissions

```yaml
permissions:
  contents: write
  pull-requests: write
```

`contents: write` pushes the staged baseline commit onto the PR branch (same-repo PRs only); `pull-requests: write` posts the PR comment.

## How It Works

1. **Loads baselines** from git history (target branch + previous commit)
2. **Runs your benchmark command** via `benchmark-run-command`
3. **Compares results** against both baselines with configurable tolerance
4. **Stages an updated baseline commit** on your PR branch when the result exceeds `update-tolerance` (same-repo PRs only, with `[skip ci]` to prevent loops) — it lands on the target branch automatically when the PR merges
5. **Posts a PR comment** with a formatted table of results and comparisons
6. **Fails the job** if any benchmark regressed beyond tolerance — after the comment and artifact are published, so you always get the full report

The action checks out your repository itself (`fetch-depth: 2`); you don't need a separate `actions/checkout` step. See [docs/example-workflow.yml](docs/example-workflow.yml) for a complete reference workflow.

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

## Runner hardware and hosted runners

Timing numbers are only comparable on the same hardware. The action judges
comparability on a **CPU/system fingerprint** — `machine_info.cpu.brand_raw` +
`arch` + core count + `system` — **not** the hostname (`machine_info.node`). The
hostname is randomized on every GitHub-hosted job, so keying on it would skip
every comparison after the first; the CPU fingerprint is stable across those
ephemeral hostnames, so two `ubuntu-latest` runs on the same CPU model compare
cleanly. (When a run predates the `cpu` block — minimal/legacy output — it falls
back to the hostname.)

`enforce-same-node` decides what happens when the current run's **hardware**
differs from the baseline's:

- **`enforce-same-node: "false"` (default)** — the comparison is **skipped** with
  a `::warning::`, a PR-comment note, and `comparison-skipped=true`. The job does
  **not** fail. Sensible default for hosted runners.
- **`enforce-same-node: "true"`** — a hardware mismatch **fails** the job. Use on
  a **stable/self-hosted runner**, where a different CPU is a real misconfiguration.

Caveat: GitHub rotates its hosted pool across CPU generations, so occasionally
two `ubuntu-latest` jobs land on different CPUs and the comparison is skipped;
and shared-VM noise is not removed by fingerprinting (the `cross-branch-tolerance`
absorbs it). For the most reliable numbers, use a stable/self-hosted runner and
set `enforce-same-node: "true"`.

## Accepting a known regression

Sometimes a PR is intentionally slower and you want to merge it anyway without
loosening tolerances for the whole repo. Add the **`benchmark-override`** label
(configurable via `override-label`) to that pull request:

- the regression is **still detected and still shown** in the PR comment (marked
  as overridden) and in the `regression-overridden` output;
- but the **job does not fail**.

The waiver is scoped to that one PR and self-clearing — remove the label to
re-enforce. It only applies on `pull_request` events; regressions on `push`
events are always enforced.

## Troubleshooting

**First run / "No baseline found".** Expected: there is nothing to compare against yet. The action skips the comparison and notes it in the PR comment. Open (or update) a PR against that branch — the action stages a baseline commit on the PR branch, which lands and comparisons start working once that PR merges.

**Hardware mismatch / "comparison skipped".** Comparability is judged on the CPU fingerprint (`machine_info.cpu`), not the hostname, so a fresh runner node name alone does **not** skip. A genuinely different CPU does: by default (`enforce-same-node: "false"`) that comparison is **skipped** with a warning and `comparison-skipped=true` — which can happen when GitHub's hosted pool rotates CPU generations. Set `enforce-same-node: "true"` on a stable/self-hosted runner to turn a hardware mismatch into a hard failure. See [Runner hardware and hosted runners](#runner-hardware-and-hosted-runners).

**Fork PRs don't update baselines.** By design: the action can't push commits back to a fork, so the baseline-update commit is skipped for fork PRs. The comparison and PR comment still run — update the baseline manually afterward if needed.

**Baseline commits re-triggering CI.** Baseline commit messages always end with `[skip ci]`. If your CI provider ignores that marker, exclude `chore(benchmark):` commits or the baselines directory from your triggers.

**`python-version` not available on the runner.** The default tracks the latest stable Python (currently `"3.14"`). On older runner images, pin `python-version: "3.12"` or `"3.13"`.

**Job fails with "Performance regression detected".** Working as intended — one or more benchmarks exceeded `cross-branch-tolerance` vs the baseline, or a benchmark present in the baseline is missing from the run. The PR comment and the step log contain the full comparison table. If the slow-down is intentional and you want to merge anyway, add the `benchmark-override` label to the PR (see [Accepting a known regression](#accepting-a-known-regression)) instead of loosening tolerances for the whole repo.

**My default branch isn't `main`.** Supported. The cross-branch comparison uses the PR's actual base branch (`github.base_ref`), and the PR comment is labelled accordingly. You just need a baseline committed on that branch (it appears after the first push to it).

## Development

This repo dogfoods itself.

```bash
# Unit tests for the helper scripts (needs pytest + pytest-benchmark)
python -m pytest tests/ -v

# End-to-end harness: runs the sample suite in bench/ and drives the full
# pipeline (run -> extract node -> compare -> save -> list -> regression)
# against real pytest-benchmark output. No GitHub required.
sh scripts/selftest.sh
```

- `bench/test_sample_benchmark.py` — a small, deterministic, stdlib-only
  pytest-benchmark suite used to exercise the action end-to-end.
- `.github/workflows/ci.yml` — runs the unit tests and the self-test on every
  push and PR.
- `.github/workflows/benchmark.yml` — runs the action against `bench/` via
  `uses: ./`, proving the full composite-action wiring on a real runner.
- `.github/workflows/release.yml` — one-click, test-gated release (tags +
  draft GitHub Release). See [docs/RELEASING.md](docs/RELEASING.md).
