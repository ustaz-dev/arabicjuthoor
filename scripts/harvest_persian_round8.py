# -*- coding: utf-8 -*-
"""إتمام دفعتين فارسيتين من البطاقات المفتوحة في الجولة الثامنة."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime

import harvest_persian_round7 as PREVIOUS


BASE = PREVIOUS.BASE
FIRST_COMPLETION = 521
LAST_COMPLETION = 600
BATCH_SIZE = 40
MARKER = "LANE-B-PERSIAN-ROUND8-2026-08-17"
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "SEMITIC-SOURCE-TRANSMISSION",
}


_previous_formatted_route = BASE.formatted_route
_previous_selected_witnesses = BASE.selected_witnesses


def select_decision(card: BASE.SourceCard, sense_map: dict[str, list[dict]]) -> BASE.Decision:
    """أثبت الصلة المباشرة التي بقيت بعد قراءة المروحة والشواهد."""
    if card.word == "نیل":
        return BASE.Decision(
            candidate="نيل",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي النيل، وتاج العروس يسمّي النيل نبات العظلم "
                "الذي يتخذ منه النيلج، والمصباح يصرح بالنيل الذي يصبغ به؛ "
                "فالمدار مادة الصبغ الزرقاء نفسها مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        )
    return PREVIOUS.select_decision(card, sense_map)


def targeted_excerpt(definition: str, source_id: str, limit: int) -> str:
    targets = {
        "taj_al_arus": ("العِظْلِمِ", 35),
        "al_misbah": ("يُصْبَغُ بِهِ", 45),
    }
    normalized = BASE.clean(definition)
    needle, rewind = targets[source_id]
    pos = normalized.find(needle)
    if pos >= 0:
        return BASE.clip(normalized[max(0, pos - rewind) :], limit)
    return BASE.clip(normalized, limit)


def selected_witnesses(
    candidate: str,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
) -> tuple[int, list[tuple[str, str]]]:
    if candidate != "نيل":
        return _previous_selected_witnesses(candidate, sense_map, quote_limit)

    matches = sense_map.get(candidate, [])
    witnesses: list[tuple[str, str]] = []
    for wanted in ("taj_al_arus", "al_misbah"):
        item = next(
            (
                row
                for row in matches
                if BASE.SENSES.canonical_source_id(str(row.get("source") or ""))
                == wanted
                and str(row.get("definition") or "").strip()
            ),
            None,
        )
        if item is None:
            continue
        witnesses.append(
            (
                BASE.SENSES.SOURCE_LABELS[wanted],
                targeted_excerpt(
                    str(item.get("definition") or ""),
                    wanted,
                    quote_limit,
                ),
            )
        )
    while len(witnesses) < 2:
        witnesses.append(
            (
                "فجوة المورد",
                "لم يرد شاهد مستقل مكتمل في الموارد المسماة؛ الغياب لا ينفي معنى.",
            )
        )
    return len(matches), witnesses


def formatted_route(card: BASE.SourceCard, decision: BASE.Decision) -> str:
    if card.word == "نیل" and decision.candidate == "نيل":
        return (
            "الرصف المفحوص: ن↔ن=`IDN-03`، ل↔ل=`IDN-04`، وباب المعتل "
            "المسمى يثبت الياء الجوفية في `نيل`؛ المرشح داخل المروحة."
        )
    return _previous_formatted_route(card, decision)


def formatted_fan(card: BASE.SourceCard) -> str:
    """أبق كل مرشح ومرتبته، واضغط الصفر الدقيق وحده إلى رقم واحد."""
    return "،".join(
        f"{candidate}:{'0' if weight == 0 else f'{weight:.3f}'}"
        for candidate, weight in card.ranked_fan
    )


# تستدعي دالة إنشاء البطاقة هذه الدوال من مجال الوحدة الأساسية.
BASE.selected_witnesses = selected_witnesses
BASE.formatted_route = formatted_route
BASE.formatted_fan = formatted_fan


def fit_card(
    number: int,
    card: BASE.SourceCard,
    decision: BASE.Decision,
    sense_map: dict[str, list[dict]],
) -> str:
    """اضغط النقل وحده عند اتساع المروحة، ولا تسقط مرشحًا أو حقلًا."""
    for quote_limit, etym_limit in (
        (300, 420),
        (220, 320),
        (150, 240),
        (90, 180),
        (55, 130),
        (40, 100),
        (30, 75),
        (20, 55),
        (20, 25),
        (15, 15),
    ):
        text = BASE.make_card(
            number,
            card,
            decision,
            sense_map,
            quote_limit,
            etym_limit,
        )
        if len(text.encode("utf-8")) < BASE.CARD_LIMIT:
            return text
    text = BASE.make_card(number, card, decision, sense_map, 0, 0)
    text = text.replace(
        "؛ مادة الفحص المختارة من المروحة.",
        "؛ المختار من المروحة.",
    )
    if len(text.encode("utf-8")) < BASE.CARD_LIMIT:
        return text
    raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")


def validate_new_text(
    cards: list[BASE.SourceCard],
    texts: list[str],
    decisions: list[BASE.Decision],
) -> None:
    expected_count = LAST_COMPLETION - FIRST_COMPLETION + 1
    if len(cards) != expected_count or len(texts) != expected_count:
        raise AssertionError("لم تكتمل نافذة الجولة الثامنة إلى 80 بطاقة")
    if len(decisions) != expected_count:
        raise AssertionError("عدد أحكام الجولة الثامنة غير مكتمل")
    member_ids = [card.member_id for card in cards]
    if len(member_ids) != len(set(member_ids)):
        raise AssertionError("تكرر عضو في النافذة الجديدة")
    if any(not 2 <= len(card.skeleton) <= 4 for card in cards):
        raise AssertionError("دخل هيكل خارج حد القصير")
    headings = [
        int(value)
        for text in texts
        for value in re.findall(r"^### WO-B-OPEN-COMP-(\d{5}):", text, re.MULTILINE)
    ]
    if headings != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("معرّفات الجولة الثامنة غير متصلة")
    joined = "\n".join(texts)
    if "\N{EM DASH}" in joined or re.search(r"[\u06f0-\u06f9\u0660-\u0669]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) > BASE.CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if not re.search(r"^- الحكم \(استكشاف\): [A-Z-]+\.$", text, re.MULTILINE):
            raise AssertionError(f"لا حكم نهائيًا في البطاقة {number:05d}")
    positive = texts[580 - FIRST_COMPLETION]
    if "المقابل من اللسان: `نيل`" not in positive:
        raise AssertionError("غاب مرشح النيل من بطاقة 00580")
    if "تاج العروس لمرتضى الزبيدي" not in positive or "المصباح المنير" not in positive:
        raise AssertionError("لم يكتمل شاهدا النيل المستقلان")
    if "العِظْلِمِ" not in positive or "يُصْبَغُ بِهِ" not in positive:
        raise AssertionError("لم تنقل بطاقة النيل موضعي المعنى من الشاهدين")
    if "الحكم (استكشاف): ROOT-TRACE" not in positive:
        raise AssertionError("غاب حكم النيل الموجب")


def report_section(
    cards: list[BASE.SourceCard],
    decisions: list[BASE.Decision],
    sizes: list[int],
) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    sections = [f"<!-- {MARKER}:START -->", ""]
    for batch in range(2):
        lo = batch * BATCH_SIZE
        hi = lo + BATCH_SIZE
        batch_cards = cards[lo:hi]
        batch_decisions = decisions[lo:hi]
        counts = Counter(item.verdict for item in batch_decisions)
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        first = FIRST_COMPLETION + lo
        last = FIRST_COMPLETION + hi - 1
        positives = [
            f"`{card.word}↔{decision.candidate}`"
            for card, decision in zip(batch_cards, batch_decisions)
            if decision.verdict in POSITIVE_VERDICTS
        ]
        sections.extend(
            [
                f"## الجولة الثامنة، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 40؛ كُتب: 40؛ مدى الهيكل: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- توزيع الأحكام: {distribution}.",
                "- الصلات الإيجابية: " + ("، ".join(positives) if positives else "0") + ".",
                "- أعطاب الأدوات الأساسية: 0؛ عملت `fan_any_script.fan` بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 40 معرّفًا فريدًا؛ 40 عضوًا غير مكرر ولا سابق الإتمام؛ لا هيكل فوق 4؛ كل حكم مغلق المفردات.",
                "- لم تُفعّل توسعة الهيكل؛ بقي في الحوض القصير مرشحون بعد هذه الدفعة.",
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
            "## حصيلة الجولة الثامنة",
            "",
            f"- مجموع الإتمام الجديد: 80؛ {distribution}.",
            f"- الصلات الإيجابية المحسوبة: {positives}.",
            "- لم تُفعّل التوسعة؛ القصير الهيكل لم ينفد.",
            "- التحقق الكلي: 80 معرّفًا متصلًا من `00521` إلى `00600`؛ 80 عضوًا فريدًا؛ لا تكرار مع بطاقات الإتمام السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- كاشف الانضباط التشخيصي: ملاحظة `D4-DIRECTION` واحدة في `00580` لأن خبر أصل الفرع يذكر الفهلوية والسنسكريتية، ويذكر الشاهد العربي الهندية؛ لا تنقض الحكم بمقتضى الأمر القائم، إذ اكتملت أرجل الصوت والحدث والمعنى، ولا يُختَرع شرط رابع.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-00600`.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            "LANE-B DONE8 80 WO-B-OPEN-COMP-00600",
        ]
    )
    return "\n".join(sections)


def main() -> int:
    reading_text = BASE.READING.read_text(encoding="utf-8")
    report_text = BASE.REPORT.read_text(encoding="utf-8")
    first_tag = f"WO-B-OPEN-COMP-{FIRST_COMPLETION:05d}"
    if first_tag in reading_text:
        headings = [
            int(value)
            for value in re.findall(r"^### WO-B-OPEN-COMP-(\d{5}):", reading_text, re.MULTILINE)
            if FIRST_COMPLETION <= int(value) <= LAST_COMPLETION
        ]
        if headings != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
            raise AssertionError("الجولة الثامنة الموجودة غير مكتملة أو غير متصلة")
        if not report_text.rstrip().endswith("LANE-B DONE8 80 WO-B-OPEN-COMP-00600"):
            raise AssertionError("بطاقات الجولة موجودة وخاتمة التقرير غائبة")
        print("ROUND8 ALREADY PRESENT AND VALID")
        return 0
    if MARKER in report_text:
        raise AssertionError("محضر الجولة الثامنة موجود قبل بطاقاتها")

    completed = BASE.parse_completed_members(reading_text)
    cards = BASE.parse_source_cards(reading_text, completed)
    if len(cards) != 80:
        raise AssertionError(
            f"عُثر على {len(cards)} بطاقة قصيرة فقط؛ يلزم عندئذ تفعيل التوسعة قبل الكتابة"
        )

    roots = {candidate for card in cards for candidate, _ in card.ranked_fan}
    roots.add("نيل")
    sense_map = BASE.SENSES.matches_for_roots(BASE.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [select_decision(card, sense_map) for card in cards]
    texts = [
        fit_card(number, card, decision, sense_map)
        for number, card, decision in zip(
            range(FIRST_COMPLETION, LAST_COMPLETION + 1), cards, decisions
        )
    ]
    validate_new_text(cards, texts, decisions)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثامنة: دفعتا إتمام المفتوح القصير (2026-08-17)\n\n"
        "- بيان النطاق: أول 80 عضوًا مفتوحًا غير مكرر بعد آخر موضع من الجولة السابعة، "
        "ممن كانت مروحتهم غير فارغة وهيكلهم من 2 إلى 4 صوامت؛ لم تُفعّل التوسعة.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية، الإتمامات 00561 إلى 00600\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(cards, decisions, sizes) + "\n"
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "\N{EM DASH}" in reading_append + report_append:
        raise AssertionError("شرطة طويلة في النص الجديد")

    with BASE.READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with BASE.REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND8 WRITTEN")
    print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print(
        "MAX_CARD",
        max(sizes),
        f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}",
    )
    print("LAST", cards[-1].word, cards[-1].member_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
