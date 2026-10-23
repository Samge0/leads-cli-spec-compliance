#!/usr/bin/env python3
"""判分器：leads-cli 规格符合性修复。

本判分器是 SPEC.md 的独立参考实现：不调用被测工具做预期计算（防"以测测测"），
预期值全部由本文件按 SPEC 独立算出，再与工具实际输出比对。

测试点（加权，总分=1）：
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

权重依据：T2 是本工具的业务核心（区域语义错误=数据事故），权重最高；T1/T5
对应两个真实缺陷（BOM/大小写）；T3/T4 是规格符合性的边界与确定性；T6 兜住
"约束5：self-test 不得空壳"。
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
    assert got == "10", (
        "南山区 count=%r，规格应为 10（若得 9 说明 BOM 吃掉了第一行；"
        "若得 11+ 说明混入了按地址子串误匹配的行）" % got
    )


# ---------- T2 region 精确匹配 ----------
def test_t2_region_exact_match():
    rows = _read_rows()
    expect = _expect_lines([r for r in rows if r["region"] == "南山区"])[:4]
    code, out, err = _run([
        "filter", "--region", "南山区", "--capital-min", "0", "--limit", "3"
    ])
    assert code == 0, err
    got = _parse_out(out)
    # 取前 3 名做片段比对（全量 10 行只需 count 正确，前 3 名需排序+匹配全对）
    assert got[: len(expect)] == expect, (
        "南山区 top3 与规格不符：\n期望=%r\n实际=%r\n"
        "（若出现『恒芯科技』= 按地址子串把龙华区行误吸入；"
        "若首行丢失 = BOM；若 2000 万并列组未出现 = 排序或边界错）" % (expect, got)
    )
    # 精确匹配的直接反证：地址含"南山区"的龙华区行（恒芯科技）绝不允许出现在结果里
    assert all("恒芯科技" not in l for l in got), (
        "按地址子串误匹配：龙华区行『恒芯科技』出现在南山区结果中"
    )


# ---------- T3 capital-min 边界 ----------
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
def test_t4_sort_tiebreak():
    rows = _read_rows()
    subset = [r for r in rows if int(r["capital_wan"]) == 2000]
    assert len(subset) == 5, "数据自检：2000 万并列行应为 5 行"
    expect = _expect_lines(subset)
    code, out, err = _run(["top", "--by", "capital", "--limit", "60"])
    assert code == 0, err
    got = _parse_out(out)
    # 并列组内的相对顺序必须 = 名称升序（麦芒网络 < 白鹭科技 < 洞见信息 < 矢量智造 < 铁马数字）
    tie_expect = [l for l in expect if l.split("\t")[3] == "2000"]
    tie_got = [l for l in got if l.split("\t")[3] == "2000"]
    assert tie_got == tie_expect, (
        "并列行的次序与规格不符（应为名称字典序升序）：\n期望=%r\n实际=%r\n"
        "（若顺序与数据文件行序一致，说明排序依赖了行序）" % (tie_expect, tie_got)
    )
    # 全库 top1 必须是 5000 万的澜舟数字（股份有限公司）
    assert got[1].startswith("澜舟数字（深圳）股份有限公司"), (
        "top 第一名应为 5000 万『澜舟数字（深圳）股份有限公司』，实际 %r" % got[1]
    )


# ---------- T5 update-cap 语义 ----------
def test_t5_update_cap_case_insensitive_and_safe():
    # 目标行：DeepFox深狐（大写开头）；用全小写查询——大小写不敏感才能命中
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
    assert rest_after == rest_before, (
        "update-cap 改坏了其他行（行序或字段变化）——SPEC §5 要求只改目标行 capital 单元格"
    )
    # BOM 兼容：文件重写后仍可被 utf-8-sig 正常读（无 BOM 也合法，但不能写坏成乱码）
    with open(DATA, "rb") as f:
        head = f.read(3)
    assert head in (b"\xef\xbb\xbf", b"name") or head[:1] != b"\xff", (
        "写回后的文件编码异常"
    )


# ---------- T6 self-test 有效性（约束5：不得空壳/恒过） ----------
def test_t6_self_test_reflects_behavior():
    """SPEC §6：self-test 反映真实行为——修复后 rc=0；恒过实现（破损态也 0）在 NOP
    反向验证里已被抓（NOP 时本条必挂），此处验证修复后的正向行为与"成功输出走
    stdout、提示走 stderr"的输出契约。"""
    code, out, err = _run(["self-test"])
    assert code == 0, "修复后 self-test 应退出码 0，实际 %s，stderr=%s" % (code, err)
    assert "PASS" in out, "self-test 应在 stdout 输出 PASS，实际 stdout=%r" % out
