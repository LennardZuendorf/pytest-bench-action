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

echo "[1/7] run real benchmark suite"
python3 -m pytest "${REPO_ROOT}/bench/" --benchmark-only \
  --benchmark-json="${RESULTS}" -q >/dev/null 2>&1 \
  || fail "benchmark run did not exit 0"
[ -s "${RESULTS}" ] || fail "no results JSON produced"
ok "results.json written"

echo "[2/7] extract node (same snippet as action.yml)"
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

echo "[3/7] compare results vs themselves (zero drift -> pass)"
python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${RESULTS}" --tolerance=5 >/dev/null \
  || fail "self-comparison did not exit 0"
ok "self-comparison passed"

echo "[4/7] save baseline (strip data, inject baseline_info)"
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

echo "[5/7] list baselines"
python3 "${SCRIPTS}/benchmark_baseline.py" list "${BASELINES}" \
  | grep -q "selftest-branch" || fail "saved baseline not listed"
ok "baseline listed"

echo "[6/7] inject 2x regression -> compare must fail"
python3 -c "
import json
d = json.load(open('${RESULTS}'))
d['benchmarks'][0]['stats']['mean'] *= 2
json.dump(d, open('${REGRESSED}', 'w'))
"
EXIT_CODE=0
python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${REGRESSED}" --tolerance=10 >/dev/null 2>&1 || EXIT_CODE=$?
[ "${EXIT_CODE}" -eq 1 ] || fail "injected regression must exit 1 (got ${EXIT_CODE})"
ok "regression correctly detected (exit 1)"

echo "[7/7] hardware fingerprint gate (different hostname compares; different CPU cannot)"
# (7a) Same CPU, different hostname = the GitHub-hosted-runner case. Must still
# compare — we key on hardware, not the ephemeral node name.
SAME_HW="${WORK}/same_hw_diff_host.json"
python3 -c "
import json
d = json.load(open('${RESULTS}'))
d.setdefault('machine_info', {})['node'] = 'a-totally-different-hostname'
json.dump(d, open('${SAME_HW}', 'w'))
"
python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${SAME_HW}" --tolerance=5 >/dev/null 2>&1 \
  || fail "same CPU with a different hostname must still compare (hosted-runner case)"
ok "different hostname, same CPU -> comparison runs (not skipped)"

# (7b) Different CPU model -> cannot compare (exit 3), distinct from regression (1).
DIFF_HW="${WORK}/diff_hw.json"
python3 -c "
import json
d = json.load(open('${RESULTS}'))
d.setdefault('machine_info', {}).setdefault('cpu', {})['brand_raw'] = 'Selftest Different CPU @ 9.99GHz'
json.dump(d, open('${DIFF_HW}', 'w'))
"
EXIT_CODE=0
python3 "${SCRIPTS}/benchmark_compare.py" compare-json \
  "${RESULTS}" "${DIFF_HW}" --tolerance=5 >/dev/null 2>&1 || EXIT_CODE=$?
[ "${EXIT_CODE}" -eq 3 ] || fail "different CPU model must exit 3 (cannot compare), got ${EXIT_CODE}"
ok "different CPU model -> cannot compare (exit 3, distinct from regression)"

echo "SELFTEST PASS: full pipeline validated against real pytest-benchmark output"
