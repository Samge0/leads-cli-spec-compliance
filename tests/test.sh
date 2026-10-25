#!/bin/bash
# Weighted verifier: reward = gate ? 0 : sum(pass_i * w_i), weights in percent:
# T1=18 T2=22 T3=18 T4=13 T5=18 T6=11 (total 100).
# Weight rationale (assignment basis, per test-weight guideline):
#   T2=22 highest -- region exact-match is the core semantic deviation of the task
#     (substring matching on address pollutes both count and filter);
#   T1=18, T3=18, T5=18 -- each an independent user-visible correctness behavior
#     (BOM-tolerant parsing / inclusive capital-min bound / case-insensitive safe update);
#   T4=13, T6=11 -- supporting behaviors (deterministic tiebreak, self-check);
#     combined 24% < 40% so partial fixes cannot score high via side items alone.
# No bonus/cap/zero-out rules: every point maps to a SPEC-necessary behavior,
# there is no advanced space beyond the acceptance contract.
# T0 is a zero-weight gate (immutable assets). Any runner crash writes 0.
set -uo pipefail
REWARD_FILE="/logs/verifier/reward.txt"
mkdir -p /logs/verifier

write_reward () { echo "$1" > "$REWARD_FILE"; }

run_scored () {
python3 - <<'PY'
import importlib.util
import sys
import traceback

GATE = "test_t0_immutable_assets"
WEIGHTS = {
    "test_t1_bom_tolerant": 18,
    "test_t2_region_exact_match": 22,
    "test_t3_capital_min_inclusive": 18,
    "test_t4_sort_tiebreak": 13,
    "test_t5_update_cap_case_insensitive_and_safe": 18,
    "test_t6_self_test_reflects_behavior": 11,
}

spec = importlib.util.spec_from_file_location("verifier_tests", "/tests/test_outputs.py")
mod = importlib.util.module_from_spec(spec)
try:
    spec.loader.exec_module(mod)
except Exception:
    traceback.print_exc()
    sys.exit(0)

try:
    getattr(mod, GATE)()
    print("gate PASS")
except Exception:
    print("gate FAIL -> reward 0")
    traceback.print_exc()
    sys.exit(0)

total = 0
for name, weight in sorted(WEIGHTS.items()):
    try:
        getattr(mod, name)()
        total += weight
        print("PASS %s +%d" % (name, weight))
    except Exception:
        print("FAIL %s +0" % name)
        traceback.print_exc()

print("reward = %d/100" % total)
sys.exit(total)
PY
}

run_scored >/tmp/verifier_output.txt 2>&1
rc=$?
tail -n 40 /tmp/verifier_output.txt

if [ "$rc" -ge 0 ] && [ "$rc" -le 100 ] 2>/dev/null; then
    write_reward "$(awk "BEGIN{printf \"%.2f\", $rc/100}")"
else
    write_reward 0
fi
cat "$REWARD_FILE"
exit 0
