#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""判分器：leads-cli 规格符合性修复。

本判分器是 SPEC.md 的独立参考实现：不调用被测工具做预期计算（防"以测测测"），
预期值全部由本文件按 SPEC 从内嵌基线独立算出，再与工具实际输出比对。

测试点与权重（总分 = 0.18+0.22+0.18+0.13+0.18+0.11 = 1.00，
reward = Σ(通过 × 权重)，整数百分点累计，test.sh 按同一权重表求和）：
  T0 硬性门槛（weight 0，失败→reward 直接清零）：不可变资产完整性
            —— SPEC.md 与 PATH 包装脚本与镜像构建时逐字节一致（约束2/4）；
               数据文件除 update-cap 目标行的 capital 单元格外与原始基线逐字节
               一致，BOM/CRLF/行数保持（约束1）。
  T1 (0.18) BOM：带 BOM 的数据文件必须正确解析——南山区 count 必须=10
  T2 (0.22) region 精确匹配：按 region 列整串比对；地址含"南山区"的龙华区行不得
            计入，地址不含"南山区"字样的南山区行必须计入（防子串实现）
  T3 (0.18) capital-min 边界：>= 语义，恰好等于阈值（500/1000 探测行）必须计入
  T4 (0.13) 排序确定性：注册资本降序 + 名称升序次键；5 行并列 2000 的顺序唯一
  T5 (0.18) update-cap 语义：大小写不敏感匹配唯一记录；写回后其余字段与行序不变，
            目标行 capital 更新；BOM/行尾保持
  T6 (0.11) self-test 有效性：修复后退出码 0 且输出 PASS；破坏态下必须非 0

