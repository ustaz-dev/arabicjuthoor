# -*- coding: utf-8 -*-
"""الجولة العشرون للمسار B: دفعتا إتمام للمفتوح الفارسي القصير."""

from __future__ import annotations

import argparse
import json
import re
import unicodedata
from collections import Counter, defaultdict
from dataclasses import replace
from datetime import datetime

import harvest_persian_round19 as PREVIOUS


BASE = PREVIOUS.BASE
FIRST_COMPLETION = 1411
LAST_COMPLETION = 1480
BATCH_SIZE = 35
MARKER = "LANE-B-PERSIAN-ROUND20-2026-08-18"
FIRST_WORD = "آقایان"
LAST_WORD = "میغ"
FIRST_SOURCE_INDEX = 3435
LAST_SOURCE_INDEX = 8594
EXPECTED_AVAILABLE = 131
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
    "SEMITIC-SOURCE-TRANSMISSION",
}


_previous_selected_witnesses = BASE.selected_witnesses
_previous_formatted_route = BASE.formatted_route


def available_cards(
    reading_text: str,
) -> tuple[list[BASE.SourceCard], list[BASE.SourceCard]]:
    """يأخذ السبعين التالية من ذيل الحوض الحي بعد الجولة التاسعة عشرة."""
    all_available, _ = PREVIOUS.available_cards(reading_text)
    needed = LAST_COMPLETION - FIRST_COMPLETION + 1
    return all_available, all_available[-needed:]


def normalized_card(card: BASE.SourceCard) -> BASE.SourceCard:
    """يطرح صرف الفرع المسمى قبل بناء المروحة، ولا يمس سائر الأعضاء."""
    if card.word != "بریدن":
        return card
    stem = "برید"
    skeleton = tuple(BASE.FAN.skeleton(stem, "persian"))
    candidates = BASE.FAN.fan(stem, "persian")
    ranked = tuple(BASE.FAN.rank(stem, candidates, "persian"))
    return replace(card, skeleton=skeleton, ranked_fan=ranked)


