#!/usr/bin/env python3
"""Measure Egyptian and Coptic with one authoritative card standard.

This is a measurement and diagnostics pass only.  It does not issue or change
any linguistic verdict.  It reads the live fields of each card, counts each
card once, measures the same two-source evidence gate on positive verdicts,
and joins Coptic family IDs to the pinned inventory to quantify Greek-marked
loan families.
"""
from __future__ import annotations

import json
import re
import sqlite3
import tempfile
import os
from pathlib import Path

import apply_third_lens_round_two as review
import build_status_snapshot as status


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
CACHE = (
    ROOT
    / "cache"
    / "recovery_pipeline"
    / "egyptian-coptic-same-standard.json"
)
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-27-egyptian-coptic-same-standard.md"
)
# Exclude the legacy Coptic subrange U+03E2..U+03EF.
GREEK = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")
FAMILY_ID = re.compile(r"coptic:family:[0-9a-f]+")


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def measure_file(name: str) -> tuple[dict[str, object], list[str]]:
    path = status.READINGS / name
    cards = status.reading_cards(path.read_text(encoding="utf-8"))
    positives: list[str] = []
    closures: list[str] = []
    unresolved: list[str] = []
    outcomes: dict[str, int] = {}
    for card in cards:
        outcome = status.counted_outcome(card)
        if outcome:
            outcomes[outcome] = outcomes.get(outcome, 0) + 1
        if outcome in status.POSITIVE_VERDICTS:
            positives.append(card)
        elif outcome in status.CLOSURE_VERDICTS:
            closures.append(card)
        else:
            unresolved.append(card)

    source_pass = sum(
        len(review.named_sources(card)) >= 2 for card in positives
    )
    resolved = len(positives) + len(closures)
    return {
        "cards": len(cards),
        "positive_links": len(positives),
        "closures": len(closures),
        "resolved": resolved,
        "unresolved": len(unresolved),
        "yield": len(positives) / resolved if resolved else None,
        "positive_two_source_pass": source_pass,
        "positive_two_source_fail": len(positives) - source_pass,
        "positive_two_source_pass_rate": (
            source_pass / len(positives) if positives else None
        ),
        "outcomes": dict(sorted(outcomes.items())),
    }, cards


def coptic_greek_inventory(cards: list[str]) -> dict[str, object]:
    connection = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    try:
        rows = connection.execute(
            """
            SELECT e.entry_id, e.etymology
            FROM entries e
            WHERE e.language = 'coptic' AND e.etymology <> ''
            """
        ).fetchall()
        greek_entries = {
            entry_id
            for entry_id, etymology in rows
            if GREEK.search(etymology or "")
        }
        placeholders = ",".join("?" for _ in greek_entries)
        greek_families = {
            row[0]
            for row in connection.execute(
                f"""
                SELECT DISTINCT fm.family_id
                FROM family_members fm
                WHERE fm.entry_id IN ({placeholders})
                """,
                tuple(greek_entries),
            )
        }
        total_families = connection.execute(
            "SELECT COUNT(*) FROM families WHERE language = 'coptic'"
        ).fetchone()[0]
    finally:
        connection.close()

    mapped_cards = 0
    greek_mapped_cards = 0
    greek_mapped_resolved = 0
    greek_mapped_unresolved = 0
    for card in cards:
        ids = set(FAMILY_ID.findall(card))
        if ids:
            mapped_cards += 1
        if ids & greek_families:
            greek_mapped_cards += 1
            if status.counted_outcome(card):
                greek_mapped_resolved += 1
            else:
                greek_mapped_unresolved += 1

    named_greek_loan_closures = sum(
        status.counted_outcome(card) == "LOANWORD"
        and bool("اليونان" in card or GREEK.search(card))
        for card in cards
    )
    return {
        "inventory_families": total_families,
        "greek_marked_families": len(greek_families),
        "greek_marked_family_share": (
            len(greek_families) / total_families if total_families else None
        ),
        "reading_cards_with_family_id": mapped_cards,
        "reading_cards_greek_marked": greek_mapped_cards,
        "reading_cards_greek_marked_share": (
            greek_mapped_cards / mapped_cards if mapped_cards else None
        ),
        "greek_marked_resolved": greek_mapped_resolved,
        "greek_marked_unresolved": greek_mapped_unresolved,
        "named_greek_loan_closures": named_greek_loan_closures,
    }


