#!/usr/bin/env python3
"""Comparison engine for pytest-bench-action."""

import json
import sys


def format_time(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1e6:.1f}µs"
    if seconds < 1:
        return f"{seconds * 1e3:.2f}ms"
    return f"{seconds:.4f}s"


def compare_json(baseline_file: str, current_file: str, tolerance: float) -> bool:
    """Compare two benchmark JSON files. Returns True if all passed."""
    try:
        baseline_data = json.loads(open(baseline_file, encoding="utf-8").read())
    except Exception as e:
        print(f"ERROR: cannot load baseline file '{baseline_file}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        current_data = json.loads(open(current_file, encoding="utf-8").read())
    except Exception as e:
        print(f"ERROR: cannot load current results file '{current_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Node consistency check
    baseline_node = baseline_data.get("machine_info", {}).get("node")
    current_node = current_data.get("machine_info", {}).get("node")
    if baseline_node and current_node and baseline_node != current_node:
        print(
            f"ERROR: cross-machine comparison is invalid.\n"
            f"  Baseline node: {baseline_node}\n"
            f"  Current node:  {current_node}\n"
            "Benchmarks must be run on the same machine for meaningful comparison.",
            file=sys.stderr,
        )
        sys.exit(1)

    # Build name → mean maps
    def build_map(data: dict) -> dict[str, float]:
        result = {}
        for bench in data.get("benchmarks", []):
            name = bench.get("name", "")
            mean = bench.get("stats", {}).get("mean")
            if name and mean is not None:
                result[name] = mean
        return result

    baseline_map = build_map(baseline_data)
    current_map = build_map(current_data)

    all_names = sorted(set(baseline_map) | set(current_map))

    col_w = max((len(n) for n in all_names), default=10) + 2
    col_w = max(col_w, 42)

    header = f"{'Benchmark':<{col_w}} {'Baseline':<13} {'Current':<13} {'Change':<13} Status"
    separator = "-" * (col_w + 13 + 13 + 13 + 12)
    print(header)
    print(separator)

    all_passed = True
    for name in all_names:
        if name not in baseline_map:
            print(f"{name:<{col_w}} {'N/A':<13} {format_time(current_map[name]):<13} {'NEW':<13} ⚪ NEW")
            continue

        if name not in current_map:
            print(f"{name:<{col_w}} {format_time(baseline_map[name]):<13} {'MISSING':<13} {'N/A':<13} ❌ MISSING")
            all_passed = False
            continue

        baseline_mean = baseline_map[name]
        current_mean = current_map[name]
        if baseline_mean == 0:
            change_pct = 0.0
        else:
            change_pct = (current_mean - baseline_mean) / baseline_mean * 100

        change_str = f"{change_pct:+.1f}%"
        if change_pct > tolerance:
            status = "❌ FAIL"
            all_passed = False
        else:
            status = "✅ PASS"

        print(
            f"{name:<{col_w}} {format_time(baseline_mean):<13} {format_time(current_mean):<13} {change_str:<13} {status}"
        )

    print(separator)
    if all_passed:
        print(f"All benchmarks within {tolerance}% tolerance.")
    else:
        print(f"One or more benchmarks exceeded {tolerance}% tolerance or are MISSING.")

    return all_passed


def main() -> None:
    if len(sys.argv) < 2:
        print("Usage: benchmark_compare.py compare-json <baseline> <current> [--tolerance=N]")
        sys.exit(1)

    command = sys.argv[1]

    if command == "compare-json":
        if len(sys.argv) < 4:
            print("Usage: benchmark_compare.py compare-json <baseline-file> <current-file> [--tolerance=N]")
            sys.exit(1)

        baseline_file = sys.argv[2]
        current_file = sys.argv[3]
        tolerance = 20.0
        for arg in sys.argv[4:]:
            if arg.startswith("--tolerance="):
                try:
                    tolerance = float(arg.split("=", 1)[1])
                except ValueError:
                    print(f"ERROR: invalid tolerance value: {arg}", file=sys.stderr)
                    sys.exit(1)

        passed = compare_json(baseline_file, current_file, tolerance)
        sys.exit(0 if passed else 1)

    else:
        print(f"Unknown command: {command}. Use compare-json.")
        sys.exit(1)


if __name__ == "__main__":
    main()
