#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 7 without writing, committing, or shipping.

The renderer has two append-only products: retroactive completion cards for
the sixteen 2026-08-16 lane cards whose sole sound-law gap is now covered by
BR-GREC-02..06, and forty open-inventory completions numbered 00019..00058.
It emits bounded apply_patch patches; the old cards are never rewritten.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round6 as R6  # noqa: E402


R2 = R6.R2
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-17"
FIRST_COMPLETION = 19
LAST_COMPLETION = 58


NEW_ROUTES = {
    ("θ", "ط"): "BR-GREC-02",
    ("θ", "ت"): "BR-GREC-03",
    ("τ", "د"): "BR-GREC-04",
    ("γ", "ق"): "BR-GREC-05",
    ("π", "ف"): "BR-GREC-06",
}
R2.ROUTES.update(NEW_ROUTES)

GAP_ROWS = {
    "θ ↔ ط": "BR-GREC-02",
    "θ ↔ ت": "BR-GREC-03",
    "τ ↔ د": "BR-GREC-04",
    "γ ↔ ق": "BR-GREC-05",
    "π ↔ ف": "BR-GREC-06",
}

EXPECTED_RETRO = {
    "LANE-A-PROBE-003": ("BR-GREC-02",),
    "LANE-A-R2-031": ("BR-GREC-04",),
    "LANE-A-R2-035": ("BR-GREC-04",),
    "LANE-A-R2-043": ("BR-GREC-05",),
    "LANE-A-R2-084": ("BR-GREC-06",),
    "LANE-A-R3-103": ("BR-GREC-06",),
    "LANE-A-R3-108": ("BR-GREC-03",),
    "LANE-A-R3-128": ("BR-GREC-03",),
    "LANE-A-R3-141": ("BR-GREC-02",),
    "LANE-A-R3-142": ("BR-GREC-02",),
    "LANE-A-R4-176": ("BR-GREC-05",),
    "LANE-A-R4-177": ("BR-GREC-02",),
    "LANE-A-R4-202": ("BR-GREC-04",),
    "LANE-A-R4-209": ("BR-GREC-03", "BR-GREC-06"),
    "LANE-A-R5-313": ("BR-GREC-03",),
    "LANE-A-R6-365": ("BR-GREC-05",),
}


