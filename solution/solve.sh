#!/bin/sh
# Install the fixed implementation; data/companies.csv untouched.
set -eu

LEADS_DIR=/opt/leads
SRC="$(cd "$(dirname "$0")" && pwd)/leads_cli.py"

if [ ! -f "$SRC" ]; then
    echo "solve.sh: $SRC not found" >&2
    exit 1
fi

echo "[solve] installing fixed leads_cli.py -> $LEADS_DIR/leads_cli.py"
cp "$SRC" "$LEADS_DIR/leads_cli.py"
chmod +x "$LEADS_DIR/leads_cli.py"
rm -rf "$LEADS_DIR/__pycache__"

cd "$LEADS_DIR"
echo "[solve] self-test:"
leads self-test
echo "[solve] count Nanshan = $(leads count --region 南山区)"
echo "[solve] done."
