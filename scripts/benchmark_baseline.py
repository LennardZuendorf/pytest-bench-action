#!/usr/bin/env python3
"""Baseline save/load/list helper for pytest-bench-action."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path


def sanitize_branch(branch: str) -> str:
    """Replace /, \\, space, . with _ for safe filenames."""
    for ch in "/\\ .":
        branch = branch.replace(ch, "_")
    return branch


def save(branch: str, results_file: str, baselines_dir: str = ".benchmarks/baselines") -> None:
    results_path = Path(results_file)
    if not results_path.exists():
        print(f"ERROR: results file not found: {results_file}", file=sys.stderr)
        sys.exit(1)

    data = json.loads(results_path.read_text())
    node = data.get("machine_info", {}).get("node", "unknown")

    # Strip raw timing data to reduce file size ~99%
    for bench in data.get("benchmarks", []):
        bench.get("stats", {}).pop("data", None)

    # Inject baseline metadata
    data["baseline_info"] = {
        "branch": branch,
        "node": node,
        "created_at": datetime.now(timezone.utc).isoformat(),
    }

    baselines_path = Path(baselines_dir)
    baselines_path.mkdir(parents=True, exist_ok=True)

    out_file = baselines_path / f"{sanitize_branch(branch)}.json"
    out_file.write_text(json.dumps(data, indent=2))
    print(f"Saved baseline: {out_file} (node={node})")


def load(branch: str, baselines_dir: str = ".benchmarks/baselines") -> dict:
    path = Path(baselines_dir) / f"{sanitize_branch(branch)}.json"
    if not path.exists():
        print(f"ERROR: no baseline for branch '{branch}'", file=sys.stderr)
        sys.exit(1)
    return json.loads(path.read_text())


def list_baselines(baselines_dir: str = ".benchmarks/baselines") -> None:
    path = Path(baselines_dir)
    if not path.exists():
        print("No baselines directory found.")
        return
    files = sorted(path.glob("*.json"))
    if not files:
        print("No baselines found.")
        return
    print(f"{'Branch':<40} {'Node':<30} {'Created'}")
    print("-" * 90)
    for f in files:
        try:
            data = json.loads(f.read_text())
            info = data.get("baseline_info", {})
            print(f"{info.get('branch', f.stem):<40} {info.get('node', 'unknown'):<30} {info.get('created_at', 'unknown')}")
        except Exception as e:
            print(f"{f.stem:<40} ERROR: {e}")


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: benchmark_baseline.py <save|load|list> [args...]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "save":
        if len(sys.argv) < 4:
            print("Usage: benchmark_baseline.py save <branch> <results-file> [--baselines-dir=DIR]")
            sys.exit(1)
        branch = sys.argv[2]
        results_file = sys.argv[3]
        baselines_dir = ".benchmarks/baselines"
        for arg in sys.argv[4:]:
            if arg.startswith("--baselines-dir="):
                baselines_dir = arg.split("=", 1)[1]
        save(branch, results_file, baselines_dir)

    elif command == "load":
        if len(sys.argv) < 3:
            print("Usage: benchmark_baseline.py load <branch> [--baselines-dir=DIR]")
            sys.exit(1)
        branch = sys.argv[2]
        baselines_dir = ".benchmarks/baselines"
        for arg in sys.argv[3:]:
            if arg.startswith("--baselines-dir="):
                baselines_dir = arg.split("=", 1)[1]
        data = load(branch, baselines_dir)
        print(json.dumps(data, indent=2))

    elif command == "list":
        baselines_dir = sys.argv[2] if len(sys.argv) > 2 else ".benchmarks/baselines"
        list_baselines(baselines_dir)

    else:
        print(f"Unknown command: {command}. Use save, load, or list.")
        sys.exit(1)


if __name__ == "__main__":
    main()
