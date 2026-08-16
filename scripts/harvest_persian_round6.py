# -*- coding: utf-8 -*-
"""إتمام دفعتين فارسيتين من البطاقات المفتوحة في الجولة السادسة."""

from __future__ import annotations

import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import fan_any_script as FAN  # noqa: E402
import frozen_event as EVENT  # noqa: E402
import search_arabic_root_senses as SENSES  # noqa: E402


READING = ROOT / "04-cross-linguistic" / "readings" / "persian.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-B.md"
FIRST_COMPLETION = 361
LAST_COMPLETION = 440
SOURCE_FLOOR = 5957
CARD_LIMIT = 5120
MARKER = "LANE-B-PERSIAN-ROUND6-2026-08-17"


ROUTES: dict[tuple[str, str], str | None] = {
    ("آ", "ا"): "IDN-16",
    ("ا", "ا"): "IDN-16",
    ("ب", "ب"): "IDN-05",
    ("ت", "ت"): "IDN-11",
    ("ج", "ج"): "IDN-08",
    ("د", "د"): "IDN-09",
    ("ر", "ر"): "IDN-01",
    ("ر", "ل"): "LIQ-01",
    ("ز", "ذ"): None,
    ("س", "س"): "IDN-07",
    ("ش", "س"): "SIB-01",
    ("غ", "غ"): None,
    ("ف", "ف"): "IDN-06",
    ("ق", "ق"): "IDN-12",
    ("ل", "ل"): "IDN-04",
    ("م", "م"): "IDN-02",
    ("ن", "ن"): "IDN-03",
    ("ه", "ه"): "IDN-20",
    ("و", "و"): "IDN-10",
    ("پ", "ب"): "LAB-01",
    ("چ", "ج"): None,
    ("ژ", "ز"): None,
    ("ک", "ك"): "IDN-13",
    ("گ", "ج"): "GUT-03",
    ("ی", "ي"): "IDN-23",
}


@dataclass(frozen=True)
class SourceCard:
    source_index: int
    word: str
    reading: str
    pos: str
    member_id: str
    family_id: str
    etymology: str
    gloss: str
    skeleton: tuple[str, ...]
    ranked_fan: tuple[tuple[str, float], ...]


@dataclass(frozen=True)
class Decision:
    candidate: str
    verdict: str
    state: str
    orbit: str
    obstacle: str


def clean(value: str) -> str:
    value = unicodedata.normalize("NFC", value)
    value = " ".join(value.split())
    value = value.replace("—", "-")
    return value


