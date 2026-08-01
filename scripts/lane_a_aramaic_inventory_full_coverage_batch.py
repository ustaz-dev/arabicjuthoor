#!/usr/bin/env python3
"""Write one ordered Lane A Aramaic whole-inventory coverage batch.

Terminal closures receive cards; non-issued members receive one JSONL row.
"""

from __future__ import annotations

import argparse
import json
import sqlite3
from collections import defaultdict
from pathlib import Path
from typing import Any

import lane_a_hebrew_full_coverage_batch as common
import lane_a_validate_batch as validator


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DATE = "2026-07-30"
FAMILY_LIMIT = 200


def block_markers(batch_number: int) -> tuple[str, str]:
    stem = (
        "<!-- LANE-A-ARAMAIC-WHOLE-INVENTORY-"
        f"2026-07-30-BATCH-{batch_number:03d}"
    )
    return f"{stem}:START -->", f"{stem}:END -->"


def audit_path(batch_number: int) -> Path:
    return (
        ROOT
        / "05-audits"
        / (
            "lane-a-2026-07-30-aramaic-inventory-full-coverage-"
            f"batch-{batch_number:03d}.md"
        )
    )


def covered_entry_ids(text: str) -> set[str]:
    _, cards = validator.read_cards("aramaic", READING)
    covered = {
        entry_id
        for card in cards
        for entry_id in card.member_ids
        if entry_id.startswith("kaikki_aramaic:")
    }
    covered.update(common.issued_entry_ids_from_text(text, "aramaic"))
    covered.update(common.coverage_entry_ids("aramaic"))
    return covered


def load_cohort(base_text: str) -> list[dict[str, Any]]:
    covered = covered_entry_ids(base_text)
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
            WHERE f.language='aramaic'
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
                        "own_witnesses": [],
                        "family_witness": None,
                        "coverage_label": "التغطية الآرامية العامة المرتبة",
                        "source_label": "Kaikki Aramaic",
                    }
                )
            if chosen_families >= FAMILY_LIMIT:
                break
    finally:
        connection.close()
    return selected


def classify(entry: dict[str, Any]) -> tuple[str, str, bool]:
    if bool(entry["form_of"]) or entry["role"] == "form":
        return (
            "FORM-OF-ISOLATED",
            "صورة صرفية منشورة لمدخل آخر؛ لا ترث حكم الأم",
            True,
        )
    if entry["role"] == "nonlexical":
        return (
            "NONLEXICAL-ISOLATED",
            "صنف غير معجمي مصرح به في بناء الجرد؛ لا يحمل جذرا مستقلا",
            True,
        )
    gloss = str(entry["gloss"] or "").lower()
    if entry["role"] == "alternative" and "spelling of" in gloss:
        return (
            "FORM-OF-ISOLATED",
            "رسم بديل مصرح بأنه صورة لمدخل آخر؛ لا يرث حكمه",
            True,
        )
    if entry["pos"] == "name":
        return (
            "PROPER-NAME-ISOLATED",
            "علم مصرح به في حقل الصنف؛ يعزل عن المقارنة المعجمية",
            True,
        )
    if entry["role"] == "alternative" and (
        "acronym" in gloss or "abbreviation" in gloss
    ):
        return (
            "ABBREVIATION",
            "اختصار مصرح به، لا مدخل جذري مستقل",
            True,
        )
    named_loan_route = common.loan_route(entry)
    if named_loan_route is not None:
        return named_loan_route
    if "calque" in str(entry["etymology"] or "").lower():
        return (
            "LOAN-ROUTE-ISOLATED",
            "ترجمة اقتراضية ذات مانح أجنبي مسمى في حقل التأثيل",
            True,
        )
    if entry["pos"] in {"prep", "pron"}:
        return (
            "FUNCTION-WORD",
            "أداة نحوية أو ضمير؛ يعزل عن حكم الجذر المعجمي في هذه الجولة",
            True,
        )
    if entry["pos"] == "phrase":
        return (
            "PHRASE-LINK",
            "عبارة متعددة الكلمات مصرح بها؛ لا تعامل جذرا مفردا",
            True,
        )
    if any(
        token in str(entry["etymology"] or "")
        for token in ("Unknown", "Uncertain", "possibly", "Likely")
    ):
        return (
            "SOURCE-GAP",
            "حقل التأثيل يحمل عدم يقين صريحا في أصل العضو أو مساره",
            False,
        )
    return (
        "OPEN-CANDIDATE",
        "فحص العضو ومرشحات جذره، ولم يجتمع بعد مقابل عربي مرخص "
        "ومروحة معنى من مصدرين عربيين قديمين",
        False,
    )