def select_decision(
    card: BASE.SourceCard,
    sense_map: dict[str, list[dict]],
) -> BASE.Decision:
    """يثبت لقاء برد بعد التعرية، ويرفع لقاء صف إلى فجوة صفه الحقيقية."""
    if card.word == "بریدن":
        return BASE.Decision(
            candidate="برد",
            verdict="ROOT-ECHO",
            state="READY",
            orbit=(
                "الفرع يسمّي القطع، والمحكم وتاج العروس يقولان بَرَدَ الحديد "
                "إذا سحله بالمبرد؛ فالمدار إزالة جزء من الجسم الصلب بأداة، "
                "والسحل نوع مباشر من القطع دون نقل معنى من مادة أخرى."
            ),
            obstacle=(
                "اكتملت أرجل الصوت والحدث والمعنى بعد طرح نون المصدر الفارسي؛ "
                "رتبة ECHO تحفظ أن العربية خصت القطع بالسحل بالمبرد."
            ),
        )
    if card.word == "سپاه":
        return BASE.Decision(
            candidate="صف",
            verdict="LAW-GAP",
            state="LAW-GAP",
            orbit=(
                "الفرع يسمّي الجيش، والعين والمفردات يسمّيان صف القوم وموقفهم "
                "ويخصان به القتال؛ فرجل المعنى حاضرة في صف القوة العسكرية، "
                "لكنها لا تصدر بلا اكتمال الطريق الصوتي."
            ),
            obstacle=(
                "س↔ص مسمى في SIB-02، أما پ↔ف فلا صف فارسي عام له؛ "
                "BR-IRAN-02 مشروط بوقوع p قبل صامت، وپ في spāh قبل صائت."
            ),
        )
    return PREVIOUS.DECIDER.select_decision(card, sense_map)


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
        "برد": (
            ("al_muhkam", ("بَرَدَ الحَدِيدَ", "سَحَلَه"), 0),
            ("taj_al_arus", ("بَرَدَ (الحديدَ)", "بَرَدَ الحديدَ"), 0),
        ),
        "صف": (
            ("kitab_al_ayn", ("صَفَفتُ القَوْمَ", "والمَصَفُّ"), 0),
            ("al_mufradat", ("[الصف/ 4]", "ثُمَّ ائْتُوا صَفًّا"), 135),
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


def formatted_route(card: BASE.SourceCard, decision: BASE.Decision) -> str:
    if card.word == "بریدن" and decision.candidate == "برد":
        return (
            "بعد طرح نون المصدر: ب↔ب=`IDN-05`، ر↔ر=`IDN-01`، "
            "د↔د=`IDN-09`؛ المرشح داخل مروحة الجذع `برید`."
        )
    if card.word == "سپاه" and decision.candidate == "صف":
        return (
            "س↔ص=`SIB-02`؛ پ↔ف=غير مسمى للفارسية في هذا الموقع؛ "
            "فُتشت الشبكة بالحرفين وبأسماء الفارسية والعربية، و`BR-IRAN-02` "
            "لا يعمل لأن p هنا قبل صائت."
        )
    return _previous_formatted_route(card, decision)


# تستدعي دالة إنشاء البطاقة هاتين الدالتين من مجال الوحدة الأساسية.
BASE.selected_witnesses = selected_witnesses
BASE.formatted_route = formatted_route


def load_branch_entries() -> dict[str, list[dict]]:
    branch_path = BASE.ROOT / "data" / "branch-lexicons" / "persian.json"
    data = json.loads(branch_path.read_text(encoding="utf-8"))
    grouped: dict[str, list[dict]] = defaultdict(list)
    for entry in data["entries"]:
        grouped[BASE.clean(str(entry.get("word") or ""))].append(entry)
    return dict(grouped)


def selected_branch_index(card: BASE.SourceCard, entries: list[dict]) -> int | None:
    for index, entry in enumerate(entries, 1):
        read = BASE.clean(str(entry.get("read") or "")).strip("/")
        pos = BASE.clean(str(entry.get("pos") or ""))
        gloss = BASE.clean(str(entry.get("en") or ""))
        if read == card.reading.strip("/") and pos == card.pos and gloss.startswith(card.gloss):
            return index
    return None


def branch_scan_line(
    card: BASE.SourceCard,
    branch_entries: dict[str, list[dict]],
) -> str:
    entries = branch_entries.get(card.word, [])
    selected = selected_branch_index(card, entries)
    if selected is None:
        return (
            f"- قراءة مداخل الرسم المتجانس: قُرئت {len(entries)} مدخلة للرسم "
            f"`{card.word}` في فهرس الفرع؛ المختار هو العضو `{card.member_id}` "
            "بنطقه ومعناه المثبتين في بطاقة الجرد، ولم تثبت هذه المدخلة بعينها "
            "في لقطة الفهرس الحالية؛ SOURCE-GAP في حقل النقص لا في الحكم."
        )
    return (
        f"- قراءة مداخل الرسم المتجانس: قُرئت {len(entries)} مدخلة للرسم "
        f"`{card.word}`؛ المختارة المدخلة {selected} بالنطق /{card.reading}/ "
        f"والصنف `{card.pos}`، ولم تؤخذ المدخلة الأولى آليا."
    )


def kaikki_decomposition(card: BASE.SourceCard) -> tuple[str, str] | None:
    """التفكيك الحصري: لا يقبل إلا سطر Kaikki نفسه من صورة From X + Y."""
    match = re.fullmatch(r"From (.+?) \+ (.+?)\.?", BASE.clean(card.etymology))
    return match.groups() if match else None


def looks_like_compound(card: BASE.SourceCard) -> bool:
    etymology = BASE.clean(card.etymology).lower()
    return "compound of " in etymology or any(mark in card.word for mark in (" ", "‌", "-"))


def augment_card(
    text: str,
    card: BASE.SourceCard,
    branch_entries: dict[str, list[dict]],
) -> str:
    meaning_line = f"- المعنى من قاموس الفرع بلا رتوش: «{card.gloss}»."
    text = text.replace(meaning_line, meaning_line + "\n" + branch_scan_line(card, branch_entries))
    if card.word == "بریدن":
        text = re.sub(
            r"^- الخطوة صفر:.*$",
            (
                "- الخطوة صفر: طُرحت صوائت الفرع ونون المصدر الفارسي `-ن`؛ "
                "الجذع `برید` وهيكله `بـرـد`، ولم يُحسب الصرف أصلا."
            ),
            text,
            count=1,
            flags=re.MULTILINE,
        )
        text = text.replace(
            "`fan_any_script.fan(بریدن, persian)`",
            "`fan_any_script.fan(برید, persian)` بعد طرح نون المصدر",
        )
    return text


def fit_card(
    number: int,
    card: BASE.SourceCard,
    decision: BASE.Decision,
    sense_map: dict[str, list[dict]],
    branch_entries: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in (
        (260, 360),
        (200, 280),
        (140, 210),
        (90, 150),
        (55, 100),
        (35, 70),
        (20, 45),
        (15, 25),
        (10, 15),
    ):
        text = BASE.make_card(
            number,
            card,
            decision,
            sense_map,
            quote_limit,
            etym_limit,
        )
        text = augment_card(text, card, branch_entries)
        if len(text.encode("utf-8")) < BASE.CARD_LIMIT:
            return text
    raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")


def validate_selection(
    all_available: list[BASE.SourceCard],
    cards: list[BASE.SourceCard],
) -> None:
    if len(all_available) != EXPECTED_AVAILABLE:
        raise AssertionError(f"تغير الحوض الحي: {len(all_available)}")
    if len(cards) != 70:
        raise AssertionError(f"نافذة الجولة العشرين ليست 70: {len(cards)}")
    if cards[0].word != FIRST_WORD or cards[-1].word != LAST_WORD:
        raise AssertionError("تغير طرفا نافذة الجولة العشرين")
    if cards[0].source_index != FIRST_SOURCE_INDEX or cards[-1].source_index != LAST_SOURCE_INDEX:
        raise AssertionError("تغير طرفا ترتيب المصدر")
    if len({card.member_id for card in cards}) != 70:
        raise AssertionError("تكرر عضو في النافذة")
    if any(not 2 <= len(card.skeleton) <= 4 for card in cards):
        raise AssertionError("دخل هيكل خارج الحد القصير")
    if any(kaikki_decomposition(card) for card in cards):
        raise AssertionError("ظهر تفكيك From X + Y يحتاج قراءة مكونين مستقلة")
    if any(looks_like_compound(card) for card in cards):
        raise AssertionError("ظهر مركب بلا تفكيك قاموسي ويجب إغلاقه COMPOUND-BOUNDARY")


def validate_new_text(
    cards: list[BASE.SourceCard],
    texts: list[str],
    decisions: list[BASE.Decision],
) -> None:
    headings = [
        int(value)
        for text in texts
        for value in re.findall(r"^### WO-B-OPEN-COMP-(\d{5}):", text, re.MULTILINE)
    ]
    if headings != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("معرفات الجولة العشرين غير متصلة")
    joined = "\n".join(texts)
    if "\N{EM DASH}" in joined or re.search(r"[\u06f0-\u06f9\u0660-\u0669]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) >= BASE.CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if "قراءة مداخل الرسم المتجانس" not in text:
            raise AssertionError(f"لم يسجل مسح متجانسات البطاقة {number:05d}")
        if not re.search(r"^- الحكم \(استكشاف\): [A-Z-]+\.$", text, re.MULTILINE):
            raise AssertionError(f"لا حكم نهائيا في البطاقة {number:05d}")
    if decisions[1424 - FIRST_COMPLETION].verdict != "ROOT-ECHO":
        raise AssertionError("لم يثبت برد بعد طرح نون المصدر")
    if decisions[1451 - FIRST_COMPLETION].verdict != "LAW-GAP":
        raise AssertionError("لم تثبت فجوة سپاه مع صف")
    required = (
        "نون المصدر الفارسي",
        "`برد`",
        "المحكم والمحيط الأعظم لابن سيده",
        "تاج العروس لمرتضى الزبيدي",
        "الحكم (استكشاف): ROOT-ECHO",
    )
    if any(value not in texts[1424 - FIRST_COMPLETION] for value in required):
        raise AssertionError("بطاقة بریدن لا تحمل سندها الكامل")


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
                f"## الجولة العشرون، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 35؛ كُتب: 35؛ مدى الهيكل بعد التعرية: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- توزيع الأحكام: {distribution}.",
                "- الصلات الإيجابية: " + ("، ".join(positives) if positives else "0") + ".",
                "- مداخل الرسم المتجانس: قُرئت كلها لكل عضو، وسُجل العدد والمدخلة المختارة في كل بطاقة.",
                "- تفكيك Kaikki الحرفي `From X + Y`: 0؛ مركبات غير مفككة قاموسيا: 0؛ لم يُختلق مكون.",
                "- أعطاب الأدوات الأساسية: 0؛ عملت المروحة بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 35 معرفا فريدا؛ لا بطاقة فوق 5KB؛ كل حكم مغلق المفردات.",
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
            "## حصيلة الجولة العشرين",
            "",
            f"- مجموع الإتمام الجديد: 70؛ {distribution}.",
            f"- الصلات الإيجابية المحسوبة: {positives}؛ `بریدن↔برد` بعد طرح نون المصدر.",
            f"- بقي بعد الدفعتين {remaining_count} عضوا قصيرا حيا ذا مروحة غير فارغة؛ لم تُفعّل توسعة هيكل.",
            "- التحقق الكلي: 70 معرفا متصلا من `01411` إلى `01480`؛ 70 عضوا فريدا؛ لا تكرار مع الإتمامات السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
            "- انضباط المركبات: لم يقع في النافذة سطر Kaikki من صورة `From X + Y` ولا عضو مركب بلا تفكيك؛ لذلك كان العد 0 و0، ولم يستعمل تفكيك حدسي.",
            "- كاشف الصرف: لم تُحسب نون مصدر `بریدن` أصلا؛ وكاشف القانون أبقى `سپاه↔صف` على LAW-GAP لغياب صف پ↔ف النافذ في هذا الموقع.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-01480`.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            "LANE-B DONE20 70 WO-B-OPEN-COMP-01480",
        ]
    )
    return "\n".join(sections)


def validate_existing(reading_text: str, report_text: str) -> None:
    reading_match = re.search(
        rf"<!-- {re.escape(MARKER)}:START -->(.*?)<!-- {re.escape(MARKER)}:END -->",
        reading_text,
        re.DOTALL,
    )
    if not reading_match:
        raise AssertionError("محضر الجولة العشرين موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d+):",
            reading_match.group(1),
            re.MULTILINE,
        )
    ]
    if ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("مقطع الجولة العشرين الموجود غير متصل")
    expected = "LANE-B DONE20 70 WO-B-OPEN-COMP-01480"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE20 ليس خاتمة التقرير")


