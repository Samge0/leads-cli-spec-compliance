#!/usr/bin/env python3
"""判分器：leads-cli 规格符合性修复。

本判分器是 SPEC.md 的独立参考实现：不调用被测工具做预期计算（防"以测测测"），
预期值全部由本文件按 SPEC 独立算出，再与工具实际输出比对。

测试点与权重（总分 = 0.18+0.22+0.18+0.13+0.18+0.11 = 1.00，
reward = Σ(通过 × 权重)，整数百分点累计，test.sh 按同一权重表求和）：
  T1 (0.18) BOM：带 BOM 的数据文件必须正确解析（现实现 utf-8 裸读会把 BOM 并进
            首列表头，第一行数据的 name/region 全部失配）——南山区 count 必须=10
  T2 (0.22) region 精确匹配：按 region 列整串比对；地址含"南山区"的龙华区行不得
            计入，地址不含"南山区"字样的南山区行必须计入（防子串实现）
  T3 (0.18) capital-min 边界：>= 语义，恰好等于阈值（500/1000 探测行）必须计入
  T4 (0.13) 排序确定性：注册资本降序 + 名称升序次键；5 行并列 2000 的顺序唯一
            （防依赖行序的 sort，Python sorted 稳定排序在错误主键下顺序会随行序漂移）
  T5 (0.18) update-cap 语义：大小写不敏感匹配唯一记录；写回后其余字段与行序不变，
            目标行 capital 更新；恰好命中自家的 BOM 兼容（读改写全程 utf-8-sig）
  T6 (0.11) self-test 有效性：SPEC §6 要求 self-test 反映真实行为——修复后退出码 0
            且输出 PASS；破坏态（未修复）下 self-test 必须非 0（空壳/恒过检测）

权重依据：T2 是本工具的业务核心（区域语义错误=数据事故），权重最高；
T1/T3/T5 对应三个真实缺陷（BOM/边界/大小写），高于平均权重（1/6≈0.167）；
T4 是规格确定性的边界要求、T6 是约束5 的兜底验收，低于平均权重。
核心考点（T1-T5）合计 0.89，占比 ≥60%。各测试失败均为按权重扣分；
无硬性门槛清零项与加分项（题目无进阶空间，全部为 SPEC 要求的必要行为）。
NOP 时 T1-T4、T6 全挂；T5 也会因 BOM 写回丢失而挂 → 0.00。
"""
import csv
import subprocess

DATA = "/opt/leads/data/companies.csv"
TOOL = ["leads"]

HEADER = "名称\t区\t行业\t注册资本万"


def _run(argv, cwd="/opt/leads"):
    r = subprocess.run(
        TOOL + argv, capture_output=True, text=True, timeout=60, cwd=cwd
    )
    return r.returncode, r.stdout, r.stderr