def remaining_family_count(covered: set[str]) -> int:
    connection = sqlite3.connect(DB)
    try:
        families: dict[str, list[str]] = defaultdict(list)
        for family_id, entry_id in connection.execute(
            """
            SELECT f.family_id,fm.entry_id
            FROM families AS f
            JOIN family_members AS fm USING(family_id)
            WHERE f.language='aramaic'
            """
        ):
            families[str(family_id)].append(str(entry_id))
        return sum(
            any(entry_id not in covered for entry_id in members)
            for members in families.values()
        )
    finally:
        connection.close()


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
        raise ValueError("لا أسرة آرامية باقية؛ لا تكتب دفعة فارغة")

    cards: list[str] = []
    coverage_updates: list[dict[str, str]] = []
    terminal_entry_ids: set[str] = set()
    positives = 0
    closures = 0
    pending = 0
    distribution: dict[str, int] = defaultdict(int)
    for rank, entry in enumerate(cohort, 1):
        state, reason, terminal = classify(entry)
        distribution[state] += 1
        if terminal:
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
                    "aramaic",
                    state,
                    reason,
                    f"aramaic-inventory-{args.batch_number:03d}",
                )
            )

    family_ids = list(dict.fromkeys(entry["family_id"] for entry in cohort))
    first_line = cohort[0]["family_first_source_line"]
    last_family_entries = [
        entry for entry in cohort if entry["family_id"] == family_ids[-1]
    ]
    last_line = last_family_entries[0]["family_first_source_line"]
    covered_after = covered_entry_ids(base)
    covered_after.update(entry["entry_id"] for entry in cohort)
    remaining = remaining_family_count(covered_after)
    queue_position = (
        f"بدأت الدفعة من الأسرة `{family_ids[0]}` عند سطر المصدر "
        f"{first_line}، وانتهت عند الأسرة `{family_ids[-1]}` ذات أول "
        f"سطر مصدر {last_line}؛ بقي في جرد الآرامية {remaining} أسرة."
    )

    block = "\n".join(
        [
            "",
            start,
            "",
            "## التغطية الآرامية العامة المرتبة، "
            f"الدفعة {args.batch_number} ({DATE})",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "أول الأسر غير المغطاة في جرد الآرامية مرتبة بأقدم سطر "
            "مصدر Kaikki داخل الأسرة. كتبت بطاقة RECOVERY-v2 "
            "للإغلاق النهائي فقط، وسجلت غير المحكوم سطرًا آليًا "
            "واحدًا؛ ولم يحول غياب الشاهدين العربيين القديمين إلى "
            "حكم سالب.",
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
            "# محضر المسار أ: التغطية الآرامية العامة المرتبة، "
            f"الدفعة {args.batch_number}",
            "",
            f"- التاريخ: {DATE}.",
            "- الحالة: محلي للمراجعة المضادة الثالثة، بلا إيداع.",
            "- الملكية: ملف الآرامية وحده.",
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
            "- `04-cross-linguistic/readings/aramaic.md`.",
            "- `04-cross-linguistic/data/lane_a_coverage.jsonl`.",
            "- `05-audits/"
            "lane-a-2026-07-30-aramaic-inventory-full-coverage-"
            f"batch-{args.batch_number:03d}.md`.",
            "- `scripts/lane_a_aramaic_inventory_full_coverage_batch.py`.",
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
                "remaining_aramaic_families": remaining,
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
