#!/usr/bin/env python3
"""Write one ordered Lane A Hebrew whole-inventory coverage batch.

This lane-local writer runs only after the Biblical-witness priority queue is
empty.  It selects the first still-uncovered Hebrew families by the earliest
Kaikki source line represented in each family.  Judgments and terminal
closures receive cards; non-issued members receive one JSONL row.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

import lane_a_hebrew_full_coverage_batch as common


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
WITNESSES = ROOT / "data" / "hebrew-temporal-witnesses.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DATE = "2026-07-30"
FAMILY_LIMIT = 500


def block_markers(batch_number: int) -> tuple[str, str]:
    stem = (
        "<!-- LANE-A-HEBREW-WHOLE-INVENTORY-"
        f"2026-07-30-BATCH-{batch_number:03d}"
    )
    return f"{stem}:START -->", f"{stem}:END -->"


def audit_path(batch_number: int) -> Path:
    return (
        ROOT
        / "05-audits"
        / (
            "lane-a-2026-07-30-hebrew-inventory-full-coverage-"
            f"batch-{batch_number:03d}.md"
        )
    )


def load_temporal_witnesses() -> tuple[
    dict[str, list[dict[str, Any]]],
    dict[str, list[dict[str, Any]]],
]:
    document = json.loads(WITNESSES.read_text(encoding="utf-8"))
    by_entry: dict[str, list[dict[str, Any]]] = defaultdict(list)
    by_family: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for row in document["witnesses"]:
        by_entry[str(row["entry_id"])].append(row)
        by_family[str(row["family_id"])].append(row)
    return by_entry, by_family


def load_cohort(base_text: str) -> list[dict[str, Any]]:
    covered = common.covered_entry_ids(base_text)
    witnesses_by_entry, witnesses_by_family = load_temporal_witnesses()
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    selected: list[dict[str, Any]] = []
    try:
        families = connection.execute(
            """
            SELECT
              f.*,
              MIN(
                CAST(
                  substr(e.entry_id,instr(e.entry_id,':')+1)
                  AS INTEGER
                )
              ) AS first_source_line
            FROM families AS f
            JOIN family_members AS fm USING(family_id)
            JOIN entries AS e USING(entry_id)
            WHERE f.language='hebrew'
            GROUP BY f.family_id
            ORDER BY first_source_line,f.anchor_entry_id,f.family_id
            """
        ).fetchall()
        chosen_families = 0
        for family in families:
            members = [
                dict(row)
                for row in connection.execute(
                    """
                    SELECT e.*,fm.role,fm.link_types_json
                    FROM family_members AS fm
                    JOIN entries AS e USING(entry_id)
                    WHERE fm.family_id=?
                    ORDER BY
                      CAST(
                        substr(e.entry_id,instr(e.entry_id,':')+1)
                        AS INTEGER
                      ),
                      e.entry_id
                    """,
                    (family["family_id"],),
                )
            ]
            uncovered = [
                member
                for member in members
                if member["entry_id"] not in covered
            ]
            if not uncovered:
                continue
            chosen_families += 1
            family_witnesses = witnesses_by_family.get(
                str(family["family_id"]),
                [],
            )
            for member in uncovered:
                candidates = [
                    dict(row)
                    for row in connection.execute(
                        """
                        SELECT kind,form,status,rule_ids_json,route_flag
                        FROM candidates
                        WHERE entry_id=? AND kind IN ('root','core')
                        ORDER BY kind,route_flag,status,form,rule_ids_json
                        """,
                        (member["entry_id"],),
                    )
                ]
                selected.append(
                    {
                        **member,
                        "family_id": str(family["family_id"]),
                        "family_anchor": family["anchor_headword"],
                        "family_member_count": family["member_count"],
                        "family_construction": family["construction"],
                        "family_first_source_line": int(
                            family["first_source_line"]
                        ),
                        "candidates": candidates,
                        "own_witnesses": witnesses_by_entry.get(
                            str(member["entry_id"]),
                            [],
                        ),
                        "family_witness": (
                            family_witnesses[0]
                            if family_witnesses
                            else None
                        ),
                        "coverage_label": "التغطية العبرية العامة المرتبة",
                    }
                )
            if chosen_families >= FAMILY_LIMIT:
                break
    finally:
        connection.close()
    return selected


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch-number", type=int, required=True)
    args = parser.parse_args()
    if args.batch_number < 1:
        raise ValueError("رقم الدفعة يبدأ من 1")

    start, end = block_markers(args.batch_number)
    original = READING.read_text(encoding="utf-8")
    base = common.strip_own_block(original, start, end)
    cohort = load_cohort(base)
    if not cohort:
        raise ValueError("لا أسرة عبرية باقية؛ لا تكتب دفعة فارغة")

    cards: list[str] = []
    coverage_updates: list[dict[str, str]] = []
    terminal_entry_ids: set[str] = set()
    positives = 0
    closures = 0
    pending = 0
    distribution: dict[str, int] = defaultdict(int)
    for rank, entry in enumerate(cohort, 1):
        state, reason, terminal = common.classify(entry)
        distribution[state] += 1
        if (
            entry["entry_id"] in common.POSITIVE_SPECS
            and entry["own_witnesses"]
        ):
            positives += 1
            terminal_entry_ids.add(entry["entry_id"])
            cards.append(common.render_positive(rank, entry))
        elif terminal:
            closures += 1
            terminal_entry_ids.add(entry["entry_id"])
            cards.append(
                common.render_nonpositive(
                    rank,
                    entry,
                    state,
                    reason,
                    terminal,
                )
            )
        else:
            pending += 1
            coverage_updates.append(
                common.coverage_row(
                    entry,
                    "hebrew",
                    state,
                    reason,
                    f"hebrew-inventory-{args.batch_number:03d}",
                )
            )

    family_ids = list(dict.fromkeys(entry["family_id"] for entry in cohort))
    first_line = cohort[0]["family_first_source_line"]
    last_family_entries = [
        entry for entry in cohort if entry["family_id"] == family_ids[-1]
    ]
    last_line = last_family_entries[0]["family_first_source_line"]
    covered_after = common.covered_entry_ids(base)
    covered_after.update(entry["entry_id"] for entry in cohort)
    biblical_remaining, whole_remaining = common.remaining_family_counts(
        covered_after
    )
    queue_position = (
        f"بدأت الدفعة من الأسرة `{family_ids[0]}` عند سطر المصدر "
        f"{first_line}، وانتهت عند الأسرة `{family_ids[-1]}` ذات أول "
        f"سطر مصدر {last_line}؛ بقي في جرد العبرية {whole_remaining} "
        f"أسرة، وبقي من أولوية الشاهد التوراتي "
        f"{biblical_remaining} أسرة."
    )

    block = "\n".join(
        [
            "",
            start,
            "",
            "## التغطية العبرية العامة المرتبة، "
            f"الدفعة {args.batch_number} ({DATE})",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "أول الأسر غير المغطاة في جرد العبرية مرتبة بأقدم سطر "
            "مصدر Kaikki داخل الأسرة، بعد قياس فراغ أولوية الشاهد "
            "التوراتي. كتبت بطاقة RECOVERY-v2 للحكم الموجب أو "
            "الإغلاق النهائي فقط، وسجلت غير المحكوم سطرًا آليًا "
            "واحدًا؛ ولم يرث عضو حكم عضو آخر.",
            "",
            f"- الأسر: {len(family_ids)}.",
            f"- الأعضاء ذوو البطاقات الجديدة: {len(cards)}.",
            f"- سجلات التغطية الآلية الجديدة: {pending}.",
            f"- الصلات الموجبة: {positives}.",
            f"- الإغلاقات: {closures}.",
            f"- الأحكام غير الصادرة: {pending}.",
            f"- موضع الطابور: {queue_position}",
            "",
            *cards,
            end,
            "",
        ]
    )
    common.atomic_write(READING, base.rstrip() + "\n" + block)
    common.write_coverage_updates(coverage_updates, terminal_entry_ids)

    distribution_lines = [
        f"| `{state}` | {count} |"
        for state, count in sorted(distribution.items())
    ]
    audit = "\n".join(
        [
            "# محضر المسار أ: التغطية العبرية العامة المرتبة، "
            f"الدفعة {args.batch_number}",
            "",
            f"- التاريخ: {DATE}.",
            "- الحالة: محلي للمراجعة المضادة الثالثة، بلا إيداع.",
            "- الملكية: ملف العبرية وحده.",
            "- الترتيب: أقدم سطر مصدر في الأسرة ثم سطر كل عضو.",
            "- وحدة التغطية: بطاقة للحكم/الإغلاق، وسطر JSONL "
            "لغير المحكوم.",
            "- وحدة الحكم: العضو أو سلسلة المعنى، بلا وراثة أسرية.",
            f"- موضع الطابور: {queue_position}",
            "",
            "## الحصيلة",
            "",
            f"- الأسر المعالجة: {len(family_ids)}.",
            f"- البطاقات الجديدة: {len(cards)}.",
            f"- سجلات التغطية الآلية الجديدة: {pending}.",
            f"- الصلات الموجبة: {positives}.",
            f"- الإغلاقات: {closures}.",
            f"- الأحكام غير الصادرة: {pending}.",
            "",
            "| المصير | العدد |",
            "|---|---:|",
            *distribution_lines,
            "",
            "## الرقمان المفصولان",
            "",
            f"- الصلات الموجبة: {positives}.",
            f"- الإغلاقات: {closures}.",
            "",
            "## الملفات المكتوبة",
            "",
            "- `04-cross-linguistic/readings/hebrew.md`.",
            "- `04-cross-linguistic/data/lane_a_coverage.jsonl`.",
            "- `05-audits/"
            "lane-a-2026-07-30-hebrew-inventory-full-coverage-"
            f"batch-{args.batch_number:03d}.md`.",
            "- `scripts/lane_a_hebrew_inventory_batch.py`.",
            "",
            "لم يشغل git ولا أداة مشتركة ولا خط البرهان.",
            "",
        ]
    )
    common.atomic_write(audit_path(args.batch_number), audit)
    print(
        json.dumps(
            {
                "families": len(family_ids),
                "cards": len(cards),
                "coverage_rows": pending,
                "positive_connections": positives,
                "closures": closures,
                "pending_without_verdict": pending,
                "remaining_biblical_families": biblical_remaining,
                "remaining_hebrew_families": whole_remaining,
                "start_family": family_ids[0],
                "start_source_line": first_line,
                "end_family": family_ids[-1],
                "end_source_line": last_line,
                "distribution": dict(sorted(distribution.items())),
            },
            ensure_ascii=False,
            indent=2,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
