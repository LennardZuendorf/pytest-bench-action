# Pre-commit Baseline Newline Fix Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Stop bot-committed baseline JSON from tripping pre-commit.ci, by (1) making `benchmark_baseline.py` write a trailing newline like a normal text file, and (2) adding standard hygiene hooks (`end-of-file-fixer`, `trailing-whitespace`, `check-json`) to `.pre-commit-config.yaml`, with `.benchmarks/baselines/` excluded from the first two but still covered by `check-json` as a corruption safety net.

**Architecture:** `scripts/benchmark_baseline.py::save()` currently writes baseline files via `out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")`, which produces no trailing `\n`. Appending `"\n"` to that write closes the root cause for all future baseline commits. Separately, `.pre-commit-config.yaml` has no `pre-commit-hooks` repo at all today, so the project has no general whitespace/EOF/JSON hygiene checks. Adding that repo (three hooks) plus an `exclude` regex on the baselines directory for the two hooks that would otherwise fight with machine-written JSON gives general hygiene everywhere else while treating `.benchmarks/baselines/` as generated data (still parse-checked via `check-json`).

**Tech Stack:** Python 3.x stdlib (`json`, `pathlib`), pytest + `pytest-benchmark` for tests, `pre-commit` with `pre-commit-hooks` (upstream `https://github.com/pre-commit/pre-commit-hooks`).

## Global Constraints

- Stdlib only in `scripts/` — no third-party packages (per `CLAUDE.md`).
- Idempotency: re-running `save()` on the same branch must still produce a valid, well-formed file.
- Do not touch action.yml, README, or any other unrelated files.

---

### Task 1: Baseline writer emits a trailing newline

**Files:**
- Modify: `scripts/benchmark_baseline.py:41`
- Test: `tests/test_benchmark_baseline.py`

**Interfaces:**
- Consumes: nothing new.
- Produces: `save()` behavior unchanged except the on-disk file now ends with `\n`. No callers depend on the absence of a trailing newline (`load()` uses `json.loads`, which tolerates trailing whitespace).

- [ ] **Step 1: Write the failing test**

Add to `tests/test_benchmark_baseline.py`, inside `class TestSave:` (after `test_overwrite_is_idempotent`):

```python
    def test_saved_file_ends_with_newline(self, run_script, fixtures_dir, tmp_path):
        run_script(
            SCRIPT,
            "save",
            "main",
            str(fixtures_dir / "results.json"),
            f"--baselines-dir={tmp_path}",
        )
        raw = (tmp_path / "main.json").read_bytes()
        assert raw.endswith(b"\n")
        assert not raw.endswith(b"\n\n")
```

- [ ] **Step 2: Run test to verify it fails**

Run: `python -m pytest tests/test_benchmark_baseline.py::TestSave::test_saved_file_ends_with_newline -v`
Expected: FAIL — `assert raw.endswith(b"\n")` is `False` because `json.dumps(...)` has no trailing newline.

- [ ] **Step 3: Fix the writer**

In `scripts/benchmark_baseline.py`, change line 41 from:

```python
    out_file.write_text(json.dumps(data, indent=2), encoding="utf-8")
```

to:

