# -*- coding: utf-8 -*-
"""الجولة الحادية عشرة للمسار B: استنفاد حوض المركبات الفارسية المفتوحة."""

from __future__ import annotations

import re
import sys
import unicodedata

import harvest_persian_round9_compounds as R


R.MARKER = "LANE-B-PERSIAN-ROUND11-COMPOUNDS-2026-08-17"
R.FIRST_ID = 763
R.COMPOUND_COUNT = 78
R.BATCH_SIZES = (39, 39)
R.DECOMPOSITIONS = {
    source_index: R.DECOMPOSITION_CATALOG[source_index]
    for source_index in (16108, 16111, 16126, 16128, 16170, 16175)
}

# قُرئ هذا المكون في آخر بطاقة من الجولة العاشرة؛ فلا تعاد قراءته.
R.PRIOR_COMPONENTS["ـکوک"] = R.ComponentRef(762, "SOURCE-GAP")

FIRST_WORD = "استافیلوکوک"
LAST_WORD = "دموگرافی"


def parse_compounds(text: str) -> list[R.Compound]:
    """ينتقي كل ما بقي من حوض الهيكل الطويل بعد الإتمامات السابقة."""
    completed_members = set(re.findall(r"العضو الفردي `([^`]+)`", text))
    compounds: list[R.Compound] = []
    for block in re.split(r"(?=^### )", text, flags=re.MULTILINE):
        if not block.startswith("### بطاقة: `persian:family:"):
            continue
        if "الحكم (استكشاف): غير صادر" not in block:
            continue
        member = re.search(
            r"- الكلمةُ في الفرع: (.*?) \((.*?)\) \[([^؛]+)؛ "
            r"`(kaikki_persian_[^`]+)`\]\.",
            block,
        )
        family = re.search(r"`(persian:family:[0-9a-f]+)`", block)
        etymology = re.search(r"- أقدمُ صورةٍ مستعادة: (.*?) \[Kaikki Persian", block)
        gloss = re.search(r"- المعنى من قاموس الفرع: «(.*?)» \[Kaikki Persian", block)
        if not (member and family and etymology and gloss):
            continue
        word, reading, pos, member_id = member.groups()
        source_index = int(member_id.split(":", 2)[1])
        skeleton = tuple(R.FAN.skeleton(word, "persian"))
        if (
            source_index < R.FIRST_SOURCE
            or member_id in completed_members
            or len(skeleton) <= 4
        ):
            continue
        compounds.append(
            R.Compound(
                source_index=source_index,
                word=R.clean(word),
                reading=R.clean(reading),
                pos=R.clean(pos),
                member_id=R.clean(member_id),
                family_id=family.group(1),
                etymology=R.clean(etymology.group(1)),
                gloss=R.clean(gloss.group(1)),
                previous_id=None,
                previous_verdict=None,
            )
        )
    compounds.sort(key=lambda item: item.source_index)
    if len(compounds) != R.COMPOUND_COUNT:
        raise AssertionError(
            f"تغير باقي حوض المركبات: {len(compounds)} لا {R.COMPOUND_COUNT}"
        )
    if compounds[0].word != FIRST_WORD or compounds[-1].word != LAST_WORD:
        raise AssertionError("تغير طرفا نافذة الجولة الحادية عشرة")
    if len({item.member_id for item in compounds}) != len(compounds):
        raise AssertionError("تكرر عضو في نافذة المركبات")
    if set(R.DECOMPOSITIONS) - {item.source_index for item in compounds}:
        raise AssertionError("تفكيك نصي خارج نافذة الجولة الحادية عشرة")
    return compounds


def batch_sections(
    rendered: list[R.RenderedCompound],
) -> tuple[str, list[dict[str, object]]]:
    text, summaries = R.batch_sections(rendered)
    return text.replace("الجولة التاسعة", "الجولة الحادية عشرة"), summaries