INVENTORY_MEMBER_IDS = [
    "kaikki_ancient_greek:38767:en-πάξ-grc-intj-pK0JvPVn",
    "kaikki_ancient_greek:44199:en-ὡρεῖον-grc-noun-atMbedSd",
    "kaikki_ancient_greek:52468:en-κοῦπα-grc-noun-LA2ku-Rh",
    "kaikki_ancient_greek:27289:en-βέκος-grc-noun-mFYEwrYC",
    "kaikki_ancient_greek:4884:en-φράζω-grc-verb-pMMD3dH6",
    "kaikki_ancient_greek:217:en-γράφω-grc-verb-pVb8IsLd",
    "kaikki_ancient_greek:292:en-μάγος-grc-adj-DOLUxwh3",
    "kaikki_ancient_greek:293:en-μάγος-grc-noun-KmMrIFlR",
    "kaikki_ancient_greek:556:en-λεγεών-grc-noun-FhTO7sUK",
    "kaikki_ancient_greek:1083:en-σάπων-grc-noun-c2vC1OCU",
    "kaikki_ancient_greek:1773:en-Καῖσαρ-grc-noun-yCwLAW1j",
    "kaikki_ancient_greek:2047:en-Ἰνδός-grc-noun-oW-aVwW5",
    "kaikki_ancient_greek:3372:en-Σούηβος-grc-noun-ex~EL9gK",
    "kaikki_ancient_greek:3479:en-ἄλβος-grc-adj-AY-pakRx",
    "kaikki_ancient_greek:4173:en-πέρνα-grc-noun-Dsz-JjZo",
    "kaikki_ancient_greek:4603:en-νάφθα-grc-noun-1UKvegq6",
    "kaikki_ancient_greek:4747:en-ἔβενος-grc-noun-XTn2t~NY",
    "kaikki_ancient_greek:4831:en-ὀπτίων-grc-noun-sFef~Hh8",
    "kaikki_ancient_greek:4915:en-κόμης-grc-noun-gs0l5WwE",
    "kaikki_ancient_greek:5172:en-σκάλα-grc-noun-VgWlFqfr",
    "kaikki_ancient_greek:5340:en-τιμόνι-grc-noun-zvkdaJu0",
    "kaikki_ancient_greek:6611:en-κόμμι-grc-noun-vEpoTpvY",
    "kaikki_ancient_greek:7515:en-λίτρα-grc-noun-UhDdFU1g",
    "kaikki_ancient_greek:8176:en-λείριον-grc-noun-qt~-A0JP",
    "kaikki_ancient_greek:8216:en-ἄρτος-grc-noun-uD6Hl7RH",
    "kaikki_ancient_greek:10482:en-ῥινός-grc-noun-U0veQ6T6",
    "kaikki_ancient_greek:10785:en-χάλυψ-grc-noun-Xc~IzMWA",
    "kaikki_ancient_greek:12685:en-σάκρα-grc-noun-KraSS3x-",
    "kaikki_ancient_greek:17457:en-ῥομφαία-grc-noun-jPhA439k",
    "kaikki_ancient_greek:18183:en-βούλλα-grc-noun-q1R3V9o3",
    "kaikki_ancient_greek:18380:en-αἰδίλης-grc-noun-EJXL98VD",
    "kaikki_ancient_greek:22072:en-σίτλα-grc-noun-fxLinubx",
    "kaikki_ancient_greek:22150:en-βατιάκη-grc-noun-ayEgpAVo",
    "kaikki_ancient_greek:22169:en-μέλκα-grc-noun-cS70R9Op",
    "kaikki_ancient_greek:22711:en-πάρμη-grc-noun-Q-w0F1dC",
    "kaikki_ancient_greek:23564:en-βῖκος-grc-noun-9pHJ0p-L",
    "kaikki_ancient_greek:23679:en-τραβέα-grc-noun-hQ1EYxXT",
    "kaikki_ancient_greek:23874:en-κάμψα-grc-noun-XIL-xIUO",
    "kaikki_ancient_greek:24157:en-ἰσίκιον-grc-noun-t~gO5O6U",
    "kaikki_ancient_greek:25210:en-μίνιον-grc-noun-H0R-tyOZ",
]

INVENTORY_ROOTS = [
    "بك", "رن", "كب", "بكس", "برز", "جرف", "مجس", "مجس", "لجن", "صبن",
    "كسر", "ندس", "سبس", "لبس", "برن", "نفط", "بنس", "بتن", "كمس", "سكل",
    "تمن", "كمم", "لتر", "لرن", "رطس", "رنش", "خلب", "سكر", "رمف", "بلل",
    "دلس", "سطل", "بتك", "ملك", "برم", "بكس", "ترب", "كمب", "سكن", "منن",
]

POSITIVE_SOURCES = {
    23: "LANE-A-R2-017",
    24: "LANE-A-R2-053",
    26: "LANE-A-R2-054",
    28: "LANE-A-R2-058",
    34: "LANE-A-PROBE-003",
    50: "LANE-A-R2-022",
}
SOURCE_GAPS = {41, 42, 47, 56}
LAW_GAPS = {19, 45}


@dataclass(frozen=True)
class SourceCard:
    card_id: str
    word: str
    read: str
    root: str
    blocker: str
    event: str
    orbit: str
    counterpart: str
    block: str


@dataclass(frozen=True)
class InventoryItem:
    family_id: str
    member_id: str
    word: str
    read: str
    pos: str
    meaning: str
    etym: str
    entries: tuple[dict, ...]
    selection_way: str
    previous_verdict: str
    source_position: int


def field(block: str, pattern: str, default: str = "") -> str:
    values = re.findall(pattern, block, re.MULTILINE)
    return " ".join(values[-1].split()) if values else default


