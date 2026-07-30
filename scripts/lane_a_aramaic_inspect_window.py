#!/usr/bin/env python3
"""Read-only inspector for a contiguous Aramaic source-ordinal window."""

from __future__ import annotations

import argparse
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"


def main() -> None:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--high", type=int, required=True)
    parser.add_argument("--count", type=int, default=100)
    args = parser.parse_args()

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = con.execute(
        "select entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
        "from entries where language='aramaic'"
    ).fetchall()
    con.close()
    by_ordinal = {int(row["entry_id"].split(":")[1]): row for row in rows}
    for ordinal in range(args.high, args.high - args.count, -1):
        row = by_ordinal.get(ordinal)
        if row is None:
            print(f"{ordinal}\t<MISSING>")
            continue
        print(
            f"{ordinal}\t{row['headword']}\t{row['romanization'] or ''}\t"
            f"{row['pos']}\t{row['gloss']}\t{row['etymology'] or ''}\t"
            f"loan={row['loan_hint']}\t{row['entry_id']}"
        )


if __name__ == "__main__":
    main()
