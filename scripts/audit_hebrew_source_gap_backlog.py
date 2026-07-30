#!/usr/bin/env python3
"""Inventory the live Hebrew SOURCE-GAP backlog without issuing verdicts.

The audit joins each real reading card to the pinned family inventory and to
the explicit biblical or Mishnaic examples extracted from Kaikki.  A witness
is kept at entry level as well as family level because the signed verdict-unit
law forbids one member from lending its chronology to another.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

import build_status_snapshot as status


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CACHE = ROOT / "cache" / "recovery_pipeline" / "hebrew-source-gap-audit.json"
FAMILY = re.compile(r"hebrew:family:[0-9a-f]+")
REQUIRED = re.compile(
    r"^-\s*عائق:\s*النوع=SOURCE-GAP؛\s*يتطلب=(?P<required>[^\n]+)$",
    re.MULTILINE,
)


def temporal_maps() -> tuple[
    dict[str, list[dict[str, object]]],
    dict[str, list[dict[str, object]]],
]:
    payload = json.loads(WITNESSES.read_text(encoding="utf-8"))
    by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    by_entry: dict[str, list[dict[str, object]]] = defaultdict(list)
    for witness in payload["witnesses"]:
        if witness["stratum"] not in {"biblical", "mishnaic"}:
            continue
        by_family[str(witness["family_id"])].append(witness)
        by_entry[str(witness["entry_id"])].append(witness)
    return by_family, by_entry


def family_members(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "entry_id": row[0],
            "headword": row[1],
            "part_of_speech": row[2],
            "gloss": row[3],
            "etymology": row[4],
            "loan_hint": bool(row[5]),
            "form_of": bool(row[6]),
        }
        for row in connection.execute(
            """
            SELECT e.entry_id,e.headword,e.pos,e.gloss,e.etymology,
                   e.loan_hint,e.form_of
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE fm.family_id=?
            ORDER BY e.entry_id
            """,
            (family,),
        )
    ]


def candidate_roots(
    connection: sqlite3.Connection, family: str
) -> list[dict[str, object]]:
    return [
        {
            "kind": row[0],
            "form": row[1],
            "status": row[2],
            "rules": json.loads(row[3]),
        }
        for row in connection.execute(
            """
            SELECT DISTINCT c.kind,c.form,c.status,c.rule_ids_json
            FROM family_members fm
            JOIN candidates c ON c.entry_id=fm.entry_id
            WHERE fm.family_id=?
              AND c.kind IN ('root','hollow-root','nucleus')
            ORDER BY c.kind,c.status,c.form,c.rule_ids_json
            """,
            (family,),
        )
    ]


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    by_family, by_entry = temporal_maps()
    cards = status.reading_cards(READING.read_text(encoding="utf-8"))
    targets = [card for card in cards if status.live_blocker(card) == "SOURCE-GAP"]
    records: list[dict[str, object]] = []
    connection = sqlite3.connect(DB)
    try:
        for card in targets:
            family_match = FAMILY.search(card)
            if not family_match:
                raise ValueError(f"SOURCE-GAP card lacks family id: {card.splitlines()[0]}")
            family = family_match.group(0)
            members = family_members(connection, family)
            roots = candidate_roots(connection, family)
            member_witnesses = {
                str(member["entry_id"]): by_entry.get(str(member["entry_id"]), [])
                for member in members
                if by_entry.get(str(member["entry_id"]))
            }
            required_match = REQUIRED.search(card)
            records.append(
                {
                    "heading": card.splitlines()[0],
                    "family": family,
                    "required": (
                        required_match.group("required").strip()
                        if required_match
                        else ""
                    ),
                    "members": members,
                    "candidate_roots": roots,
                    "family_old_witnesses": by_family.get(family, []),
                    "member_old_witnesses": member_witnesses,
                }
            )
    finally:
        connection.close()

    with_family_witness = sum(bool(row["family_old_witnesses"]) for row in records)
    with_member_witness = sum(bool(row["member_old_witnesses"]) for row in records)
    loan_hint = sum(
        any(bool(member["loan_hint"]) for member in row["members"])
        for row in records
    )
    all_form_of = sum(
        bool(row["members"])
        and all(bool(member["form_of"]) for member in row["members"])
        for row in records
    )
    parts_of_speech = Counter(
        str(member["part_of_speech"] or "UNSPECIFIED")
        for row in records
        for member in row["members"]
    )
    summary = {
        "cards": len(records),
        "with_family_old_witness": with_family_witness,
        "with_entry_level_old_witness": with_member_witness,
        "without_old_witness": len(records) - with_family_witness,
        "with_loan_hint": loan_hint,
        "all_members_form_of": all_form_of,
        "member_parts_of_speech": dict(parts_of_speech.most_common()),
    }
    payload = {
        "schema": "hebrew-source-gap-audit-v1",
        "status": "RETRIEVAL-ONLY-NO-VERDICTS",
        "summary": summary,
        "records": records,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    CACHE.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
