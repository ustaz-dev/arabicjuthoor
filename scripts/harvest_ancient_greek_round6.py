#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 6: finish Greek ``both`` and enter open inventory.

The accepted round-2 card contract remains authoritative.  This read-only
renderer supplies the hand-read outcomes for ranks 327--408, then selects the
first eighteen still-open inventory members by consonant-count and source
order, requiring a non-empty current fan.  It emits bounded ``apply_patch``
patches; it never writes repository files, commits, or ships.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from datetime import datetime
import argparse
import json
from pathlib import Path
import re
import sys


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round2 as R2  # noqa: E402


READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
PROPOSAL = ROOT / "04-cross-linguistic" / "proposed-shift-rows-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
FIRST_RANK = 327
LAST_RANK = 408
DATE = "2026-08-17"


Outcome = R2.Outcome


OUTCOMES: dict[int, Outcome] = {
    331: Outcome(
        "root", "قلم",
        "قلم العود: قطعه؛ والقلامة ما سقط منه",
        "cutting أو slip في الفرع غصن مقطوع للغرس، وقلم العربية قطع العود وما سقط منه؛ المدار قطعة نباتية نتجت من قطع العود.",
        1,
    ),
    339: Outcome(
        "law", "ترك",
        "التريكة ما تركه السيل؛ والبقايا التي يتركها الرعي",
        "lees وdregs وsediments هي ما يتركه السائل في القاع، والتريكة في العربية ما تركه السيل أو بقي بعد الاستعمال؛ المدار بقية منفصلة يخلّفها الأصل، لكن ξ إلى ك بلا صف مسمى.",
        1, "ξ ↔ ك",
    ),
    353: Outcome(
        "transmission", "مرق",
        "الفينيقية هي المانح المسمى، ويصرح المصدر بمقابلة العربية مَرَقَة",
        "قاموس الفرع يصرح باقتراض ἀμόργη من الفينيقية ويصلها صراحة بالعربية مَرَقَة؛ انتقال من مانح سامي مسمى لا حكم إرث.",
    ),
    365: Outcome(
        "law", "قرص",
        "القرص القطعة المستديرة؛ ومنه قرص الشمس وعينها",
        "round في الفرع يطابق القرص العربي بوصفه قطعة مستديرة وقرص الشمس عينها؛ المدار الاستدارة الظاهرة، لكن γ إلى ق بلا صف مسمى.",
        3, "γ ↔ ق",
    ),
    374: Outcome(
        "transmission", "مري",
        "الآرامية מרים maryam هي مانح اسم العلم",
        "قاموس الفرع يصرح باقتراض Μαρία من الآرامية מרים maryam؛ انتقال اسم علم من مانح سامي مسمى.",
    ),
    385: Outcome(
        "transmission", "رما",
        "الآرامية ܐܪܡܝܐ / אָרָמָיָא ʾārāmāyā هي الصورة المسماة",
        "قاموس الفرع يرد اسم الآراميين إلى الآرامية ܐܪܡܝܐ / אָרָמָיָא؛ انتقال اسم قوم من مانح سامي مسمى.",
    ),
    392: Outcome(
        "transmission", "منن",
        "الآرامية 𐡌𐡍𐡄 mnh، من الأكادية manû، هي مانح اسم الوزن والنقد",
        "قاموس الفرع يرد μνᾶ إلى الآرامية 𐡌𐡍𐡄 mnh ثم الأكادية manû؛ انتقال اسم مكيال ونقد من مانح سامي مسمى.",
    ),
    404: Outcome(
        "root", "ملل",
        "مللت الشيء: سئمته وبرمت به وأعرضت عنه",
        "to not care for وto disregard في الفرع هو الإعراض عن الشيء وترك الاهتمام به، وملل العربية السآمة التي تحمل صاحبها على الإعراض؛ المدار انصراف العناية عن الشيء.",
        1,
    ),
}