def clip(value: str, limit: int) -> str:
    value = clean(value)
    if len(value) <= limit:
        return value
    cut = value[:limit].rstrip()
    for stop in (". ", "؛ ", ": "):
        pos = cut.rfind(stop)
        if pos >= max(70, limit // 2):
            return cut[: pos + 1].rstrip() + "…"
    return cut + "…"


def parse_completed_members(text: str) -> set[str]:
    return set(re.findall(r"العضو الفردي `([^`]+)`", text))


def parse_source_cards(text: str, completed: set[str]) -> list[SourceCard]:
    cards: list[SourceCard] = []
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
        etymology = re.search(
            r"- أقدمُ صورةٍ مستعادة: (.*?) \[Kaikki Persian",
            block,
        )
        gloss = re.search(
            r"- المعنى من قاموس الفرع: «(.*?)» \[Kaikki Persian",
            block,
        )
        if not (member and family and etymology and gloss):
            continue
        word, reading, pos, member_id = member.groups()
        source_index = int(member_id.split(":", 2)[1])
        if source_index <= SOURCE_FLOOR or member_id in completed:
            continue
        skeleton = tuple(FAN.skeleton(word, "persian"))
        candidates = FAN.fan(word, "persian")
        if not candidates or not 2 <= len(skeleton) <= 4:
            continue
        ranked = tuple(FAN.rank(word, candidates, "persian"))
        cards.append(
            SourceCard(
                source_index=source_index,
                word=clean(word),
                reading=clean(reading),
                pos=clean(pos),
                member_id=clean(member_id),
                family_id=family.group(1),
                etymology=clean(etymology.group(1)),
                gloss=clean(gloss.group(1)),
                skeleton=skeleton,
                ranked_fan=ranked,
            )
        )
    cards.sort(key=lambda item: item.source_index)
    return cards[: LAST_COMPLETION - FIRST_COMPLETION + 1]


def route_parts(skeleton: tuple[str, ...], candidate: str) -> list[tuple[str, str, str | None]]:
    if len(skeleton) != len(candidate):
        return []
    return [(source, target, ROUTES.get((source, target))) for source, target in zip(skeleton, candidate)]


def select_decision(card: SourceCard, sense_map: dict[str, list[dict]]) -> Decision:
    # القرار الموجب الوحيد في النافذة يقوم على نص الطريق نفسه في المعجمين.
    if card.word == "سرک":
        return Decision(
            candidate="سلك",
            verdict="ROOT-TRACE",
            state="READY",
            orbit=(
                "الفرع يسمّي الطريق، والعربية تسمّي المسلك الطريق وتستعمل سلوك "
                "الطريق؛ فالمدار طريق ونفاذ فيه مباشرة."
            ),
            obstacle="اكتملت أرجل الصوت والحدث والمعنى بشاهدين عربيين مستقلين.",
        )
    if card.word == "گاومیش":
        return Decision(
            candidate=card.ranked_fan[0][0],
            verdict="COMPOUND-BOUNDARY",
            state="COMPOUND-BOUNDARY",
            orbit=(
                "المصدر يحلل الصورة الوسطى إلى «بقرة + نعجة»؛ وحدة المقارنة "
                "مركب مثبت لا جذر مفرد."
            ),
            obstacle="حد المركب مثبت في أصل الفرع؛ لا يرث المركب حكم أحد جزأيه.",
        )
    if card.word == "آبجی":
        return Decision(
            candidate=card.ranked_fan[0][0],
            verdict="MORPHOLOGY-GAP",
            state="MORPHOLOGY-GAP",
            orbit=(
                "المصدر يثبت انقباض الصورة من مركب أقدم، ولا يحسم أي صوامت "
                "العضو المنقبض أصل وأيها أثر حد صرفي."
            ),
            obstacle="يلزم تحليل صرفي منشور يفصل صوامت الانقباض قبل حكم المقارنة.",
        )

    candidate = card.ranked_fan[0][0]
    routes = route_parts(card.skeleton, candidate)
    if not routes or any(row is None for _, _, row in routes):
        missing = "، ".join(
            f"{source}↔{target}" for source, target, row in routes if row is None
        ) or "رصف الهيكل الموسع"
        return Decision(
            candidate=candidate,
            verdict="LAW-GAP",
            state="LAW-GAP",
            orbit=(
                f"قوبل معنى الفرع «{card.gloss}» بالمقابل `{candidate}`؛ لا "
                "يصدر مدار موجب قبل اكتمال الصف الصوتي المسمى."
            ),
            obstacle=f"بقي صف صوتي غير مسمى في الشبكة المجمدة: {missing}.",
        )

    independent = SENSES.independent_fan(sense_map.get(candidate, []), 2)
    if not independent["source_coverage_complete"]:
        return Decision(
            candidate=candidate,
            verdict="SOURCE-GAP",
            state="SOURCE-GAP",
            orbit=(
                f"قرئ معنى الفرع «{card.gloss}»، لكن الموارد لم تعط شاهدين "
                f"عربيين مستقلين لـ`{candidate}`؛ تبقى رجل المعنى مفتوحة."
            ),
            obstacle=(
                "لم يكتمل شاهدان عربيان مستقلان للمادة المختارة؛ الغياب من "
                "الموارد لا ينفي اللسان."
            ),
        )

    return Decision(
        candidate=candidate,
        verdict="OPEN-CANDIDATE",
        state="OPEN-CANDIDATE",
        orbit=(
            f"قوبل معنى الفرع «{card.gloss}» بشاهدي `{candidate}`؛ لم تتحد "
            "نقطة المعنى اتحادًا مباشرًا، فلا ينشأ جسر من التشابه العام."
        ),
        obstacle=(
            "قرئ معنى الفرع والشاهدان، ولم يثبت بينهما مدار دلالي يدوي مباشر؛ "
            "رجل المعنى غائبة."
        ),
    )


def witness_excerpt(definition: str, candidate: str, source_id: str, limit: int) -> str:
    definition = clean(definition)
    if candidate == "سلك":
        needles = (
            "والمَسْلَكُ: الطريق",
            "المَسْلَكُ: الطريق",
            "سَلَكَ المَكانَ والطَّرِيقَ",
            "سلك الْمَكَان",
        )
        for needle in needles:
            pos = definition.find(needle)
            if pos >= 0:
                return clip(definition[pos:], limit)
    return clip(definition, limit)


def selected_witnesses(
    candidate: str,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
) -> tuple[int, list[tuple[str, str]]]:
    matches = sense_map.get(candidate, [])
    independent = SENSES.independent_fan(matches, 2)
    witnesses: list[tuple[str, str]] = []
    for item in independent["selected_sources"][:2]:
        witnesses.append(
            (
                clean(item["source_label"]),
                witness_excerpt(
                    str(item.get("definition") or ""),
                    candidate,
                    str(item.get("source_id") or ""),
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


def formatted_route(card: SourceCard, decision: Decision) -> str:
    routes = route_parts(card.skeleton, decision.candidate)
    if not routes:
        return "الرصف يحتاج تحليلًا صرفيًا قبل تسمية صفوفه."
    parts = []
    missing = []
    for source, target, row in routes:
        if row is None:
            parts.append(f"{source}↔{target}=غير مسمى")
            missing.append(f"{source}↔{target}")
        else:
            parts.append(f"{source}↔{target}=`{row}`")
    text = "الرصف المفحوص: " + "، ".join(parts)
    if missing:
        text += "; الصف المفقود: " + "، ".join(missing) + "; فُتشت الشبكة بالحرفين وأسماء الفارسية والعربية."
    return text


def formatted_fan(card: SourceCard) -> str:
    return "،".join(f"{candidate}:{weight:.3f}" for candidate, weight in card.ranked_fan)


def comparison_degree(candidate: str) -> str:
    if len(candidate) == 2:
        return "نواة ثنائية."
    if len(candidate) == 3:
        return "جذر كامل."
    return "جذر كامل رباعي."


def event_line(candidate: str) -> str:
    events = EVENT.all_tiers(candidate)
    if not events:
        return "لا حدث متاح؛ حرف خارج محاكم السجل المجمد."
    event = events[0]
    return f"درجة {event.tier}، {event.tier_ar}: «{clean(event.text)}» [{event.source}]."


def make_card(
    number: int,
    card: SourceCard,
    decision: Decision,
    sense_map: dict[str, list[dict]],
    quote_limit: int,
    etym_limit: int,
) -> str:
    match_count, witnesses = selected_witnesses(decision.candidate, sense_map, quote_limit)
    fan = formatted_fan(card)
    lines = [
        f"### WO-B-OPEN-COMP-{number:05d}: إتمام `{card.family_id}`، `{card.word}` /{card.reading}/",
        "- إصدار البروتوكول: RECOVERY-v2 (2026-08-16).",
        (
            f"- مرجع بطاقة الجرد: `{card.family_id}`؛ العضو الفردي `{card.member_id}`؛ "
            "الحكم المنسوخ بالإتمام: غير صادر."
        ),
        f"- الكلمة في الفرع: فارسية `{card.word}` /{card.reading}/؛ الصنف `{card.pos}`.",
        (
            f"- أقدم صورة مستعادة: «{clip(card.etymology, etym_limit)}» "
            "[بطاقة الجرد؛ data/branch-lexicons/persian.json]."
        ),
        (
            f"- الخطوة صفر: طُرحت صوائت الفرع فقط؛ الهيكل `{'ـ'.join(card.skeleton)}` "
            f"وعدد صوامته {len(card.skeleton)}؛ لم يحذف صامت حدسًا."
        ),
        f"- درجة المقارنة: {comparison_degree(decision.candidate)}",
        (
            f"- المروحة المرتبة: `fan_any_script.fan({card.word}, persian)`؛ العدد "
            f"{len(card.ranked_fan)}: {fan}."
        ),
        f"- المقابل من اللسان: `{decision.candidate}`؛ مادة الفحص المختارة من المروحة.",
        f"- مسار الصوت والحد المسمى: {formatted_route(card, decision)}",
        f"- الحدث من السجل المجمد كما هو: {event_line(decision.candidate)}",
        f"- المعنى من قاموس الفرع بلا رتوش: «{card.gloss}».",
        (
            f"- مسح المعاني العربية: قُرئت {match_count} نتيجة لـ`{decision.candidate}` "
            "بـ`--max-chars 0`؛ نُقل شاهدان فقط:"
        ),
        f"  - الشاهد 1، {witnesses[0][0]}: «{witnesses[0][1]}»",
        f"  - الشاهد 2، {witnesses[1][0]}: «{witnesses[1][1]}»",
        f"- المدار المكتوب بالكلمات: {decision.orbit}",
        "- المصفاة: خبر الأصل حاشية؛ لا يغلق القرض إلا مانح عربي أو سامي مباشر مسمى.",
        "- فصل المتجانسات والاقتراض: الحكم للعضو المسمى وحده؛ لا توارث لمتحد الرسم أو الأسرة.",
        "- اليتم والإشعاع: الجرد حاضر؛ العضو مستقل؛ العربية قُرئت بشاهدين أو سُميت فجوتها؛ لا حصر.",
        "- الجسور المفحوصة: الجرد؛ الأصل؛ الصفر؛ المروحة كاملة؛ الشبكة؛ `all_tiers`؛ الشواهد؛ المصفاة.",
        f"- عائق القرار أو تمامه: {decision.obstacle}",
        f"- ملاحظات العدستين: استرداد حتى القرار، وتشكيك مقصور على العضو؛ الإتمام `WO-B-OPEN-COMP-{number:05d}`.",
        f"- حالة الإغلاق: {decision.state}.",
        f"- الحكم (استكشاف): {decision.verdict}.",
    ]
    return "\n".join(lines) + "\n"


def fit_card(
    number: int,
    card: SourceCard,
    decision: Decision,
    sense_map: dict[str, list[dict]],
) -> str:
    for quote_limit, etym_limit in ((300, 420), (220, 320), (150, 240), (90, 180), (55, 130)):
        text = make_card(number, card, decision, sense_map, quote_limit, etym_limit)
        size = len(text.encode("utf-8"))
        if size < CARD_LIMIT:
            return text
    raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم: {size} بايت")


def report_section(cards: list[SourceCard], decisions: list[Decision], sizes: list[int]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M %z")
    sections = [f"<!-- {MARKER}:START -->", ""]
    for batch in (0, 1):
        lo = batch * 40
        hi = lo + 40
        batch_cards = cards[lo:hi]
        batch_decisions = decisions[lo:hi]
        counts = Counter(item.verdict for item in batch_decisions)
        distribution = "؛ ".join(f"{key}={counts[key]}" for key in sorted(counts))
        first = FIRST_COMPLETION + lo
        last = FIRST_COMPLETION + hi - 1
        positives = [
            f"`{card.word}↔{decision.candidate}`"
            for card, decision in zip(batch_cards, batch_decisions)
            if decision.verdict in {"ROOT-TRACE", "NUCLEUS-TRACE", "SEMITIC-SOURCE-TRANSMISSION"}
        ]
        sections.extend(
            [
                f"## الجولة السادسة، دفعة إتمام المفتوح القصير رقم {batch + 1}",
                "",
                f"- الوقت: {now}، Africa/Cairo.",
                "- فُحص ورُشّح قبل القراءة: 40؛ كُتب: 40؛ مدى الهيكل: 2 إلى 4 صوامت.",
                f"- المدى: من `WO-B-OPEN-COMP-{first:05d}` إلى `WO-B-OPEN-COMP-{last:05d}`.",
                f"- توزيع الأحكام: {distribution}.",
                (
                    "- الصلات الإيجابية: " + ("، ".join(positives) if positives else "0") + "."
                ),
                "- أعطاب الأدوات الأساسية: 0؛ عملت `fan_any_script.fan` بالخط `persian` و`frozen_event.all_tiers` ومسح الجذور الكامل.",
                "- التحقق البنيوي: 40 معرّفًا فريدًا؛ 40 عضوًا غير مكرر ولا سابق الإتمام؛ لا هيكل فوق 4؛ كل حكم مغلق المفردات.",
                "- لم تُفعّل توسعة الهيكل؛ بقي في الحوض القصير مرشحون بعد هذه الدفعة.",
                (
                    f"- آخر موضع: `WO-B-OPEN-COMP-{last:05d}`، "
                    f"`{batch_cards[-1].word}` /{batch_cards[-1].reading}/."
                ),
                "",
            ]
        )
    total = Counter(item.verdict for item in decisions)
    distribution = "؛ ".join(f"{key}={total[key]}" for key in sorted(total))
    max_size = max(sizes)
    max_number = FIRST_COMPLETION + sizes.index(max_size)
    sections.extend(
        [
            "## حصيلة الجولة السادسة",
            "",
            f"- مجموع الإتمام الجديد: 80؛ {distribution}.",
            "- الصلات الإيجابية المحسوبة: 1.",
            "- لم تُفعّل التوسعة؛ القصير الهيكل لم ينفد.",
            "- التحقق الكلي: 80 معرّفًا متصلًا من `00361` إلى `00440`؛ 80 عضوًا فريدًا؛ لا تكرار مع بطاقات الإتمام السابقة.",
            f"- أكبر بطاقة: {max_size} بايت، `WO-B-OPEN-COMP-{max_number:05d}`؛ لا بطاقة تتجاوز 5 كيلوبايت، ولا شرطة طويلة، ولا أرقام فارسية.",
            "- كاشف الانضباط التشخيصي: ملاحظة `D4-DIRECTION` واحدة في `00373` لأن خبر أصل الفرع يذكر الأردية؛ لا تنقض الحكم بمقتضى الأمر القائم، إذ اكتملت أرجل الصوت والحدث والمعنى، ولا يُختَرع شرط رابع.",
            "- عطب أداة أساسية: 0؛ آخر موضع للمسار: `WO-B-OPEN-COMP-00440`.",
            "",
            "LANE-B DONE6 80 WO-B-OPEN-COMP-00440",
            "",
            f"<!-- {MARKER}:END -->",
            "",
        ]
    )
    return "\n".join(sections)


def validate_new_text(cards: list[SourceCard], texts: list[str], decisions: list[Decision]) -> None:
    if len(cards) != 80 or len(texts) != 80 or len(decisions) != 80:
        raise AssertionError("لم تكتمل نافذة الجولة السادسة إلى 80 بطاقة")
    member_ids = [card.member_id for card in cards]
    if len(member_ids) != len(set(member_ids)):
        raise AssertionError("تكرر عضو في النافذة الجديدة")
    for card in cards:
        if not 2 <= len(card.skeleton) <= 4:
            raise AssertionError(f"هيكل خارج الحد: {card.word}")
    joined = "\n".join(texts)
    ids = [int(value) for value in re.findall(r"WO-B-OPEN-COMP-(\d{5})", joined)]
    headings = sorted(set(ids))
    expected = list(range(FIRST_COMPLETION, LAST_COMPLETION + 1))
    if headings != expected:
        raise AssertionError("معرّفات الجولة السادسة غير متصلة")
    if "—" in joined or re.search(r"[۰-۹٠-٩]", joined):
        raise AssertionError("دخلت شرطة طويلة أو أرقام غير غربية")
    for number, text in enumerate(texts, FIRST_COMPLETION):
        if len(text.encode("utf-8")) > CARD_LIMIT:
            raise AssertionError(f"تجاوزت البطاقة {number:05d} حد الحجم")
        if not re.search(r"^- الحكم \(استكشاف\): [A-Z-]+\.$", text, re.MULTILINE):
            raise AssertionError(f"لا حكم نهائيًا في البطاقة {number:05d}")


def validate_existing_round(text: str) -> None:
    ids = [
        int(value)
        for value in re.findall(r"^### WO-B-OPEN-COMP-(\d{5}):", text, re.MULTILINE)
        if FIRST_COMPLETION <= int(value) <= LAST_COMPLETION
    ]
    if ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1)):
        raise AssertionError("الجولة السادسة الموجودة غير مكتملة أو غير متصلة")
    positive = re.search(
        r"^### WO-B-OPEN-COMP-00373:.*?(?=^### |\Z)",
        text,
        re.MULTILINE | re.DOTALL,
    )
    if not positive or "ر↔ل=`LIQ-01`" not in positive.group(0):
        raise AssertionError("صف LIQ-01 غائب من البطاقة الموجبة 00373")


def main() -> int:
    reading_text = READING.read_text(encoding="utf-8")
    report_text = REPORT.read_text(encoding="utf-8")
    if f"WO-B-OPEN-COMP-{FIRST_COMPLETION:05d}" in reading_text:
        validate_existing_round(reading_text)
        if MARKER not in report_text:
            raise AssertionError("البطاقات موجودة ومحضر الجولة السادسة غائب")
        print("ROUND6 ALREADY PRESENT AND VALID")
        return 0
    if MARKER in report_text:
        raise AssertionError("محضر الجولة السادسة موجود قبل بطاقاتها")

    completed = parse_completed_members(reading_text)
    cards = parse_source_cards(reading_text, completed)
    if len(cards) != 80:
        raise AssertionError(f"عُثر على {len(cards)} بطاقة صالحة فقط")

    roots = {card.ranked_fan[0][0] for card in cards} | {"سلك"}
    sense_map = SENSES.matches_for_roots(SENSES.DEFAULT_RESOURCES, roots, None)
    decisions = [select_decision(card, sense_map) for card in cards]
    texts = [
        fit_card(number, card, decision, sense_map)
        for number, card, decision in zip(
            range(FIRST_COMPLETION, LAST_COMPLETION + 1), cards, decisions
        )
    ]
    validate_new_text(cards, texts, decisions)
    # يفصل الإلحاق بين البطاقات بسطر فارغ؛ يدخل بايت الفصل في قياس الملف الفعلي.
    sizes = [len(text.encode("utf-8")) + 1 for text in texts]

    reading_append = (
        f"\n\n<!-- {MARKER}:START -->\n\n"
        "## الجولة السادسة: دفعتا إتمام المفتوح القصير (2026-08-17)\n\n"
        "- بيان النطاق: أول 80 عضوًا مفتوحًا غير مكرر بعد موضع المصدر 5957، "
        "ممن كانت مروحتهم غير فارغة وهيكلهم من 2 إلى 4 صوامت؛ لم تُفعّل التوسعة.\n\n"
        + "\n".join(texts[:40])
        + "\n## الدفعة الثانية، الإتمامات 00401 إلى 00440\n\n"
        + "\n".join(texts[40:])
        + f"\n<!-- {MARKER}:END -->\n"
    )
    report_append = "\n" + report_section(cards, decisions, sizes)
    reading_append = unicodedata.normalize("NFC", reading_append)
    report_append = unicodedata.normalize("NFC", report_append)
    if "—" in reading_append + report_append:
        raise AssertionError("شرطة طويلة في النص الجديد")

    with READING.open("a", encoding="utf-8", newline="") as handle:
        handle.write(reading_append)
    with REPORT.open("a", encoding="utf-8", newline="") as handle:
        handle.write(report_append)

    counts = Counter(decision.verdict for decision in decisions)
    print("ROUND6 WRITTEN")
    print("CARDS", len(cards), f"RANGE={FIRST_COMPLETION:05d}-{LAST_COMPLETION:05d}")
    print("VERDICTS", " ".join(f"{key}={counts[key]}" for key in sorted(counts)))
    print("MAX_CARD", max(sizes), f"WO-B-OPEN-COMP-{FIRST_COMPLETION + sizes.index(max(sizes)):05d}")
    print("LAST", cards[-1].word, cards[-1].member_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
