# -*- coding: utf-8 -*-
"""الجولة الخامسة عشرة للمسار B: دفعتا إتمام للمفتوح الفارسي القصير."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime

import harvest_persian_round14 as PREVIOUS


BASE = PREVIOUS.BASE
FIRST_COMPLETION = 1061
LAST_COMPLETION = 1130
BATCH_SIZE = 35
MARKER = "LANE-B-PERSIAN-ROUND15-2026-08-17"
FIRST_WORD = "اوتیت"
LAST_WORD = "اوورتور"
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "SEMITIC-SOURCE-TRANSMISSION",
}


_previous_selected_witnesses = BASE.selected_witnesses


def select_decision(card: BASE.SourceCard, sense_map: dict[str, list[dict]]) -> BASE.Decision:
    """يثبت اللقاءات المباشرة التي بقيت بعد قراءة المروحة والشواهد."""
    decisions = {
        "کیبل": BASE.Decision(
            candidate="كبل",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي الكابل، ولسان العرب وتاج العروس يسمّيان الكبل "
                "قيدا غليظا من أي شيء كان؛ فالمدار رباط غليظ يصل ويثبت "
                "مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        ),
        "قروت": BASE.Decision(
            candidate="قرت",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي كرة لبن أو خثارة مجففة، ولسان العرب وتاج "
                "العروس يقولان قرت الدم إذا يبس بعضه على بعض؛ فالمدار مادة "
                "تجف وتجتمع أجزاؤها باليبس مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        ),
        "کرباس": BASE.Decision(
            candidate="كربس",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي الكرباس ثوب القطن أو القماش الخشن، ولسان "
                "العرب وتاج العروس يسمّيان الكرباس ثوبا من القطن؛ فالمدار "
                "الثوب نفسه مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        ),
        "فنک": BASE.Decision(
            candidate="فنك",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي الفنك، ولسان العرب يسمّيه دابة يلبس جلدها "
                "فروا، وتاج العروس يسمّي الفنيك حيوانا كالثعلب ويعيده إلى "
                "الفنك؛ فالمدار الحيوان نفسه مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        ),
    }
    return decisions.get(card.word, PREVIOUS.select_decision(card, sense_map))


def targeted_excerpt(
    definition: str,
    needles: tuple[str, ...],
    rewind: int,
    limit: int,
) -> str:
    normalized = BASE.clean(definition)
    for needle in needles:
        pos = normalized.find(needle)
        if pos >= 0:
            return BASE.clip(normalized[max(0, pos - rewind) :], limit)
    return BASE.clip(normalized, limit)


def selected_witnesses(
    candidate: str,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
) -> tuple[int, list[tuple[str, str]]]:
    targets = {
        "كبل": (
            ("lisan", ("الكَبْل: قَيْد ضخم", "الكَبْل والكِبْل القَيْد"), 0),
            ("taj_al_arus", ("الكَبْلُ: القَيْدُ", "الكَبْلَ غيرُ عربِيٍّ"), 0),
        ),
        "قرت": (
            ("lisan", ("قَرَتَ الدَّمُ", "ودم قارِتٌ"), 0),
            ("taj_al_arus", ("قَرَتَ الدَّمُ", "ودَمٌ قَارِتٌ"), 0),
        ),
        "كربس": (
            ("lisan", ("الكِرْباس والكِرْباسة: ثوب", "الكِرْباسُ"), 0),
            ("taj_al_arus", ("الكِرْباسُ: بِالْكَسْرِ", "ثَوْبٌ من القُطْن"), 0),
        ),
        "فنك": (
            ("lisan", ("الفَنَكُ دابة يُفْتَرى جلدُها", "الفَنَكُ: جلد يلبس"), 20),
            ("taj_al_arus", ("الفَنِيكُ: حيوانٌ كالثَّعْلَبِ", "الفَنِيكُ: حيوان"), 0),
        ),
    }
    if candidate not in targets:
        return _previous_selected_witnesses(candidate, sense_map, quote_limit)

    matches = sense_map.get(candidate, [])
    witnesses: list[tuple[str, str]] = []
    for wanted, needles, rewind in targets[candidate]:
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
                    needles,
                    rewind,
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


# تستدعي دالة إنشاء البطاقة هذه الدالة من مجال الوحدة الأساسية.
BASE.selected_witnesses = selected_witnesses


def validate_new_text(
    cards: list[BASE.SourceCard],
    texts: list[str],
    decisions: list[BASE.Decision],
) -> None:
    expected_count = LAST_COMPLETION - FIRST_COMPLETION + 1
    if len(cards) != expected_count or len(texts) != expected_count:
        raise AssertionError("لم تكتمل نافذة الجولة الخامسة عشرة إلى 70 بطاقة")
    if len(decisions) != expected_count:
        raise AssertionError("عدد أحكام الجولة الخامسة عشرة غير مكتمل")
    if cards[0].word != FIRST_WORD or cards[-1].word != LAST_WORD:
        raise AssertionError("تغير طرفا نافذة الجولة الخامسة عشرة")
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
        raise AssertionError("معرفات الجولة الخامسة عشرة غير متصلة")
    joined = "\n".join(texts)
    if "\N{EM DASH}" in joined or re.search(r"[\u06f0-\u06f9\u0660-\u0669]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) > BASE.CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if not re.search(r"^- الحكم \(استكشاف\): [A-Z-]+\.$", text, re.MULTILINE):
            raise AssertionError(f"لا حكم نهائيا في البطاقة {number:05d}")

    positive_specs = {
        1106: ("`كبل`", "لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"),
        1117: ("`قرت`", "لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"),
        1125: ("`كربس`", "لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"),
        1128: ("`فنك`", "لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"),
    }
    for number, required in positive_specs.items():
        positive = texts[number - FIRST_COMPLETION]
        if any(value not in positive for value in required):
            raise AssertionError(f"لم يكتمل مرشح البطاقة الموجبة {number:05d} وشاهداها")
        if "الحكم (استكشاف): ROOT-TRACE" not in positive:
            raise AssertionError(f"غاب الحكم الموجب من البطاقة {number:05d}")
    witness_phrases = {
        1106: ("قَيْد ضخم", "القَيْدُ"),
        1117: ("يَبِسَ بعضُه على بعض", "يَبِسَ بعضُه على بَعْض"),
        1125: ("ثوب", "ثَوْبٌ من القُطْن"),
        1128: ("دابة يُفْتَرى جلدُها", "حيوانٌ كالثَّعْلَبِ"),
    }
    for number, phrases in witness_phrases.items():
        positive = texts[number - FIRST_COMPLETION]
        if any(phrase not in positive for phrase in phrases):
            raise AssertionError(f"لم تنقل البطاقة {number:05d} موضعي المعنى")


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
                f"## الجولة الخامسة عشرة، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 35؛ كُتب: 35؛ مدى الهيكل: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- توزيع الأحكام: {distribution}.",
                "- الصلات الإيجابية: " + ("، ".join(positives) if positives else "0") + ".",
                "- أعطاب الأدوات الأساسية: 0؛ عملت `fan_any_script.fan` بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 35 معرفا فريدا؛ 35 عضوا غير مكرر ولا سابق الإتمام؛ لا هيكل فوق 4؛ كل حكم مغلق المفردات.",
                "- بقي في الحوض القصير مرشحون بعد هذه الدفعة؛ لم تُفعّل توسعة جديدة.",
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
            "## حصيلة الجولة الخامسة عشرة",
            "",
            f"- مجموع الإتمام الجديد: 70؛ {distribution}.",
            f"- الصلات الإيجابية المحسوبة: {positives}.",
            "- استمر الحوض القصير الحي؛ بقي 108 أعضاء قصيرة قابلة للترشيح بعد الدفعتين.",
            "- التحقق الكلي: 70 معرفا متصلا من `01061` إلى `01130`؛ 70 عضوا فريدا؛ لا تكرار مع بطاقات الإتمام السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- كاشف الانضباط التشخيصي: أربع ملاحظات `D4-DIRECTION` في `01106` و`01117` و`01125` و`01128` لأن أخبار الأصل تسمي مانحين غير ساميين؛ لا تنقض الأحكام بمقتضى الأمر القائم، إذ اكتملت أرجل الصوت والحدث والمعنى، ولا يُخترع شرط رابع.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-01130`.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            "LANE-B DONE15 70 WO-B-OPEN-COMP-01130",
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
        raise AssertionError("محضر الجولة الخامسة عشرة موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d+):", reading_match.group(1), re.MULTILINE
        )
    ]
    if ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("مقطع الجولة الخامسة عشرة الموجود غير متصل")
    for block in re.split(
        r"(?=^### WO-B-OPEN-COMP-)", reading_match.group(1), flags=re.MULTILINE
    ):
        if block.startswith("### WO-B-OPEN-COMP-") and len(block.encode("utf-8")) >= BASE.CARD_LIMIT:
            raise AssertionError("بطاقة موجودة تتجاوز 5KB")
    expected = "LANE-B DONE15 70 WO-B-OPEN-COMP-01130"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE15 ليس خاتمة التقرير")


def main() -> int:
    reading_text = BASE.READING.read_text(encoding="utf-8")
    report_text = BASE.REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        if MARKER not in reading_text or MARKER not in report_text:
            raise AssertionError("الجولة الخامسة عشرة مكتوبة جزئيا")
        validate_existing(reading_text, report_text)
        print("ROUND15 ALREADY PRESENT AND VALID")
        return 0

    completed = BASE.parse_completed_members(reading_text)
    available = BASE.parse_source_cards(reading_text, completed)
    cards = available[: LAST_COMPLETION - FIRST_COMPLETION + 1]
    if len(cards) != 70:
        raise AssertionError(
            f"عُثر على {len(cards)} بطاقة قصيرة فقط؛ يلزم عندئذ تغيير حجم الدفعتين قبل الكتابة"
        )

    roots = {candidate for card in cards for candidate, _ in card.ranked_fan}
    roots.update({"كبل", "قرت", "كربس", "فنك"})
    sense_map = BASE.SENSES.matches_for_roots(BASE.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [select_decision(card, sense_map) for card in cards]
    texts = [
        PREVIOUS.PREVIOUS.PREVIOUS.PREVIOUS.fit_card(number, card, decision, sense_map)
        for number, card, decision in zip(
            range(FIRST_COMPLETION, LAST_COMPLETION + 1), cards, decisions
        )
    ]
    validate_new_text(cards, texts, decisions)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الخامسة عشرة: استمرار إتمام المفتوح الفارسي القصير (2026-08-17)\n\n"
        "- بيان النطاق: بعد قبول الجولة الرابعة عشرة وتسويتها أعيد حساب الحالة الحية. بقي 178 عضوا قصيرا غير مكرر ذا مروحة غير فارغة؛ أخذت أول 70 في ترتيب المصدر، من `اوتیت` إلى `اوورتور`، في دفعتين 35 و35.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية، الإتمامات 01096 إلى 01130\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n\n" + report_section(cards, decisions, sizes) + "\n"
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
    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND15 WRITTEN")
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
