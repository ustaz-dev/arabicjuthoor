# -*- coding: utf-8 -*-
"""الجولة الثامنة عشرة للمسار B: دفعتا إتمام للمفتوح الفارسي القصير."""

from __future__ import annotations

import argparse
import re
import unicodedata
from collections import Counter
from datetime import datetime

import harvest_persian_round17 as PREVIOUS


BASE = PREVIOUS.BASE
FIRST_COMPLETION = 1271
LAST_COMPLETION = 1340
BATCH_SIZE = 35
MARKER = "LANE-B-PERSIAN-ROUND18-2026-08-17"
FIRST_WORD = "پاول"
LAST_WORD = "ورسای"
FIRST_SOURCE_INDEX = 12155
LAST_SOURCE_INDEX = 16698
EXPECTED_AVAILABLE = 271
EXPECTED_FAMILY_REFS = 0
EXPECTED_DIRECT_REFS = 70
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "SEMITIC-SOURCE-TRANSMISSION",
}


def available_cards(
    reading_text: str,
) -> tuple[list[BASE.SourceCard], list[BASE.SourceCard]]:
    """يأخذ النافذة التالية من ذيل الحوض الحي بعد الجولة السابعة عشرة."""
    all_available, _ = PREVIOUS.available_cards(reading_text)
    needed = LAST_COMPLETION - FIRST_COMPLETION + 1
    return all_available, all_available[-needed:]


def validate_selection(
    all_available: list[BASE.SourceCard],
    cards: list[BASE.SourceCard],
) -> None:
    expected_count = LAST_COMPLETION - FIRST_COMPLETION + 1
    if len(all_available) != EXPECTED_AVAILABLE:
        raise AssertionError(
            f"تغير عدد الحوض القصير الحي في مطلع الجولة الثامنة عشرة: {len(all_available)}"
        )
    if len(cards) != expected_count:
        raise AssertionError(
            f"عُثر على {len(cards)} بطاقة في نافذة الجولة الثامنة عشرة؛ يلزم 70"
        )
    if cards[0].word != FIRST_WORD or cards[-1].word != LAST_WORD:
        raise AssertionError("تغير طرفا نافذة الجولة الثامنة عشرة")
    if (
        cards[0].source_index != FIRST_SOURCE_INDEX
        or cards[-1].source_index != LAST_SOURCE_INDEX
    ):
        raise AssertionError("تغير طرفا ترتيب المصدر في الجولة الثامنة عشرة")
    member_ids = [card.member_id for card in cards]
    if len(member_ids) != len(set(member_ids)):
        raise AssertionError("تكرر عضو في نافذة الجولة الثامنة عشرة")
    if any(not 2 <= len(card.skeleton) <= 4 for card in cards):
        raise AssertionError("دخل هيكل خارج حد القصير")
    family_count = sum(
        card.family_id.startswith("persian:family:") for card in cards
    )
    direct_count = len(cards) - family_count
    if family_count != EXPECTED_FAMILY_REFS or direct_count != EXPECTED_DIRECT_REFS:
        raise AssertionError(
            "تغير توزيع صيغتي مرجع الجرد: "
            f"family={family_count} direct={direct_count}"
        )


def validate_new_text(
    cards: list[BASE.SourceCard],
    texts: list[str],
    decisions: list[BASE.Decision],
) -> None:
    expected_count = LAST_COMPLETION - FIRST_COMPLETION + 1
    if len(cards) != expected_count or len(texts) != expected_count:
        raise AssertionError("لم تكتمل نافذة الجولة الثامنة عشرة إلى 70 بطاقة")
    if len(decisions) != expected_count:
        raise AssertionError("عدد أحكام الجولة الثامنة عشرة غير مكتمل")
    headings = [
        int(value)
        for text in texts
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d{5}):",
            text,
            re.MULTILINE,
        )
    ]
    if headings != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("معرفات الجولة الثامنة عشرة غير متصلة")
    joined = "\n".join(texts)
    if "\N{EM DASH}" in joined or re.search(r"[\u06f0-\u06f9\u0660-\u0669]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) >= BASE.CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if not re.search(
            r"^- الحكم \(استكشاف\): [A-Z-]+\.$",
            text,
            re.MULTILINE,
        ):
            raise AssertionError(f"لا حكم نهائيا في البطاقة {number:05d}")
    if any(item.verdict in POSITIVE_VERDICTS for item in decisions):
        raise AssertionError("دخل حكم موجب غير مثبت في الجولة الثامنة عشرة")


