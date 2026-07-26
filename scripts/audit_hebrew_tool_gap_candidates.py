#!/usr/bin/env python3
"""Inventory the live Hebrew TOOL-GAP cards and their available evidence.

This is a retrieval-only audit.  It does not edit a reading or issue a verdict.
It joins the ledger, family database, and temporal-witness inventory so the
Arabic-fan campaign can distinguish new candidates from superseded cards.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import defaultdict
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
LEDGER = ROOT / "data" / "recovery-ledger.json"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CARD = re.compile(
    r"^### بطاقة: `(?P<family>hebrew:family:[0-9a-f]+)`، "
    r"(?P<title>[^\n]+)$",
    re.MULTILINE,
)
BLOCKER = re.compile(r"^-\s*عائق:\s*النوع=(?P<state>[^؛\n]+)", re.MULTILINE)
VERDICT = re.compile(
    r"^-\s*الحكم \(استكشاف\):\s*(?P<verdict>[^\n]+)", re.MULTILINE
)
SECTION = re.compile(r"(?=^### )", re.MULTILINE)


def reading_states() -> dict[str, list[dict[str, str]]]:
    result: dict[str, list[dict[str, str]]] = defaultdict(list)
    for section in SECTION.split(READING.read_text(encoding="utf-8")):
        match = CARD.match(section)
        if not match:
            continue
        blocker = BLOCKER.search(section)
        verdict = VERDICT.search(section)
        result[match.group("family")].append(
            {
                "title": match.group("title"),
                "blocker": blocker.group("state") if blocker else "",
                "verdict": verdict.group("verdict") if verdict else "",
            }
        )
    return result


def temporal_map() -> dict[str, list[dict[str, object]]]:
    payload = json.loads(WITNESSES.read_text(encoding="utf-8"))
    result: dict[str, list[dict[str, object]]] = defaultdict(list)
    for witness in payload["witnesses"]:
        if witness["stratum"] in {"biblical", "mishnaic"}:
            result[witness["family_id"]].append(witness)
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    targets = [
        row
        for row in ledger["suspended"]
        if row["file"] == "04-cross-linguistic/readings/hebrew.md"
        and row.get("blocker_type") == "TOOL-GAP"
    ]
    states = reading_states()
    witnesses = temporal_map()
    records: list[dict[str, object]] = []
    connection = sqlite3.connect(DB)
    try:
        for target in targets:
            family_match = re.search(
                r"hebrew:family:[0-9a-f]+", str(target["card"])
            )
            if not family_match:
                raise ValueError(f"Hebrew TOOL-GAP card lacks family id: {target}")
            family = family_match.group(0)
            members = [
                {
                    "entry_id": row[0],
                    "headword": row[1],
                    "pos": row[2],
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
            candidates = [
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
            other_cards = [
                row
                for row in states[family]
                if row["blocker"] != "TOOL-GAP"
                and (
                    row["blocker"] in {"READY", "VERIFIED"}
                    or row["verdict"].startswith(
                        ("ROOT-", "NUCLEUS-", "LOANWORD")
                    )
                )
            ]
            records.append(
                {
                    "card": target["card"],
                    "family": family,
                    "required": target.get("required", ""),
                    "members": members,
                    "candidates": candidates,
                    "old_witnesses": witnesses.get(family, []),
                    "issued_sibling_cards": other_cards,
                }
            )
    finally:
        connection.close()

    payload = {
        "schema": "hebrew-tool-gap-candidate-audit-v1",
        "status": "RETRIEVAL-ONLY-NO-VERDICTS",
        "count": len(records),
        "records": records,
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"TOOL-GAP cards: {len(records)}")
        for row in records:
            roots = sorted(
                {
                    str(item["form"])
                    for item in row["candidates"]
                    if item["status"] in {"licensed", "manual-condition"}
                }
            )
            print(
                f"{row['card']}\told={len(row['old_witnesses'])}"
                f"\tissued={len(row['issued_sibling_cards'])}"
                f"\troots={','.join(roots)}"
            )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