def source_cards() -> dict[str, SourceCard]:
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<word>[^`]+)`(?P<title>[^\n]*?)؛ (?P<id>LANE-A-(?:PROBE|R[2-6])-\d+)$",
        text,
        re.MULTILINE,
    ))
    cards: dict[str, SourceCard] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        read_match = re.search(r" /([^/]+?)/", match.group("title"))
        cards[match.group("id")] = SourceCard(
            card_id=match.group("id"),
            word=match.group("word"),
            read=R2.clean(read_match.group(1)) if read_match else "",
            root=field(block, r"^- المقابل من اللسان: `([^`]+)`"),
            blocker=field(block, r"^- عائق: (.+)$"),
            event=field(block, r"^- الحدث[^:]*: (.+)$"),
            orbit=field(block, r"^- المدار: (.+)$"),
            counterpart=field(block, r"^- المقابل من اللسان: (.+)$"),
            block=block,
        )
    return cards


def retro_sources(cards: dict[str, SourceCard]) -> list[SourceCard]:
    found: dict[str, tuple[str, ...]] = {}
    for card_id, card in cards.items():
        if "LAW-GAP" not in card.block:
            continue
        rows = tuple(row for gap, row in GAP_ROWS.items() if gap in card.blocker)
        if rows:
            found[card_id] = rows
    if found != EXPECTED_RETRO:
        missing = sorted(set(EXPECTED_RETRO) - set(found))
        extra = sorted(set(found) - set(EXPECTED_RETRO))
        wrong = sorted(key for key in set(found) & set(EXPECTED_RETRO) if found[key] != EXPECTED_RETRO[key])
        raise AssertionError(f"تغير حوض الأثر الرجعي: missing={missing} extra={extra} wrong={wrong}")
    return [cards[card_id] for card_id in EXPECTED_RETRO]


def retro_card(number: int, card: SourceCard) -> tuple[str, dict]:
    rows = EXPECTED_RETRO[card.card_id]
    licensed, route, gaps = R2.sound_route(card.word, card.root)
    if not licensed or gaps:
        raise AssertionError(f"لم يكتمل صوت {card.card_id}: {gaps}")
    if any(row not in route for row in rows):
        raise AssertionError(f"غاب الصف الجديد من طريق {card.card_id}: {route}")
    completion_id = f"LANE-A-LAW-COMP-{number:05d}"
    row_text = " + ".join(rows)
    lines = [
        f"### {completion_id}: إتمام رجعي لـ`{card.card_id}`، `{card.word}` /{card.read}/ ↔ `{card.root}`",
        "",
        f"- تاريخ الإتمام: {DATE}؛ الطبقة: استكشاف؛ البطاقة القديمة محفوظة بلا تعديل.",
        f"- الخبر الناقل للقانون: دخل `{row_text}` الشبكة النافذة بملحق 2026-08-17 المأذون في `shift-network-draft.md`.",
        f"- رجل الصوت: PASS؛ المرشح `{card.root}` حاضر في المروحة، وطريقه الكامل الآن `{route}`؛ الساق التي كانت غائبة يغطيها `{row_text}`.",
        f"- رجل الحدث: PASS؛ يبقى فحص البطاقة القديمة نافذا كما كُتب: {card.event}",
        f"- رجل المعنى: PASS؛ المدار المثبت في البطاقة القديمة هو: {card.orbit} وإحالته الأخيرة إلى غياب الصف وصف للحكم القديم، لا نقض للمدار.",
        f"- شواهد العربية والفرع: الشواهد المسماة والمدخلة المعجمية في `{card.card_id}` باقية هي مادة الحكم؛ لم تُضف مقارنة دلالية جديدة.",
        "- حكم الأرجل الثلاث: الصوت PASS؛ الحدث PASS؛ المعنى PASS؛ لا شرط رابع.",
        "- حالة الإغلاق الجديدة: READY.",
        "- الحكم الجديد (استكشاف): ROOT-TRACE.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `LAW-GAP؛ غير صادر`؛ الحكم الجديد `ROOT-TRACE`؛ السبب الحاصر هو نفاذ `{row_text}` مع بقاء رجلي الحدث والمعنى المستوفتين.",
    ]
    rendered = "\n".join(lines)
    size = len((rendered + "\n").encode("utf-8"))
    if size > R2.MAX_CARD_BYTES:
        raise AssertionError(f"بطاقة الأثر الرجعي كبيرة: {completion_id} {size}")
    return rendered, {
        "completion_id": completion_id,
        "source_id": card.card_id,
        "word": card.word,
        "root": card.root,
        "rows": rows,
        "closure": "READY",
        "verdict": "ROOT-TRACE",
        "bytes": size,
        "kind": "retro",
    }


