#!/bin/sh
# Weighted verifier entry. Runs the self-contained test file directly:
# no pip, no pytest install, no network. Weights and the zero-weight
# immutability gate live in test_outputs.py's __main__ block.
# POSIX sh only: the grading sandbox may invoke this via dash.
set -u

mkdir -p /logs/verifier
REWARD_FILE="/logs/verifier/reward.txt"

# Locate test_outputs.py next to this script (survives any cwd or a
# copied entry), with standard mount points as fallback.
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
TEST_PY=""
for d in "$SCRIPT_DIR" /tests /tests-ro; do
    if [ -f "$d/test_outputs.py" ]; then
        TEST_PY="$d/test_outputs.py"
        break
    fi
done
if [ -z "$TEST_PY" ]; then
    echo "test_outputs.py not found (searched $SCRIPT_DIR, /tests, /tests-ro)" >&2
    echo 0.00 > "$REWARD_FILE"
    exit 0
fi

python3 "$TEST_PY" > /tmp/verifier_output.txt 2>&1
rc=$?
tail -n 40 /tmp/verifier_output.txt

# The runner writes reward.txt itself; rc != 0 means it crashed before
# writing (or the file is missing) -> force 0.
if [ $rc -ne 0 ] || [ ! -s "$REWARD_FILE" ]; then
    echo 0.00 > "$REWARD_FILE"
fi
cat "$REWARD_FILE"
exit 0
