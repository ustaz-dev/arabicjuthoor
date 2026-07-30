#!/usr/bin/env python3
"""Build the deterministic Hebrew queue led by explicit biblical witnesses.

This is a retrieval-only artifact. It does not turn a reference into a
linguistic verdict, and it keeps every recorded temporal stratum distinct.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from collections import defaultdict
from pathlib import Path

import build_status_snapshot as status


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DATABASE = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
OUTPUT = ROOT / "data" / "hebrew-biblical-priority-queue.json"

FAMILY_ID = re.compile(r"hebrew:family:[0-9a-f]+")
TEMPORAL_BLOCKER_PREFIX = "وسم طبقة أو نطاق زمني منشور"
REFINED_MARKER = "<!-- HEBREW-TEMPORAL-PRIORITY:HEBREW-BIBLICAL-01:"
STRATUM_ORDER = {
    "biblical": 0,
    "mishnaic": 1,
    "rabbinic-other": 2,
    "other-referenced": 3,
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def eligible_lexical_members(
    connection: sqlite3.Connection,
) -> dict[str, dict[str, object]]:
    rows = connection.execute(
        """
        WITH candidate_strength AS (
          SELECT c.entry_id,
                 MAX(CASE WHEN c.kind='root' AND c.status='licensed'
                               AND c.route_flag=0 THEN 1 ELSE 0 END)
                   AS licensed_full_root,
                 MIN(CASE WHEN c.kind='root' AND c.status='licensed'
                               AND c.route_flag=0
                          THEN json_array_length(c.rule_ids_json) END)
                   AS root_rule_count,
                 MIN(CASE WHEN c.status='licensed' AND c.route_flag=0
                          THEN json_array_length(c.rule_ids_json) END)
                   AS any_rule_count,
                 SUM(CASE WHEN c.status='licensed' AND c.route_flag=1
                          THEN 1 ELSE 0 END)
                   AS route_required_candidate_count
          FROM candidates AS c
          GROUP BY c.entry_id
        ), eligible AS (
          SELECT fm.family_id,e.entry_id,e.headword,e.romanization,e.pos,e.gloss,
                 COALESCE(cs.licensed_full_root,0) AS licensed_full_root,
                 COALESCE(cs.root_rule_count,cs.any_rule_count)
                   AS licensed_rule_count,
                 COALESCE(cs.route_required_candidate_count,0)
                   AS route_required_candidate_count
          FROM family_members AS fm
          JOIN entries AS e ON e.entry_id=fm.entry_id
          LEFT JOIN candidate_strength AS cs ON cs.entry_id=e.entry_id
          WHERE e.language='hebrew'
            AND fm.role NOT IN ('form','nonlexical')
            AND e.form_of=0
            AND e.loan_hint=0
            AND e.pos NOT IN (
              'name','character','symbol','punct','suffix','prefix','affix',
              'infix','circumfix','interfix','combining_form'
            )
        )
        SELECT family_id,entry_id,headword,romanization,pos,gloss,
               licensed_full_root,licensed_rule_count,
               route_required_candidate_count
        FROM eligible
        ORDER BY entry_id
        """
    ).fetchall()
    fields = (
        "family_id",
        "entry_id",
        "headword",
        "romanization",
        "part_of_speech",
        "gloss",
        "licensed_full_root",
        "licensed_rule_count",
        "route_required_candidate_count",
    )
    return {
        row[1]: dict(zip(fields, row))
        for row in rows
    }


def strength_key(item: dict[str, object]) -> tuple[object, ...]:
    rule_count = item["licensed_rule_count"]
    return (
        -int(item["licensed_full_root"]),
        999 if rule_count is None else int(rule_count),
        -len(str(item["gloss"]).strip()),
        str(item["entry_id"]),
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    witness_document = json.loads(WITNESSES.read_text(encoding="utf-8"))
    witnesses_by_family: dict[str, list[dict[str, object]]] = defaultdict(list)
    for witness in witness_document["witnesses"]:
        witnesses_by_family[witness["family_id"]].append(witness)

    reading_text = READING.read_text(encoding="utf-8")
    cards = status.reading_cards(reading_text)
    written_families = set(FAMILY_ID.findall(reading_text))
    completed_priority_batch = (
        10
        if "<!-- HEBREW-BIBLICAL-UNREAD-BATCH-01 -->" in reading_text
        else 0
    )
    biblical_families = {
        family_id
        for family_id, witnesses in witnesses_by_family.items()
        if any(item["stratum"] == "biblical" for item in witnesses)
    }

    temporal_blocked: list[dict[str, object]] = []
    temporal_refined: list[dict[str, object]] = []
    for card in cards:
        family_match = FAMILY_ID.search(card)
        if not family_match:
            continue
        family_id = family_match.group(0)
        is_refined = REFINED_MARKER in card
        blocker = re.search(
            r"^- عائق: النوع=SOURCE-GAP؛ يتطلب=(.+)$",
            card,
            re.MULTILINE,
        )
        is_blocked = (
            status.live_blocker(card) == "SOURCE-GAP"
            and blocker is not None
            and blocker.group(1).startswith(TEMPORAL_BLOCKER_PREFIX)
        )
        if not is_refined and not is_blocked:
            continue
        family_witnesses = witnesses_by_family.get(family_id, [])
        strata = sorted(
            {item["stratum"] for item in family_witnesses},
            key=STRATUM_ORDER.get,
        )
        record = {
            "family_id": family_id,
            "heading": card.splitlines()[0].removeprefix("### "),
            "strata": strata,
            "witnesses": [
                {
                    "entry_id": item["entry_id"],
                    "headword": item["headword"],
                    "stratum": item["stratum"],
                    "reference": item["reference"],
                    "example_text": item["example_text"],
                }
                for item in family_witnesses
            ],
        }
        if is_refined:
            temporal_refined.append(record)
        else:
            temporal_blocked.append(record)

    connection = sqlite3.connect(DATABASE)
    try:
        eligible_by_entry = eligible_lexical_members(connection)
        eligible_families = {
            str(item["family_id"]) for item in eligible_by_entry.values()
        }
        family_metadata = {
            row[0]: {
                "anchor_headword": row[1],
                "construction": row[2],
                "member_count": row[3],
                "lemma_count": row[4],
                "form_count": row[5],
                "nonlexical_count": row[6],
            }
            for row in connection.execute(
                """
                SELECT family_id,anchor_headword,construction,member_count,
                       lemma_count,form_count,nonlexical_count
                FROM families
                WHERE language='hebrew'
                """
            )
        }
    finally:
        connection.close()

    unread_biblical = biblical_families - written_families
    lexical_queue: list[dict[str, object]] = []
    witness_resolution_queue: list[dict[str, object]] = []
    isolation_queue: list[dict[str, object]] = []
    for family_id in unread_biblical:
        witness_rows = [
            {
                "entry_id": item["entry_id"],
                "headword": item["headword"],
                "part_of_speech": item["part_of_speech"],
                "reference": item["reference"],
                "example_text": item["example_text"],
            }
            for item in witnesses_by_family[family_id]
            if item["stratum"] == "biblical"
        ]
        base = {
            "family_id": family_id,
            **family_metadata[family_id],
            "biblical_witnesses": witness_rows,
        }
        exact_witness_members = {
            str(item["entry_id"]): eligible_by_entry[str(item["entry_id"])]
            for item in witness_rows
            if str(item["entry_id"]) in eligible_by_entry
        }
        if exact_witness_members:
            selected = min(
                exact_witness_members.values(),
                key=strength_key,
            )
            lexical_queue.append({**selected, **base})
        elif family_id in eligible_families:
            witness_resolution_queue.append(base)
        else:
            isolation_queue.append(base)

    lexical_queue.sort(key=strength_key)
    for rank, item in enumerate(lexical_queue, 1):
        item["strength_rank"] = rank
    witness_resolution_queue.sort(
        key=lambda item: (item["anchor_headword"], item["family_id"])
    )
    isolation_queue.sort(
        key=lambda item: (item["anchor_headword"], item["family_id"])
    )
    covered_temporal = [
        item for item in temporal_blocked if item["strata"]
    ]
    refined_temporal = [
        item for item in temporal_refined if item["strata"]
    ]
    exclusive_strata = defaultdict(int)
    for item in [*covered_temporal, *refined_temporal]:
        exclusive_strata[item["strata"][0]] += 1

    summary = {
        "biblical_families": len(biblical_families),
        "biblical_families_already_written": len(
            biblical_families & written_families
        ),
        "biblical_families_unread": len(unread_biblical),
        "unread_exact_member_lexical_queue": len(lexical_queue),
        "unread_witness_resolution_queue": len(witness_resolution_queue),
        "unread_isolation_queue": len(isolation_queue),
        "temporal_blocker_cards": len(temporal_blocked),
        "temporal_blocker_cards_with_any_reference": len(covered_temporal),
        "temporal_refined_cards_with_any_reference": len(refined_temporal),
        "covered_temporal_exclusive_strata": dict(
            sorted(exclusive_strata.items())
        ),
    }
    expected = {
        "biblical_families": 1289,
        "biblical_families_already_written": 197 + completed_priority_batch,
        "biblical_families_unread": 1092 - completed_priority_batch,
        "unread_exact_member_lexical_queue": (
            summary["unread_exact_member_lexical_queue"]
        ),
        "unread_witness_resolution_queue": (
            summary["unread_witness_resolution_queue"]
        ),
        "unread_isolation_queue": summary["unread_isolation_queue"],
        "temporal_blocker_cards": summary["temporal_blocker_cards"],
        "temporal_blocker_cards_with_any_reference": (
            summary["temporal_blocker_cards_with_any_reference"]
        ),
        "temporal_refined_cards_with_any_reference": (
            summary["temporal_refined_cards_with_any_reference"]
        ),
        "covered_temporal_exclusive_strata": {
            "biblical": 16,
            "mishnaic": 3,
            "other-referenced": 9,
            "rabbinic-other": 1,
        },
    }
    if summary != expected:
        raise ValueError(f"unexpected Hebrew queue state: {summary}")
    if (
        summary["temporal_blocker_cards"]
        + summary["temporal_refined_cards_with_any_reference"]
        != 134
        or summary["temporal_blocker_cards_with_any_reference"]
        + summary["temporal_refined_cards_with_any_reference"]
        != 29
    ):
        raise ValueError(
            "the 134-card temporal baseline or its 29 referenced cards drifted"
        )

    document = {
        "schema": "hebrew-biblical-priority-queue-v2",
        "status": "RETRIEVAL-ONLY-NO-VERDICTS",
        "source": {
            "temporal_inventory": str(WITNESSES.relative_to(ROOT)).replace(
                "\\", "/"
            ),
            "reading": str(READING.relative_to(ROOT)).replace("\\", "/"),
            "inventory": str(DATABASE.relative_to(ROOT)).replace("\\", "/"),
        },
        "ordering_contract": [
            "the queued lexical member itself must carry the explicit biblical witness",
            "a family witness never transfers automatically to a homonymous or compound member",
            "licensed full root before lower comparison degrees",
            "fewer licensed shift rows before more rows",
            "richer gloss only as a retrieval tie-breaker",
            "families requiring witness-to-member resolution remain visible in a separate queue",
            "proper names and nonlexical-only families remain visible in a separate isolation queue",
        ],
        "summary": summary,
        "blocked_temporal_cards_with_references": covered_temporal,
        "refined_temporal_cards_with_references": refined_temporal,
        "unread_biblical_lexical_queue": lexical_queue,
        "unread_biblical_witness_resolution_queue": witness_resolution_queue,
        "unread_biblical_isolation_queue": isolation_queue,
    }
    rendered = json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Hebrew biblical-priority queue is stale")
        print("Hebrew biblical-priority queue: CLEAN")
        return 0

    atomic_write(OUTPUT, rendered)
    print(json.dumps(summary, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