def reference_distribution(cards: list[BASE.SourceCard]) -> str:
    family = sum(card.family_id.startswith("persian:family:") for card in cards)
    return f"مرجع أسرة={family}؛ مرجع عضو مباشر={len(cards) - family}"


def report_section(
    cards: list[BASE.SourceCard],
    decisions: list[BASE.Decision],
    sizes: list[int],
    remaining_count: int,
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    sections = [f"<!-- {MARKER}:START -->", ""]
    for batch in range(2):
        lo = batch * BATCH_SIZE
        hi = lo + BATCH_SIZE
        batch_cards = cards[lo:hi]
        batch_decisions = decisions[lo:hi]
        counts = Counter(item.verdict for item in batch_decisions)
        distribution = "؛ ".join(
            f"{key}={counts[key]}" for key in sorted(counts)
        )
        first = FIRST_COMPLETION + lo
        last = FIRST_COMPLETION + hi - 1
        positives = [
            f"`{card.word}↔{decision.candidate}`"
            for card, decision in zip(batch_cards, batch_decisions)
            if decision.verdict in POSITIVE_VERDICTS
        ]
        sections.extend(
            [
                f"## الجولة الثامنة عشرة، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 35؛ كُتب: 35؛ مدى الهيكل: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- صيغ مرجع الجرد: {reference_distribution(batch_cards)}.",
                f"- توزيع الأحكام: {distribution}.",
                "- الصلات الإيجابية: "
                + ("، ".join(positives) if positives else "0")
                + ".",
                "- أعطاب الأدوات الأساسية: 0؛ عملت `fan_any_script.fan` بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 35 معرفا فريدا؛ 35 عضوا غير مكرر ولا سابق الإتمام؛ لا هيكل فوق 4؛ كل حكم مغلق المفردات.",
                "- لم تُفعّل توسعة الهيكل؛ استمر جرد العناوين ذات مرجع العضو المباشر.",
                f"- آخر موضع: `WO-B-OPEN-COMP-{last:05d}`، `{batch_cards[-1].word}` /{batch_cards[-1].reading}/.",
                "",
            ]
        )

    total = Counter(item.verdict for item in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    positives = sum(total[key] for key in POSITIVE_VERDICTS)
    max_size = max(sizes)
    max_number = FIRST_COMPLETION + sizes.index(max_size)
    sections.extend(
        [
            "## حصيلة الجولة الثامنة عشرة",
            "",
            f"- مجموع الإتمام الجديد: 70؛ {distribution}.",
            f"- الصلات الإيجابية المحسوبة: {positives}.",
            f"- بقي بعد الدفعتين {remaining_count} عضوا قصيرا حيا ذا مروحة غير فارغة في صيغة العنوان المباشر؛ لم تُفعّل توسعة هيكل.",
            "- التحقق الكلي: 70 معرفا متصلا من `01271` إلى `01340`؛ 70 عضوا فريدا؛ لا تكرار مع بطاقات الإتمام السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- كاشف الانضباط التشخيصي: بقي الحكم مقصورا على العضو المباشر؛ لم تُنشأ أسرة مصطنعة ولم تتحول مشابهة عامة إلى صلة موجبة.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-01340`.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            "LANE-B DONE18 70 WO-B-OPEN-COMP-01340",
        ]
    )
    return "\n".join(sections)


def validate_existing(reading_text: str, report_text: str) -> None:
    reading_match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)"
        rf"<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not reading_match:
        raise AssertionError("محضر الجولة الثامنة عشرة موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d+):",
            reading_match.group(1),
            re.MULTILINE,
        )
    ]
    if ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("مقطع الجولة الثامنة عشرة الموجود غير متصل")
    for block in re.split(
        r"(?=^### WO-B-OPEN-COMP-)",
        reading_match.group(1),
        flags=re.MULTILINE,
    ):
        if (
            block.startswith("### WO-B-OPEN-COMP-")
            and len(block.encode("utf-8")) >= BASE.CARD_LIMIT
        ):
            raise AssertionError("بطاقة موجودة تتجاوز 5KB")
    expected = "LANE-B DONE18 70 WO-B-OPEN-COMP-01340"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE18 ليس خاتمة التقرير")


