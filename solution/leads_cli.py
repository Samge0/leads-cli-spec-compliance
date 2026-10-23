#!/usr/bin/env python3
"""leads -- 名录查询 CLI（v1.0，行为基准：SPEC.md v1.2）。

用法见 SPEC.md。v0.9 -> v1.0 修复的偏离：
- CSV 带 BOM 时第一列列名被污染（filter/top/update-cap 崩 KeyError: 'name'）
  -> 改用 utf-8-sig 读取，有无 BOM 均正确解析（SPEC §1）；
- region 匹配误用 address 子串推断 -> 改为 region 列整串精确相等（SPEC §3）；
- update-cap 名称大小写敏感 -> 改为 casefold 大小写不敏感匹配（SPEC §3/§5）；
- update-cap 全量重写 CSV 丢 BOM/行尾 -> 改为仅替换目标行 capital 单元格（SPEC §5）；
- 成功提示打到 stdout -> 提示一律走 stderr（SPEC §4）；
- --limit 非正整数 / --by 非法值未按用法错误处理 -> 校验并退出码 2（SPEC §2/§7）；
- self-test 只查表头 -> 对 BOM/精确匹配/>=边界/排序稳定性做真实行为断言（SPEC §6）。
"""
import argparse
import csv
import io
import os
import sys
import tempfile

DATA = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "companies.csv")
FIELDS = ["name", "region", "address", "trade", "capital_wan"]


def log_err(msg):
    print(msg, file=sys.stderr)


def load_rows(path=DATA):
    """读取名录 CSV，返回 dict 列表。

    utf-8-sig：带 BOM 时剥掉、不带时照常（SPEC §1 有无 BOM 均必须正确解析）。
    """
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def match_rows(rows, region=None, capital_min=None, trade=None):
    """按 SPEC §3 过滤：region/trade 与列值整串精确相等；capital-min 为 >=。"""
    out = []
    for r in rows:
        if region is not None and r["region"] != region:
            continue
        if capital_min is not None and int(r["capital_wan"]) < capital_min:
            continue
        if trade is not None and r["trade"] != trade:
            continue
        out.append(r)
    return out


def sort_rows(rows):
    """注册资本降序，并列时按名称字典序升序（SPEC §4：两级键，不依赖行序）。"""
    return sorted(rows, key=lambda r: (-int(r["capital_wan"]), r["name"]))


def row_line(r):
    return "%s\t%s\t%s\t%s" % (r["name"], r["region"], r["trade"], r["capital_wan"])


HEADER = "名称\t区\t行业\t注册资本万"


def print_table(rows):
    print(HEADER)
    for r in rows:
        print(row_line(r))


def cmd_filter(args):
    rows = match_rows(load_rows(), region=args.region,
                      capital_min=args.capital_min, trade=args.trade)
    print_table(sort_rows(rows)[: args.limit])
    return 0


def cmd_top(args):
    rows = sort_rows(load_rows())
    print_table(rows[: args.limit])
    return 0


def cmd_count(args):
    print(len(match_rows(load_rows(), region=args.region)))
    return 0


def cmd_update_cap(args):
    rows = load_rows()
    key = args.name.casefold()
    hits = [i for i, r in enumerate(rows) if r["name"].casefold() == key]
    if len(hits) != 1:
        log_err("no such company" if not hits else "ambiguous company")
        return 1
    rewrite_capital(hits[0], str(args.capital))
    log_err("updated: %s -> %d" % (rows[hits[0]]["name"], args.capital))
    return 0