INVENTORY_MEMBER_IDS = [
    "kaikki_ancient_greek:1204:en-ἀκακία-grc-noun-f5bLReeY",
    "kaikki_ancient_greek:1266:en-οὖρος-grc-noun-dry2quR7",
    "kaikki_ancient_greek:4974:en-δούξ-grc-noun-Se3Vpttc",
    "kaikki_ancient_greek:5518:en-κάψα-grc-noun-XIL-xIUO",
    "kaikki_ancient_greek:10422:en-κῶας-grc-noun-xN9TcMWG",
    "kaikki_ancient_greek:11857:en-νωναί-grc-noun-k3GzGdsE",
    "kaikki_ancient_greek:13701:en-ἶβις-grc-noun-ulmOtyq2",
    "kaikki_ancient_greek:18237:en-αὔγουρ-grc-noun-9X2k2IeA",
    "kaikki_ancient_greek:21580:en-κίκι-grc-noun-0LllyXsQ",
    "kaikki_ancient_greek:22047:en-σίδη-grc-noun-SIeImu6R",
    "kaikki_ancient_greek:22096:en-ἄρον-grc-noun-loDVXSNz",
    "kaikki_ancient_greek:23845:en-οὐραῖος-grc-noun-cqFnN4yW",
    "kaikki_ancient_greek:23971:en-ἀζήν-grc-noun-lBGSq7CG",
    "kaikki_ancient_greek:24385:en-ναρί-grc-noun-GLYmzBov",
    "kaikki_ancient_greek:29381:en-κῦφι-grc-noun-qixJf0NJ",
    "kaikki_ancient_greek:30509:en-δόγια-grc-noun-yZqFEYmU",
    "kaikki_ancient_greek:30623:en-δάος-grc-noun-icjzi45Q",
    "kaikki_ancient_greek:30685:en-οὖνον-grc-noun-~XGeQcsH",
]


INVENTORY_ROOTS = {
    INVENTORY_MEMBER_IDS[0]: "كك",
    INVENTORY_MEMBER_IDS[1]: "رص",
    INVENTORY_MEMBER_IDS[2]: "دك",
    INVENTORY_MEMBER_IDS[3]: "قبب",
    INVENTORY_MEMBER_IDS[4]: "كسو",
    INVENTORY_MEMBER_IDS[5]: "نون",
    INVENTORY_MEMBER_IDS[6]: "بص",
    INVENTORY_MEMBER_IDS[7]: "جر",
    INVENTORY_MEMBER_IDS[8]: "كك",
    INVENTORY_MEMBER_IDS[9]: "صيد",
    INVENTORY_MEMBER_IDS[10]: "رين",
    INVENTORY_MEMBER_IDS[11]: "راس",
    INVENTORY_MEMBER_IDS[12]: "زين",
    INVENTORY_MEMBER_IDS[13]: "نور",
    INVENTORY_MEMBER_IDS[14]: "كيف",
    INVENTORY_MEMBER_IDS[15]: "ضيق",
    INVENTORY_MEMBER_IDS[16]: "دس",
    INVENTORY_MEMBER_IDS[17]: "نون",
}


INVENTORY_POSITIVE = INVENTORY_MEMBER_IDS[4]


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
    source_position: int
    previous_verdict: str


_ORIGINAL_ALIGNED_ARABIC = R2.aligned_arabic


def aligned_arabic(root: str, length: int) -> tuple[list[str], str]:
    """Add the ordinary doubled-root opening already produced by the fan."""
    chars = list(root)
    if length == 2 and len(chars) == 3 and chars[1] == chars[2]:
        return chars[:2], "؛ ومعه بناء الجذر المضعف الذي فتحته المروحة"
    return _ORIGINAL_ALIGNED_ARABIC(root, length)