def build_round(
    reading_text: str,
) -> tuple[
    list[BASE.SourceCard],
    list[BASE.Decision],
    list[str],
    list[int],
    int,
]:
    all_available, cards = available_cards(reading_text)
    validate_selection(all_available, cards)
    roots = {
        candidate
        for card in cards
        for candidate, _ in card.ranked_fan
    }
    sense_map = BASE.SENSES.matches_for_roots(
        BASE.SENSES.DEFAULT_RESOURCES,
        roots,
        None,
    )
    decisions = [
        PREVIOUS.PREVIOUS.select_decision(card, sense_map) for card in cards
    ]
    texts = [
        PREVIOUS.fit_card(number, card, decision, sense_map)
        for number, card, decision in zip(
            range(FIRST_COMPLETION, LAST_COMPLETION + 1),
            cards,
            decisions,
        )
    ]
    validate_new_text(cards, texts, decisions)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]
    return cards, decisions, texts, sizes, len(all_available) - len(cards)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--preview",
        action="store_true",
        help="يبني الجولة ويتحقق منها بلا كتابة",
    )
    args = parser.parse_args()

    reading_text = BASE.READING.read_text(encoding="utf-8")
    report_text = BASE.REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        if MARKER not in reading_text or MARKER not in report_text:
            raise AssertionError("الجولة الثامنة عشرة مكتوبة جزئيا")
        validate_existing(reading_text, report_text)
        print("ROUND18 ALREADY PRESENT AND VALID")
        return 0

    cards, decisions, texts, sizes, remaining_count = build_round(reading_text)
    counts = Counter(decision.verdict for decision in decisions)
    if args.preview:
        print("ROUND18 PREVIEW VALID")
        print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
        print("SOURCE", cards[0].source_index, cards[-1].source_index)
        family_count = sum(
            card.family_id.startswith("persian:family:") for card in cards
        )
        print("REFS", f"family={family_count}", f"direct={len(cards) - family_count}")
        print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
        print(
            "MAX_CARD",
            max(sizes),
            f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}",
        )
        print("REMAINING", remaining_count)
        return 0

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثامنة عشرة: مواصلة المفتوح الفارسي القصير (2026-08-17)\n\n"
        "- بيان النطاق: بعد قبول الجولة السابعة عشرة وتسويتها استمر جرد بطاقات العضو المباشر من ذيل المصدر القصير الحي؛ أُخذت 70 بطاقة مرتبة بموضع المصدر، من `پاول` إلى `ورسای`، في دفعتين 35 و35، بلا توسعة هيكل.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية، الإتمامات 01306 إلى 01340\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = (
        "\n\n"
        + report_section(cards, decisions, sizes, remaining_count)
        + "\n"
    )
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "\N{EM DASH}" in reading_append + report_append:
        raise AssertionError("شرطة طويلة في النص الجديد")

    with BASE.READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with BASE.REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)

    validate_existing(
        BASE.READING.read_text(encoding="utf-8"),
        BASE.REPORT.read_text(encoding="utf-8"),
    )
    print("ROUND18 WRITTEN")
    print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print(
        "MAX_CARD",
        max(sizes),
        f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}",
    )
    print("LANE-B DONE18 70 WO-B-OPEN-COMP-01340")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
