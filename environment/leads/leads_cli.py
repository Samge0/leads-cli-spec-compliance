#!/usr/bin/env python3
"""leads -- 名录查询 CLI（v0.9，内部使用）。"""
import argparse
import csv
import sys

DATA = "data/companies.csv"


def log_err(msg):
    print(msg, file=sys.stderr)


def load_rows():
    with open(DATA, "r", encoding="utf-8", newline="") as f:
        reader = csv.DictReader(f)
        return list(reader)


def sort_rows(rows):
    return sorted(rows, key=lambda r: (-int(r["capital_wan"]), r["name"]))


def row_line(r):
    return "%s\t%s\t%s\t%s" % (r["name"], r["region"], r["trade"], r["capital_wan"])


HEADER = "名称\t区\t行业\t注册资本万"


def cmd_filter(args):
    rows = load_rows()
    out = []
    for r in rows:
        if args.region and args.region not in r["address"]:
            continue
        if args.capital_min is not None and int(r["capital_wan"]) < args.capital_min:
            continue
        if args.trade and r["trade"] != args.trade:
            continue
        out.append(r)
    out = sort_rows(out)[: args.limit]
    print(HEADER)
    for r in out:
        print(row_line(r))
    return 0


def cmd_top(args):
    rows = sort_rows(load_rows())
    print(HEADER)
    for r in rows[: args.limit]:
        print(row_line(r))
    return 0


def cmd_count(args):
    rows = load_rows()
    n = 0
    for r in rows:
        if args.region and args.region not in r["address"]:
            continue
        n += 1
    print(n)
    return 0


def cmd_update_cap(args):
    rows = load_rows()
    hits = [r for r in rows if r["name"] == args.name]
    if len(hits) != 1:
        log_err("no such company" if not hits else "ambiguous company")
        return 1
    target = hits[0]
    target["capital_wan"] = str(args.capital)
    with open(DATA, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=["name", "region", "address", "trade", "capital_wan"])
        w.writeheader()
        w.writerows(rows)
    print("updated:", target["name"], "->", target["capital_wan"])
    return 0


def cmd_self_test(args):
    ok = True
    try:
        rows = load_rows()
        if not rows:
            log_err("self-test: no data")
            ok = False
        _ = rows[0]["name"]
    except Exception as e:
        log_err("self-test: load failed: %r" % (e,))
        ok = False
    if not ok:
        print("self-test: FAIL")
        return 1
    ns = [r for r in rows if r["region"] == "南山区"]
    if len(ns) != 10:
        log_err("self-test: nanshan count = %d (expect 10)" % len(ns))
        ok = False
    print("self-test:", "PASS" if ok else "FAIL")
    return 0 if ok else 1


def main():
    p = argparse.ArgumentParser(prog="leads", description="名录查询工具")
    sub = p.add_subparsers(dest="cmd")

    pf = sub.add_parser("filter")
    pf.add_argument("--region", required=True)
    pf.add_argument("--capital-min", type=int, required=True)
    pf.add_argument("--trade")
    pf.add_argument("--limit", type=int, required=True)
    pf.set_defaults(func=cmd_filter)

    pt = sub.add_parser("top")
    pt.add_argument("--by", default="capital")
    pt.add_argument("--limit", type=int, required=True)
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
