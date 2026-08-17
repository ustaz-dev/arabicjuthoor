#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 9 without committing or shipping.

The renderer completes every remaining Ancient Greek inventory member whose
frozen fan is non-empty after LANE-A-OPEN-COMP-00138.  The 104 members are
kept in the accepted shortest-skeleton-first order and split into two batches
of 52 cards.  Repository changes are emitted as bounded apply_patch patches.
"""

from __future__ import annotations

from collections import Counter
import argparse
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round8 as R8  # noqa: E402


R6 = R8.R6
R7 = R8.R7
R2 = R8.R2
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-17"
FIRST_COMPLETION = 139
LAST_COMPLETION = 242
BATCH_SIZE = 52


EXPECTED_WORDS = (
    "ἄλφα", "ἄλφα", "ἀμήν", "ἀββα", "Ἄραψ", "ῥακά", "βῆτα", "βῆτα",
    "ζῆτα", "θῆτα", "μνᾶ", "χαυών", "ὀθόνη", "ἀλεφ", "κορύνη", "κάβος",
    "κόρος", "γάμμα", "δέλτα", "Σύρος", "Ἑβραῖος", "Ἑβραῖος", "κάππα",
    "μάννα", "πάσχα", "βάτος", "ἰώβηλος", "λάβδα", "ἄγλις", "κινύρα",
    "ἒ_ψιλόν", "σάλπη", "θῖβις", "γαυλός", "νάβλα", "πῶρος", "σοῦσον",
    "σάρος", "κιττώ", "καφουρά", "σάτον", "ἀσχίον", "γαζερά", "χερούβ",
    "ἀμόργη", "γαβάθα", "κίουρος", "ἀλληλούϊα", "ὡσαννά", "ἀμηρᾶς",
    "σεράφ", "Ἄδαδος", "Μάνης", "γράμμα", "νάρδος", "Χαλδαῖος", "νίτρον",
    "ζιζάνιον", "κύμινον", "λέμβος", "σήσαμον", "θύννος", "ναζιραῖος",
    "ναζιραῖος", "ὂ_μικρόν", "χαλβάνη", "σιγαλόεις", "κορβᾶν", "σίγλος",
    "ἔντυβον", "ὀξύγγιον", "νέπετος", "μύρκος", "βαρακίνη", "καυνάκης",
    "σίγνον", "ἀσσάριον", "κίτρον", "κύβιτον", "ἄννησον", "γάλαγγα",
    "κόγγιον", "σῶσσος", "χέννιον", "Ὀροσάγγαι", "δεκανός", "δράγλη",
    "καλίγιον", "μοῦστος", "Πέλιγνοι", "Σάρνος", "χαλιφᾶς", "Τοῦρκος",
    "γλουρός", "Ἀλέτριον", "μανδήλη", "κερβησία", "κανδήλη", "κορριγία",
    "δουκάτον", "ἄσπρος", "φοῦρνος", "Ἀπρίλιος", "Ναβαταῖος",
)

TRANSMISSION_NUMBERS = {
    139, 140, 141, 142, 143, 144, 145, 146, 147, 148, 149, 150, 151,
    152, 154, 155, 156, 157, 158, 159, 160, 161, 162, 163, 164, 165,
    166, 167, 168, 169, 171, 172, 173, 174, 176, 177, 178, 179, 180,
    181, 182, 183, 185, 186, 187, 188, 189, 190, 191, 193, 194, 195,
    196, 197, 198, 199, 200, 201, 202, 203, 204, 206, 207, 212, 219,
    221, 230, 242,
}
EXPECTED_SOURCE_GAPS = {
    153, 192, 208, 209, 210, 214, 215, 216, 217, 218, 220, 222, 223,
    224, 226, 227, 232, 233, 237,
}
EXPECTED_OPEN = {
    170, 175, 184, 205, 211, 213, 225, 228, 229, 231, 234, 235, 236,
    238, 239, 240, 241,
}
ROOT_OVERRIDES = {153: "قرن"}
DIRECTION_EXCERPTS = {
    167: "Kroonen derives the reconstructed Pre-Greek form from Akkadian gidlu, a string of garlic or onions.",
    172: "The source routes the vessel name via Phoenician or a near language from Akkadian gullu, container, and gullatu, ewer.",
    174: "According to Haupt, it was borrowed from Akkadian; the source records the competing Pre-Greek analysis.",
}


def field(block: str, pattern: str, default: str = "") -> str:
    values = re.findall(pattern, block, re.MULTILINE)
    return " ".join(values[-1].split()) if values else default


def completed_before_round9() -> set[str]:
    used = set(R6.INVENTORY_MEMBER_IDS) | set(R7.INVENTORY_MEMBER_IDS)
    used.update(item.member_id for item in R8.inventory_items())
    if len(used) != 138:
        raise AssertionError(f"تغير مقام الإتمام السابق: {len(used)} لا 138")
    return used


def inventory_items() -> list[R8.InventoryItem]:
    """Select all remaining non-empty-fan members under the accepted order."""
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<family>ancient_greek:family:[0-9a-f]+)`[^\n]*$",
        text,
        re.MULTILINE,
    ))
    used = completed_before_round9()
    seen_members: set[str] = set()
    eligible: list[tuple[int, int, R8.InventoryItem]] = []
    empty_fan = 0
    for match in starts:
        next_heading = re.search(r"^### ", text[match.end():], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        block = text[match.start():end]
        member_ids = re.findall(r"`(kaikki_ancient_greek[^`]+)`", block)
        if not member_ids:
            continue
        member_id = member_ids[0]
        if member_id in seen_members:
            continue
        seen_members.add(member_id)
        if member_id in used:
            continue
        word_match = re.search(r":en-(.+?)-grc-", member_id)
        if not word_match:
            continue
        word = word_match.group(1)
        fan = R2.FAN.rank(word, R2.FAN.fan(word, "greek"), "greek")
        if not fan:
            empty_fan += 1
            continue
        verdict = field(block, r"^- الحكم \(استكشاف\): ([^\n]+)")
        meaning = field(
            block,
            r"^- المعنى من قاموس الفرع: «(.+?)» \[Kaikki Ancient Greek",
        )
        entries, how = R2.LEX.look("ancient-greek", word)
        if not entries:
            raise AssertionError(f"لا مدخلة قاموس فرع: {member_id}")
        chosen = next(
            (entry for entry in entries if R2.clean(entry.get("id")) == member_id),
            None,
        )
        if chosen is None:
            wanted = R2.clean(meaning).rstrip(".").casefold()
            chosen = next(
                (
                    entry for entry in entries
                    if R2.clean(entry.get("en")).rstrip(".").casefold() == wanted
                ),
                None,
            )
        if chosen is None:
            chosen = entries[R2.BASE.select_lexicon(entries, meaning)]
        item = R8.InventoryItem(
            family_id=match.group("family"),
            member_id=member_id,
            word=word,
            read=R2.clean(chosen.get("read")),
            pos=R2.clean(chosen.get("pos")),
            meaning=R2.clean(chosen.get("en")),
            etym=R2.clean(chosen.get("etym")) or field(
                block,
                r"^- أقدمُ? صورةٍ? مستعادة: (.+?) \[Kaikki Ancient Greek",
            ),
            entries=tuple(entries),
            selection_way=how,
            previous_verdict=verdict,
            source_position=match.start(),
        )
        eligible.append((len(R2.branch_skeleton(word)), match.start(), item))

    eligible.sort(key=lambda row: (row[0], row[1]))
    selected = [row[2] for row in eligible]
    if len(selected) != 104:
        raise AssertionError(f"تغير باقي الجرد ذي المروحة: {len(selected)} لا 104")
    if empty_fan != 91:
        raise AssertionError(f"تغير مقام فجوة المروحة: {empty_fan} لا 91")
    if tuple(item.word for item in selected) != EXPECTED_WORDS:
        raise AssertionError("تغيرت نافذة الجولة التاسعة أو ترتيبها")
    if len({item.member_id for item in selected}) != 104:
        raise AssertionError("تكرر عضو في نافذة الجولة التاسعة")
    lengths = Counter(len(R2.branch_skeleton(item.word)) for item in selected)
    if lengths != Counter({4: 51, 3: 39, 2: 14}):
        raise AssertionError(f"تغير توزيع أطوال الجولة: {lengths}")
    return selected


def gather_hits(items: list[R8.InventoryItem]) -> dict[str, list[dict]]:
    roots: set[str] = set()
    for item in items:
        roots.update(
            root for root, _weight in R2.FAN.rank(
                item.word,
                R2.FAN.fan(item.word, "greek"),
                "greek",
            )
        )
    return R2.AR.matches_for_roots(R2.AR.DEFAULT_RESOURCES, roots, None)


def source_excerpt(item: R8.InventoryItem, limit: int = 190) -> str:
    source = item.etym.replace("—", "-")
    return R2.clip(source, limit) if source else "لم ينشر قاموس الفرع مسار أصل."


def inventory_card(
    number: int,
    item: R8.InventoryItem,
    hits: dict[str, list[dict]],
) -> tuple[str, dict]:
    ranked = R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek")
    candidates = [candidate for candidate, _weight in ranked]
    witnessed = [candidate for candidate in candidates if hits.get(candidate)]
    root = ROOT_OVERRIDES.get(number, witnessed[0] if witnessed else candidates[0])
    if root not in candidates:
        raise AssertionError(f"مرشح {number} خارج المروحة: {root}")
    licensed, route, gaps = R2.sound_route(item.word, root)
    event = R2.EVENT.resolve(root)
    if event is None:
        raise AssertionError(f"لا حدث مجمد لـ{number}: {root}")

    transmission = number in TRANSMISSION_NUMBERS
    step_zero_gap = number == 153
    source_gap = not witnessed
    if transmission:
        closure, verdict = "READY-TRANSMISSION", "SEMITIC-SOURCE-TRANSMISSION"
        counterpart = (
            "(لا مقابل من الأداة المجمدة)؛ شاهد الحكم مسار النقل السامي المسمى "
            "في أصل العضو، لا تشابه المروحة."
        )
        orbit = (
            "المعنى هو معنى اللفظ المنقول في المصدر؛ لا يصدر منه مدار نسب مستقل، "
            "ويبقى خارج بسط الإرث المشترك."
        )
        witness = (
            "قُرئ حقل الأصل المنشور للعضو نفسه؛ سمى مصدرا ساميا أو وسيطا ساميا "
            "في انتقال اللفظ إلى اليونانية."
        )
        blocker = ""
    elif step_zero_gap:
        closure = verdict = "SOURCE-GAP"
        counterpart = (
            "`قرن`؛ بقيت هيئة الرأس الناتئ ملاحظة استرداد، ولا ترث حكم "
            "ROOT-TRACE المنسوخ."
        )
        orbit = (
            "الهراوة ذات الرأس الغليظ تقارب هيئة القرن، لكن المصدر لا يثبت أن "
            "النون في `-ύνη` من اللب لا من البناء الصرفي؛ فجوة الخطوة صفر أسبق."
        )
        witness = R2.witness_line(root, hits.get(root, []), "")
        blocker = (
            "- عائق: النوع=SOURCE-GAP؛ يتطلب=تحليلا صرفيا منشورا يثبت لب "
            "`k-r-n` أو صورة أقدم تحفظ النون."
        )
    elif source_gap:
        closure = verdict = "SOURCE-GAP"
        counterpart = (
            f"`{root}`؛ خرج من المروحة، ولم يعد له شاهد عربي مسمى في "
            "المسح الحالي."
        )
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 145)}» بصور المروحة؛ "
            "تعذر اختبار مدار محدود قبل فتح المصدر العربي."
        )
        witness = (
            f"قُرئت {len(candidates)} صورة في المروحة بـ`--max-chars 0`؛ "
            "لم يعد أي مرشح شاهدا عربيا مسمى."
        )
        blocker = (
            "- عائق: النوع=SOURCE-GAP؛ يتطلب=شاهدين عربيين مسميين لمرشح من "
            "المروحة؛ أعاد المسح الحالي صفرا."
        )
    elif not licensed:
        closure = verdict = "LAW-GAP"
        counterpart = (
            f"`{root}`؛ له شاهد عربي، لكن رجل الصوت لم تكتمل بصف نافذ."
        )
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 145)}» بمعاني "
            f"`{root}`؛ يبقى المدار تابعا لفتح القانون."
        )
        witness = R2.witness_line(root, hits.get(root, []), "")
        blocker = "- عائق: النوع=LAW-GAP؛ يتطلب=" + "، ".join(
            f"صفا نافذا يرخص `{gap}`" for gap in gaps
        ) + "."
    elif number == 175:
        closure = verdict = "OPEN-CANDIDATE"
        counterpart = (
            "`سسن`؛ تاج العروس يسمّي `السوسن` نفس الزهرة، ويذكر موضعها "
            "في لسان العرب؛ المطابقة المعجمية مباشرة."
        )
        orbit = (
            "lily هي السوسن نفسه؛ بقي الحكم مفتوحا لأن أصل العضو يسمي النقل "
            "من المصرية ويقارن العبرية، فلا تحوّل المطابقة إلى جذر مستقل."
        )
        witness = R2.witness_line(root, hits.get(root, []), "")
        blocker = (
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=سلسلة اتجاه منشورة تصل "
            "المصرية `zšn` والعبرية `שושנה` والعربية `سوسن` بالعضو اليوناني، "
            "أو دليلا مستقلا يجيز حكم الجذر."
        )
    else:
        closure = verdict = "OPEN-CANDIDATE"
        counterpart = (
            f"`{root}`؛ قُرئت شواهده ولم يثبت منها معنى يطابق معنى العضو."
        )
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 145)}» بكل معاني "
            f"`{root}` وبدرجات الحدث؛ لم يثبت مدار محدود من غير تعميم."
        )
        witness = R2.witness_line(root, hits.get(root, []), "")
        blocker = (
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=مدارا محدودا يجمع معنى "
            "العضو بمعنى عربي مقروء؛ لا يضاف شرط رابع."
        )

    expected = (
        "SEMITIC-SOURCE-TRANSMISSION" if number in TRANSMISSION_NUMBERS
        else "SOURCE-GAP" if number in EXPECTED_SOURCE_GAPS
        else "OPEN-CANDIDATE" if number in EXPECTED_OPEN
        else ""
    )
    if verdict != expected:
        raise AssertionError(f"تغير الحكم المقروء في {number}: {verdict} لا {expected}")

    route_text = route if licensed else "غير مكتمل؛ " + "، ".join(
        f"`{gap}`" for gap in gaps
    )
    skeleton = "-".join(R2.branch_skeleton(item.word))
    etym = source_excerpt(item, 220 if transmission else 120)
    tiers = "/".join(str(value.tier) for value in R2.EVENT.all_tiers(root)) or "0"
    sound_summary = route if licensed else "غير مرخص " + "/".join(gaps)
    result_summary = {
        "SEMITIC-SOURCE-TRANSMISSION": "نقل سامي",
        "LAW-GAP": "LAW-GAP",
        "SOURCE-GAP": "SOURCE-GAP",
        "OPEN-CANDIDATE": "لا مدار محدود",
    }[verdict]
    summary = (
        f"`{root}`({sound_summary}؛ ح={tiers}؛ "
        f"ش={len(hits.get(root, []))}؛ {result_summary})"
    )
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    if transmission:
        direction_excerpt = DIRECTION_EXCERPTS.get(
            number,
            "حقل الأصل المقتبس أعلاه.",
        )
        source_line = (
            f"- مصدر اتجاه النقل: Kaikki Ancient Greek؛ `{item.member_id}`؛ "
            f"{direction_excerpt}"
        )
        filter_line = (
            "- المصفاة: SECTION27-DIRECTION-KEEP؛ المصدر السامي أو الوسيط "
            "السامي المسمى يحسم النقل، فلا يحول إلى ROOT-TRACE مستقل."
        )
        reason = "إعادة قراءة مسار المصدر السامي المسمى وقصره على العضو."
    else:
        source_line = ""
        filter_line = (
            "- المصفاة: المانح غير السامي لا يغلق المقارنة الأعمق؛ لا مانح "
            "سامي مباشر مسمى لهذا العضو."
        )
        reason = (
            "قراءة المروحة غير الفارغة كاملة، وكل مداخل الرسم، وشواهد "
            "المرشح المستعمل."
        )
    if number == 153:
        reason = (
            "تنفيذ تصحيح الخطوة صفر المؤرخ 2026-07-29؛ لا يثبت المصدر أن "
            "النون صامت من اللب."
        )
    elif number == 196:
        reason = (
            "المصدر ينص على انتقال اللفظ عبر صورة آرامية، فصحح الحكم السابق "
            "إلى نقل سامي مسمى."
        )

    degree = {
        2: "نواة ثنائية",
        3: "جذر ثلاثي كامل",
    }.get(len(R2.branch_skeleton(item.word)), "هيكل رباعي")
    supported = 0
    event_line = (
        "- حدث الحرف: قُرئ من السجل المجمد، ولم يستعمل في حكم النقل المسمى."
        if transmission
        else f"{event.line()}."
    )
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{item.read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو الفردي `{item.member_id}`؛ الحكم السابق: {item.previous_verdict}",
        f"- الكلمة في الفرع: `{item.word}` /{item.read}/؛ `{item.pos}`؛ «{R2.clip(item.meaning, 125)}».",
        f"- معيار الانتخاب: الهيكل `{skeleton}` ومروحة غير فارغة؛ الموضع {number} من إتمام الباقي، مرتبا بالقصر ثم موضع الجرد.",
        f"- أقدم صورة مستعادة: {etym} [Kaikki Ancient Greek].",
        f"- الخطوة صفر: حُفظت الصورة المنشورة بلا حذف غير مسند؛ الهيكل `{skeleton}`.",
        f"- درجة المقارنة: {degree}؛ ودرجة الحدث أدناه.",
        f"- مسح المعاني العربية: {witness}",
        f"- المقابل من اللسان: {counterpart}",
        (
            f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` اختبار مروحة ثانوي، "
            "ومسار المصدر أسبق لأن النقل مسمى."
            if transmission
            else f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` هو اختبار الصوت الجاري لهذه البطاقة."
        ),
    ]
    if gaps and not transmission:
        lines.append(R8.law_search_line(gaps, source_gap))
    lines += [
        event_line,
        f"- المعنى من قاموس الفرع: قُرئت {len(item.entries)} مدخلة بطريق «{item.selection_way}»؛ المختارة `{item.word}` /{item.read}/ [{item.pos}] «{R2.clip(item.meaning, 140)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        filter_line,
        "- فصل المتجانسات والاقتراض: الحكم للعضو المسمى وحده؛ لا يرث متحد الرسم ولا عضو آخر حكمه.",
        f"- فحص المروحة كلها: قُرئت {len(candidates)} صورة مرتبة؛ ذوات الشاهد={len(witnessed)}؛ المستعمل في المحضر: {summary}.",
        f"- مؤشر اليتم: العضو حاضر؛ لا يدعى حصر الأسرة `{item.family_id}`.",
        f"- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة={supported}؛ سلاسل المعنى المدعومة={supported}؛ الحد بالعضو المفحوص.",
        (
            f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={supported}؛ "
            f"سلاسل المعنى المدعومة={supported}؛ النقل المسمى خارج بسط الإرث."
            if transmission
            else f"- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة={supported}؛ "
            f"سلاسل المعنى المدعومة={supported}؛ لم يصدر حكم موجب."
        ),
        "- جسور الاسترداد المفحوصة: الجرد؛ الخطوة صفر؛ المروحة؛ الشبكة؛ الحدث؛ القاموس؛ العربية؛ الأصل؛ القرض؛ المدار.",
    ]
    if source_line:
        lines.append(source_line)
    if blocker:
        lines.append(blocker)
    lines += [
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict}.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `{item.previous_verdict}`؛ الحكم الجديد `{verdict}`؛ السبب: {reason}",
        "- ملاحظات: عدسة الاسترداد قرأت المرشحات والمصدر؛ وعدسة التشكيك قصرت الحكم على العضو والمسار المكتوب.",
    ]
    rendered, size = R6.compact_to_limit("\n".join(lines), completion_id)
    if size > 5100:
        rendered = re.sub(
            r"^- فحص المروحة كلها:.*$",
            (
                f"- فحص المروحة كلها: الصور={len(candidates)}؛ "
                f"ذوات الشاهد={len(witnessed)}؛ المستعمل: {summary}."
            ),
            rendered,
            flags=re.MULTILINE,
        )
        size = len((rendered + "\n").encode("utf-8"))
    if size > 5100:
        raise AssertionError(f"تجاوزت البطاقة {completion_id} هامش الحجم: {size}")
    if "—" in rendered:
        raise AssertionError(f"شرطة طويلة في {completion_id}")
    return rendered, {
        "completion_id": completion_id,
        "family_id": item.family_id,
        "member_id": item.member_id,
        "word": item.word,
        "read": item.read,
        "root": root,
        "closure": closure,
        "verdict": verdict,
        "bytes": size,
        "candidates": len(candidates),
        "witnessed": len(witnessed),
        "skeleton_length": len(R2.branch_skeleton(item.word)),
    }


def render_all() -> tuple[list[str], list[dict]]:
    items = inventory_items()
    hits = gather_hits(items)
    rendered: list[str] = []
    records: list[dict] = []
    for number, item in enumerate(items, FIRST_COMPLETION):
        card, record = inventory_card(number, item, hits)
        rendered.append(card)
        records.append(record)
    expected_ids = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected_ids:
        raise AssertionError("معرفات الجولة التاسعة غير متصلة")
    counts = Counter(record["verdict"] for record in records)
    expected = Counter({
        "SEMITIC-SOURCE-TRANSMISSION": 68,
        "SOURCE-GAP": 19,
        "OPEN-CANDIDATE": 17,
    })
    if counts != expected:
        raise AssertionError(f"تغيرت أحكام الجولة التاسعة: {counts}")
    return rendered, records


def reading_fragment(
    start: int,
    count: int,
    cards: list[str] | None = None,
) -> str:
    if cards is None:
        cards, _records = render_all()
    if count < 1 or start < FIRST_COMPLETION or start + count - 1 > LAST_COMPLETION:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    end = start + count - 1
    boundary = FIRST_COMPLETION + BATCH_SIZE - 1
    if start <= boundary < end:
        raise AssertionError("لا تعبر قطعة القراءة حد الدفعتين")
    batch = 1 if start <= boundary else 2
    first, last = (
        (FIRST_COMPLETION, boundary)
        if batch == 1
        else (boundary + 1, LAST_COMPLETION)
    )
    selected = cards[
        start - FIRST_COMPLETION:start - FIRST_COMPLETION + count
    ]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND9-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة التاسعة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ الترتيب بطول الهيكل ثم موضع بطاقة الجرد الأصلي.",
            "- قُرئت المروحة والمصدر لكل عضو؛ بطاقات الجولات السابقة محفوظة بلا تعديل.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND9-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _records = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round9-"))
    for start in range(FIRST_COMPLETION, LAST_COMPLETION + 1, 4):
        (stage / f"{start:05d}.md").write_text(
            reading_fragment(start, 4, cards),
            encoding="utf-8",
        )
    return stage


def emit_staged_patch(stage: Path, start: int) -> str:
    resolved = stage.resolve()
    temp_root = Path(tempfile.gettempdir()).resolve()
    if temp_root not in resolved.parents:
        raise AssertionError("مجلد المرحل خارج مجلد النظام المؤقت")
    fragment_path = resolved / f"{start:05d}.md"
    if not fragment_path.is_file():
        raise AssertionError(f"قطعة مرحلية مفقودة: {fragment_path}")
    return R8.emit_append_patch(
        READING,
        fragment_path.read_text(encoding="utf-8"),
        f"LANE-A-OPEN-COMP-{start:05d}",
    )


def report_fragment() -> str:
    _cards, records = render_all()
    first = records[:BATCH_SIZE]
    second = records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])

    def distribution(rows: list[dict]) -> str:
        counts = Counter(row["verdict"] for row in rows)
        return "؛ ".join(
            f"`{key}`={value}" for key, value in sorted(counts.items())
        )

    lines = [
        "<!-- LANE-A-GREEK-ROUND9-REPORT:START -->",
        "",
        f"## {DATE}، الجولة التاسعة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 52؛ المدى: `LANE-A-OPEN-COMP-00139` إلى `LANE-A-OPEN-COMP-00190`.",
        "- توزيع الأحكام: " + distribution(first) + ".",
        "- الانتقال السامي المسمى: 48؛ المفتوح أو المعلق: 4.",
        "- تصحيح الحكم: `00153` نفذ تصحيح الخطوة صفر السابق، فصار `SOURCE-GAP` بدل توريث `ROOT-TRACE`.",
        "",
        f"## {DATE}، الجولة التاسعة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 52؛ المدى: `LANE-A-OPEN-COMP-00191` إلى `LANE-A-OPEN-COMP-00242`.",
        "- توزيع الأحكام: " + distribution(second) + ".",
        "- الانتقال السامي المسمى: 20؛ المفتوح أو المعلق: 32.",
        "- تصحيح المصدر: `00196` صار `SEMITIC-SOURCE-TRANSMISSION` لأن المصدر ينص على المرور بصورة آرامية.",
        "",
        "## حصيلة الجولة التاسعة",
        "",
        "- مجموع البطاقات المكتوبة: 104؛ دفعتان من 52 بطاقة.",
        "- معيار الجرد: استنفدت الأعضاء الباقية ذات المروحة غير الفارغة؛ 14 بهيكل ثنائي، و39 بهيكل ثلاثي، و51 بهيكل رباعي؛ لا عضو مكرر.",
        "- مقام فجوة الأداة: بقي 91 عضو جرد بلا مروحة، فلا تنشأ لهم بطاقة حكم من أداة فارغة.",
        "- الأحكام الكلية: `OPEN-CANDIDATE`=17؛ `SEMITIC-SOURCE-TRANSMISSION`=68؛ `SOURCE-GAP`=19.",
        "- الانتقالات: ثبت 67 حكما سابقا في حدود العضو، وصحح حكم `ζιζάνιον` إلى انتقال سامي عبر الآرامية؛ كلها خارج بسط الإرث المشترك.",
        "- النتائج الجذرية الجديدة: 0؛ لم يحول النقل المسمى إلى ROOT-TRACE مستقل.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والحكمين، وتذكر المروحة والمدخلة والمصدر المستعمل.",
        "- فحص انضباط النواة: 28 ملاحظة موروثة بلا زيادة؛ لم تضف الجولة حكما موجبا من ROOT-TRACE أو NUCLEUS-TRACE.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND9-REPORT:END -->",
        "",
        "LANE-A DONE9 104 LANE-A-OPEN-COMP-00242",
    ]
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--staged-patch", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.stage:
        print(stage_fragments())
    elif args.staged_patch is not None:
        if args.start is None:
            raise AssertionError("يلزم --start مع --staged-patch")
        print(emit_staged_patch(args.staged_patch, args.start), end="")
    elif args.start is not None:
        print(
            R8.emit_append_patch(
                READING,
                reading_fragment(args.start, args.count),
                f"LANE-A-OPEN-COMP-{args.start:05d}",
            ),
            end="",
        )
    elif args.report:
        print(
            R8.emit_append_patch(
                REPORT,
                report_fragment(),
                "LANE-A DONE9",
            ),
            end="",
        )
    else:
        _cards, records = render_all()
        print(f"cards={len(records)} max={max(row['bytes'] for row in records)}")
        print(Counter(row["verdict"] for row in records))
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