```python
    out_file.write_text(json.dumps(data, indent=2) + "\n", encoding="utf-8")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `python -m pytest tests/test_benchmark_baseline.py::TestSave -v`
Expected: PASS (all `TestSave` tests, including the new one and `test_overwrite_is_idempotent`, which must still produce exactly one file).

- [ ] **Step 5: Run the full existing suite to check for regressions**

Run: `python -m pytest tests/ -v`
Expected: PASS — no other test asserts on the absence of a trailing newline (`TestLoad`/`TestList` parse with `json.loads`, which ignores trailing whitespace).

- [ ] **Step 6: Commit**

```bash
git add scripts/benchmark_baseline.py tests/test_benchmark_baseline.py
git commit -m "fix(baseline): write trailing newline in saved baseline JSON"
```

---

### Task 2: Add hygiene hooks with baseline exclusion

**Files:**
- Modify: `.pre-commit-config.yaml`

**Interfaces:**
- Consumes: nothing (config-only change).
- Produces: `pre-commit run --all-files` now also runs `end-of-file-fixer`, `trailing-whitespace`, and `check-json`. `.benchmarks/baselines/` is excluded from `end-of-file-fixer` and `trailing-whitespace` but still checked by `check-json`.

- [ ] **Step 1: Add the `pre-commit-hooks` repo block**

Edit `.pre-commit-config.yaml`. Insert a new `repo:` entry before the existing `astral-sh/ruff-pre-commit` entry (so general hygiene runs first), and add a top-level comment explaining the baseline exclusion. Full resulting file:

```yaml
# Pre-commit hooks for pytest-bench-action.
#
#   pip install pre-commit        # or: pipx install pre-commit
#   pre-commit install            # enable the git commit hook
#   pre-commit run --all-files    # run against the whole repo
#
# Ruff lints (--fix) and formats the Python helper scripts + tests; ty
# type-checks them. Ruff config lives in ruff.toml, ty config in ty.toml.
#
# .benchmarks/baselines/*.json is bot-committed generated data (see
# scripts/benchmark_baseline.py). It's excluded from end-of-file-fixer and
# trailing-whitespace so a machine-written file can't fail CI on
# whitespace it didn't choose; check-json still runs on it as a
# corruption safety net.
repos:
  - repo: https://github.com/pre-commit/pre-commit-hooks
    rev: v5.0.0
    hooks:
      - id: end-of-file-fixer
        exclude: ^\.benchmarks/baselines/
      - id: trailing-whitespace
        exclude: ^\.benchmarks/baselines/
      - id: check-json

  - repo: https://github.com/astral-sh/ruff-pre-commit
    rev: v0.15.8
    hooks:
      - id: ruff-check
        args: [--fix]
      - id: ruff-format

  # ty is installed from PyPI (not the standalone GitHub-release binary the
  # official astral-sh/ty-pre-commit hook downloads) so the hook also works in
  # locked-down CI that only permits the Python package index. The test deps are
  # listed so ty can resolve `pytest` imports in the suite.
  - repo: local
    hooks:
      - id: ty
        name: ty (type check)
        entry: ty check
        language: python
        additional_dependencies: ["ty==0.0.58", "pytest", "pytest-benchmark"]
        types: [python]
        pass_filenames: false
        require_serial: true
```

- [ ] **Step 2: Verify pre-commit is installed, install if missing**

Run: `pre-commit --version`
Expected: prints a version string. If instead you get `command not found`, run `pip install --user pre-commit` first.

- [ ] **Step 3: Run pre-commit against the whole repo**

Run: `pre-commit run --all-files`
Expected: `end-of-file-fixer`, `trailing-whitespace`, `check-json`, `ruff-check`, `ruff-format`, and `ty` all report `Passed` (or `Passed, no files to check` for a hook whose scope has no matching files). No hook should report `Failed`.

- [ ] **Step 4: Verify the exclusion actually works against a real baseline file**

Run: `pre-commit run end-of-file-fixer --files .benchmarks/baselines/main.json`
Expected: `Skipped, no files to check` (proves the `exclude` regex matches the committed baseline path). Then run:
Run: `pre-commit run check-json --files .benchmarks/baselines/main.json`
Expected: `Passed` (proves `check-json` still runs on that same file).

- [ ] **Step 5: Commit**

```bash
git add .pre-commit-config.yaml
git commit -m "chore(precommit): exclude baselines from EOF/whitespace hooks"
```

---

## Self-Review Notes

- **Spec coverage:** Root cause (no trailing newline) → Task 1. Hook addition + exclusion + `check-json` safety net → Task 2. Local verification before pushing → Task 2 Steps 3-4.
- **No placeholders:** every step has literal file paths, exact diffs, and exact commands with expected output.
- **Type/signature consistency:** `save()`'s public behavior (arguments, return type `None`) is unchanged; only the written bytes change.
