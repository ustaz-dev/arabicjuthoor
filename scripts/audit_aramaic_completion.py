#!/usr/bin/env python3
"""Audit live Aramaic reading completeness against the current family inventory.

This is accountability and retrieval infrastructure only.  Family identifiers
can change when the structural family layer is rebuilt, while source entry
identifiers remain stable.  The audit therefore reconciles reading cards to
the current inventory by source entry ID, and treats an explicit organic
semantic-reading line or a fully written two-lens positive card as evidence of
human reading.  A Week 17 attempt marker by itself is deliberately insufficient.

The script does not write a verdict, refresh a shared ledger, or run the proof
line.
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
DEFAULT_READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DEFAULT_OUTPUT = (
    ROOT / "cache" / "recovery_pipeline" / "aramaic-completion-audit.json"
)

CARD = re.compile(r"^### (?:بطاقة|مراجعة عضوية).*$", re.MULTILINE)
ENTRY_ID = re.compile(r"(kaikki_aramaic:(\d+):[^`\s،؛\]\)\.]+)")
FAMILY_ID = re.compile(r"(aramaic:family:[0-9a-f]+)")
ORGANIC_LINE = re.compile(r"القراءةُ?\s+الدلاليةُ?\s+العضوية")
POSITIVE = re.compile(r"الحكم \(استكشاف\):\s*(?:ROOT|NUCLEUS)-(?:TRACE|ECHO)")
# Older approved cards sometimes record both lenses in the notes field rather
# than as two standalone bullets.  The constitutional requirement is that both
# reviews be present, not that a colon follow the lens name.
RECOVERY_LENS = re.compile(r"عدسة الاسترداد(?:\s|:)")
SKEPTICAL_LENS = re.compile(r"عدسة التشكيك(?:\s|:)")
STRUCTURAL_CLOSURE = re.compile(
    r"(?:PROPER-NAME-ISOLATED|LOAN-ROUTE-ISOLATED|NONLEXICAL|FORM-OF|"
    r"ALTERNATIVE-FORM|SOURCE-GAP)"
)
SOURCE_CITATION = re.compile(
    r"Kaikki Aramaic[^0-9\n]{0,40}"
    r"(?:الأسطر|السطر|المداخل|المدخلين|المدخل)"
    r"\s+([0-9]+)(?:\s*[-–]\s*([0-9]+))?"
)


def cards(reading: Path) -> list[dict[str, Any]]:
    text = reading.read_text(encoding="utf-8")
    starts = list(CARD.finditer(text))
    output: list[dict[str, Any]] = []
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        section = text[match.start():end]
        family_match = FAMILY_ID.search(match.group(0))
        explicit_organic = bool(
            ORGANIC_LINE.search(section)
            or match.group(0).startswith("### مراجعة عضوية:")
        )
        full_positive = bool(
            POSITIVE.search(section)
            and RECOVERY_LENS.search(section)
            and SKEPTICAL_LENS.search(section)
        )
        explicit_ids = sorted({item[0] for item in ENTRY_ID.findall(section)})
        source_rows = {int(item[1]) for item in ENTRY_ID.findall(section)}
        for citation in SOURCE_CITATION.finditer(section):
            start = int(citation.group(1))
            end_row = int(citation.group(2) or start)
            if end_row >= start and end_row - start <= 100:
                source_rows.update(range(start, end_row + 1))
        output.append(
            {
                "line": text.count("\n", 0, match.start()) + 1,
                "heading": match.group(0),
                "family_id": family_match.group(1) if family_match else None,
                "entry_ids": explicit_ids,
                "source_rows": sorted(source_rows),
                "organic_evidence": explicit_organic or full_positive,
                "organic_evidence_kind": (
                    "explicit-organic-line"
                    if explicit_organic
                    else "full-two-lens-positive"
                    if full_positive
                    else None
                ),
                "attempt_marker_only": (
                    "WEEK17-CLINIC-ATTEMPT:" in section
                    and not explicit_organic
                    and not full_positive
                ),
                "structural_closure_evidence": bool(STRUCTURAL_CLOSURE.search(section)),
            }
        )
    return output


def build(db: Path, reading: Path) -> dict[str, Any]:
    card_rows = cards(reading)
    family_to_cards: dict[str, list[dict[str, Any]]] = defaultdict(list)

    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    try:
        family_rows = connection.execute(
            """
            SELECT family_id, anchor_headword, construction, member_count,
                   lemma_count, form_count, nonlexical_count,
                   candidate_bearing_member_count
            FROM families
            WHERE language='aramaic'
            ORDER BY family_id
            """
        ).fetchall()
        members_by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
        for row in connection.execute(
            """
            SELECT fm.family_id, fm.entry_id, fm.role, e.headword,
                   e.romanization, e.pos, e.gloss, e.processing_status,
                   e.candidate_count, e.loan_hint
            FROM family_members fm
            JOIN entries e ON e.entry_id=fm.entry_id
            WHERE e.language='aramaic'
            ORDER BY fm.family_id, fm.entry_id
            """
        ):
            members_by_family[row["family_id"]].append(dict(row))
    finally:
        connection.close()

    source_row_to_entry: dict[int, str] = {}
    for members in members_by_family.values():
        for member in members:
            match = re.match(r"kaikki_aramaic:(\d+):", member["entry_id"])
            if match:
                source_row_to_entry[int(match.group(1))] = member["entry_id"]

    entry_to_cards: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for card in card_rows:
        if card["family_id"]:
            family_to_cards[card["family_id"]].append(card)
        reconciled = set(card["entry_ids"])
        reconciled.update(
            source_row_to_entry[row]
            for row in card["source_rows"]
            if row in source_row_to_entry
        )
        card["reconciled_entry_ids"] = sorted(reconciled)
        for entry_id in reconciled:
            entry_to_cards[entry_id].append(card)

    families: list[dict[str, Any]] = []
    for row in family_rows:
        family = dict(row)
        members = members_by_family[family["family_id"]]
        member_results: list[dict[str, Any]] = []
        for member in members:
            matching = entry_to_cards.get(member["entry_id"], [])
            organic = [card for card in matching if card["organic_evidence"]]
            attempts = [card for card in matching if card["attempt_marker_only"]]
            member_results.append(
                {
                    **member,
                    "organic_read": bool(organic),
                    "organic_cards": [
                        {
                            "line": card["line"],
                            "heading": card["heading"],
                            "kind": card["organic_evidence_kind"],
                        }
                        for card in organic
                    ],
                    "attempt_only_cards": [
                        {"line": card["line"], "heading": card["heading"]}
                        for card in attempts
                    ],
                }
            )

        lexical = [
            member
            for member in member_results
            if member["role"] != "nonlexical"
        ]
        direct_family_cards = family_to_cards.get(family["family_id"], [])
        structural_only = not lexical and any(
            card["structural_closure_evidence"] for card in direct_family_cards
        )
        organically_read = sum(member["organic_read"] for member in lexical)
        status = (
            "complete-organic"
            if lexical and organically_read == len(lexical)
            else "complete-structural"
            if structural_only
            else "partial-organic"
            if organically_read
            else "attempt-only"
            if any(member["attempt_only_cards"] for member in lexical)
            else "unread"
        )
        families.append(
            {
                **family,
                "status": status,
                "lexical_member_count": len(lexical),
                "organically_read_member_count": organically_read,
                "members": member_results,
            }
        )

    status_counts = Counter(family["status"] for family in families)
    lexical_members = sum(family["lexical_member_count"] for family in families)
    organic_members = sum(
        family["organically_read_member_count"] for family in families
    )
    return {
        "schema": "aramaic-completion-audit-v1",
        "contract": {
            "retrieval_only": True,
            "family_ids_reconciled_by_stable_entry_ids": True,
            "attempt_marker_is_not_organic_reading": True,
            "verdicts_written": False,
            "shared_ledger_touched": False,
            "proof_executed": False,
        },
        "inventory_db": db.relative_to(ROOT).as_posix(),
        "reading": reading.relative_to(ROOT).as_posix(),
        "summary": {
            "family_count": len(families),
            "lexical_member_count": lexical_members,
            "organically_read_member_count": organic_members,
            "remaining_lexical_member_count": lexical_members - organic_members,
            "family_status_counts": dict(sorted(status_counts.items())),
        },
        "families": families,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--reading", type=Path, default=DEFAULT_READING)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.db.resolve(), args.reading.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Aramaic completion audit is missing or stale")
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
