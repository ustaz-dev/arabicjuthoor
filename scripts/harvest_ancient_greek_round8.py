#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A, round 8 without committing or shipping.

The renderer completes the next eighty Ancient Greek open-inventory members
after LANE-A-OPEN-COMP-00058.  Selection remains shortest consonant skeleton
first and original inventory order second, with an obligatory non-empty fan.
It emits append-only apply_patch patches in two batches of forty cards.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round7 as R7  # noqa: E402


R6 = R7.R6
R2 = R7.R2
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-17"
FIRST_COMPLETION = 59
LAST_COMPLETION = 138
BATCH_SIZE = 40


EXPECTED_WORDS = (
    "ῥώψ", "σόλιον", "γαῖσος", "λῶρος", "τύρμα", "φέκλη", "πᾶγος", "βέργαι", "χάννη",
    "σεργοί", "δοῦμος", "αὔσπιξ", "μόδιος", "λυδίων", "καροῦχα", "βυκάνη",
    "Ὀδρύσαι", "λαγκία", "βωρεύς", "διάριον", "κάμον", "τάβλα", "κόδρα",
    "ὗ_ψιλόν", "κέλλα", "λίβος", "φασκία", "δηνάριον", "Κελτός", "Γότθος",
    "Κάρβων", "Ἀλβανός", "Βλάχος", "Φαλέριος", "Λατῖνος", "Λατῖνος", "Λευκανός",
    "Μάκρων", "Ῥωμανός", "Βιθυνός", "Πέρσης", "Νέρβιος", "Πικηνός", "Κυρίτης",
    "Σαβῖνος", "Σκύθης", "Σηκουανός", "Οὐολοῦσκος", "βωλίτης", "πτέρνη", "κόστος",
    "βόμβος", "στάτωρ", "μουστάκια", "φασίολος", "βίρρος", "κυρβασία", "πόρκος",
    "Σαβάζιος", "θάμβος", "ψχέντ", "τάριχος", "καλανδαί", "κάμπος", "μαρούλιον",
    "βάσανος", "σουδάριον", "ψάγδας", "σέσελις", "βοῦστον", "μόσχος", "στίμμι",
    "πάτελλα", "κάρρον", "βουρδών", "φακιάλιον", "ὁσπίτιον", "βέρεδος", "σάκχαρ",
    "μνάσιον",
)

EXPECTED_SOURCE_GAPS = {
    86, 88, 89, 90, 92, 93, 94, 95, 98, 99, 100, 103, 104, 106, 108,
    110, 111, 113, 114, 117, 120, 122, 123, 124, 125, 126, 127, 129,
    130, 131, 132, 134, 137, 138,
}
EXPECTED_LAW_GAPS = {59, 70, 82, 119, 133}
ROOT_OVERRIDES = {133: "برذن"}


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