def inventory_items() -> list[InventoryItem]:
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<family>ancient_greek:family:[0-9a-f]+)`[^\n]*$",
        text,
        re.MULTILINE,
    ))
    wanted = set(INVENTORY_MEMBER_IDS)
    items: dict[str, InventoryItem] = {}
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        ids = re.findall(r"`(kaikki_ancient_greek[^`]+)`", block)
        if not ids or ids[0] not in wanted:
            continue
        member_id = ids[0]
        word_match = re.search(r":en-(.+?)-grc-", member_id)
        if not word_match:
            raise AssertionError(f"لا كلمة في معرف {member_id}")
        word = word_match.group(1)
        meaning = field(block, r"^- المعنى من قاموس الفرع: «(.+?)» \[Kaikki Ancient Greek")
        entries, how = R2.LEX.look("ancient-greek", word)
        if not entries:
            raise AssertionError(f"لا مدخلة قاموس فرع: {member_id}")
        chosen = next((entry for entry in entries if R2.clean(entry.get("id")) == member_id), None)
        if chosen is None:
            wanted_meaning = R2.clean(meaning).rstrip(".").casefold()
            chosen = next((entry for entry in entries if R2.clean(entry.get("en")).rstrip(".").casefold() == wanted_meaning), None)
        if chosen is None:
            chosen = entries[R2.BASE.select_lexicon(entries, meaning)]
        items[member_id] = InventoryItem(
            family_id=match.group("family"),
            member_id=member_id,
            word=word,
            read=R2.clean(chosen.get("read")),
            pos=R2.clean(chosen.get("pos")),
            meaning=R2.clean(chosen.get("en")),
            etym=R2.clean(chosen.get("etym")) or field(block, r"^- أقدمُ? صورةٍ? مستعادة: (.+?) \[Kaikki Ancient Greek"),
            entries=tuple(entries),
            selection_way=how,
            previous_verdict=field(block, r"^- الحكم \(استكشاف\): ([^\n]+)"),
            source_position=match.start(),
        )
    missing = [member_id for member_id in INVENTORY_MEMBER_IDS if member_id not in items]
    if missing:
        raise AssertionError(f"غابت بطاقات الجرد: {missing}")
    ordered = [items[member_id] for member_id in INVENTORY_MEMBER_IDS]
    if len(ordered) != 40 or len(set(INVENTORY_MEMBER_IDS)) != 40:
        raise AssertionError("حوض الجولة السابعة ليس أربعين عضوا فريدا")
    return ordered


def gather_hits(items: list[InventoryItem]) -> dict[str, list[dict]]:
    roots: set[str] = set(INVENTORY_ROOTS)
    for item in items:
        roots.update(root for root, _weight in R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek"))
    return R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, roots, None)


def positive_reading(number: int, cards: dict[str, SourceCard]) -> tuple[str, str, str]:
    source = cards[POSITIVE_SOURCES[number]]
    if not source.root or not source.orbit or not source.counterpart:
        raise AssertionError(f"نقصت مادة الموجب في {source.card_id}")
    return source.counterpart, source.orbit, source.card_id


def inventory_card(
    number: int,
    item: InventoryItem,
    root: str,
    hits: dict[str, list[dict]],
    cards: dict[str, SourceCard],
) -> tuple[str, dict]:
    ranked = R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek")
    candidates = [candidate for candidate, _weight in ranked]
    if not candidates or root not in candidates:
        raise AssertionError(f"مرشح {number} خارج المروحة: {item.word} {root}")
    licensed, route, gaps = R2.sound_route(item.word, root)
    event = R2.EVENT.resolve(root)
    if event is None:
        raise AssertionError(f"لا حدث مجمد لـ{number}: {root}")

    if number in POSITIVE_SOURCES:
        counterpart, orbit, source_id = positive_reading(number, cards)
        if number == 34:
            orbit = orbit.split("؛ لكن المدار", 1)[0].rstrip(".؛ ") + "."
        closure, verdict = "READY", "ROOT-TRACE"
        blocker = ""
        if not licensed:
            raise AssertionError(f"موجب بصوت غير مكتمل {number}: {gaps}")
    else:
        source_id = ""
        counterpart = f"`{root}`؛ قُرئت شواهده ولم يثبت منها معنى يطابق معنى العضو."
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 150)}» بكل معاني `{root}` وبدرجات الحدث؛ "
            "لم يثبت مدار محدود من غير تعميم أو قفزة."
        )
        if number in SOURCE_GAPS:
            closure = verdict = "SOURCE-GAP"
            blocker = (
                "- عائق: النوع=SOURCE-GAP؛ يتطلب=شاهدين عربيين مسميين لمرشح من المروحة؛ "
                "أعاد المسح الحالي صفرا لكل مرشح، فلا يصدر حكم معنى."
            )
        elif number in LAW_GAPS:
            closure = verdict = "LAW-GAP"
            blocker = "- عائق: النوع=LAW-GAP؛ يتطلب=" + "، ".join(f"صفا نافذا يرخص `{gap}`" for gap in gaps) + "."
        else:
            closure = verdict = "OPEN-CANDIDATE"
            blocker = "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=مدارا محدودا يجمع معنى العضو بمعنى عربي مقروء؛ لا يضاف شرط رابع."

    if number in LAW_GAPS and licensed:
        raise AssertionError(f"بطاقة القانون {number} صارت مرخصة بلا تحديث")
    if number not in LAW_GAPS and number not in SOURCE_GAPS and not licensed:
        raise AssertionError(f"بطاقة غير مسماة بفجوة قانون {number}: {gaps}")
    if number in SOURCE_GAPS:
        if any(hits.get(candidate) for candidate in candidates):
            raise AssertionError(f"بطاقة SOURCE-GAP لها شاهد عربي: {number}")

    route_text = route if licensed else "غير مكتمل؛ " + "، ".join(f"`{gap}`" for gap in gaps)
    skeleton = "-".join(R2.branch_skeleton(item.word))
    etym = R2.clip(item.etym, 120) if item.etym else "لم ينشر قاموس الفرع صورة أقدم؛ SOURCE-GAP في حقل الأصل وحده."
    witness_orbit = orbit if number in POSITIVE_SOURCES else ""
    witness = R2.witness_line(root, hits.get(root, []), witness_orbit)
    tiers = "/".join(str(value.tier) for value in R2.EVENT.all_tiers(root)) or "0"
    sound_summary = route if licensed else "غير مرخص " + "/".join(gaps)
    result_summary = {
        "ROOT-TRACE": "ROOT-TRACE",
        "LAW-GAP": "LAW-GAP",
        "SOURCE-GAP": "SOURCE-GAP",
        "OPEN-CANDIDATE": "لا مدار محدود",
    }[verdict]
    summary = f"`{root}`({sound_summary}؛ ح={tiers}؛ ش={len(hits.get(root, []))}؛ {result_summary})"
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    previous = item.previous_verdict
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{item.read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو الفردي `{item.member_id}`؛ الحكم السابق: {previous}",
        f"- الكلمة في الفرع: `{item.word}` /{item.read}/؛ `{item.pos}`؛ «{R2.clip(item.meaning, 125)}».",
        f"- معيار الانتخاب: هيكل `{skeleton}` ومروحة غير فارغة؛ الموضع {number} من المواصلة.",
        f"- أقدم صورة مستعادة: {etym} [Kaikki Ancient Greek].",
        f"- الخطوة صفر: حُفظت الصورة المنشورة بلا حذف غير مسند؛ الهيكل `{skeleton}`.",
        f"- درجة المقارنة: {'جذر معتل أو مضعف' if len(R2.branch_skeleton(item.word)) == 2 else 'جذر ثلاثي كامل'}؛ ودرجة الحدث أدناه.",
        f"- مسح المعاني العربية: {witness}",
        f"- المقابل من اللسان: {counterpart}",
        f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` {'مرخص كاملا' if licensed else 'معلق'} في `fan_any_script.fan('{item.word}', 'greek')`.",
        f"{event.line()}.",
        f"- المعنى من قاموس الفرع: قُرئت {len(item.entries)} مدخلة بطريق «{item.selection_way}»؛ المختارة `{item.word}` /{item.read}/ [{item.pos}] «{R2.clip(item.meaning, 145)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        "- المصفاة: المانح غير السامي لا يغلق المقارنة الأعمق؛ لا مانح سامي مباشر مسمى.",
        "- فصل المتجانسات والاقتراض: الحكم للعضو المسمى وحده.",
        f"- فحص المروحة كلها: قُرئت {len(candidates)} صورة مرتبة مع شواهدها؛ المستعمل في القرار وحده: {summary}.",
        f"- مؤشر اليتم: العضو حاضر؛ لا يدعى حصر الأسرة `{item.family_id}`.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={1 if verdict == 'ROOT-TRACE' else 0}؛ سلاسل المعنى المدعومة={1 if verdict == 'ROOT-TRACE' else 0}؛ الحد بالعضو المفحوص.",
        f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={1 if verdict == 'ROOT-TRACE' else 0}؛ سلاسل المعنى المدعومة={1 if verdict == 'ROOT-TRACE' else 0}؛ اقتصر النقل على الشواهد العاملة.",
        "- جسور الاسترداد: الجرد؛ الخطوة صفر؛ المروحة؛ الشبكة؛ الحدث؛ القاموس؛ العربية؛ الأصل؛ المدار.",
    ]
    if blocker:
        lines.append(blocker)
    lines += [
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict}.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `{previous}`؛ الحكم الجديد `{verdict}`؛ السبب: قراءة المروحة غير الفارغة كاملة، وكل مداخل الرسم، وشواهد المرشح المستعمل.",
        f"- ملاحظات: عدسة الاسترداد قرأت المرشحات؛ وعدسة التشكيك قصرت الحكم على العضو والمدار المكتوب{f'، مع إعادة استعمال قراءة {source_id} الموجبة' if source_id else ''}.",
    ]
    rendered = "\n".join(lines)
    rendered, size = R6.compact_to_limit(rendered, completion_id)
    return rendered, {
        "completion_id": completion_id,
        "family_id": item.family_id,
        "member_id": item.member_id,
        "word": item.word,
        "root": root,
        "closure": closure,
        "verdict": verdict,
        "bytes": size,
        "candidates": len(candidates),
        "kind": "inventory",
    }


def render_all() -> tuple[list[str], list[dict], list[str], list[dict]]:
    cards = source_cards()
    retro_rendered: list[str] = []
    retro_records: list[dict] = []
    for number, source in enumerate(retro_sources(cards), 1):
        rendered, record = retro_card(number, source)
        retro_rendered.append(rendered)
        retro_records.append(record)

    items = inventory_items()
    hits = gather_hits(items)
    inventory_rendered: list[str] = []
    inventory_records: list[dict] = []
    for number, (item, root) in enumerate(zip(items, INVENTORY_ROOTS), FIRST_COMPLETION):
        rendered, record = inventory_card(number, item, root, hits, cards)
        inventory_rendered.append(rendered)
        inventory_records.append(record)

    if len(retro_records) != 16 or len(inventory_records) != 40:
        raise AssertionError("عدد الجولة السابعة غير صحيح")
    if [record["completion_id"] for record in inventory_records] != [
        f"LANE-A-OPEN-COMP-{number:05d}" for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]:
        raise AssertionError("معرفات الجرد غير متصلة")
    return retro_rendered, retro_records, inventory_rendered, inventory_records


def reading_fragment(kind: str, start: int, count: int) -> str:
    retro, _retro_records, inventory, _inventory_records = render_all()
    if kind == "retro":
        cards = retro
        first, last = 1, 16
        heading = [
            "<!-- LANE-A-GREEK-ROUND7-RETRO:START -->",
            "",
            "## اليونانية، الجولة السابعة: الأثر الرجعي لملحق الصفوف الخمسة (2026-08-17)",
            "",
            "- هذه بطاقات إتمام ناسخة للحكم فقط؛ بطاقات `LANE-A-PROBE/R2/R3/R4/R5/R6` القديمة محفوظة بلا تعديل.",
            "- دخلت الصفوف `BR-GREC-02` إلى `BR-GREC-06` وحدها؛ ولم يدخل `χ↔ك` ولا `θ↔ث` ولا `ψ↔ب` ولا `ξ↔ك`.",
            "",
        ]
        ending = ["", "<!-- LANE-A-GREEK-ROUND7-RETRO:END -->"]
    elif kind == "inventory":
        cards = inventory
        first, last = FIRST_COMPLETION, LAST_COMPLETION
        heading = [
            "<!-- LANE-A-GREEK-ROUND7-INVENTORY:START -->",
            "",
            "## اليونانية، الجولة السابعة: مواصلة إتمام الجرد المفتوح (2026-08-17)",
            "",
            "- المواصلة متصلة من `LANE-A-OPEN-COMP-00019`، مرتبة بطول الهيكل ثم موضع بطاقة الجرد الأصلي، مع استبعاد الأعضاء الثمانية عشر المكتملة في الجولة السادسة.",
            "",
        ]
        ending = ["", "<!-- LANE-A-GREEK-ROUND7-INVENTORY:END -->"]
    else:
        raise AssertionError("نوع قطعة القراءة غير صحيح")
    if start < first or start + count - 1 > last or count < 1:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    offset = start - first
    selected = cards[offset:offset + count]
    lines: list[str] = []
    if start == first:
        lines += heading
    for card in selected:
        lines += [card, ""]
    if start + count - 1 == last:
        lines += ending
    return "\n".join(lines).rstrip()


def report_fragment() -> str:
    _retro, retro_records, _inventory, inventory_records = render_all()
    inventory_counts = Counter(record["closure"] for record in inventory_records)
    row_counts = Counter(row for record in retro_records for row in record["rows"])
    maximum = max(retro_records + inventory_records, key=lambda record: record["bytes"])
    lines = [
        "<!-- LANE-A-GREEK-ROUND7-REPORT:START -->",
        "",
        "## 2026-08-17، الجولة السابعة، دفعة الأثر الرجعي",
        "",
        "- البطاقات: 16 بطاقة إتمام رجعي؛ القديم محفوظ بلا تعديل.",
        "- التوزيع بحسب الصف الجديد: " + "؛ ".join(f"`{row}`={count}" for row, count in sorted(row_counts.items())) + ".",
        "- حكم الأرجل الثلاث: 16 بطاقة `PASS/PASS/PASS`؛ الإغلاق `READY`=16؛ الحكم `ROOT-TRACE`=16.",
        "- البطاقة ذات الصفين: `LANE-A-R4-209` أتمها `BR-GREC-03 + BR-GREC-06`؛ لم يجزها أحدهما منفردا.",
        "- الحراسة السلبية: بطاقات `χ↔ك` و`θ↔ث` و`ψ↔ب` و`ξ↔ك` السابقة لم تُنسخ ولم تدخل هذه الدفعة.",
        "",
        "## 2026-08-17، الجولة السابعة، دفعة مواصلة الجرد",
        "",
        "- البطاقات: 40؛ المدى: `LANE-A-OPEN-COMP-00019` إلى `LANE-A-OPEN-COMP-00058`.",
        "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(inventory_counts.items())) + ".",
        "- الموجب المحتسب: 6 `ROOT-TRACE`؛ المفتوح أو المعلق: 34.",
        "- الأزواج الموجبة: `φράζω↔برز`؛ `γράφω↔جرف`؛ `μάγος↔مجس`؛ `σάπων↔صبن`؛ `νάφθα↔نفط`؛ `σίτλα↔سطل`.",
        "- فجوات القانون في المواصلة: `ξ↔ك` في `πάξ` و`ψ↔ب` في `χάλυψ`؛ بقيتا `LAW-GAP` بلا اختراع صف، وبقي `ψ↔ب` أيضا غير موقع في بطاقة `κάμψα` ذات الإغلاق الأولي `SOURCE-GAP`.",
        "- فجوات المصدر العربية: `λίτρα` و`λείριον` و`ῥομφαία` و`κάμψα`؛ المروحة غير فارغة لكن البحث أعاد صفرا لشواهد جذورها.",
        "- ضبط الجرد: 40 معرف عضو فريدًا؛ لا تكرار مع `00001–00018`؛ كل بطاقة تسمي الأسرة والعضو والحكم السابق والجديد.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: 27 ملاحظة، منها 24 موروثة من المادة السابقة وثلاث `D4-DIRECTION` جديدة في `00026` و`00034` و`00050`؛ روجعت وأبقيت بموجب إعادة فتح 2026-08-05 للقرض ذي المانح غير السامي، فلا يصير خبر الأصل شرطًا رابعًا.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        "",
        "## حصيلة الجولة السابعة",
        "",
        "- مجموع البطاقات المكتوبة: 56؛ منها 16 إتمام قانون رجعي و40 إتمام جرد مفتوح.",
        "- النتائج الموجبة: 22 `ROOT-TRACE`؛ منها 16 من نفاذ الصفوف الخمسة و6 من مواصلة الجرد.",
        "- آخر موضع: `LANE-A-OPEN-COMP-00058`، `μίνιον` /mĭ́nĭon/.",
        "",
        "<!-- LANE-A-GREEK-ROUND7-REPORT:END -->",
        "",
        "LANE-A DONE7 56 LANE-A-OPEN-COMP-00058",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def emit_append_patch(path: Path, fragment: str, marker: str) -> str:
    current = path.read_text(encoding="utf-8")
    if marker in current:
        raise AssertionError(f"الموضع موجود: {marker}")
    tail = current.rstrip().splitlines()[-12:]
    relative = path.relative_to(ROOT).as_posix()
    patch = [
        "*** Begin Patch",
        f"*** Update File: {relative}",
        "@@",
        *(" " + line for line in tail),
        "+",
        add_lines(fragment),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reading-kind", choices=("retro", "inventory"))
    parser.add_argument("--start", type=int)
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--records", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.report:
        print(emit_append_patch(REPORT, report_fragment(), "LANE-A DONE7"), end="")
    elif args.reading_kind:
        if args.start is None:
            raise AssertionError("يلزم --start")
        fragment = reading_fragment(args.reading_kind, args.start, args.count)
        if args.reading_kind == "retro":
            marker = f"LANE-A-LAW-COMP-{args.start:05d}"
        else:
            marker = f"LANE-A-OPEN-COMP-{args.start:05d}"
        print(emit_append_patch(READING, fragment, marker), end="")
    else:
        _r, rr, _i, ir = render_all()
        print(f"retro={len(rr)} inventory={len(ir)} max={max(row['bytes'] for row in rr + ir)}")
        print(Counter(row["closure"] for row in rr + ir))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