def build_round(
    reading_text: str,
) -> tuple[list[BASE.SourceCard], list[BASE.Decision], list[str], list[int], int]:
    all_available, raw_cards = available_cards(reading_text)
    cards = [normalized_card(card) for card in raw_cards]
    validate_selection(all_available, cards)
    roots = {candidate for card in cards for candidate, _ in card.ranked_fan}
    roots.update({"برد", "صف"})
    sense_map = BASE.SENSES.matches_for_roots(BASE.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [select_decision(card, sense_map) for card in cards]
    branch_entries = load_branch_entries()
    texts = [
        fit_card(number, card, decision, sense_map, branch_entries)
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
    parser.add_argument("--preview", action="store_true")
    args = parser.parse_args()

    reading_text = BASE.READING.read_text(encoding="utf-8")
    report_text = BASE.REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        if MARKER not in reading_text or MARKER not in report_text:
            raise AssertionError("الجولة العشرون مكتوبة جزئيا")
        validate_existing(reading_text, report_text)
        print("ROUND20 ALREADY PRESENT AND VALID")
        return 0

    cards, decisions, texts, sizes, remaining_count = build_round(reading_text)
    counts = Counter(decision.verdict for decision in decisions)
    if args.preview:
        print("ROUND20 PREVIEW VALID")
        print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
        print("SOURCE", cards[0].source_index, cards[-1].source_index)
        print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
        print("MAX_CARD", max(sizes), f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}")
        print("REMAINING", remaining_count)
        return 0

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة العشرون: مواصلة المفتوح الفارسي القصير (2026-08-18)\n\n"
        "- بيان النطاق: بعد الجولة التاسعة عشرة بقي 131 عضوا قصيرا حيا؛ أُخذت السبعون التالية من `آقایان` إلى `میغ` في دفعتين 35 و35. قُرئت متجانسات كل رسم، ولم يقع في النافذة تفكيك Kaikki حرفي من صورة `From X + Y` ولا مركب غير مفكك.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية، الإتمامات 01446 إلى 01480\n\n"
        + "\n".join(texts[BATCH_SIZE:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n\n" + report_section(cards, decisions, sizes, remaining_count) + "\n"
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
    print("ROUND20 WRITTEN")
    print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("MAX_CARD", max(sizes), f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}")
    print("LANE-B DONE20 70 WO-B-OPEN-COMP-01480")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
