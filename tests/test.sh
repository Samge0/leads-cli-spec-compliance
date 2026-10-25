#!/bin/bash
# Weighted verifier entry. Runs the self-contained test file directly:
# no pip, no pytest install, no network. Weights and the zero-weight
# immutability gate live in test_outputs.py's __main__ block.
set -uo pipefail

mkdir -p /logs/verifier
REWARD_FILE="/logs/verifier/reward.txt"

python3 /tests/test_outputs.py > /tmp/verifier_output.txt 2>&1
rc=$?
tail -n 40 /tmp/verifier_output.txt

# The runner always writes reward.txt itself; rc != 0 means it crashed
# before writing (or the file is missing) -> force 0.
if [ $rc -ne 0 ] || [ ! -s "$REWARD_FILE" ]; then
    echo 0.00 > "$REWARD_FILE"
fi
cat "$REWARD_FILE"
exit 0
