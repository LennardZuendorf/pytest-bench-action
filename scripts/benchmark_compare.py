#!/usr/bin/env python3
"""Comparison engine for pytest-bench-action."""

import json
import sys

# Exit-code contract (exit codes are the API — see .spec/tech.md):
#   0 = all benchmarks within tolerance (or NEW)
#   1 = a real result: regression beyond tolerance and/or a MISSING benchmark,
#       or an I/O error (unreadable/malformed file, bad --tolerance)
#   3 = cannot compare: baseline and current ran on different hardware.
#       Distinct from 1 so callers can distinguish "compared and it regressed"
#       from "no valid comparison was possible". The action.yml wrapper decides
#       whether this hard-fails (enforce-same-node: true) or skips with a
#       warning (enforce-same-node: false). We NEVER emit a cross-machine
#       comparison either way.
NODE_MISMATCH_EXIT = 3


def machine_key(data: dict) -> str | None:
    """A stable identity for the hardware a run executed on.

    Prefer the actual CPU/system identity (``machine_info.cpu``) over
    ``machine_info.node``. The ``node`` is the hostname, which GitHub-hosted
    runners randomize on every job — keying on it made every hosted-runner
    comparison after the first look like a different machine and skip/fail. The
    CPU brand + arch + core count + OS is stable across those ephemeral
    hostnames, so two ``ubuntu-latest`` runs on the same CPU model compare
    cleanly while genuinely different hardware is still rejected.

    Falls back to ``node`` when no ``cpu`` block is present (minimal or legacy
    payloads, e.g. hand-written fixtures). Returns ``None`` when neither is
    available, in which case the caller proceeds without a hardware gate.
    """
    mi = data.get("machine_info", {}) or {}
    cpu = mi.get("cpu") or {}
    if cpu:
        parts = [
            str(cpu.get("brand_raw", "")).strip(),
            str(cpu.get("arch", "")).strip(),
            str(cpu.get("count", "")).strip(),
            str(mi.get("system", "")).strip(),
        ]
        fingerprint = "|".join(p for p in parts if p)
        if fingerprint:
            return fingerprint
    # No cpu block (minimal / legacy payload): fall back to the hostname.
    node = mi.get("node")
    return node or None


def format_time(seconds: float) -> str:
    if seconds < 0.001:
        return f"{seconds * 1e6:.1f}µs"
    if seconds < 1:
        return f"{seconds * 1e3:.2f}ms"
    return f"{seconds:.4f}s"


def compare_json(baseline_file: str, current_file: str, tolerance: float) -> bool:
    """Compare two benchmark JSON files. Returns True if all passed."""
    try:
        with open(baseline_file, encoding="utf-8") as f:
            baseline_data = json.load(f)
    except Exception as e:
        print(f"ERROR: cannot load baseline file '{baseline_file}': {e}", file=sys.stderr)
        sys.exit(1)

    try:
        with open(current_file, encoding="utf-8") as f:
            current_data = json.load(f)
    except Exception as e:
        print(f"ERROR: cannot load current results file '{current_file}': {e}", file=sys.stderr)
        sys.exit(1)

    # Hardware consistency check. We compare on the CPU/system fingerprint, not
    # the hostname, so the same hardware compares cleanly even when the runner's
    # node name changes between jobs (as it does on GitHub-hosted runners).
    baseline_key = machine_key(baseline_data)
    current_key = machine_key(current_data)
    if baseline_key and current_key and baseline_key != current_key:
        print(
            f"ERROR: cross-machine comparison is invalid.\n"
            f"  Baseline machine: {baseline_key}\n"
            f"  Current machine:  {current_key}\n"
            "Benchmarks must be run on the same hardware for meaningful comparison.",
            file=sys.stderr,
        )
        sys.exit(NODE_MISMATCH_EXIT)

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
            print(
                f"{name:<{col_w}} {'N/A':<13} {format_time(current_map[name]):<13} {'NEW':<13} ⚪ NEW"
            )
            continue

        if name not in current_map:
            print(
                f"{name:<{col_w}} {format_time(baseline_map[name]):<13} {'MISSING':<13} {'N/A':<13} ❌ MISSING"
            )
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
            print(
                "Usage: benchmark_compare.py compare-json <baseline-file> <current-file> [--tolerance=N]"
            )
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
