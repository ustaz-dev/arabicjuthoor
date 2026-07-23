#!/usr/bin/env python3
"""Audit organic completion of the pinned Phoenician and Punic scouts.

Stable source entry identifiers, not rebuildable family identifiers, reconcile
the reading files to the live inventory.  A generated gap card or clinic
attempt marker alone is not evidence of an organic reading.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DEFAULT_SCOPE = ROOT / "data" / "phoenician-punic-family-scope.json"
DEFAULT_OUTPUT = (
    ROOT / "cache" / "recovery_pipeline" / "phoenician-punic-completion-audit.json"
)
READINGS = {
    "phoenician": ROOT / "04-cross-linguistic" / "readings" / "phoenician-punic-scout.md",
    "punic": ROOT / "04-cross-linguistic" / "readings" / "punic.md",
}

CARD = re.compile(r"^### (?:بطاقة|مراجعة عضوية):.*$", re.MULTILINE)
ENTRY_ID = re.compile(r"(kaikki_(?:phoenician|punic)_bounded_2026_07_16:\d+:[^`\s،؛\]\)\.]+)")
FAMILY_ID = re.compile(r"((?:phoenician|punic):family:[0-9a-f]+)")
ORGANIC = re.compile(r"القراءة الدلالية العضوية:")
POSITIVE = re.compile(r"الحكم \(استكشاف\):\s*(?:ROOT|NUCLEUS)-(?:TRACE|ECHO)")
RECOVERY = re.compile(r"عدسة الاسترداد(?:\s|:)")
SKEPTICAL = re.compile(r"عدسة التشكيك(?:\s|:)")


def reading_cards(path: Path) -> list[dict[str, Any]]:
    text = path.read_text(encoding="utf-8")
    starts = list(CARD.finditer(text))
    output: list[dict[str, Any]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        section = text[match.start():end]
        entry_ids = sorted(set(ENTRY_ID.findall(section)))
        family = FAMILY_ID.search(section)
        organic = bool(ORGANIC.search(section))
        positive = bool(
            POSITIVE.search(section)
            and RECOVERY.search(section)
            and SKEPTICAL.search(section)
        )
        output.append(
            {
                "line": text.count("\n", 0, match.start()) + 1,
                "heading": match.group(0),
                "entry_ids": entry_ids,
                "family_id": family.group(1) if family else None,
                "organic": organic or positive,
                "positive": positive,
                "attempt_only": (
                    "WEEK17-CLINIC-ATTEMPT:" in section
                    and not organic
                    and not positive
                ),
            }
        )
    return output


def build(db: Path, scope_path: Path) -> dict[str, Any]:
    scope = json.loads(scope_path.read_text(encoding="utf-8"))
    scope_by_family = {
        language: {
            family["family_id"]: family["scope_disposition"]
            for family in scope["languages"][language]["families"]
        }
        for language in READINGS
    }
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    try:
        language_payload: dict[str, Any] = {}
        overall = Counter()
        for language, reading in READINGS.items():
            cards = reading_cards(reading)
            entry_cards: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for card in cards:
                for entry_id in card["entry_ids"]:
                    entry_cards[entry_id].append(card)
            family_rows = connection.execute(
                """
                SELECT family_id,anchor_headword,construction,member_count
                FROM families WHERE language=? ORDER BY family_id
                """,
                (language,),
            ).fetchall()
            members: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in connection.execute(
                """
                SELECT fm.family_id,fm.entry_id,fm.role,e.headword,e.romanization,
                       e.pos,e.gloss,e.source_stratum
                FROM family_members fm JOIN entries e ON e.entry_id=fm.entry_id
                WHERE e.language=? ORDER BY fm.family_id,fm.entry_id
                """,
                (language,),
            ):
                members[row["family_id"]].append(dict(row))
            families: list[dict[str, Any]] = []
            positive_ids: set[str] = set()
            for row in family_rows:
                family = dict(row)
                disposition = scope_by_family[language].get(family["family_id"])
                lexical = [
                    member
                    for member in members[family["family_id"]]
                    if member["role"] != "nonlexical"
                    and member["source_stratum"] not in {"proper-name", "reconstruction"}
                ]
                member_results = []
                for member in lexical:
                    matches = entry_cards.get(member["entry_id"], [])
                    organic_cards = [card for card in matches if card["organic"]]
                    positive_cards = [card for card in matches if card["positive"]]
                    if positive_cards:
                        positive_ids.add(member["entry_id"])
                    member_results.append(
                        {
                            **member,
                            "organic_read": bool(organic_cards),
                            "positive": bool(positive_cards),
                            "cards": [
                                {"line": card["line"], "heading": card["heading"]}
                                for card in organic_cards
                            ],
                        }
                    )
                organic_count = sum(item["organic_read"] for item in member_results)
                structural = not lexical and disposition in {
                    "nonlexical-isolated",
                    "proper-name-isolated",
                    "reconstruction-isolated",
                }
                status = (
                    "complete-organic"
                    if lexical and organic_count == len(lexical)
                    else "complete-structural"
                    if structural
                    else "partial-organic"
                    if organic_count
                    else "unread"
                )
                families.append(
                    {
                        **family,
                        "scope_disposition": disposition,
                        "status": status,
                        "lexical_member_count": len(lexical),
                        "organically_read_member_count": organic_count,
                        "members": member_results,
                    }
                )
            statuses = Counter(family["status"] for family in families)
            lexical_count = sum(family["lexical_member_count"] for family in families)
            organic_count = sum(
                family["organically_read_member_count"] for family in families
            )
            summary = {
                "family_count": len(families),
                "lexical_member_count": lexical_count,
                "organically_read_member_count": organic_count,
                "remaining_lexical_member_count": lexical_count - organic_count,
                "positive_member_count": len(positive_ids),
                "family_status_counts": dict(sorted(statuses.items())),
            }
            overall["family_count"] += len(families)
            overall["lexical_member_count"] += lexical_count
            overall["organically_read_member_count"] += organic_count
            overall["remaining_lexical_member_count"] += lexical_count - organic_count
            overall["positive_member_count"] += len(positive_ids)
            language_payload[language] = {
                "reading": reading.relative_to(ROOT).as_posix(),
                "summary": summary,
                "families": families,
            }
    finally:
        connection.close()
    return {
        "schema": "phoenician-punic-completion-audit-v1",
        "contract": {
            "bounded_scout_only": True,
            "stable_entry_ids_are_reconciliation_key": True,
            "attempt_marker_is_not_organic_reading": True,
            "shared_ledger_touched": False,
            "proof_executed": False,
        },
        "inventory_db": db.relative_to(ROOT).as_posix(),
        "scope": scope_path.relative_to(ROOT).as_posix(),
        "overall_summary": dict(overall),
        "languages": language_payload,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--scope", type=Path, default=DEFAULT_SCOPE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.db.resolve(), args.scope.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Phoenician/Punic completion audit is missing or stale")
        print(json.dumps(payload["overall_summary"], ensure_ascii=False))
        for language in READINGS:
            print(
                language
                + ": "
                + json.dumps(
                    payload["languages"][language]["summary"],
                    ensure_ascii=False,
                )
            )
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(payload["overall_summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
