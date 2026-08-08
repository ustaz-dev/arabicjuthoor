#!/usr/bin/env python3
"""Rank proof families by the number of members still lacking final disposal.

This is a read-only view over ``data/proof-eligible-families.json``.  It keeps
all unresolved members together at family level, unlike the older singleton
inspector, and can enrich each member with the source-inventory row.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
REPORT = ROOT / "data" / "proof-eligible-families.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"


def compact(value: Any) -> str:
    return " ".join(str(value or "").split())


def load_entry(connection: sqlite3.Connection, entry_id: str) -> dict[str, Any]:
    row = connection.execute(
        "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
        "FROM entries WHERE entry_id=?",
        (entry_id,),
    ).fetchone()
    if row is None:
        return {}
    roots = connection.execute(
        "SELECT DISTINCT form,status,rule_ids_json,route_flag "
        "FROM candidates WHERE entry_id=? AND kind='root' "
        "ORDER BY route_flag,status,form,rule_ids_json",
        (entry_id,),
    ).fetchall()
    root_text = " | ".join(
        f"{candidate['form']}[{candidate['status']};"
        f"{','.join(json.loads(candidate['rule_ids_json'])) or 'identity'}]"
        for candidate in roots
    )
    return {
        "romanization": compact(row["romanization"]),
        "etymology": compact(row["etymology"]),
        "loan_hint": compact(row["loan_hint"]),
        "root_candidates": root_text,
    }


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument("--language", choices=("aramaic", "hebrew"))
    parser.add_argument(
        "--max-missing",
        type=int,
        default=2,
        help="show families with at most this many unresolved members",
    )
    parser.add_argument(
        "--state",
        action="append",
        help="retain families having an unresolved member in this state; repeatable",
    )
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--json", action="store_true", dest="as_json")
    parser.add_argument(
        "--no-inventory",
        action="store_true",
        help="do not enrich unresolved members from the inventory database",
    )
    args = parser.parse_args()
    if args.max_missing < 1 or args.limit < 1:
        parser.error("--max-missing and --limit must be positive")

    report = json.loads(REPORT.read_text(encoding="utf-8"))
    languages = [args.language] if args.language else ["aramaic", "hebrew"]
    wanted_states = set(args.state or [])
    families: list[dict[str, Any]] = []
    for language in languages:
        queue = report["languages"][language]["incomplete_family_queue"]
        for family in queue:
            if family["missing_member_count"] > args.max_missing:
                continue
            states = {member["current_state"] for member in family["missing_members"]}
            if wanted_states and states.isdisjoint(wanted_states):
                continue
            item = dict(family)
            item["language"] = language
            families.append(item)

    # Distance to closure is the governing key.  Within a tie, expose truly
    # unrecorded paperwork before already named parked states, then use stable
    # language/family identifiers so repeated runs cannot silently reorder work.
    families.sort(
        key=lambda family: (
            family["missing_member_count"],
            not any(
                member["current_state"] == "UNRECORDED"
                for member in family["missing_members"]
            ),
            family["language"],
            family["family_id"],
        )
    )
    families = families[: args.limit]

    connection: sqlite3.Connection | None = None
    if not args.no_inventory:
        connection = sqlite3.connect(DB)
        connection.row_factory = sqlite3.Row
        try:
            for family in families:
                for member in family["missing_members"]:
                    member.update(load_entry(connection, member["entry_id"]))
        finally:
            connection.close()

    if args.as_json:
        print(json.dumps(families, ensure_ascii=False, indent=2))
        return 0

    for rank, family in enumerate(families, 1):
        print(
            f"{rank}\t{family['language']}\t{family['family_id']}\t"
            f"missing={family['missing_member_count']}/{family['member_count']}\t"
            f"anchor={family['anchor_headword']}"
        )
        for member in family["missing_members"]:
            print(
                "  "
                + "\t".join(
                    [
                        member["entry_id"],
                        compact(member["headword"]),
                        compact(member.get("romanization")),
                        compact(member["pos"]),
                        compact(member["current_state"]),
                        compact(member["gloss"]),
                        compact(member.get("root_candidates")),
                        compact(member.get("etymology")),
                        compact(member.get("loan_hint")),
                    ]
                )
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
