#!/usr/bin/env python3
"""Cache complete old-Arabic sense fans for every licensed Aramaic root.

Retrieval only.  The output preserves the full selected witnesses without a
display character cap, names the independent lexica, and emits no candidate
choice or linguistic verdict.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
from pathlib import Path

from search_arabic_root_senses import (
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DEFAULT_OUTPUT = (
    ROOT / "cache" / "recovery_pipeline" / "aramaic-complete-root-fans.json"
)


def roots(db: Path) -> set[str]:
    connection = sqlite3.connect(db)
    try:
        return {
            row[0]
            for row in connection.execute(
                """
                SELECT DISTINCT c.form
                FROM candidates c
                JOIN entries e ON e.entry_id=c.entry_id
                WHERE e.language='aramaic'
                  AND c.kind IN ('root', 'hollow-root')
                  AND c.status='licensed'
                ORDER BY c.form
                """
            )
            if row[0]
        }
    finally:
        connection.close()


def build(db: Path, resources: Path) -> dict:
    wanted = roots(db)
    matches = matches_for_roots(resources, wanted, None)
    fans = {}
    for root in sorted(wanted):
        fan = independent_fan(matches.get(root, []))
        fans[root] = {
            "root": root,
            "independent_fan": fan,
        }
    complete = sum(
        item["independent_fan"]["judgment_ready"] for item in fans.values()
    )
    return {
        "schema": "aramaic-complete-root-fans-v1",
        "contract": {
            "retrieval_only": True,
            "full_witnesses_unclipped": True,
            "minimum_independent_old_lexica": 2,
            "verdicts_written": False,
            "proof_executed": False,
        },
        "summary": {
            "root_count": len(fans),
            "judgment_ready_count": complete,
            "fan_gap_count": len(fans) - complete,
        },
        "fans": fans,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.db.resolve(), args.resources.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Aramaic root-fan cache is missing or stale")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