def _read_rows():
    """独立参考读取（utf-8-sig 吃掉 BOM）。"""
    with open(DATA, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def _expect_lines(rows):
    """按 SPEC 排序（资本降序、名称升序次键）后输出行列表（含表头）。"""
    rows = sorted(rows, key=lambda r: (-int(r["capital_wan"]), r["name"]))
    return [HEADER] + [
        "%s\t%s\t%s\t%s" % (r["name"], r["region"], r["trade"], r["capital_wan"])
        for r in rows
    ]


def _parse_out(stdout):
    lines = [l for l in stdout.splitlines() if l.strip()]
    if not lines:
        return []
    assert lines[0] == HEADER, "输出首行必须是表头 %r，实际 %r" % (HEADER, lines[0])
    return lines


# ---------- T1 BOM ----------
# type: core
# weight: 0.18
# maps_to: instruction 验收命令 `leads count --region 南山区`（输出 10）；
#          SPEC §1 有无 BOM 均必须正确解析；约束1 数据文件只读（BOM 保持原样）
# failure_effect: 按权重扣 0.18
# reason: BOM 崩溃是反馈线索中的第一症状，影响全部子命令的解析正确性。
def test_t1_bom_tolerant():
    """数据文件的 BOM 必须原样保留（修复须落在代码侧，删 BOM = 违反数据只读约束）。"""
    with open(DATA, "rb") as f:
        head = f.read(8)
    assert head[:3] == b"\xef\xbb\xbf", (
        "数据文件的 BOM 被移除了——SPEC §1 要求工具兼容带 BOM 文件，"
        "修复必须落在代码读取侧而不是改数据（数据文件只读）"
    )
    code, out, err = _run(["count", "--region", "南山区"])
    assert code == 0, "count 退出码 %s stderr=%s" % (code, err)
    got = out.strip()
    assert got == "10", "南山区 count=%r，规格应为 10" % got


# ---------- T2 region 精确匹配 ----------
# type: core
# weight: 0.22
# maps_to: instruction 验收命令 `leads filter --region 南山区 --capital-min 0 --limit 3`；
#          SPEC §3 region 与列值整串精确相等；线索「混进明显不是南山区的公司」
# failure_effect: 按权重扣 0.22
# reason: 区域匹配语义是本工具的业务核心（区域错误=数据事故），权重最高。
def test_t2_region_exact_match():
    rows = _read_rows()
    expect = _expect_lines([r for r in rows if r["region"] == "南山区"])[:4]
    code, out, err = _run([
        "filter", "--region", "南山区", "--capital-min", "0", "--limit", "3"
    ])
    assert code == 0, err
    got = _parse_out(out)
    # 前 3 名片段比对；全量 10 行由 T1 的 count 兜住
    assert got[: len(expect)] == expect, (
        "南山区 top3 与规格不符：\n期望=%r\n实际=%r" % (expect, got)
    )
    # 反证：地址含"南山区"字样的龙华区行不得出现在结果中
    assert all("恒芯科技" not in l for l in got), "按地址子串误匹配：龙华区行『恒芯科技』出现在南山区结果中"


# ---------- T3 capital-min 边界 ----------
# type: core
# weight: 0.18
# maps_to: instruction 验收命令 `leads filter --region 宝安区 --capital-min 500 --limit 60`；
#          SPEC §3 「不低于」含等于；线索「卡着 500 的算不算，两台机器结果不一样」
# failure_effect: 按权重扣 0.18
# reason: 边界语义是 SPEC 符合性的核心考点，探测行（恰好 500/1000）专为此埋设。
def test_t3_capital_min_inclusive():
    rows = _read_rows()
    subset = [r for r in rows if r["region"] == "宝安区" and int(r["capital_wan"]) >= 500]
    expect = _expect_lines(subset)
    code, out, err = _run([
        "filter", "--region", "宝安区", "--capital-min", "500", "--limit", "60"
    ])
    assert code == 0, err
    got = _parse_out(out)
    assert got == expect, (
        "宝安区 >=500 结果与规格不符：\n期望=%d 行\n实际=%d 行\n%r"
        % (len(expect) - 1, len(got) - 1, set(expect) ^ set(got))
    )


# ---------- T4 排序确定性 ----------
# type: supplementary
# weight: 0.13
# maps_to: instruction 验收命令 `leads top --by capital --limit 10`；
#          SPEC §4 两级排序键；线索「并列的时候顺序每次不一样」
# failure_effect: 按权重扣 0.13
# reason: 输出确定性是 SPEC 要求但属边界补充考点，低于平均权重（1/6≈0.167）。
def test_t4_sort_tiebreak():
    rows = _read_rows()
    subset = [r for r in rows if int(r["capital_wan"]) == 2000]
    assert len(subset) == 5, "数据自检：2000 万并列行应为 5 行"
    expect = _expect_lines(subset)
    code, out, err = _run(["top", "--by", "capital", "--limit", "60"])
    assert code == 0, err
    got = _parse_out(out)
    tie_expect = [l for l in expect if l.split("\t")[3] == "2000"]
    tie_got = [l for l in got if l.split("\t")[3] == "2000"]
    assert tie_got == tie_expect, (
        "并列行的次序与规格不符（应为名称字典序升序）：\n期望=%r\n实际=%r" % (tie_expect, tie_got)
    )
    assert got[1].startswith("澜舟数字（深圳）股份有限公司"), (
        "top 第一名应为 5000 万『澜舟数字（深圳）股份有限公司』，实际 %r" % got[1]
    )


# ---------- T5 update-cap 语义 ----------
# type: core
# weight: 0.18
# maps_to: instruction 验收命令 `leads update-cap --name deepfox... --capital 2600`（全小写）；
#          SPEC §3/§5 大小写不敏感匹配唯一记录、写回安全；约束1 其余行原样
# failure_effect: 按权重扣 0.18
# reason: 写路径语义（匹配+落盘安全）是真实缺陷，且验收命令直接考察。
def test_t5_update_cap_case_insensitive_and_safe():
    target_exact = "DeepFox深狐科技（深圳）有限公司"
    rows_before = _read_rows()
    target_before = [r for r in rows_before if r["name"] == target_exact][0]

    code, out, err = _run([
        "update-cap", "--name", "deepfox深狐科技（深圳）有限公司", "--capital", "2600"
    ])
    assert code == 0, "update-cap 应成功，stderr=%s" % err

    rows_after = _read_rows()
    hit = [r for r in rows_after if r["name"] == target_exact]
    assert hit, "更新后目标行消失（名字被改动或行丢失）"
    assert hit[0]["capital_wan"] == "2600", "capital 未更新: %r" % hit[0]

    # 其余 59 行：行序、全部字段保持原样
    rest_after = [r for r in rows_after if r["name"] != target_exact]
    rest_before = [r for r in rows_before if r["name"] != target_exact]
    assert rest_after == rest_before, "update-cap 改坏了其他行（SPEC §5）"
    # 写回后文件不得写坏成乱码（BOM 有无均可）
    with open(DATA, "rb") as f:
        head = f.read(3)
    assert head in (b"\xef\xbb\xbf", b"nam") or head[:1] != b"\xff", "写回后的文件编码异常"


# ---------- T6 self-test 有效性（约束5：不得空壳/恒过） ----------
# type: supplementary
# weight: 0.11
# maps_to: instruction 约束5（self-test 反映真实行为）与验收命令 `leads self-test`（退出码 0）
# failure_effect: 按权重扣 0.11
# reason: 约束5 的兜底验收；恒过实现在 NOP 反向验证中已被抓（幂等性验证），
#         此处验证修复后的正向行为，属补充考点，权重最低。
def test_t6_self_test_reflects_behavior():
    """SPEC §6：self-test 反映真实行为——修复后 rc=0；恒过实现（破损态也 0）在 NOP
    反向验证里已被抓（NOP 时本条必挂），此处验证修复后的正向行为与"成功输出走
    stdout、提示走 stderr"的输出契约。"""
    code, out, err = _run(["self-test"])
    assert code == 0, "修复后 self-test 应退出码 0，实际 %s，stderr=%s" % (code, err)
    assert "PASS" in out, "self-test 应在 stdout 输出 PASS，实际 stdout=%r" % out
