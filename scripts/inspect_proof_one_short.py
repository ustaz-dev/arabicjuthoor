#!/usr/bin/env python3
"""Print a compact, read-only slice of the official one-member-short queue."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "proof-eligible-families.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("language", choices=("aramaic", "hebrew"))
    parser.add_argument("--state")
    parser.add_argument("--start", type=int, default=1)
    parser.add_argument("--end", type=int, default=50)
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start:
        parser.error("require 1 <= start <= end")
    payload = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = payload["languages"][args.language]["one_member_short"]
    if args.state:
        queue = [item for item in queue if item["current_state"] == args.state]
    selected = queue[args.start - 1 : args.end]
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for rank, item in enumerate(selected, args.start):
            entry_id = item["missing_entry_id"]
            entry = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,"
                "loan_hint FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            roots = connection.execute(
                "SELECT DISTINCT form,status,rule_ids_json,route_flag "
                "FROM candidates WHERE entry_id=? AND kind='root' "
                "ORDER BY route_flag,status,form,rule_ids_json",
                (entry_id,),
            ).fetchall()
            root_text = " | ".join(
                f"{row['form']}[{row['status']};"
                f"{','.join(json.loads(row['rule_ids_json'])) or 'identity'}]"
                for row in roots
            )
            etymology = (
                " ".join(str(entry["etymology"]).split()) if entry else ""
            )
            print(
                f"{rank}\t{item['family_id']}\t{entry_id}\t"
                f"{item['missing_headword']}\t{item['missing_pos']}\t"
                f"{item['current_state']}\t{item['missing_gloss']}\t"
                f"{root_text}\t{etymology}"
            )
    finally:
        connection.close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