def report_section(
    rendered: list[R.RenderedCompound], summaries: list[dict[str, object]]
) -> str:
    text = R.report_section(rendered, summaries)
    return text.replace("الجولة التاسعة", "الجولة الحادية عشرة").replace(
        "DONE9", "DONE11"
    )


def validate_existing(reading_text: str, report_text: str) -> None:
    reading_match = re.search(
        rf"<!-- {re.escape(R.MARKER)}:START -->(.*?)"
        rf"<!-- {re.escape(R.MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not reading_match:
        raise AssertionError("محضر الجولة الحادية عشرة موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d+):", reading_match.group(1), re.MULTILINE
        )
    ]
    if not ids or ids != list(range(R.FIRST_ID, ids[-1] + 1)):
        raise AssertionError("مقطع الجولة الحادية عشرة الموجود غير متصل")
    for block in re.split(
        r"(?=^### WO-B-OPEN-COMP-)", reading_match.group(1), flags=re.MULTILINE
    ):
        if (
            block.startswith("### WO-B-OPEN-COMP-")
            and len(block.encode("utf-8")) >= R.CARD_LIMIT
        ):
            raise AssertionError("بطاقة موجودة تتجاوز 5KB")
    expected = f"LANE-B DONE11 {R.COMPOUND_COUNT} WO-B-OPEN-COMP-{ids[-1]:05d}"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE11 ليس خاتمة التقرير")


def main() -> int:
    reading_text = R.READING.read_text(encoding="utf-8")
    report_text = R.REPORT.read_text(encoding="utf-8")
    if R.MARKER in reading_text or R.MARKER in report_text:
        if R.MARKER not in reading_text or R.MARKER not in report_text:
            raise AssertionError("الجولة الحادية عشرة مكتوبة جزئيا")
        validate_existing(reading_text, report_text)
        print("ROUND11 COMPOUNDS ALREADY PRESENT AND VALID")
        return 0

    compounds = parse_compounds(reading_text)
    rendered = R.render_all(compounds)
    R.validate_rendered(rendered)
    reading_cards, summaries = batch_sections(rendered)
    reading_append = (
        f"\n\n<!-- {R.MARKER}:START -->\n\n"
        "## الجولة الحادية عشرة: تفكيك المركبات الفارسية (2026-08-17)\n\n"
        "- النطاق: كل ما بقي من حوض الهيكل الطويل المؤجل، 78 عضوا من "
        "`استافیلوکوک` إلى `دموگرافی`؛ دفعتان 39 و39. نقل المكونان من "
        "سطر قاموس الفرع وحده، وما لم يسمهما السطر بقي COMPOUND-BOUNDARY. "
        "بهاتين الدفعتين نفد الحوض الطويل المؤجل.\n\n"
        + reading_cards
        + f"\n<!-- {R.MARKER}:END -->\n"
    )
    report_append = "\n\n" + report_section(rendered, summaries) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)

    with R.READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with R.REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)

    new_reading = R.READING.read_text(encoding="utf-8")
    new_report = R.REPORT.read_text(encoding="utf-8")
    validate_existing(new_reading, new_report)
    all_cards = [
        (card_id, text)
        for item in rendered
        for card_id, text in zip(item.card_ids, item.texts)
    ]
    print("ROUND11 COMPOUNDS WRITTEN")
    print("COMPOUNDS", len(rendered), f"BATCHES={R.BATCH_SIZES[0]}+{R.BATCH_SIZES[1]}")
    print("DECOMPOSED", sum(item.decomposed for item in rendered))
    print("BOUNDARY", sum(not item.decomposed for item in rendered))
    print(
        "PHYSICAL_CARDS",
        len(all_cards),
        f"RANGE={R.FIRST_ID:05d}-{all_cards[-1][0]:05d}",
    )
    print("SPLITS", sum(len(item.card_ids) == 2 for item in rendered))
    print("MAX_CARD", max(len(text.encode("utf-8")) for _, text in all_cards))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
