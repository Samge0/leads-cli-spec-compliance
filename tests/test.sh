#!/bin/bash
# 判分入口：先跑硬性门槛（T0）-> 逐测试点加权求和 -> 写 reward.txt
# reward = 门槛 ? 0 : Σ(测试点通过 × 权重)，权重与 test_outputs.py 注释一致
# （附件 test weight 说明）：T1=18 T2=22 T3=18 T4=13 T5=18 T6=11（合计 100）。
# T0 硬性门槛（weight 0）：不可变资产完整性（SPEC/包装脚本 md5、数据文件
# 除目标行 capital 外逐字节原样）。失败 = 改动了评测基准本身 -> 直接清零。
# 装依赖失败/runner 崩溃/任何异常路径都必须写入 0（QA 3.5），不缺写、不沿用旧值。
# 逐函数直跑不依赖 pytest（模块级 test_* 函数 unittest discover 收不到），
# 也不依赖在线 pip——判分现场零装配，测试执行方式在 test.sh 内自含解决。
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
spec.loader.exec_module(mod)

# 1) 硬性门槛先行：失败 -> reward 直接 0（后续行为测试失去意义，跳过）
gate_fn = getattr(mod, GATE, None)
if gate_fn is None:
    print("MISS %s" % GATE)
    print("reward = 0/100")
    sys.exit(0)
try:
    gate_fn()
    print("PASS %-44s (gate)" % GATE)
except Exception:
    print("FAIL %-44s (gate) -> reward = 0" % GATE)
    traceback.print_exc()
    sys.exit(0)

# 2) 行为测试点加权
total = 0
for name, weight in sorted(WEIGHTS.items()):
    fn = getattr(mod, name, None)
    if fn is None:
        print("MISS %s" % name)
        continue
    try:
        fn()
        total += weight
        print("PASS %-44s +0.%02d (total 0.%02d)" % (name, weight, total))
    except Exception:
        print("FAIL %-44s +0.00 (total 0.%02d)" % (name, total))
        traceback.print_exc()

print("reward = %d/100" % total)
sys.exit(total)
PY
}

run_scored >/tmp/verifier_output.txt 2>&1
rc=$?
tail -n 40 /tmp/verifier_output.txt

# rc = 已得百分点（0-100），映射为两位小数；任何意外 rc 范围一律按 0 处理。
if [ "$rc" -ge 0 ] && [ "$rc" -le 100 ] 2>/dev/null; then
    write_reward "$(awk "BEGIN{printf \"%.2f\", $rc/100}")"
else
    write_reward 0
fi
cat "$REWARD_FILE"
exit 0