def rewrite_capital(row_index, new_capital):
    """只把第 row_index 条数据行的 capital_wan 单元格改为 new_capital（SPEC §5）。

    BOM 有无、行序、行尾、其余行的内容保持字节原样。
    """
    with open(DATA, "r", encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    target = row_index + 1  # 第 0 行是表头
    line = lines[target]
    ending = "\r\n" if line.endswith("\r\n") else ("\n" if line.endswith("\n") else "")
    body = line[: len(line) - len(ending)] if ending else line
    fields = next(csv.reader([body]))
    fields[FIELDS.index("capital_wan")] = new_capital
    buf = io.StringIO()
    csv.writer(buf, lineterminator="").writerow(fields)
    lines[target] = buf.getvalue() + ending
    with open(DATA, "w", encoding="utf-8", newline="") as f:
        f.write("".join(lines))


def cmd_self_test(args):
    """SPEC §6 自检：BOM 解析、region 精确匹配、>= 边界、排序稳定性。

    断言跑在临时目录的合成数据集上，不修改 data/companies.csv。
    """
    failures = []

    def check(label, cond):
        print(("ok   " if cond else "FAIL ") + label)
        if not cond:
            failures.append(label)

    sample = [
        ("B公司", "龙岗区", "深圳市观澜大道1号（毗邻南山区交界）", "软件", 500),
        ("A公司", "南山区", "深圳市高新南一道1号", "软件", 500),
        ("C公司", "南山区", "深圳市高新南一道2号", "贸易", 499),
        ("D公司", "南山区", "深圳市高新南一道3号", "软件", 501),
        ("E公司", "南山区", "深圳市高新南一道4号", "贸易", 500),
    ]
    try:
        with tempfile.TemporaryDirectory() as td:
            p = os.path.join(td, "sample.csv")
            with open(p, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.writer(f)
                w.writerow(FIELDS)
                w.writerows(sample)
            rows = load_rows(p)
            # 1) BOM 解析：列名不被 BOM 污染（否则 name 列取不到）
            check("BOM 解析", len(rows) == len(sample)
                  and all(r.get("name") and r.get("capital_wan") for r in rows))
            ns = match_rows(rows, region="南山区")
            # 2) region 精确匹配：只看 region 列；B公司地址含“南山区”但属龙岗区，不得命中
            check("region 精确匹配（不做 address 子串推断）",
                  sorted(r["name"] for r in ns) == ["A公司", "C公司", "D公司", "E公司"])
            # 3) capital-min >= 边界：恰好等于阈值（500）的必须计入，499 排除
            ge = match_rows(rows, region="南山区", capital_min=500)
            check("capital-min >= 边界（等于阈值计入）",
                  sorted(r["name"] for r in ge) == ["A公司", "D公司", "E公司"])
            # 4) 排序稳定性：capital 降序、并列按名称升序（A公司<E公司），与输入行序无关
            expect = ["D公司", "A公司", "E公司", "C公司"]
            got = [r["name"] for r in sort_rows(ns)]
            got_rev = [r["name"] for r in sort_rows(list(reversed(ns)))]
            check("排序稳定（资本降序、并列名称升序、与行序无关）",
                  got == expect and got_rev == expect)
    except Exception as e:
        log_err("self-test: %r" % (e,))
        failures.append("exception")

    # 真实数据只读加载（带 BOM 的真实文件也必须干净解析）
    try:
        check("真实数据加载", bool(load_rows()))
    except Exception as e:
        log_err("self-test: load real data failed: %r" % (e,))
        failures.append("real data")

    print("self-test:", "PASS" if not failures else "FAIL")
    return 0 if not failures else 1


def positive_int(s):
    v = int(s)
    if v <= 0:
        raise argparse.ArgumentTypeError("N 必须为正整数，得到 %r" % (s,))
    return v


def main():
    p = argparse.ArgumentParser(prog="leads", description="名录查询工具")
    sub = p.add_subparsers(dest="cmd")

    pf = sub.add_parser("filter")
    pf.add_argument("--region", required=True)
    pf.add_argument("--capital-min", type=int, required=True)
    pf.add_argument("--trade")
    pf.add_argument("--limit", type=positive_int, required=True)
    pf.set_defaults(func=cmd_filter)

    pt = sub.add_parser("top")
    pt.add_argument("--by", choices=["capital"], default="capital")
    pt.add_argument("--limit", type=positive_int, required=True)
    pt.set_defaults(func=cmd_top)

    pc = sub.add_parser("count")
    pc.add_argument("--region", required=True)
    pc.set_defaults(func=cmd_count)

    pu = sub.add_parser("update-cap")
    pu.add_argument("--name", required=True)
    pu.add_argument("--capital", type=int, required=True)
    pu.set_defaults(func=cmd_update_cap)

    ps = sub.add_parser("self-test")
    ps.set_defaults(func=cmd_self_test)

    args = p.parse_args()
    if not getattr(args, "func", None):
        p.print_help(sys.stderr)
        return 2
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