def inventory_items() -> list[InventoryItem]:
    """Select the next eighty open members under the accepted ordering."""
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<family>ancient_greek:family:[0-9a-f]+)`[^\n]*$",
        text,
        re.MULTILINE,
    ))
    used = set(R6.INVENTORY_MEMBER_IDS) | set(R7.INVENTORY_MEMBER_IDS)
    seen_members: set[str] = set()
    eligible: list[tuple[int, int, InventoryItem]] = []
    for match in starts:
        next_heading = re.search(r"^### ", text[match.end():], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        block = text[match.start():end]
        verdict = field(block, r"^- الحكم \(استكشاف\): ([^\n]+)")
        if "غير صادر" not in verdict and "OPEN-CANDIDATE" not in verdict:
            continue
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
            continue
        meaning = field(block, r"^- المعنى من قاموس الفرع: «(.+?)» \[Kaikki Ancient Greek")
        entries, how = R2.LEX.look("ancient-greek", word)
        if not entries:
            raise AssertionError(f"لا مدخلة قاموس فرع: {member_id}")
        chosen = next((entry for entry in entries if R2.clean(entry.get("id")) == member_id), None)
        if chosen is None:
            wanted = R2.clean(meaning).rstrip(".").casefold()
            chosen = next(
                (entry for entry in entries if R2.clean(entry.get("en")).rstrip(".").casefold() == wanted),
                None,
            )
        if chosen is None:
            chosen = entries[R2.BASE.select_lexicon(entries, meaning)]
        item = InventoryItem(
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
    if len(eligible) != 109:
        raise AssertionError(f"تغير باقي الجرد المرشح: {len(eligible)} لا 109")
    selected = [row[2] for row in eligible[:80]]
    if tuple(item.word for item in selected) != EXPECTED_WORDS:
        raise AssertionError("تغيرت نافذة الجولة الثامنة أو ترتيبها")
    if len({item.member_id for item in selected}) != 80:
        raise AssertionError("تكرر عضو في نافذة الجولة الثامنة")
    lengths = Counter(len(R2.branch_skeleton(item.word)) for item in selected)
    if lengths != Counter({4: 53, 3: 26, 2: 1}):
        raise AssertionError(f"تغير توزيع أطوال الجولة: {lengths}")
    return selected


def gather_hits(items: list[InventoryItem]) -> dict[str, list[dict]]:
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


def decision_material(number: int) -> tuple[str, str, str] | None:
    if number == 83:
        return (
            "`كلل`؛ تاج اللغة وصحاح العربية للجوهري: «الكِلّةُ: السِترُ الرَّقيقُ يُخاطُ كالبيتِ، يُتَوَقَّى فيه من البقّ»؛ "
            "والمحكم والمحيط الأعظم لابن سيده الأندلسي: «الكِلّةُ: السّتْر الرقيق يخاط كالبيت... وغشاء من ثوب رقيق يتوقى به البعوض».",
            "cell وroom وchamber حيز محوط يؤوي داخله، والكِلّة ستر مخيط كالبيت يحوط من بداخله؛ "
            "المدار حيز ساتر مصنوع يحد موضع الإيواء.",
            "ROOT-TRACE",
        )
    if number == 133:
        return (
            "`برذن`؛ الخليل: «البَرْذَنَةُ سَيْرةُ البِرْذونِ والفَرَس»؛ "
            "والجوهري: «البرذون: الدابة».",
            "mule دابة ركوب من جنس الخيل والبغال، والبرذون دابة تسمى ويضرب بمشيها المثل؛ "
            "المدار دابة ركوب رباعية من جنس الخيل، لكن رجل الصوت غير مكتملة.",
            "LAW-GAP",
        )
    return None


def law_search_line(gaps: list[str], source_first: bool) -> str:
    searches = "؛ ".join(f"`{gap}` وعكسه" for gap in gaps)
    tail = "؛ ويبقى هذا النقص تابعا بعد فتح المصدر" if source_first else ""
    return (
        f"- تفتيش صف القانون: فُتش {searches}، ثم `اليونانية` و`Greek` في عمود الشاهد؛ "
        f"لم يوجد صف نافذ{tail}."
    )


def inventory_card(
    number: int,
    item: InventoryItem,
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

    material = decision_material(number)
    if material:
        counterpart, orbit, intended = material
    else:
        counterpart = f"`{root}`؛ قُرئت شواهده ولم يثبت منها معنى يطابق معنى العضو."
        orbit = (
            f"قوبل معنى الفرع «{R2.clip(item.meaning, 150)}» بكل معاني `{root}` وبدرجات الحدث؛ "
            "لم يثبت مدار محدود من غير تعميم أو قفزة."
        )
        intended = ""

    source_gap = not witnessed
    if number == 83:
        if not licensed or source_gap:
            raise AssertionError("لم تستوف بطاقة κέλλα الموجبة رجلي الصوت والمصدر")
        closure, verdict = "READY", "ROOT-TRACE"
        blocker = ""
    elif source_gap:
        closure = verdict = "SOURCE-GAP"
        blocker = (
            "- عائق: النوع=SOURCE-GAP؛ يتطلب=شاهدين عربيين مسميين لمرشح من المروحة؛ "
            "أعاد المسح الحالي صفرا لكل المرشحين."
        )
    elif not licensed:
        closure = verdict = "LAW-GAP"
        blocker = "- عائق: النوع=LAW-GAP؛ يتطلب=" + "، ".join(
            f"صفا نافذا يرخص `{gap}`" for gap in gaps
        ) + "."
    else:
        closure = verdict = "OPEN-CANDIDATE"
        blocker = (
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=مدارا محدودا يجمع معنى العضو "
            "بمعنى عربي مقروء؛ لا يضاف شرط رابع."
        )

    if intended and verdict != intended:
        raise AssertionError(f"تغير الحكم اليدوي في {number}: {verdict} لا {intended}")
    if number in EXPECTED_SOURCE_GAPS and verdict != "SOURCE-GAP":
        raise AssertionError(f"تغيرت فجوة المصدر {number}")
    if number in EXPECTED_LAW_GAPS and verdict != "LAW-GAP":
        raise AssertionError(f"تغيرت فجوة القانون {number}")
    if verdict == "SOURCE-GAP" and number not in EXPECTED_SOURCE_GAPS:
        raise AssertionError(f"فجوة مصدر جديدة غير مقروءة: {number}")
    if verdict == "LAW-GAP" and number not in EXPECTED_LAW_GAPS:
        raise AssertionError(f"فجوة قانون جديدة غير مقروءة: {number}")

    if number in {83, 133}:
        witness = counterpart.removeprefix(f"`{root}`؛ ").rstrip()
    elif source_gap:
        witness = (
            f"قُرئت {len(candidates)} صورة في المروحة بـ`--max-chars 0`؛ "
            "لم يعد أي مرشح شاهدا عربيا مسمى."
        )
    else:
        witness = R2.witness_line(root, hits.get(root, []), "")

    route_text = route if licensed else "غير مكتمل؛ " + "، ".join(f"`{gap}`" for gap in gaps)
    skeleton = "-".join(R2.branch_skeleton(item.word))
    etym = R2.clip(item.etym, 125) if item.etym else "لم ينشر قاموس الفرع صورة أقدم؛ SOURCE-GAP في حقل الأصل وحده."
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
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{item.read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو الفردي `{item.member_id}`؛ الحكم السابق: {item.previous_verdict}",
        f"- الكلمة في الفرع: `{item.word}` /{item.read}/؛ `{item.pos}`؛ «{R2.clip(item.meaning, 125)}».",
        f"- معيار الانتخاب: هيكل `{skeleton}` ومروحة غير فارغة؛ الموضع {number} من المواصلة القصيرة أولا.",
        f"- أقدم صورة مستعادة: {etym} [Kaikki Ancient Greek].",
        f"- الخطوة صفر: حُفظت الصورة المنشورة بلا حذف غير مسند؛ الهيكل `{skeleton}`.",
        f"- درجة المقارنة: {'جذر ثلاثي كامل' if len(R2.branch_skeleton(item.word)) == 3 else 'هيكل رباعي'}؛ ودرجة الحدث أدناه.",
        f"- مسح المعاني العربية: {witness}",
        f"- المقابل من اللسان: {counterpart}",
        f"- مسار الصوت: `{route_text}`؛ المرشح `{root}` {'مرخص كاملا' if licensed else 'معلق'} في `fan_any_script.fan('{item.word}', 'greek')`.",
    ]
    if gaps:
        lines.append(law_search_line(gaps, source_gap))
    lines += [
        f"{event.line()}.",
        f"- المعنى من قاموس الفرع: قُرئت {len(item.entries)} مدخلة بطريق «{item.selection_way}»؛ المختارة `{item.word}` /{item.read}/ [{item.pos}] «{R2.clip(item.meaning, 145)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        "- المصفاة: المانح غير السامي لا يغلق المقارنة الأعمق؛ لا مانح سامي مباشر مسمى.",
        "- فصل المتجانسات والاقتراض: الحكم للعضو المسمى وحده.",
        f"- فحص المروحة كلها: قُرئت {len(candidates)} صورة مرتبة مع شواهدها؛ ذوات الشاهد={len(witnessed)}؛ المستعمل في القرار وحده: {summary}.",
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
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `{item.previous_verdict}`؛ الحكم الجديد `{verdict}`؛ السبب: قراءة المروحة غير الفارغة كاملة، وكل مداخل الرسم، وشواهد المرشح المستعمل.",
        "- ملاحظات: عدسة الاسترداد قرأت المرشحات؛ وعدسة التشكيك قصرت الحكم على العضو والمدار المكتوب.",
    ]
    rendered, size = R6.compact_to_limit("\n".join(lines), completion_id)
    if size > 5080:
        rendered = re.sub(
            r"^- فحص المروحة كلها:.*$",
            f"- فحص المروحة كلها: الصور={len(candidates)}؛ ذوات الشاهد={len(witnessed)}؛ المستعمل: {summary}.",
            rendered,
            flags=re.MULTILINE,
        )
        size = len((rendered + "\n").encode("utf-8"))
    if size > 5080:
        raise AssertionError(f"تجاوزت البطاقة {completion_id} هامش الحجم: {size}")
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
    if len(records) != 80:
        raise AssertionError("لم تكتمل الجولة الثامنة إلى 80 بطاقة")
    if [record["completion_id"] for record in records] != [
        f"LANE-A-OPEN-COMP-{number:05d}" for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]:
        raise AssertionError("معرفات الجولة الثامنة غير متصلة")
    counts = Counter(record["closure"] for record in records)
    if counts != Counter({"OPEN-CANDIDATE": 40, "SOURCE-GAP": 34, "LAW-GAP": 5, "READY": 1}):
        raise AssertionError(f"تغيرت أحكام الجولة الثامنة: {counts}")
    return rendered, records


def reading_fragment(start: int, count: int, cards: list[str] | None = None) -> str:
    if cards is None:
        cards, _records = render_all()
    if count < 1 or start < FIRST_COMPLETION or start + count - 1 > LAST_COMPLETION:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    end = start + count - 1
    if start <= 98 < end:
        raise AssertionError("لا تعبر قطعة القراءة حد الدفعتين")
    batch = 1 if start <= 98 else 2
    first, last = ((59, 98) if batch == 1 else (99, 138))
    selected = cards[start - FIRST_COMPLETION:start - FIRST_COMPLETION + count]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND8-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الثامنة: دفعة إتمام الجرد المفتوح {batch} (2026-08-17)",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ الترتيب بطول الهيكل ثم موضع بطاقة الجرد الأصلي.",
            "- قُرئت المروحة كلها لكل عضو، وكتب المستعمل وحده؛ بطاقات الجولات السابقة محفوظة بلا تعديل.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND8-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    """Render once and stage bounded fragments in the system temp directory."""
    cards, _records = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round8-"))
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
    return emit_append_patch(
        READING,
        fragment_path.read_text(encoding="utf-8"),
        f"LANE-A-OPEN-COMP-{start:05d}",
    )


def report_fragment() -> str:
    _cards, records = render_all()
    first = records[:BATCH_SIZE]
    second = records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])
    lines = [
        "<!-- LANE-A-GREEK-ROUND8-REPORT:START -->",
        "",
        "## 2026-08-17، الجولة الثامنة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 40؛ المدى: `LANE-A-OPEN-COMP-00059` إلى `LANE-A-OPEN-COMP-00098`.",
        "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(Counter(row["closure"] for row in first).items())) + ".",
        "- الموجب المحتسب: 1 `ROOT-TRACE`؛ المفتوح أو المعلق: 39.",
        "- الزوج الموجب: `κέλλα↔كلل`؛ المدار حيز ساتر مخيط كالبيت بإزاء cell وroom وchamber.",
        "- فجوات القانون: `ψ↔ب` في `00059` و`00082`، و`ξ↔ك` في `00070`؛ وفجوات المصدر 9.",
        "",
        "## 2026-08-17، الجولة الثامنة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 40؛ المدى: `LANE-A-OPEN-COMP-00099` إلى `LANE-A-OPEN-COMP-00138`.",
        "- توزيع الإغلاق: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(Counter(row["closure"] for row in second).items())) + ".",
        "- الموجب المحتسب: 0؛ المفتوح أو المعلق: 40.",
        "- فجوتا القانون: `ψ↔ب` في `00119` و`δ↔ذ` في `00133`؛ الثانية تحمل مدار الدابة `βουρδών↔برذن` لكن رجل الصوت لم تكتمل.",
        "- فجوات المصدر: 25؛ لم يعد أي مرشح في مروحة كل بطاقة شاهدا عربيا مسمى.",
        "",
        "## حصيلة الجولة الثامنة",
        "",
        "- مجموع البطاقات المكتوبة: 80؛ دفعتان من 40 بطاقة.",
        "- معيار الجرد: 80 عضوًا فريدًا تالية للجولة السابعة؛ 1 بهيكل ثنائي، ثم 26 بهيكل ثلاثي، ثم 53 بهيكل رباعي؛ لا عضو مكرر.",
        "- الإغلاق الكلي: `LAW-GAP`=5؛ `OPEN-CANDIDATE`=40؛ `READY`=1؛ `SOURCE-GAP`=34.",
        "- النتائج الموجبة: 1 `ROOT-TRACE`؛ ولم يحول خبر القرض غير السامي إلى شرط رابع.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والحكمين، وتذكر عدد صور المروحة وذوات الشاهد والمدخلة المختارة.",
        "- فحص انضباط النواة: 28 ملاحظة؛ 27 موروثة من المادة السابقة، و`D4-DIRECTION` واحدة جديدة في `00083`؛ روجعت وأبقيت بموجب إعادة فتح 2026-08-05 للقرض ذي المانح غير السامي، فلا يصير خبر الأصل شرطا رابعا.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND8-REPORT:END -->",
        "",
        "LANE-A DONE8 80 LANE-A-OPEN-COMP-00138",
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


def emit_remove_tail(start: int) -> str:
    """Emit a bounded rollback patch for uncommitted round-8 chunks only."""
    current = READING.read_text(encoding="utf-8")
    marker = (
        "<!-- LANE-A-GREEK-ROUND8-BATCH-1:START -->"
        if start == FIRST_COMPLETION
        else f"### LANE-A-OPEN-COMP-{start:05d}:"
    )
    position = current.find(marker)
    if position < 0:
        raise AssertionError(f"لا يوجد ذيل الجولة عند {marker}")
    prefix = current[:position].rstrip().splitlines()
    removed = current[position:].rstrip().splitlines()
    if any("LANE-A DONE7" in line for line in removed):
        raise AssertionError("تجاوز التراجع حد الجولة الثامنة")
    patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/readings/ancient-greek.md",
        "@@",
        *(" " + line for line in prefix[-12:]),
        " ",
        *("-" + line for line in removed),
        "*** End Patch",
    ]
    return "\n".join(patch) + "\n"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--rollback-start", type=int)
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
    elif args.rollback_start is not None:
        print(emit_remove_tail(args.rollback_start), end="")
    elif args.start is not None:
        print(
            emit_append_patch(
                READING,
                reading_fragment(args.start, args.count),
                f"LANE-A-OPEN-COMP-{args.start:05d}",
            ),
            end="",
        )
    elif args.report:
        print(emit_append_patch(REPORT, report_fragment(), "LANE-A DONE8"), end="")
    else:
        _cards, records = render_all()
        print(f"cards={len(records)} max={max(row['bytes'] for row in records)}")
        print(Counter(row["closure"] for row in records))
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
