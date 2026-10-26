#!/bin/sh
# Install the fixed implementation; data/companies.csv untouched.
set -eu

LEADS_DIR=/opt/leads

echo "[solve] installing fixed leads_cli.py -> $LEADS_DIR/leads_cli.py"
cat > "$LEADS_DIR/leads_cli.py" <<'PYEOF'
#!/usr/bin/env python3
"""leads -- 名录查询 CLI（v1.0）。v0.9 -> v1.0 修复：
- 读 CSV 改用 utf-8-sig，带 BOM 的文件不再崩 KeyError；
- region 匹配从 address 子串改为 region 列整串精确相等；
- update-cap 名称匹配改 casefold（大小写不敏感）；
- update-cap 写回只替换目标行 capital 单元格（BOM/行尾/行序原样）；
- 提示信息一律走 stderr；
- --limit 非正整数 / --by 非法值按用法错误处理（退出码 2）；
- self-test 对解析/匹配/边界/排序做真实断言。
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
    """utf-8-sig: tolerate optional BOM."""
    with open(path, "r", encoding="utf-8-sig", newline="") as f:
        return list(csv.DictReader(f))


def match_rows(rows, region=None, capital_min=None, trade=None):
    """Filter: exact region/trade match, capital_min inclusive."""
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
    """Sort: capital desc, name asc tiebreak."""
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
    """Replace only the target capital cell; keep everything else byte-identical."""
    with open(DATA, "r", encoding="utf-8", newline="") as f:
        lines = f.read().splitlines(keepends=True)
    target = row_index + 1
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
    """Self-checks on a synthetic dataset in a temp dir (never touches real data)."""
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
            check("BOM 解析", len(rows) == len(sample)
                  and all(r.get("name") and r.get("capital_wan") for r in rows))
            ns = match_rows(rows, region="南山区")
            check("region 精确匹配",
                  sorted(r["name"] for r in ns) == ["A公司", "C公司", "D公司", "E公司"])
            ge = match_rows(rows, region="南山区", capital_min=500)
            check("capital-min >= 边界",
                  sorted(r["name"] for r in ge) == ["A公司", "D公司", "E公司"])
            expect = ["D公司", "A公司", "E公司", "C公司"]
            got = [r["name"] for r in sort_rows(ns)]
            got_rev = [r["name"] for r in sort_rows(list(reversed(ns)))]
            check("排序稳定（与行序无关）",
                  got == expect and got_rev == expect)
    except Exception as e:
        log_err("self-test: %r" % (e,))
        failures.append("exception")

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
PYEOF
chmod +x "$LEADS_DIR/leads_cli.py"
rm -rf "$LEADS_DIR/__pycache__"

cd "$LEADS_DIR"
echo "[solve] self-test:"
leads self-test
echo "[solve] count Nanshan = $(leads count --region 南山区)"
echo "[solve] done."
