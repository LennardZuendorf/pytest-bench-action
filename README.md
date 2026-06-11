# pytest-bench-action

A reusable GitHub Action that runs `pytest-benchmark`, manages per-branch baselines committed to your repository, compares results against those baselines, and posts a formatted summary comment on every PR.

## Usage

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

## Outputs

| Output | Description |
|--------|-------------|
| `regression-detected` | `"true"` / `"false"` |
| `baseline-updated` | `"true"` / `"false"` |
| `node` | Hostname extracted from `machine_info.node` |

## Required Permissions

```yaml
permissions:
  contents: write
  pull-requests: write
```

## How It Works

1. **Loads baselines** from git history (target branch + previous commit)
2. **Runs your benchmark command** via `benchmark-run-command`
3. **Compares results** against both baselines with configurable tolerance
4. **Commits updated baseline** on push events (with `[skip ci]` to prevent loops)
5. **Posts a PR comment** with a formatted table of results and comparisons
6. **Fails the job** if any benchmark regressed beyond tolerance — after the comment and artifact are published, so you always get the full report

The action checks out your repository itself (`fetch-depth: 2`); you don't need a separate `actions/checkout` step. See [docs/example-workflow.yml](docs/example-workflow.yml) for a complete reference workflow.

## Troubleshooting

**First run / "No baseline found".** Expected: there is nothing to compare against yet. The action skips the comparison, notes it in the PR comment, and saves a baseline. On the next push to your default branch the baseline is committed and comparisons start working.

**"cross-machine comparison is invalid" (node mismatch).** Baselines are tied to the runner hostname (`machine_info.node` in the benchmark JSON). Comparing numbers from different machines is meaningless, so the action fails hard instead. GitHub-hosted runners get a fresh hostname per job — for stable comparisons use a self-hosted runner (or any runner with a fixed hostname).

**Fork PRs don't update baselines.** By design: forks have no write access to your repo, so the baseline commit only happens on `push` events. The comparison and PR comment still run.

**Baseline commits re-triggering CI.** Baseline commit messages always end with `[skip ci]`. If your CI provider ignores that marker, exclude `chore(benchmark):` commits or the baselines directory from your triggers.

**`python-version` not available on the runner.** The default tracks the latest stable Python (currently `"3.14"`). On older runner images, pin `python-version: "3.12"` or `"3.13"`.

**Job fails with "Performance regression detected".** Working as intended — one or more benchmarks exceeded `cross-branch-tolerance` vs the baseline, or a benchmark present in the baseline is missing from the run. The PR comment and the step log contain the full comparison table.

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