def pct(value: float | None) -> str:
    return "غير متاح" if value is None else f"{value * 100:.1f}%"


def build_report(payload: dict[str, object]) -> str:
    egyptian = payload["egyptian"]
    coptic = payload["coptic"]
    greek = payload["coptic_greek_inventory"]
    coptic_without_greek = payload["counterfactual_coptic_without_named_greek_loans"]
    evidence_gap = (
        float(egyptian["positive_two_source_pass_rate"])
        - float(coptic["positive_two_source_pass_rate"])
    )
    corrected_gap = float(coptic["yield"]) - float(egyptian["yield"])
    corrected_gap_direction = "أعلى" if corrected_gap >= 0 else "أدنى"
    lines = [
        "# إعادة فحص المصرية والقبطية بمعيار واحد، 2026-07-27",
        "",
        "## النتيجة الحاكمة",
        "",
        "الفرق المنشور في محضر 2026-07-25، 70.4% للمصرية و11.5% "
        "للقبطية، لا يصمد بعد إصلاح طريقة العد. كان العد القديم يلتقط "
        "أحكامًا تاريخية محفوظة، ولا يلتقط إغلاقات جديدة حملها سطر العائق "
        "الحي مع بقاء الحكم غير صادر. قُرئت هنا كل بطاقة مرة واحدة من "
        "حقليها الحاكمين.",
        "",
        "| اللسان | صلات حية | إغلاقات حية | محسوم | العائد |",
        "|---|---:|---:|---:|---:|",
        (
            f"| المصرية القديمة | {egyptian['positive_links']} | "
            f"{egyptian['closures']} | {egyptian['resolved']} | "
            f"{pct(egyptian['yield'])} |"
        ),
        (
            f"| القبطية | {coptic['positive_links']} | "
            f"{coptic['closures']} | {coptic['resolved']} | "
            f"{pct(coptic['yield'])} |"
        ),
        "",
        f"بالعد الموحد تصير القبطية {corrected_gap_direction} من المصرية "
        f"بمقدار {abs(corrected_gap) * 100:.1f} نقطة مئوية، فلا يبقى فرق الستة "
        "أضعاف أصلًا كي يفسر.",
        "",
        "## أثر الاقتراض اليوناني",
        "",
        (
            f"- في الجرد الكامل: {greek['greek_marked_families']} من "
            f"{greek['inventory_families']} أسرة قبطية تحمل أصلًا يونانيًا "
            f"مسمى، أي {pct(greek['greek_marked_family_share'])}."
        ),
        (
            f"- في بطاقات القراءة ذات معرف الأسرة: "
            f"{greek['reading_cards_greek_marked']} من "
            f"{greek['reading_cards_with_family_id']}، أي "
            f"{pct(greek['reading_cards_greek_marked_share'])}."
        ),
        (
            f"- من هذه البطاقات اليونانية: "
            f"{greek['greek_marked_resolved']} محسومة و"
            f"{greek['greek_marked_unresolved']} معلقة."
        ),
        (
            f"- يوجد {greek['named_greek_loan_closures']} إغلاق قرض "
            f"يوناني مسمى: {greek['greek_marked_resolved']} منها في بطاقات "
            "مرتبطة بمعرف الأسرة، والباقي في بطاقة قديمة غير مربوطة به."
        ),
        (
            f"- لو أزيل هذا الإغلاق اليوناني المسمى من المقام فقط، يصير "
            f"عائد القبطية {pct(coptic_without_greek)} بدل "
            f"{pct(coptic['yield'])}: أثر مقداره "
            f"{(float(coptic_without_greek) - float(coptic['yield'])) * 100:.1f} "
            "نقطة مئوية."
        ),
        "",
        "فالاقتراض اليوناني غزير فعلًا، ويخفض العائد الجاري بعد عزل قروضه "
        "المسماة. لكنه لا يفسر رقم المحضر السابق تفسيرًا صالحًا، لأن طريقة "
        "ذلك العد نفسها اختلطت عليها الأحكام التاريخية والحقول الحية، "
        "ولأن جمهور البطاقات اليونانية ما زال معلقًا.",
        "",
        "## تفاوت الصرامة والتغطية",
        "",
        (
            f"- اجتازت بوابة المصدرين {egyptian['positive_two_source_pass']} "
            f"من {egyptian['positive_links']} صلة مصرية حية "
            f"({pct(egyptian['positive_two_source_pass_rate'])})."
        ),
        (
            f"- اجتازتها {coptic['positive_two_source_pass']} من "
            f"{coptic['positive_links']} صلة قبطية حية "
            f"({pct(coptic['positive_two_source_pass_rate'])})."
        ),
        (
            f"- فرق بوابة الدليل بينهما {abs(evidence_gap) * 100:.1f} "
            "نقطة مئوية فقط؛ لا يفسر فرقًا بستة أضعاف."
        ),
        "",
        "التفاوت الكبير الحقيقي هو تفاوت مرحلة التغطية: الحملة المصرية "
        "حسمت أعلامًا وأدوات ونقولًا داخل البيت بصورة منظمة، بينما بطاقات "
        "القروض اليونانية القبطية ما زالت في معظمها معلقة. لذلك لا يجوز "
        "تحويل الباقي إلى مقدار اسمه «صرامة»؛ إنه خليط من ترتيب الطابور "
        "واكتمال المصفاة وبقايا بطاقات قديمة.",
        "",
        "## القرار المنهجي",
        "",
        "- يُسحب منحنى 70.4% مقابل 11.5% من الاستعمال حتى لا يبنى عليه.",
        "- يبقى غنى القروض اليونانية حقيقة جرد مستقلة، لا تفسيرًا آليًا للعائد.",
        "- تمر الصلات القديمة التي لم تستوف مصدرين على المروحة نفسها في "
        "الحملات التالية.",
        "- لا يدخل أي رقم هنا خط البرهان أو النشر.",
        "",
    ]
    return "\n".join(lines)


