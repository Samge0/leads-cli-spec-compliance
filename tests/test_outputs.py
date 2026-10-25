#!/usr/bin/env python3
"""Verifier for the leads CLI task."""
import base64
import csv
import hashlib
import io
import subprocess

DATA = "/opt/leads/data/companies.csv"
TOOL = ["leads"]
HEADER = "名称\t区\t行业\t注册资本万"

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
_ROWS = list(csv.DictReader(io.StringIO(ORIG_CSV.decode("utf-8-sig"))))
TARGET_ROW_INDEX = next(
    i for i, r in enumerate(_ROWS) if r["name"] == TARGET_ROW_NAME
)


def _run(argv, cwd="/opt/leads"):
    r = subprocess.run(TOOL + argv, capture_output=True, text=True, timeout=60, cwd=cwd)
    return r.returncode, r.stdout, r.stderr


def _md5(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


def _expect_lines(rows):
    rows = sorted(rows, key=lambda r: (-int(r["capital_wan"]), r["name"]))
    return [HEADER] + [
        "%s\t%s\t%s\t%s" % (r["name"], r["region"], r["trade"], r["capital_wan"])
        for r in rows
    ]


def _parse_out(stdout):
    lines = [l for l in stdout.splitlines() if l.strip()]
    if not lines:
        return []
    assert lines[0] == HEADER, "first line must be header %r, got %r" % (HEADER, lines[0])
    return lines


def _current_rows():
    rows = [dict(r) for r in _ROWS]
    try:
        with open(DATA, "rb") as f:
            cur = f.read().decode("utf-8-sig")
        for r in csv.DictReader(io.StringIO(cur)):
            if r["name"] == TARGET_ROW_NAME:
                idx = next(i for i, x in enumerate(_ROWS) if x["name"] == TARGET_ROW_NAME)
                rows[idx]["capital_wan"] = r["capital_wan"]
    except Exception:
        pass
    return rows


def test_t0_immutable_assets():
    try:
        wrap = _md5("/usr/local/bin/leads")
    except OSError:
        wrap = "<missing>"
    assert wrap == WRAPPER_MD5, "PATH wrapper script modified: md5=%s" % wrap
    with open(DATA, "rb") as f:
        cur = f.read()
    orig_lines = ORIG_CSV.split(b"\r\n")
    cur_lines = cur.split(b"\r\n")
    assert len(orig_lines) == len(cur_lines) and cur.endswith(b"\r\n"), (
        "data file line structure changed: %d -> %d lines" % (len(orig_lines), len(cur_lines)))
    assert cur[:3] == b"\xef\xbb\xbf", "data file BOM removed"
    diffs = [i for i, (a, b) in enumerate(zip(orig_lines, cur_lines)) if a != b]
    bad = [i for i in diffs if i != TARGET_ROW_INDEX + 1]
    assert not bad, "data file modified outside the target row: lines %r" % bad
    if diffs == [TARGET_ROW_INDEX + 1]:
        a = next(csv.reader([orig_lines[TARGET_ROW_INDEX + 1].decode("utf-8")]))
        b = next(csv.reader([cur_lines[TARGET_ROW_INDEX + 1].decode("utf-8")]))
        changed = [k for k, (x, y) in enumerate(zip(a, b)) if x != y]
        assert changed in ([], [4]), "target row changed outside capital column: %r" % changed


def test_t1_bom_tolerant():
    code, out, err = _run(["count", "--region", "南山区"])
    assert code == 0, "count exit %s, stderr=%s" % (code, err)
    assert out.strip() == "10", "count=%r, expected 10" % out.strip()


def test_t2_region_exact_match():
    expect = _expect_lines([r for r in _ROWS if r["region"] == "南山区"])[:4]
    code, out, err = _run(["filter", "--region", "南山区", "--capital-min", "0", "--limit", "3"])
    assert code == 0, err
    got = _parse_out(out)
    assert got[: len(expect)] == expect, "top3 mismatch:\nexpected=%r\ngot=%r" % (expect, got)
    assert all("恒芯科技" not in l for l in got), "non-Nanshan row leaked into result"


def test_t3_capital_min_inclusive():
    subset = [r for r in _ROWS if r["region"] == "宝安区" and int(r["capital_wan"]) >= 500]
    expect = _expect_lines(subset)
    code, out, err = _run(["filter", "--region", "宝安区", "--capital-min", "500", "--limit", "60"])
    assert code == 0, err
    got = _parse_out(out)
    assert got == expect, ">=500 mismatch: expected %d lines, got %d" % (len(expect), len(got))
    assert any(l.startswith("星岚智造") for l in got), "boundary row (==500) missing"


def test_t4_sort_tiebreak():
    expect = _expect_lines(_current_rows())
    code, out, err = _run(["top", "--by", "capital", "--limit", "60"])
    assert code == 0, err
    got = _parse_out(out)
    assert got == expect[: len(got)], "full-sort mismatch at head:\nexpected=%r\ngot=%r" % (expect[1:4], got[1:4])
    tie_e = [l for l in expect if l.split("\t")[3] == "2000"]
    tie_g = [l for l in got if l.split("\t")[3] == "2000"]
    assert tie_g == tie_e, "tie order mismatch (should be name-ascending):\nexpected=%r\ngot=%r" % (tie_e, tie_g)


def test_t5_update_cap_case_insensitive_and_safe():
    with open(DATA, "rb") as f:
        before = f.read()
    code, out, err = _run([
        "update-cap", "--name", "deepfox深狐科技（深圳）有限公司", "--capital", "2600"
    ])
    assert code == 0, "update-cap failed, stderr=%s" % err
    assert "updated" not in out, "success message leaked to stdout"
    with open(DATA, "rb") as f:
        after = f.read()
    a_lines = after.split(b"\r\n")
    assert a_lines[TARGET_ROW_INDEX + 1].endswith(b",2600"), "target capital not updated"
    diffs = [i for i, (x, y) in enumerate(zip(before.split(b"\r\n"), a_lines)) if x != y]
    assert diffs in ([], [TARGET_ROW_INDEX + 1]), "other rows modified: %r" % diffs
    assert after[:3] == b"\xef\xbb\xbf", "BOM lost on write-back"
    assert after.count(b"\r\n") == before.count(b"\r\n"), "line-ending style changed"


def test_t6_self_test_reflects_behavior():
    code, out, err = _run(["self-test"])
    assert code == 0, "self-test exit %s, stderr=%s" % (code, err)
    assert "PASS" in out, "self-test did not print PASS, stdout=%r" % out


if __name__ == "__main__":
    import sys

    REWARD = "/logs/verifier/reward.txt"
    GATE = "test_t0_immutable_assets"
    WEIGHTS = {
        "test_t1_bom_tolerant": 18,
        "test_t2_region_exact_match": 22,
        "test_t3_capital_min_inclusive": 18,
        "test_t4_sort_tiebreak": 13,
        "test_t5_update_cap_case_insensitive_and_safe": 18,
        "test_t6_self_test_reflects_behavior": 11,
    }

    def write_reward(v):
        with open(REWARD, "w") as f:
            f.write(v)

    import os, traceback
    os.makedirs("/logs/verifier", exist_ok=True)
    total = 0
    try:
        globals()[GATE]()
        print("gate PASS")
    except Exception:
        print("gate FAIL -> reward 0")
        traceback.print_exc()
        write_reward("0.00")
        sys.exit(0)

    for name, weight in sorted(WEIGHTS.items()):
        try:
            globals()[name]()
            total += weight
            print("PASS %s +%d" % (name, weight))
        except Exception:
            print("FAIL %s +0" % name)
            traceback.print_exc()

    print("reward = %d/100" % total)
    write_reward("%.2f" % (total / 100.0))
    sys.exit(0)
