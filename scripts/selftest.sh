#!/usr/bin/env sh
# Local end-to-end harness for pytest-bench-action.
#
# Mirrors the core action.yml steps (run benchmarks -> extract node -> compare ->
# save baseline -> list -> detect regression) against REAL pytest-benchmark
# output, so the full pipeline can be validated without GitHub Actions.
#
# Usage: sh scripts/selftest.sh
# Exits 0 only if every stage behaves as expected. Leaves no artifacts behind.

set -eu

REPO_ROOT=$(cd "$(dirname "$0")/.." && pwd)
SCRIPTS="${REPO_ROOT}/scripts"
WORK=$(mktemp -d)
trap 'rm -rf "${WORK}"' EXIT

RESULTS="${WORK}/results.json"
REGRESSED="${WORK}/regressed.json"
BASELINES="${WORK}/baselines"

fail() { echo "SELFTEST FAIL: $1" >&2; exit 1; }
ok()   { echo "  ok: $1"; }

echo "[1/6] run real benchmark suite"
python3 -m pytest "${REPO_ROOT}/bench/" --benchmark-only \
  --benchmark-json="${RESULTS}" -q >/dev/null 2>&1 \
  || fail "benchmark run did not exit 0"
[ -s "${RESULTS}" ] || fail "no results JSON produced"
ok "results.json written"

echo "[2/6] extract node (same snippet as action.yml)"
NODE=$(python3 -c "
import json
try:
    data = json.load(open('${RESULTS}'))
    print(data.get('machine_info', {}).get('node', 'unknown'))
except Exception:
    print('unknown')
")
[ -n "${NODE}" ] || fail "node extraction returned empty"
[ "${NODE}" != "unknown" ] || fail "node resolved to 'unknown' on real output"
ok "node=${NODE}"

echo "[3/6] compare results vs themselves (zero drift -> pass)"
python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${RESULTS}" --tolerance=5 >/dev/null \
  || fail "self-comparison did not exit 0"
ok "self-comparison passed"

echo "[4/6] save baseline (strip data, inject baseline_info)"
python3 "${SCRIPTS}/benchmark_baseline.py" save \
  "selftest-branch" "${RESULTS}" --baselines-dir="${BASELINES}" >/dev/null \
  || fail "baseline save failed"
BASELINE_FILE="${BASELINES}/selftest-branch.json"
[ -s "${BASELINE_FILE}" ] || fail "baseline file not written"
python3 -c "
import json, sys
d = json.load(open('${BASELINE_FILE}'))
assert 'baseline_info' in d, 'baseline_info missing'
assert d['baseline_info']['branch'] == 'selftest-branch'
for b in d['benchmarks']:
    assert 'data' not in b['stats'], 'raw data not stripped'
" || fail "baseline contents invalid"
ok "baseline saved, data stripped, baseline_info injected"

echo "[5/6] list baselines"
python3 "${SCRIPTS}/benchmark_baseline.py" list "${BASELINES}" \
  | grep -q "selftest-branch" || fail "saved baseline not listed"
ok "baseline listed"

echo "[6/6] inject 2x regression -> compare must fail"
python3 -c "
import json
d = json.load(open('${RESULTS}'))
d['benchmarks'][0]['stats']['mean'] *= 2
json.dump(d, open('${REGRESSED}', 'w'))
"
if python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${REGRESSED}" --tolerance=10 >/dev/null; then
  fail "injected regression did NOT fail the comparison"
fi
ok "regression correctly detected (exit 1)"

echo "SELFTEST PASS: full pipeline validated against real pytest-benchmark output"
