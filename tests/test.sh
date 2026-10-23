#!/bin/bash
# 判分入口：装测试依赖（仅 pytest，与运行时依赖分离）-> 执行 -> 全路径写 reward.txt
# 装包失败/pytest 崩溃/任何异常路径都必须写入 0（QA 3.5），不缺写、不沿用旧值。
set -uo pipefail
REWARD_FILE="/logs/verifier/reward.txt"
mkdir -p /logs/verifier

write_reward () { echo "$1" > "$REWARD_FILE"; }

if ! python3 -m pip install --quiet --no-input pytest >/dev/null 2>&1; then
    # 在线装失败的兜底：pytest 仅用最基础断言特性，用 unittest 直跑同一测试文件
    if python3 -m unittest discover -s /tests -p "test_outputs.py" >/tmp/verifier_output.txt 2>&1; then
        write_reward 1
    else
        write_reward 0
    fi
    tail -n 20 /tmp/verifier_output.txt
    cat "$REWARD_FILE"
    exit 0
fi

python3 -m pytest /tests/test_outputs.py -rA -p no:cacheprovider > /tmp/verifier_output.txt 2>&1
rc=$?
tail -n 40 /tmp/verifier_output.txt
if [ $rc -eq 0 ]; then write_reward 1; else write_reward 0; fi
cat "$REWARD_FILE"
exit 0
