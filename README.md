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
| `python-version` | No | `"3.14"` | Python version for consistent benchmarks |
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
