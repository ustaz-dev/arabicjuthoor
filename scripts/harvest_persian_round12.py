# -*- coding: utf-8 -*-
"""الجولة الثانية عشرة للمسار B: استئناف إتمام المفتوح الفارسي القصير."""

from __future__ import annotations

import re
import unicodedata
from collections import Counter
from datetime import datetime

import harvest_persian_round8 as PREVIOUS


BASE = PREVIOUS.BASE
FIRST_COMPLETION = 841
LAST_COMPLETION = 920
BATCH_SIZE = 40
MARKER = "LANE-B-PERSIAN-ROUND12-2026-08-17"
FIRST_WORD = "جوک"
LAST_WORD = "وج"
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "SEMITIC-SOURCE-TRANSMISSION",
}


_previous_formatted_route = BASE.formatted_route
_previous_selected_witnesses = BASE.selected_witnesses


def select_decision(card: BASE.SourceCard, sense_map: dict[str, list[dict]]) -> BASE.Decision:
    """يثبت الصلتين المباشرتين اللتين بقيتا بعد قراءة المروحة والشواهد."""
    if card.word == "بیش":
        return BASE.Decision(
            candidate="بيش",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي البيش نبات الأقونيطن السام، ولسان العرب وتاج "
                "العروس يسمّيان البيش نباتا هنديا ساما؛ فالمدار النبات السام "
                "نفسه مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        )
    if card.word == "وج":
        return BASE.Decision(
            candidate="وج",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي الوج نبات قصب الذريرة، وكتاب العين يسمّيه عيدانا "
                "يتداوى بها، والمعجم العربي الإنجليزي يعيّنه acorus؛ فالمدار "
                "النبات الدوائي نفسه مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        )
    return PREVIOUS.select_decision(card, sense_map)


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
        "بيش": (
            ("lisan", ("البِيْشُ، بكسر الباء", "نَبْتٌ ببلاد الهند وهو سَمٌّ"), 10),
            ("taj_al_arus", ("والبِيشُ، بالكَسر", "نَبَاتٌ ببلادِ الهِندِ"), 10),
        ),
        "وج": (
            ("kitab_al_ayn", ("الوَجُّ عِيدانٌ", "عِيدانٌ يتداوى بها"), 10),
            ("arabic_english", ("A kind of medicine", "acorus"), 10),
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
    if card.word == "بیش" and decision.candidate == "بيش":
        return (
            "الرصف المفحوص: ب↔ب=`IDN-05`، ش↔ش=`IDN-21`، وباب المعتل "
            "المسمى يثبت الياء الجوفية في `بيش`؛ المرشح داخل المروحة."
        )
    return _previous_formatted_route(card, decision)


# تستدعي دالة إنشاء البطاقة هاتين الدالتين من مجال الوحدة الأساسية.
BASE.selected_witnesses = selected_witnesses
BASE.formatted_route = formatted_route


def validate_new_text(
    cards: list[BASE.SourceCard],
    texts: list[str],
    decisions: list[BASE.Decision],
) -> None:
    expected_count = LAST_COMPLETION - FIRST_COMPLETION + 1
    if len(cards) != expected_count or len(texts) != expected_count:
        raise AssertionError("لم تكتمل نافذة الجولة الثانية عشرة إلى 80 بطاقة")
    if len(decisions) != expected_count:
        raise AssertionError("عدد أحكام الجولة الثانية عشرة غير مكتمل")
    if cards[0].word != FIRST_WORD or cards[-1].word != LAST_WORD:
        raise AssertionError("تغير طرفا نافذة الجولة الثانية عشرة")
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
        raise AssertionError("معرّفات الجولة الثانية عشرة غير متصلة")
    joined = "\n".join(texts)
    if "\N{EM DASH}" in joined or re.search(r"[\u06f0-\u06f9\u0660-\u0669]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) > BASE.CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if not re.search(r"^- الحكم \(استكشاف\): [A-Z-]+\.$", text, re.MULTILINE):
            raise AssertionError(f"لا حكم نهائيا في البطاقة {number:05d}")

    positive_specs = {
        901: ("`بيش`", "لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"),
        920: ("`وج`", "كتاب العين للخليل بن أحمد", "المعجم العربي الإنجليزي"),
    }
    for number, required in positive_specs.items():
        positive = texts[number - FIRST_COMPLETION]
        if any(value not in positive for value in required):
            raise AssertionError(f"لم يكتمل مرشح البطاقة الموجبة {number:05d} وشاهداها")
        if "الحكم (استكشاف): ROOT-TRACE" not in positive:
            raise AssertionError(f"غاب الحكم الموجب من البطاقة {number:05d}")


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
                f"## الجولة الثانية عشرة، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 40؛ كُتب: 40؛ مدى الهيكل: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- توزيع الأحكام: {distribution}.",
                "- الصلات الإيجابية: " + ("، ".join(positives) if positives else "0") + ".",
                "- أعطاب الأدوات الأساسية: 0؛ عملت `fan_any_script.fan` بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 40 معرفا فريدا؛ 40 عضوا غير مكرر ولا سابق الإتمام؛ لا هيكل فوق 4؛ كل حكم مغلق المفردات.",
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
            "## حصيلة الجولة الثانية عشرة",
            "",
            f"- مجموع الإتمام الجديد: 80؛ {distribution}.",
            f"- الصلات الإيجابية المحسوبة: {positives}.",
            "- استؤنف الحوض القصير الحي بعد استنفاد المركبات؛ بقي 318 عضوا قصيرا قابلا للترشيح بعد الدفعتين.",
            "- التحقق الكلي: 80 معرفا متصلا من `00841` إلى `00920`؛ 80 عضوا فريدا؛ لا تكرار مع بطاقات الإتمام السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- كاشف الانضباط التشخيصي: ملاحظتا `D4-DIRECTION` في `00901` و`00920` لأن نصي الأصل والشاهد العربي يسميان الهند أو التعريب من الفارسية؛ لا تنقضان الحكم بمقتضى الأمر القائم، إذ اكتملت أرجل الصوت والحدث والمعنى، ولا يُخترع شرط رابع.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-00920`.",
            "",
            f"<!-- {MARKER}:END -->",
            "",
            "LANE-B DONE12 80 WO-B-OPEN-COMP-00920",
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
        raise AssertionError("محضر الجولة الثانية عشرة موجود بلا مقطع القراءة")
    ids = [
        int(value)
        for value in re.findall(
            r"^### WO-B-OPEN-COMP-(\d+):", reading_match.group(1), re.MULTILINE
        )
    ]
    if ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("مقطع الجولة الثانية عشرة الموجود غير متصل")
    for block in re.split(
        r"(?=^### WO-B-OPEN-COMP-)", reading_match.group(1), flags=re.MULTILINE
    ):
        if block.startswith("### WO-B-OPEN-COMP-") and len(block.encode("utf-8")) >= BASE.CARD_LIMIT:
            raise AssertionError("بطاقة موجودة تتجاوز 5KB")
    expected = "LANE-B DONE12 80 WO-B-OPEN-COMP-00920"
    if not report_text.rstrip().endswith(expected):
        raise AssertionError("سطر DONE12 ليس خاتمة التقرير")


def main() -> int:
    reading_text = BASE.READING.read_text(encoding="utf-8")
    report_text = BASE.REPORT.read_text(encoding="utf-8")
    if MARKER in reading_text or MARKER in report_text:
        if MARKER not in reading_text or MARKER not in report_text:
            raise AssertionError("الجولة الثانية عشرة مكتوبة جزئيا")
        validate_existing(reading_text, report_text)
        print("ROUND12 ALREADY PRESENT AND VALID")
        return 0

    completed = BASE.parse_completed_members(reading_text)
    cards = BASE.parse_source_cards(reading_text, completed)
    if len(cards) != 80:
        raise AssertionError(
            f"عُثر على {len(cards)} بطاقة قصيرة فقط؛ يلزم عندئذ تغيير حجم الدفعتين قبل الكتابة"
        )

    roots = {candidate for card in cards for candidate, _ in card.ranked_fan}
    roots.update({"بيش", "وج"})
    sense_map = BASE.SENSES.matches_for_roots(BASE.SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [select_decision(card, sense_map) for card in cards]
    texts = [
        PREVIOUS.fit_card(number, card, decision, sense_map)
        for number, card, decision in zip(
            range(FIRST_COMPLETION, LAST_COMPLETION + 1), cards, decisions
        )
    ]
    validate_new_text(cards, texts, decisions)
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة الثانية عشرة: استئناف إتمام المفتوح الفارسي القصير (2026-08-17)\n\n"
        "- بيان النطاق: بعد قبول الجولة الحادية عشرة وتسويتها واستنفاد حوض المركبات، أعيد حساب الحالة الحية. بقي 398 عضوا قصيرا غير مكرر ذا مروحة غير فارغة؛ أخذت أول 80 في ترتيب المصدر، من `جوک` إلى `وج`، في دفعتين 40 و40.\n\n"
        + "\n".join(texts[:BATCH_SIZE])
        + "\n## الدفعة الثانية، الإتمامات 00881 إلى 00920\n\n"
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
    print("ROUND12 WRITTEN")
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