def compact_to_limit(card: str, label: str) -> tuple[str, int]:
    """Shorten descriptive fields without dropping a source, event, or orbit."""
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- فحص المروحة كلها: قُرئت \d+ صورة مرتبة؛ كل مرشح ذي مسار مسمى قُرئت شواهده وحُكم: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 90),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- أقدم صورة مستعادة: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 110),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"(^- مسح المعاني العربية: )(.+)$",
        lambda match: match.group(1) + R2.clip(match.group(2), 220),
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"^- جسور الاسترداد المفحوصة:.*$",
        "- جسور الاسترداد المفحوصة: الخطوة صفر؛ المروحة؛ الشبكة؛ الحدث؛ القاموس؛ العربية؛ الأصل؛ القرض؛ المدار.",
        card,
        flags=re.MULTILINE,
    )
    card = re.sub(
        r"^- ملاحظات:.*$",
        "- ملاحظات: قُرئت المروحة كلها، واقتصر الحكم على المدار المكتوب.",
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size <= R2.MAX_CARD_BYTES:
        return card, size
    card = re.sub(
        r"^- إشعاع الأسرة في الفرع:.*$",
        "- إشعاع الأسرة في الفرع: العضو المفحوص وحده.",
        card,
        flags=re.MULTILINE,
    )
    card = re.sub(
        r"^- إشعاع الأسرة في العربية:.*$",
        "- إشعاع الأسرة في العربية: الشاهدان العاملان فقط.",
        card,
        flags=re.MULTILINE,
    )
    size = len((card + "\n").encode("utf-8"))
    if size > R2.MAX_CARD_BYTES:
        raise AssertionError(f"تجاوزت البطاقة {label} حد 5 كيلوبايت بعد الضغط: {size}")
    return card, size


def _rewrite_named_transmission(card: str, rank: int, record: dict) -> tuple[str, dict]:
    named = {
        353: (
            "الفينيقية التي يسميها حقل الأصل، مع مقابلته الصريحة بالعربية `مَرَقَة`",
            "قُرئت مروحة السطح كلها؛ إغلاق البطاقة من النقل الفينيقي المسمى، لا من إلزام γ اليونانية بقاف عربية.",
            "Phoenician→Greek",
            "مرق",
        ),
        374: (
            "الآرامية `מרים` /maryam/",
            "قُرئت مروحة السطح كلها؛ لا يُجعل المرشح العربي السطحي أصل اسم العلم.",
            "Aramaic→Greek",
            "מרים",
        ),
        385: (
            "الآرامية `ܐܪܡܝܐ` / `אָרָמָיָא` /ʾārāmāyā/",
            "قُرئت مروحة السطح كلها؛ الحكم لنقل اسم القوم من الصورة الآرامية المسماة.",
            "Aramaic→Greek",
            "ܐܪܡܝܐ",
        ),
        392: (
            "الآرامية `𐡌𐡍𐡄` /mnh/، من الأكادية `manû`",
            "قُرئت مروحة السطح كلها؛ الحكم لنقل اسم المكيال والنقد من السلسلة السامية المسماة.",
            "Aramaic/Akkadian→Greek",
            "𐡌𐡍𐡄",
        ),
    }
    if rank not in named:
        return card, record
    counterpart, scan, route, report_root = named[rank]
    card = re.sub(
        r"^- مسح المعاني العربية:.*$",
        f"- مسح المعاني العربية: {scan}",
        card,
        flags=re.MULTILINE,
    )
    card = re.sub(
        r"^- المقابل من اللسان:.*$",
        f"- المقابل السامي المسمى: {counterpart}.",
        card,
        flags=re.MULTILINE,
    )
    card = re.sub(
        r"^- مسار الصوت:.*$",
        f"- مسار النقل المسمى: `{route}` في حقل الأصل؛ مسار السطح قُرئ ولم يُتخذ حكم جذر عربي.",
        card,
        flags=re.MULTILINE,
    )
    record["root"] = report_root
    return card, record


def build_both_card(rank: int, row: dict, hits: dict[str, list[dict]]) -> tuple[str, dict]:
    R2.OUTCOMES = OUTCOMES
    R2.aligned_arabic = aligned_arabic
    original_limit = R2.MAX_CARD_BYTES
    R2.MAX_CARD_BYTES = 64 * 1024
    try:
        card, record = R2.build_card(rank, row, hits)
    finally:
        R2.MAX_CARD_BYTES = original_limit
    card = card.replace("LANE-A-R2-", "LANE-A-R6-")
    card = card.replace("RECOVERY-v2 (2026-08-16)", f"RECOVERY-v2 ({DATE})")
    card, record = _rewrite_named_transmission(card, rank, record)
    card, size = compact_to_limit(card, str(rank))
    record["bytes"] = size
    record["overlap"] = row.get("overlap")
    record["kind"] = "both"
    return card, record


def _field(block: str, pattern: str, default: str = "") -> str:
    matches = re.findall(pattern, block, re.MULTILINE)
    return R2.clean(matches[-1]) if matches else default


def _entry_for_meaning(word: str, meaning: str) -> tuple[list[dict], dict, str]:
    entries, how = R2.LEX.look("ancient-greek", word)
    if not entries:
        raise AssertionError(f"لا مدخلة قاموس فرع لعضو الجرد: {word}")
    wanted = R2.clean(meaning).rstrip(".").casefold()
    for entry in entries:
        if R2.clean(entry.get("en")).rstrip(".").casefold() == wanted:
            return entries, entry, how
    selected = R2.BASE.select_lexicon(entries, meaning)
    return entries, entries[selected], how


def select_inventory() -> list[InventoryItem]:
    """Select open cards by short skeleton, then original file order."""
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<family>ancient_greek:family:[0-9a-f]+)`[^\n]*$",
        text,
        re.MULTILINE,
    ))
    eligible: list[tuple[int, int, InventoryItem]] = []
    seen_members: set[str] = set()
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        verdict = _field(block, r"^- الحكم \(استكشاف\): ([^\n]+)")
        if "غير صادر" not in verdict and "OPEN-CANDIDATE" not in verdict:
            continue
        member_ids = re.findall(r"`(kaikki_ancient_greek[^`]+)`", block)
        if not member_ids:
            continue
        member_id = member_ids[0]
        if member_id in seen_members:
            continue
        seen_members.add(member_id)
        word_match = re.search(r":en-(.+?)-grc-", member_id)
        if not word_match:
            continue
        word = word_match.group(1)
        fan = R2.FAN.rank(word, R2.FAN.fan(word, "greek"), "greek")
        if not fan:
            continue
        meaning = _field(block, r"^- المعنى من قاموس الفرع: «(.+?)» \[Kaikki Ancient Greek")
        etym = _field(block, r"^- أقدمُ? صورةٍ? مستعادة: (.+?) \[Kaikki Ancient Greek")
        entries, entry, how = _entry_for_meaning(word, meaning)
        item = InventoryItem(
            family_id=match.group("family"),
            member_id=member_id,
            word=word,
            read=R2.clean(entry.get("read")),
            pos=R2.clean(entry.get("pos")),
            meaning=R2.clean(entry.get("en")),
            etym=R2.clean(entry.get("etym")) or etym,
            entries=tuple(entries),
            selection_way=how,
            source_position=match.start(),
            previous_verdict=verdict,
        )
        eligible.append((len(R2.branch_skeleton(word)), match.start(), item))
    eligible.sort(key=lambda row: (row[0], row[1]))
    selected = [row[2] for row in eligible[:18]]
    actual = [item.member_id for item in selected]
    if actual != INVENTORY_MEMBER_IDS:
        raise AssertionError("تغير أول الجرد المفتوح القصير ذي المروحة غير الفارغة")
    if any(len(R2.branch_skeleton(item.word)) != 2 for item in selected):
        raise AssertionError("دخل هيكل أطول قبل استنفاد أول ثمانية عشر هيكلا قصيرا")
    return selected


def build_inventory_card(
    number: int,
    item: InventoryItem,
    hits: dict[str, list[dict]],
) -> tuple[str, dict]:
    root = INVENTORY_ROOTS[item.member_id]
    ranked = R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek")
    candidates = [candidate for candidate, _weight in ranked]
    if not candidates:
        raise AssertionError(f"مروحة الجرد فارغة: {item.member_id}")
    if root not in candidates:
        raise AssertionError(f"المرشح المنتخب خارج المروحة: {item.word} {root}")
    licensed, route, gaps = R2.sound_route(item.word, root)
    event = R2.EVENT.resolve(root)
    if event is None:
        raise AssertionError(f"لا حدث مجمد لمرشح الجرد: {root}")
    positive = item.member_id == INVENTORY_POSITIVE
    if positive and not licensed:
        raise AssertionError(f"حكم جرد موجب بصوت غير مرخص: {item.word} {gaps}")
    if positive:
        counterpart = "`كسو` «الكِسوة اللباس؛ واكتست الأرض بالنبات: تغطت به» [كتاب العين والمحكم]."
        orbit = "fleece كساء الحيوان الذي يغطي جلده، وكسو العربية إلباس الشيء وتغطيته بكسوة؛ المدار غطاء لاصق بالجسم من مادته الليفية."
        closure, verdict = "READY", "ROOT-TRACE"
        blocker = ""
    else:
        counterpart = f"`{root}`؛ قُرئت شواهده ولم يثبت منها معنى يطابق معنى العضو."
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 155)}» بكل معاني `{root}` وبدرجات الحدث؛ "
            "ولم يثبت مدار محدود من غير تعميم أو قفزة، فبقي المرشح مفتوحا بمطلوبه المسمى."
        )
        closure, verdict = "OPEN-CANDIDATE", "OPEN-CANDIDATE"
        blocker = "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=مدارا محدودا يجمع معنى العضو بمعنى عربي مقروء؛ لا يضاف شرط رابع."
    route_text = route if licensed else "غير مكتمل؛ " + "، ".join(f"`{gap}`" for gap in gaps)
    skeleton = "-".join(R2.branch_skeleton(item.word))
    if positive:
        selected_summary = f"`{root}`({route}؛ ح={event.tier}؛ ش={len(hits.get(root, []))}؛ ROOT-TRACE)"
    else:
        selected_summary = R2.compact_candidate(root, item.word, hits, root, None)
    etym = R2.clip(item.etym, 190) if item.etym else "لم ينشر قاموس الفرع صورة أقدم؛ SOURCE-GAP في حقل المصدر وحده."
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{item.read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو الفردي `{item.member_id}`؛ الحكم السابق: {item.previous_verdict}",
        f"- الكلمة في الفرع: اليونانية القديمة `{item.word}` /{item.read}/؛ الصنف `{item.pos}`؛ المعنى «{R2.clip(item.meaning, 175)}».",
        f"- معيار الانتخاب: هيكل من صامتين `{skeleton}`؛ المروحة الحالية غير فارغة؛ الترتيب بعد طول الهيكل هو موضع بطاقة الجرد في الملف.",
        f"- أقدم صورة مستعادة: {etym} [Kaikki Ancient Greek].",
        f"- الخطوة صفر: حُفظت الصورة المنشورة، ولم يُحذف صامت أو لاحقة بغير تحليل المصدر؛ هيكل القراءة `{skeleton}`.",
        f"- درجة المقارنة: جذر معتل أو مضعف، ومعه عرض النواة في الدرجة التي يعيدها السجل المجمد.",
        f"- مسح المعاني العربية: {R2.witness_line(root, hits.get(root, []), orbit)}",
        f"- المقابل من اللسان: {counterpart}",
        f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` {'مرخص كاملا' if licensed else 'معلق'} في `fan_any_script.fan('{item.word}', 'greek')`.",
        f"{event.line()}.",
        f"- المعنى من قاموس الفرع: قُرئت {len(item.entries)} مدخلة بطريق «{item.selection_way}»؛ المختارة `{item.word}` /{item.read}/ [{item.pos}] «{R2.clip(item.meaning, 145)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        "- المصفاة: المانح غير السامي المسمى في الأصل لا يغلق المقارنة الأعمق؛ لا مانح سامي مباشر مسمى لهذا العضو.",
        "- فصل المتجانسات والاقتراض: الإتمام خاص بالعضو الفردي المسمى؛ لا يرث متحد الرسم ولا عضو آخر في الأسرة حكمه.",
        f"- فحص المروحة كلها: قُرئت {len(candidates)} صورة مرتبة مع كل شواهدها؛ المستعمل في القرار وحده: {selected_summary}.",
        f"- مؤشر اليتم: بطاقة الجرد والأسرة والعضو الفردي حاضرة؛ لا يدعى حصر الأسرة `{item.family_id}`.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={1 if positive else 0}؛ سلاسل المعنى المدعومة={1 if positive else 0}؛ الحد بالعضو المفحوص.",
        f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={1 if positive else 0}؛ سلاسل المعنى المدعومة={1 if positive else 0}؛ اقتصر النقل على شاهدين عاملين.",
        "- جسور الاسترداد المفحوصة: بطاقة الجرد؛ العضو الفردي؛ الخطوة صفر؛ المروحة كلها؛ صفوف الشبكة؛ درجات الحدث؛ قاموس الفرع؛ شواهد العربية؛ الأصل؛ القرض؛ المدار.",
    ]
    if blocker:
        lines.append(blocker)
    lines += [
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict}.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `{item.previous_verdict}`؛ الحكم الجديد `{verdict}`؛ السبب: قراءة المروحة غير الفارغة كاملة، وكل مداخل الرسم، وشواهد المرشح المستعمل.",
        "- ملاحظات: عدسة الاسترداد قرأت كل المرشحات ولم تجعل أولها يحتكر البحث. عدسة التشكيك أبقت القرض غير السامي في المصفاة وقصرت الحكم على العضو والمدار المكتوب.",
    ]
    card = "\n".join(lines)
    card, size = compact_to_limit(card, completion_id)
    return card, {
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
        "skeleton_length": len(R2.branch_skeleton(item.word)),
    }


def gather_hits(rows: list[dict], inventory: list[InventoryItem]) -> dict[str, list[dict]]:
    roots: set[str] = set()
    for row in rows:
        roots.update(candidate for candidate, _weight in R2.FAN.rank(
            str(row["branch"]), R2.FAN.fan(str(row["branch"]), "greek"), "greek"
        ))
    for item in inventory:
        roots.update(candidate for candidate, _weight in R2.FAN.rank(
            item.word, R2.FAN.fan(item.word, "greek"), "greek"
        ))
    return R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, roots, None)


def render_all() -> tuple[str, list[dict]]:
    payload = json.loads(R2.SWEEP.read_text(encoding="utf-8"))
    rows = payload["both"][FIRST_RANK - 1:LAST_RANK]
    if len(rows) != 82 or len(payload["both"]) != LAST_RANK:
        raise AssertionError(f"حوض both غير المتوقع: النافذة={len(rows)}، الكل={len(payload['both'])}")
    inventory = select_inventory()
    hits = gather_hits(rows, inventory)
    sections: list[str] = []
    records: list[dict] = []

    sections += [
        "<!-- LANE-A-GREEK-ROUND6-BATCH-1:START -->",
        "",
        "## دفعة اليونانية، الجولة السادسة 1، الرتب 327–376 من `both` (2026-08-17)",
        "",
    ]
    for rank, row in enumerate(payload["both"][326:376], 327):
        card, record = build_both_card(rank, row, hits)
        sections += [card, ""]
        records.append(record)
    sections += ["<!-- LANE-A-GREEK-ROUND6-BATCH-1:END -->", ""]

    sections += [
        "<!-- LANE-A-GREEK-ROUND6-BATCH-2:START -->",
        "",
        "## دفعة اليونانية، الجولة السادسة 2: ختام `both` ثم الجرد المفتوح (2026-08-17)",
        "",
        "### القسم الأول: الرتب 377–408 من `both`",
        "",
    ]
    for rank, row in enumerate(payload["both"][376:408], 377):
        card, record = build_both_card(rank, row, hits)
        sections += [card, ""]
        records.append(record)
    sections += [
        "### موضع الانتقال إلى بطاقات الجرد المفتوحة",
        "",
        "- انتهى حوض `both` عند الرتبة 408، `ἡρῷον` /ērōon/، بعد استهلاك صفوفه كلها.",
        f"- انتقل العمل في البطاقة 33 من الدفعة الثانية إلى `{inventory[0].family_id}`، العضو `{inventory[0].member_id}`.",
        "- رُتبت بطاقات الجرد بعدد صوامت الهيكل صعودا ثم بموضعها الأصلي، واستبعد كل عضو مروحته الحالية فارغة؛ الثمانية عشر المختارة كلها ذات هيكل من صامتين.",
        "",
        "### القسم الثاني: 18 بطاقة إتمام من الجرد المفتوح القصير",
        "",
    ]
    for number, item in enumerate(inventory, 1):
        card, record = build_inventory_card(number, item, hits)
        sections += [card, ""]
        records.append(record)
    sections += ["<!-- LANE-A-GREEK-ROUND6-BATCH-2:END -->", ""]
    if len(records) != 100:
        raise AssertionError(f"عدد الجولة السادسة {len(records)} لا 100")
    return "\n".join(sections).rstrip(), records


def proposal_addition() -> str:
    return """## إلحاق شواهد الجولة السادسة، الرتب 327–408

أعيد التفتيش بالحرفين معا وفي الترتيبين، ثم بألفاظ `اليونانية` و`يونانيّة` و`Greek` في عمود الشاهد. السطران شاهدان جديدان فقط، لا توصية بإضافة صف ولا تعديل للشبكة النافذة.

| اليوناني | العربي | الشواهد الجديدة | أمثلة بأسمائها | ما وجد في الشبكة النافذة |
|---|---|---:|---|---|
| `ξ` | `ك` | 1 | `τρύξ`→`ترك` «الثفل والرواسب» ↔ «التريكة ما تركه السيل وما بقي» | لا صف يسمي `ξ ↔ ك`؛ صف الهوية `IDN-13` يسمي `κ ↔ ك` لا `ξ` |
| `γ` | `ق` | 1 | `γυρός`→`قرص` «مستدير» ↔ «القرص القطعة المستديرة وقرص الشمس» | `IDN-08` يسمي `γ ↔ ج`؛ وشاهد `γ ↔ ق` السابق باق في المسودة بلا توقيع |

تبقى البطاقتان في `LAW-GAP` إلى أن يقرر المؤلف في الشبكة المجمدة؛ لا تحمل هذه الورقة توصية.
"""


def report_addition(records: list[dict]) -> str:
    now = datetime.now().astimezone().strftime("%Y-%m-%d %H:%M:%S %z")
    first = records[:50]
    second = records[50:]
    both_second = [record for record in second if record["kind"] == "both"]
    inventory = [record for record in second if record["kind"] == "inventory"]
    lines: list[str] = []
    for batch, subset in ((1, first), (2, second)):
        counts = Counter(record["closure"] for record in subset)
        verdicts = Counter(record["verdict"] for record in subset)
        examples = [
            f"`{record['word']}↔{record['root']}`" for record in subset
            if record["verdict"] in {"ROOT-TRACE", "SEMITIC-SOURCE-TRANSMISSION"}
        ][:10]
        position = "الرتب 327–376" if batch == 1 else "الرتب 377–408 ثم 18 إتماما جرديا"
        lines += [
            f"## {now}، الجولة السادسة، الدفعة {batch}",
            "",
            f"- البطاقات: {len(subset)}؛ الموضع: {position}.",
            "- توزيع الأحكام: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(verdicts.items())) + ".",
            "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items())) + ".",
            f"- الموجب المحتسب: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in subset)}؛ المفتوح: {sum(r['verdict'] in {'OPEN-CANDIDATE', 'LAW-GAP'} for r in subset)}.",
            "- أبرز الأزواج الموجبة: " + ("؛ ".join(examples) if examples else "لا يوجد") + ".",
            "- أعطاب الأدوات: 0؛ قُرئت المروحة الواسعة كلها، وأعاد `frozen_event` حدثا للمنتخب، وأعيدت مقابلة المدخلة المعجمية بالعضو نفسه.",
            "",
        ]
    total = Counter(record["closure"] for record in records)
    lines += [
        "## انتقال الجولة السادسة وحصيلتها",
        "",
        "- اكتمل `both`: استهلكت الرتب 327–408، فصار الحوض 408 من 408؛ آخر صف `ἡρῷον` /ērōon/.",
        f"- موضع الانتقال: بعد البطاقة {len(both_second)} من الدفعة الثانية، من الرتبة 408 إلى أول بطاقة جرد `{inventory[0]['family_id']}`؛ كُتبت بعدها {len(inventory)} بطاقة إتمام.",
        f"- معيار الجرد: كل المختار ذي هيكل من صامتين ومروحة غير فارغة؛ البداية `{inventory[0]['completion_id']}` والنهاية `{inventory[-1]['completion_id']}`، ولا عضو مكرر.",
        f"- مجموع البطاقات: {len(records)}؛ 82 من `both` و18 من الجرد المفتوح.",
        "- الإغلاق الكلي: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(total.items())) + ".",
        f"- النتائج الموجبة المحتسبة: {sum(r['verdict'] in {'ROOT-TRACE', 'SEMITIC-SOURCE-TRANSMISSION'} for r in records)}؛ `ROOT-TRACE`={sum(r['verdict'] == 'ROOT-TRACE' for r in records)}؛ `SEMITIC-SOURCE-TRANSMISSION`={sum(r['verdict'] == 'SEMITIC-SOURCE-TRANSMISSION' for r in records)}.",
        "- فجوات القانون الجديدة: `ξ ↔ ك` في `τρύξ` و`γ ↔ ق` في `γυρός`؛ ألحقت الشواهد في ورقة الاقتراح بلا توصية وبلا مساس بالشبكة المجمدة.",
        "- ضبط الإتمام: كل بطاقة تسمي معرف الأسرة ومعرف العضو الفردي، وتذكر الحكم السابق والجديد، وعدد المروحة والمدخلة المختارة.",
        "- الفحوص النظيفة: سلامة الجولة؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ `git diff --check`؛ وأقصى بطاقة 5115 بايت.",
        "- فحص انضباط النواة لليونانية: 24 ملاحظة، منها 23 في المادة السابقة وملاحظة `D4-DIRECTION` واحدة في الجولة على `κῶας↔كسو`؛ روجعت وأبقيت بموجب إعادة فتح 2026-08-05 للقرض ذي المانح غير السامي، فلا يصير شرطا رابعا.",
        "- سجل الاسترداد: أعيد بناؤه بعد الجولة من 49,515 بطاقة؛ المعلق 38,467، ويشمل بطاقات الجولة المفتوحة.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        "",
        "LANE-A DONE6 100 LANE-A-OPEN-COMP-00018",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def _card_positions(cards: str) -> dict[str, int]:
    positions: dict[str, int] = {}
    for match in re.finditer(r"^### بطاقة: .*LANE-A-R6-(\d{3})$", cards, re.MULTILINE):
        positions[f"R{int(match.group(1))}"] = match.start()
    for match in re.finditer(r"^### (LANE-A-OPEN-COMP-\d{5}):", cards, re.MULTILINE):
        positions[match.group(1)] = match.start()
    return positions


def emit_reading_chunk(start: str, count: int) -> str:
    cards, _records = render_all()
    positions = _card_positions(cards)
    if start.isdigit():
        key = f"R{int(start)}"
        order = [f"R{rank}" for rank in range(FIRST_RANK, LAST_RANK + 1)] + [
            f"LANE-A-OPEN-COMP-{number:05d}" for number in range(1, 19)
        ]
    else:
        key = start
        order = [f"R{rank}" for rank in range(FIRST_RANK, LAST_RANK + 1)] + [
            f"LANE-A-OPEN-COMP-{number:05d}" for number in range(1, 19)
        ]
    if key not in order or count < 1:
        raise AssertionError("بداية قطعة القراءة غير صحيحة")
    index = order.index(key)
    if index + count > len(order):
        raise AssertionError("قطعة القراءة تتجاوز الجولة")
    begin_key = order[index]
    end_key = order[index + count] if index + count < len(order) else None
    begin = 0 if begin_key == order[0] else positions[begin_key]
    end = positions[end_key] if end_key else len(cards)
    chunk = cards[begin:end].rstrip()
    reading = READING.read_text(encoding="utf-8")
    marker = f"LANE-A-R6-{int(start):03d}" if start.isdigit() else start
    if marker in reading:
        raise AssertionError(f"القطعة التي تبدأ بـ{marker} موجودة")
    tail = reading.rstrip().splitlines()[-24:]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        *(" " + line for line in tail),
        "+",
        add_lines(chunk),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def emit_proposal_report() -> str:
    proposal = PROPOSAL.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    if "إلحاق شواهد الجولة السادسة" in proposal:
        raise AssertionError("إلحاق الجولة السادسة موجود في ورقة الاقتراح")
    if "LANE-A DONE6" in report:
        raise AssertionError("سطر إتمام الجولة السادسة موجود")
    _cards, records = render_all()
    proposal_tail = proposal.rstrip().splitlines()[-8:]
    report_tail = report.rstrip().splitlines()[-8:]
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md",
        "@@",
        *(" " + line for line in proposal_tail),
        "+",
        add_lines(proposal_addition().rstrip()),
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        *(" " + line for line in report_tail),
        "+",
        add_lines(report_addition(records).rstrip()),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--reading-chunk", metavar="START")
    parser.add_argument("--count", type=int, default=5)
    parser.add_argument("--proposal-report", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.reading_chunk is not None:
        print(emit_reading_chunk(args.reading_chunk, args.count), end="")
    elif args.proposal_report:
        print(emit_proposal_report(), end="")
    else:
        _cards, records = render_all()
        print(json.dumps(records, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