def main() -> int:
    egyptian, _ = measure_file("egyptian.md")
    coptic, coptic_cards = measure_file("coptic.md")
    greek = coptic_greek_inventory(coptic_cards)
    greek_closures = int(greek["named_greek_loan_closures"])
    adjusted_denominator = (
        int(coptic["positive_links"])
        + int(coptic["closures"])
        - greek_closures
    )
    adjusted = (
        int(coptic["positive_links"]) / adjusted_denominator
        if adjusted_denominator
        else None
    )
    payload = {
        "schema": "egyptian-coptic-same-standard-v1",
        "date": "2026-07-27",
        "status": "INTERNAL-NO-PROOF",
        "egyptian": egyptian,
        "coptic": coptic,
        "coptic_greek_inventory": greek,
        "counterfactual_coptic_without_named_greek_loans": adjusted,
    }
    atomic_write(CACHE, json.dumps(payload, ensure_ascii=False, indent=2) + "\n")
    atomic_write(AUDIT, build_report(payload))
    print(
        json.dumps(
            {
                "egyptian_yield": egyptian["yield"],
                "coptic_yield": coptic["yield"],
                "coptic_greek_family_share": greek["greek_marked_family_share"],
                "coptic_greek_resolved": greek["greek_marked_resolved"],
                "coptic_greek_unresolved": greek["greek_marked_unresolved"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
