#!/usr/bin/env python3
"""Print a read-only slice of the pinned Hebrew biblical-member queue."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int, required=True, help="one-based rank")
    parser.add_argument("--end", type=int, required=True, help="inclusive rank")
    parser.add_argument("--compact", action="store_true")
    args = parser.parse_args()
    if args.start < 1 or args.end < args.start:
        parser.error("require 1 <= start <= end")
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue = payload["unread_biblical_lexical_queue"]
    selected = queue[args.start - 1 : args.end]
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    output = []
    try:
        for rank, item in enumerate(selected, args.start):
            entry = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,"
                "loan_hint FROM entries WHERE entry_id=?",
                (item["entry_id"],),
            ).fetchone()
            roots = connection.execute(
                "SELECT DISTINCT form,status,rule_ids_json,route_flag "
                "FROM candidates WHERE entry_id=? AND kind='root' "
                "ORDER BY route_flag,status,form,rule_ids_json",
                (item["entry_id"],),
            ).fetchall()
            output.append(
                {
                    "rank": rank,
                    "family_id": item["family_id"],
                    "entry": dict(entry) if entry is not None else None,
                    "biblical_witnesses": item["biblical_witnesses"],
                    "root_candidates": [
                        {
                            "form": row["form"],
                            "status": row["status"],
                            "rules": json.loads(row["rule_ids_json"]),
                            "route_flag": bool(row["route_flag"]),
                        }
                        for row in roots
                    ],
                }
            )
    finally:
        connection.close()
    if args.compact:
        for item in output:
            entry = item["entry"] or {}
            roots = " | ".join(
                f"{root['form']}[{root['status']};"
                f"{','.join(root['rules']) or 'identity'}]"
                for root in item["root_candidates"]
            )
            etymology = " ".join(str(entry.get("etymology", "")).split())
            print(
                f"{item['rank']}\t{item['family_id']}\t"
                f"{entry.get('headword', '')}\t{entry.get('romanization', '')}\t"
                f"{entry.get('pos', '')}\t{entry.get('gloss', '')}\t"
                f"{roots}\t{etymology}"
            )
    else:
        print(json.dumps(output, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