权重依据：T2 是业务核心（区域语义错误=数据事故），权重最高；T1/T3/T5 对应
三个真实缺陷（BOM/边界/大小写），高于平均权重（1/6≈0.167）；T4 是规格确定性
的边界要求、T6 是约束5 的兜底验收，低于平均权重。核心考点（T1-T5）合计 0.89。
各计分测试失败均按权重扣分；T0 为硬性门槛（weight 0，失败清零，对应"改动
不可变资产后其余测试结果失去意义"）；无加分项（题目无进阶空间）。
NOP 时 T0 数据结构校验可过（未动文件）但 T1-T6 全挂 → 0.00；
改 SPEC/包装脚本/数据非目标单元格 → T0 清零。
"""
import base64
import csv
import hashlib
import io

DATA = "/opt/leads/data/companies.csv"
SPEC = "/opt/leads/SPEC.md"
WRAPPER = "/usr/local/bin/leads"
TOOL = ["leads"]

HEADER = "名称\t区\t行业\t注册资本万"

# ── 不可变资产基线（与镜像构建产物一致；数据文件原始基线内嵌，判分不依赖现场）──
SPEC_MD5 = "c6bcca92d02474c99e2fdc6de43a9821"
WRAPPER_MD5 = "c1a9fd4445a4819486e6e645435d4aa6"
TARGET_ROW_NAME = "DeepFox深狐科技（深圳）有限公司"
_ORIG_B64 = (
    "77u/bmFtZSxyZWdpb24sYWRkcmVzcyx0cmFkZSxjYXBpdGFsX3dhbg0K5pif5bKa56eR5oqA77yI"
    "5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOWNl+WxseWMuizmt7HlnLPluILpq5jmlrDljZfkuIDpgZMx"
    "MOWPtyzova/ku7YsODAwDQrmmJ/lsprkv6Hmga/vvIjmt7HlnLPvvInmnInpmZDlhazlj7gs56aP"
    "55Sw5Yy6LOa3seWcs+W4guemj+WNjuS4iei3rzE35Y+3LOWItumAoCw4MDANCuaYn+WymuaZuumA"
    "oO+8iOa3seWcs++8ieaciemZkOWFrOWPuCzlrp3lronljLos5rex5Zyz5biC5a6d5rqQ6LevMjTl"
    "j7cs6LS45piTLDUwMA0K5pif5bKa5pWw5a2X77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWy"
    "l+WMuizmt7HlnLPluILpvpnnv5TlpKfpgZMzMeWPtyznianmtYEsMTAwMA0K5pif5bKa572R57uc"
    "77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILop4LmvpzlpKfpgZMz"
    "OOWPtyzlkqjor6IsNTAwDQrkupHmoq/np5HmioDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs572X"
    "5rmW5Yy6LOa3seWcs+W4guS4nOmXqOi3rzQ15Y+3LOi9r+S7tiwxMDAwDQrkupHmoq/kv6Hmga/v"
    "vIjmt7HlnLPvvInmnInpmZDlhazlj7gs5Y2X5bGx5Yy6LOa3seWcs+W4gumrmOaWsOWNl+S4gOmB"
    "kzUy5Y+3LOWItumAoCwxMDANCuS6keair+aZuumAoO+8iOa3seWcs++8ieaciemZkOWFrOWPuCzn"
    "po/nlLDljLos5rex5Zyz5biC56aP5Y2O5LiJ6LevNTnlj7cs6LS45piTLDI1MDANCuS6keair+aV"
    "sOWtl++8iOa3seWcs++8ieaciemZkOWFrOWPuCzlrp3lronljLos5rex5Zyz5biC5a6d5rqQ6Lev"
    "Njblj7cs54mp5rWBLDIwMA0K5LqR5qKv572R57uc77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+"
    "meWyl+WMuizmt7HlnLPluILpvpnnv5TlpKfpgZM3M+WPtyzlkqjor6IsMjUwMA0K5oGS6Iqv56eR"
    "5oqA77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILpvpnljY7ljLro"
    "p4LmvpzlpKfpgZMxMjDlj7fvvIjmr5fpgrvljZflsbHljLrkuqTnlYzvvIks54mp5rWBLDUwMA0K"
    "5oGS6Iqv5L+h5oGv77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOe9l+a5luWMuizmt7HlnLPluILk"
    "uJzpl6jot684N+WPtyzliLbpgKAsODAwDQrmgZLoiq/mmbrpgKDvvIjmt7HlnLPvvInmnInpmZDl"
    "hazlj7gs5Y2X5bGx5Yy6LOa3seWcs+W4gumrmOaWsOWNl+S4gOmBkzk05Y+3LOi0uOaYkywxMDAw"
    "DQrmgZLoiq/mlbDlrZfvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs56aP55Sw5Yy6LOa3seWcs+W4"
    "guemj+WNjuS4iei3rzEwMeWPtyznianmtYEsODAwDQrmgZLoiq/nvZHnu5zvvIjmt7HlnLPvvInm"
    "nInpmZDlhazlj7gs5a6d5a6J5Yy6LOa3seWcs+W4guWunea6kOi3rzEwOOWPtyzlkqjor6IsODAw"
    "DQrmnoHnm67np5HmioDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs6b6Z5bKX5Yy6LOa3seWcs+W4"
    "gum+mee/lOWkp+mBkzExNeWPtyzova/ku7YsMTAwMA0K5p6B55uu5L+h5oGv77yI5rex5Zyz77yJ"
    "5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILop4LmvpzlpKfpgZMxMjLlj7cs5Yi26YCg"
    "LDEwMA0K5p6B55uu5pm66YCg77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOe9l+a5luWMuizmt7Hl"
    "nLPluILkuJzpl6jot68xMjnlj7cs6LS45piTLDI1MDANCuaegeebruaVsOWtl++8iOa3seWcs++8"
    "ieaciemZkOWFrOWPuCzljZflsbHljLos5rex5Zyz5biC6auY5paw5Y2X5LiA6YGTMTM25Y+3LOeJ"
    "qea1gSwxMDANCuaegeebrue9kee7nO+8iOa3seWcs++8ieaciemZkOWFrOWPuCznpo/nlLDljLos"
    "5rex5Zyz5biC56aP5Y2O5LiJ6LevMTQz5Y+3LOWSqOivoiwzMDANCumdkuaip+enkeaKgO+8iOa3"
    "seWcs++8ieaciemZkOWFrOWPuCzlrp3lronljLos5rex5Zyz5biC5a6d5rqQ6LevMTUw5Y+3LOWI"
    "tumAoCw1MDANCumdkuaip+S/oeaBr++8iOa3seWcs++8ieaciemZkOWFrOWPuCzpvpnlspfljLos"
    "5rex5Zyz5biC6b6Z57+U5aSn6YGTMTU35Y+3LOWItumAoCwyNTAwDQrpnZLmoqfmmbrpgKDvvIjm"
    "t7HlnLPvvInmnInpmZDlhazlj7gs6b6Z5Y2O5Yy6LOa3seWcs+W4guingua+nOWkp+mBkzE2NOWP"
    "tyzotLjmmJMsMzAwDQrpnZLmoqfmlbDlrZfvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs572X5rmW"
    "5Yy6LOa3seWcs+W4guS4nOmXqOi3rzE3MeWPtyznianmtYEsODAwDQrpnZLmoqfnvZHnu5zvvIjm"
    "t7HlnLPvvInmnInpmZDlhazlj7gs5Y2X5bGx5Yy6LOa3seWcs+W4gumrmOaWsOWNl+S4gOmBkzE3"
    "OOWPtyzlkqjor6IsMTAwDQrpgJ/ohb7np5HmioDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs56aP"
    "55Sw5Yy6LOa3seWcs+W4guemj+WNjuS4iei3rzE4NeWPtyzova/ku7YsODAwDQrpgJ/ohb7kv6Hm"
    "ga/vvIjmt7HlnLPvvInmnInpmZDlhazlj7gs5a6d5a6J5Yy6LOa3seWcs+W4guWunea6kOi3rzE5"
    "MuWPtyzliLbpgKAsNTAwDQrpgJ/ohb7mmbrpgKDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs6b6Z"
    "5bKX5Yy6LOa3seWcs+W4gum+mee/lOWkp+mBkzE5OeWPtyzotLjmmJMsMjUwMA0K6YCf6IW+5pWw"
    "5a2X77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILop4LmvpzlpKfp"
    "gZMyMDblj7cs54mp5rWBLDgwMA0K6YCf6IW+572R57uc77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4"
    "LOe9l+a5luWMuizmt7HlnLPluILkuJzpl6jot68yMTPlj7cs5ZKo6K+iLDEwMDANCua+nOiIn+en"
    "keaKgO+8iOa3seWcs++8ieaciemZkOWFrOWPuCzljZflsbHljLos5rex5Zyz5biC6auY5paw5Y2X"
    "5LiA6YGTMjIw5Y+3LOi9r+S7tiwxMDAwDQrmvpzoiJ/kv6Hmga/vvIjmt7HlnLPvvInmnInpmZDl"
    "hazlj7gs56aP55Sw5Yy6LOa3seWcs+W4guemj+WNjuS4iei3rzIyN+WPtyzliLbpgKAsMTAwDQrm"
    "vpzoiJ/mmbrpgKDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs5a6d5a6J5Yy6LOa3seWcs+W4guWu"
    "nea6kOi3rzIzNOWPtyzotLjmmJMsMTAwDQrmvpzoiJ/mlbDlrZfvvIjmt7HlnLPvvInmnInpmZDl"
    "hazlj7gs6b6Z5bKX5Yy6LOa3seWcs+W4gum+mee/lOWkp+mBkzI0MeWPtyznianmtYEsMTAwMA0K"
    "5r6c6Iif572R57uc77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILo"
    "p4LmvpzlpKfpgZMyNDjlj7cs5ZKo6K+iLDgwMA0K5piO5r6I56eR5oqA77yI5rex5Zyz77yJ5pyJ"
    "6ZmQ5YWs5Y+4LOe9l+a5luWMuizmt7HlnLPluILkuJzpl6jot68yNTXlj7cs6L2v5Lu2LDMwMA0K"
    "5piO5r6I5L+h5oGv77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOWNl+WxseWMuizmt7HlnLPluILp"
    "q5jmlrDljZfkuIDpgZMyNjLlj7cs5Yi26YCgLDUwMA0K5piO5r6I5pm66YCg77yI5rex5Zyz77yJ"
    "5pyJ6ZmQ5YWs5Y+4LOemj+eUsOWMuizmt7HlnLPluILnpo/ljY7kuInot68yNjnlj7cs6LS45piT"
    "LDEwMDANCuaYjua+iOaVsOWtl++8iOa3seWcs++8ieaciemZkOWFrOWPuCzlrp3lronljLos5rex"
    "5Zyz5biC5a6d5rqQ6LevMjc25Y+3LOeJqea1gSw4MDANCuaYjua+iOe9kee7nO+8iOa3seWcs++8"
    "ieaciemZkOWFrOWPuCzpvpnlspfljLos5rex5Zyz5biC6b6Z57+U5aSn6YGTMjgz5Y+3LOWSqOiv"
    "oiw4MDANCum6puiKkue9kee7nO+8iOa3seWcs++8ieaciemZkOWFrOWPuCznpo/nlLDljLos5rex"
    "5Zyz5biC6KeC5r6c5aSn6YGTMjkw5Y+3LOi9r+S7tiwyMDAwDQrmtJ7op4Hkv6Hmga/vvIjmt7Hl"
    "nLPvvInmnInpmZDlhazlj7gs56aP55Sw5Yy6LOa3seWcs+W4guS4nOmXqOi3rzI5N+WPtyzkv6Hm"
    "ga8sMjAwMA0K55m96bmt56eR5oqA77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOemj+eUsOWMuizm"
    "t7HlnLPluILpq5jmlrDljZfkuIDpgZMzMDTlj7cs5pm66YCgLDIwMDANCuefoumHj+aZuumAoO+8"
    "iOa3seWcs++8ieaciemZkOWFrOWPuCznpo/nlLDljLos5rex5Zyz5biC56aP5Y2O5LiJ6LevMzEx"
    "5Y+3LOaVsOWtlywyMDAwDQrpk4HpqazmlbDlrZfvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs56aP"
    "55Sw5Yy6LOa3seWcs+W4guWunea6kOi3rzMxOOWPtyznvZHnu5wsMjAwMA0K55+l5b6u5LqR56eR"
    "77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWyl+WMuizmt7HlnLPluILpvpnnv5TlpKfpgZMz"
    "MjXlj7cs6L2v5Lu2LDUwMA0K55+l5b6u5pWw6IGU77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+"
    "meWNjuWMuizmt7HlnLPluILop4LmvpzlpKfpgZMzMzLlj7cs5Yi26YCgLDUwMA0K55+l5b6u5pm6"
    "6IGU77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOe9l+a5luWMuizmt7HlnLPluILkuJzpl6jot68z"
    "Mznlj7cs6LS45piTLDIwMA0K55+l5b6u5L+h6YCa77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOWN"
    "l+WxseWMuizmt7HlnLPluILpq5jmlrDljZfkuIDpgZMzNDblj7cs54mp5rWBLDEwMA0K55+l5b6u"
    "572R56eR77yI5rex5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOemj+eUsOWMuizmt7HlnLPluILnpo/ljY7k"
    "uInot68zNTPlj7cs5ZKo6K+iLDEwMDANCuWNiuWfjuenkeaKgO+8iOa3seWcs++8ieaciemZkOWF"
    "rOWPuCzlrp3lronljLos5rex5Zyz5biC5a6d5rqQ6LevMzYw5Y+3LOi9r+S7tiwzMDANCuWNiuWf"
    "juS/oeaBr++8iOa3seWcs++8ieaciemZkOWFrOWPuCzpvpnlspfljLos5rex5Zyz5biC6b6Z57+U"
    "5aSn6YGTMzY35Y+3LOWItumAoCwxMDANCuWNiuWfjuaZuumAoO+8iOa3seWcs++8ieaciemZkOWF"
    "rOWPuCzpvpnljY7ljLos5rex5Zyz5biC6KeC5r6c5aSn6YGTMzc05Y+3LOi0uOaYkywzMDANCuWN"
    "iuWfjuaVsOWtl++8iOa3seWcs++8ieaciemZkOWFrOWPuCznvZfmuZbljLos5rex5Zyz5biC5Lic"
    "6Zeo6LevMzgx5Y+3LOeJqea1gSwxMDANCuWNiuWfjue9kee7nO+8iOa3seWcs++8ieaciemZkOWF"
    "rOWPuCzljZflsbHljLos5rex5Zyz5biC6auY5paw5Y2X5LiA6YGTMzg45Y+3LOWSqOivoiw1MDAN"
    "CkRlZXBGb3jmt7Hni5Dnp5HmioDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs56aP55Sw5Yy6LOa3"
    "seWcs+W4guemj+WNjuS4iei3rzM5NeWPtyzova/ku7YsMjAwDQrlsb/op4Hkv6Hmga/vvIjmt7Hl"
    "nLPvvInmnInpmZDlhazlj7gs5a6d5a6J5Yy6LOa3seWcs+W4guWunea6kOi3rzQwMuWPtyzliLbp"
    "gKAsMzAwDQrlsb/op4HmmbrpgKDvvIjmt7HlnLPvvInmnInpmZDlhazlj7gs6b6Z5bKX5Yy6LOa3"
    "seWcs+W4gum+mee/lOWkp+mBkzQwOeWPtyzotLjmmJMsMTAwMA0K5bG/6KeB5pWw5a2X77yI5rex"
    "5Zyz77yJ5pyJ6ZmQ5YWs5Y+4LOm+meWNjuWMuizmt7HlnLPluILop4LmvpzlpKfpgZM0MTblj7cs"
    "54mp5rWBLDgwMA0K5r6c6Iif5pWw5a2X77yI5rex5Zyz77yJ6IKh5Lu95pyJ6ZmQ5YWs5Y+4LOWN"
    "l+WxseWMuizmt7HlnLPluILkuJzpl6jot680MjPlj7cs6L2v5Lu2LDUwMDANCg=="
)
ORIG_CSV = base64.b64decode(_ORIG_B64)
TARGET_ROW_INDEX = next(
    i for i, r in enumerate(csv.DictReader(io.StringIO(ORIG_CSV.decode("utf-8-sig"))))
    if r["name"] == TARGET_ROW_NAME
)

# ── 期望值源：全部从内嵌基线计算，不从被测现场读 ──
_ROWS = list(csv.DictReader(io.StringIO(ORIG_CSV.decode("utf-8-sig"))))


def _current_rows():
    """基线行 + 现场目标行 capital 当前值（T0 已保证现场除目标行 capital 外
    与基线逐字节一致，故排序/过滤期望 = 基线替换目标行 capital 后计算）。"""
    rows = [dict(r) for r in _ROWS]
    try:
        with open(DATA, "rb") as f:
            cur = f.read().decode("utf-8-sig")
        for r in csv.DictReader(io.StringIO(cur)):
            if r["name"] == TARGET_ROW_NAME:
                rows[_ROWS.index(next(x for x in _ROWS if x["name"] == TARGET_ROW_NAME))]["capital_wan"] = r["capital_wan"]
    except Exception:
        pass
    return rows


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


import subprocess


def _run(argv, cwd="/opt/leads"):
    r = subprocess.run(
        TOOL + argv, capture_output=True, text=True, timeout=60, cwd=cwd
    )
    return r.returncode, r.stdout, r.stderr


def _md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


# ---------- T0 硬性门槛：不可变资产完整性 ----------
# type: gate
# weight: 0
# maps_to: 约束1（数据文件除目标行 capital 单元格外不得修改）、约束2（SPEC 不得修改）、
#          约束4（不得用 shell 包装后处理输出——包装脚本本身必须原样）
# failure_effect: reward = 0（硬性门槛清零）
# reason: 不可变资产被改动后，其余行为测试的结果失去评测意义（SPEC 可被改成
#         匹配错误实现、包装层可后处理输出伪造行为、数据可被改写贴合坏实现）。
GATE_FAILED = False
GATE_REASONS = []


def _gate_check(label, cond, detail=""):
    global GATE_FAILED
    if not cond:
        GATE_FAILED = True
        GATE_REASONS.append(label + (": " + detail if detail else ""))


def test_t0_immutable_assets():
    spec_md5 = _md5(SPEC)
    _gate_check("SPEC.md 被修改（约束2）", spec_md5 == SPEC_MD5,
                "md5=%s 期望=%s" % (spec_md5, SPEC_MD5))
    try:
        wrap_md5 = _md5(WRAPPER)
    except OSError:
        wrap_md5 = "<missing>"
    _gate_check("PATH 包装脚本 /usr/local/bin/leads 被修改（约束4）",
                wrap_md5 == WRAPPER_MD5, "md5=%s 期望=%s" % (wrap_md5, WRAPPER_MD5))

    with open(DATA, "rb") as f:
        cur = f.read()
    orig_lines = ORIG_CSV.split(b"\r\n")
    cur_lines = cur.split(b"\r\n")
    _gate_check("数据文件行数/行尾结构被改（约束1）",
                len(orig_lines) == len(cur_lines) and cur.endswith(b"\r\n"),
                "行数 %d->%d" % (len(orig_lines), len(cur_lines)))
    _gate_check("数据文件 BOM 被移除（约束1）", cur[:3] == b"\xef\xbb\xbf")
    diffs = [i for i, (a, b) in enumerate(zip(orig_lines, cur_lines)) if a != b]
    bad = [i for i in diffs if i != TARGET_ROW_INDEX + 1]
    _gate_check("数据文件目标行之外的行被修改（约束1）", not bad, "差异行=%r" % bad)
    if diffs == [TARGET_ROW_INDEX + 1]:
        a_fields = next(csv.reader([orig_lines[TARGET_ROW_INDEX + 1].decode("utf-8")]))
        b_fields = next(csv.reader([cur_lines[TARGET_ROW_INDEX + 1].decode("utf-8")]))
        changed = [k for k, (x, y) in enumerate(zip(a_fields, b_fields)) if x != y]
        _gate_check("目标行除 capital 外的字段被修改（约束1）",
                    changed in ([], [4]), "变化列=%r" % changed)
    assert not GATE_FAILED, "T0 硬性门槛失败：" + "；".join(GATE_REASONS)


# ---------- T1 BOM ----------
# type: core
# weight: 0.18
# maps_to: instruction 验收命令 `leads count --region 南山区`（输出 10）；
#          SPEC §1 有无 BOM 均必须正确解析；约束1 数据文件只读（BOM 保持原样）
# failure_effect: 按权重扣 0.18
# reason: BOM 崩溃是反馈线索中的第一症状，影响全部子命令的解析正确性。
def test_t1_bom_tolerant():
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
    expect = _expect_lines([r for r in _ROWS if r["region"] == "南山区"])[:4]
    code, out, err = _run([
        "filter", "--region", "南山区", "--capital-min", "0", "--limit", "3"
    ])
    assert code == 0, err
    got = _parse_out(out)
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
    subset = [r for r in _ROWS if r["region"] == "宝安区" and int(r["capital_wan"]) >= 500]
    expect = _expect_lines(subset)
    code, out, err = _run([
        "filter", "--region", "宝安区", "--capital-min", "500", "--limit", "60"
    ])
    assert code == 0, err
    got = _parse_out(out)
    assert got == expect, (
        "宝安区 >=500 结果与规格不符：\n期望=%d 行\n实际=%d 行\n差异=%r" % (
            len(expect), len(got), set(expect) ^ set(got))
    )
    assert any(l.startswith("星岚智造") for l in got), "恰好 500 的探测行（星岚智造）未计入——边界语义错误"


# ---------- T4 排序确定性 ----------
# type: supplementary
# weight: 0.13
# maps_to: instruction 验收命令 `leads top --by capital --limit 10`；
#          SPEC §4 两级排序键；线索「并列的时候顺序每次不一样」
# failure_effect: 按权重扣 0.13
# reason: 输出确定性是 SPEC 要求但属边界补充考点，低于平均权重（1/6≈0.167）。
def test_t4_sort_tiebreak():
    expect = _expect_lines(_current_rows())
    code, out, err = _run(["top", "--by", "capital", "--limit", "60"])
    assert code == 0, err
    got = _parse_out(out)
    assert got == expect[: len(got)], (
        "全库排序与规格不符（资本降序、名称升序次键）：\n期望前3=%r\n实际前3=%r" % (expect[1:4], got[1:4])
    )
    tie_expect = [l for l in expect if l.split("\t")[3] == "2000"]
    tie_got = [l for l in got if l.split("\t")[3] == "2000"]
    assert tie_got == tie_expect, (
        "并列行的次序与规格不符（应为名称字典序升序）：\n期望=%r\n实际=%r" % (tie_expect, tie_got)
    )


# ---------- T5 update-cap 语义 ----------
# type: core
# weight: 0.18
# maps_to: instruction 验收命令 `leads update-cap --name deepfox... --capital 2600`（全小写）；
#          SPEC §3/§5 大小写不敏感匹配唯一记录、写回安全；约束1 其余行原样
# failure_effect: 按权重扣 0.18
# reason: 写路径语义（匹配+落盘安全）是真实缺陷，且验收命令直接考察。
def test_t5_update_cap_case_insensitive_and_safe():
    with open(DATA, "rb") as f:
        before = f.read()

    code, out, err = _run([
        "update-cap", "--name", "deepfox深狐科技（深圳）有限公司", "--capital", "2600"
    ])
    assert code == 0, "update-cap 应成功，stderr=%s" % err
    assert "updated" not in out, "成功提示应走 stderr 而非 stdout（SPEC §4）"

    with open(DATA, "rb") as f:
        after = f.read()
    b_lines = before.split(b"\r\n")
    a_lines = after.split(b"\r\n")
    diffs = [i for i, (x, y) in enumerate(zip(b_lines, a_lines)) if x != y]
    assert a_lines[TARGET_ROW_INDEX + 1].endswith(b",2600"), (
        "目标行 capital 未更新为 2600：%r" % a_lines[TARGET_ROW_INDEX + 1][-30:]
    )
    # 目标行已是 2600 时写回可无差异（幂等）；其余任何行不允许变化
    assert diffs in ([], [TARGET_ROW_INDEX + 1]), (
        "update-cap 写回破坏了其他行（差异行=%r，仅目标行允许变化）" % diffs
    )
    assert after[:3] == b"\xef\xbb\xbf", "写回丢失 BOM（SPEC §5）"
    assert after.count(b"\r\n") == before.count(b"\r\n"), "写回改变行尾风格（SPEC §5）"


# ---------- T6 self-test 有效性（约束5：不得空壳/恒过） ----------
# type: supplementary
# weight: 0.11
# maps_to: instruction 约束5（self-test 反映真实行为）与验收命令 `leads self-test`（退出码 0）
# failure_effect: 按权重扣 0.11
# reason: 约束5 的兜底验收；恒过实现在 NOP 反向验证中已被抓（幂等性验证），
#         此处验证修复后的正向行为，属补充考点，权重最低。
def test_t6_self_test_reflects_behavior():
    code, out, err = _run(["self-test"])
    assert code == 0, "修复后 self-test 应退出码 0，实际 %s，stderr=%s" % (code, err)
    assert "PASS" in out, "self-test 应在 stdout 输出 PASS，实际 stdout=%r" % out
