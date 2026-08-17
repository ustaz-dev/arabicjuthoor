#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 10 without committing or shipping.

The round completes the 91 Greek inventory members left after 00242. A named
Semitic transmission is decided from its source even when the fan is empty;
all other members receive TOOL-GAP with an explicit requirement. Cards are
append-only and split into batches of 46 and 45.
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
import harvest_ancient_greek_round9 as R9  # noqa: E402

R8, R6, R2 = R9.R8, R9.R6, R9.R2
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION, BATCH_SIZE = 243, 333, 46

TRANSMISSION_NUMBERS = {
    243, 244, 245, 246, 247, 248, 249, 250, 251, 253, 254, 255, 259,
    271, 274, 276, 277, 278, 289, 301, 318, 324, 333,
}
READ_OVERRIDES = {243: "waû"}
EXPECTED_LENGTHS = Counter({5: 54, 6: 22, 1: 11, 7: 3, 0: 1})
SEMITIC_MARKERS = (
    "semitic", "phoenician", "hebrew", "akkadian", "arabic", "aramaic",
)


def field(block: str, pattern: str, default: str = "") -> str:
    values = re.findall(pattern, block, re.MULTILINE)
    return " ".join(values[-1].split()) if values else default


def completed_before_round10() -> set[str]:
    used = R9.completed_before_round9()
    used.update(item.member_id for item in R9.inventory_items())
    if len(used) != 242:
        raise AssertionError(f"تغير مقام الإتمام السابق: {len(used)} لا 242")
    return used


def inventory_items() -> list[R8.InventoryItem]:
    text = READING.read_text(encoding="utf-8")
    starts = list(re.finditer(
        r"^### بطاقة: `(?P<family>ancient_greek:family:[0-9a-f]+)`[^\n]*$",
        text, re.MULTILINE,
    ))
    used = completed_before_round10()
    seen: set[str] = set()
    eligible: list[tuple[int, int, R8.InventoryItem]] = []
    nonempty: list[str] = []
    for match in starts:
        next_heading = re.search(r"^### ", text[match.end():], re.MULTILINE)
        end = match.end() + next_heading.start() if next_heading else len(text)
        block = text[match.start():end]
        ids = re.findall(r"`(kaikki_ancient_greek[^`]+)`", block)
        if not ids or ids[0] in seen:
            continue
        member_id = ids[0]
        seen.add(member_id)
        if member_id in used:
            continue
        word_match = re.search(r":en-(.+?)-grc-", member_id)
        if not word_match:
            continue
        word = word_match.group(1)
        fan = R2.FAN.rank(word, R2.FAN.fan(word, "greek"), "greek")
        if fan:
            nonempty.append(member_id)
            continue
        meaning = field(
            block, r"^- المعنى من قاموس الفرع: «(.+?)» \[Kaikki Ancient Greek",
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
                (entry for entry in entries
                 if R2.clean(entry.get("en")).rstrip(".").casefold() == wanted),
                None,
            )
        if chosen is None:
            chosen = entries[R2.BASE.select_lexicon(entries, meaning)]
        full_etym = field(
            block, r"^- أقدمُ? صورةٍ? مستعادة: (.+?) \[Kaikki Ancient Greek",
        )
        item = R8.InventoryItem(
            family_id=match.group("family"),
            member_id=member_id,
            word=word,
            read=R2.clean(chosen.get("read")),
            pos=R2.clean(chosen.get("pos")),
            meaning=R2.clean(chosen.get("en")),
            etym=full_etym or R2.clean(chosen.get("etym")),
            entries=tuple(entries),
            selection_way=how,
            previous_verdict=field(
                block, r"^- الحكم \(استكشاف\): ([^\n]+)",
            ),
            source_position=match.start(),
        )
        eligible.append((len(R2.branch_skeleton(word)), match.start(), item))
    if nonempty:
        raise AssertionError(f"بقي أعضاء ذوو مروحة بعد الجولة التاسعة: {len(nonempty)}")
    eligible.sort(key=lambda row: (row[0], row[1]))
    selected = [row[2] for row in eligible]
    if len(selected) != 91:
        raise AssertionError(f"تغير مقام الجولة العاشرة: {len(selected)} لا 91")
    if (selected[0].word, selected[-1].word) != ("ϝαῦ", "σαββατισμός"):
        raise AssertionError("تغير طرفا نافذة الجولة العاشرة")
    if len({item.member_id for item in selected}) != 91:
        raise AssertionError("تكرر عضو في نافذة الجولة العاشرة")
    lengths = Counter(len(R2.branch_skeleton(item.word)) for item in selected)
    if lengths != EXPECTED_LENGTHS:
        raise AssertionError(f"تغير توزيع أطوال الجولة: {lengths}")
    return selected


def source_excerpt(item: R8.InventoryItem, limit: int = 300) -> str:
    source = item.etym.replace("—", "-")
    return R2.clip(source, limit) if source else "لم ينشر قاموس الفرع مسار أصل."


def inventory_card(number: int, item: R8.InventoryItem) -> tuple[str, dict]:
    ranked = R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek")
    if ranked:
        raise AssertionError(f"المروحة لم تعد فارغة في {number}")
    transmission = number in TRANSMISSION_NUMBERS
    if transmission:
        if not any(marker in item.etym.casefold() for marker in SEMITIC_MARKERS):
            raise AssertionError(f"مصدر النقل السامي غير ظاهر في {number}")
        closure, verdict = "READY-TRANSMISSION", "SEMITIC-SOURCE-TRANSMISSION"
        comparison = (
            "مسار المصدر السامي المسمى يحسم انتقال العضو؛ لا يطلب مقابلا "
            "عربيا من مروحة فارغة ولا يحول النقل إلى ROOT-TRACE."
        )
        orbit = (
            "المعنى هو معنى اللفظ المنقول في المصدر؛ لا يصدر منه مدار نسب "
            "مستقل، ويبقى خارج بسط الإرث المشترك."
        )
        filter_line = (
            "- المصفاة: SECTION27-DIRECTION-KEEP؛ المصدر السامي المسمى "
            "مستقل عن نتيجة المروحة ويحسم النقل إلى الفرع."
        )
        source_line = (
            f"- مصدر اتجاه النقل: Kaikki Ancient Greek؛ `{item.member_id}`؛ "
            f"{source_excerpt(item)}"
        )
        blocker = ""
        reason = "قراءة مصدر العضو وإثبات الانتقال السامي المسمى مستقلا عن فراغ المروحة."
    else:
        closure = verdict = "TOOL-GAP"
        comparison = (
            "لا مقابل مختارا؛ أعادت المروحة المجمدة صفرا، وهذا وصف لنقص "
            "الأداة لا نفيا لصلة العضو."
        )
        orbit = (
            f"قُرئ معنى الفرع «{R2.clip(item.meaning, 145)}»؛ لا يكتب مدار "
            "نسب قبل أن تنتج الأداة مرشحا عربيا يمكن قراءة معانيه."
        )
        filter_line = (
            "- المصفاة: لا مانح سامي مباشر مسمى يحسم العضو؛ وذكر مانح غير "
            "سامي أو غياب الأصل لا يغلق المقارنة الأعمق."
        )
        source_line = ""
        blocker = (
            "- عائق: النوع=TOOL-GAP؛ يتطلب=مرشحا عربيا واحدا على الأقل "
            "تعيده المروحة بعد تحليل صرف الفرع المنشور أو توسيع أداة مرخص؛ "
            "فراغ الأداة لا يثبت عدم الصلة."
        )
        reason = (
            "إتمام الجرد بتسمية فجوة الأداة ومطلوبها بعد قراءة قاموس الفرع "
            "وحقل الأصل؛ لم يصدر حكم نفي."
        )
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    read = READ_OVERRIDES.get(number, item.read) or "قراءة غير مثبتة في الفهرس"
    tokens = R2.branch_skeleton(item.word)
    skeleton = "-".join(tokens) if tokens else "∅"
    etym = source_excerpt(item, 300 if transmission else 180)
    degree = (
        "لا درجة صوتية قبل أن تنتج الأداة مرشحا؛ حكم النقل مستقل عن السلم."
        if transmission else "TOOL-GAP قبل اختبار درجات الجذر والنواة."
    )
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE})؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو الفردي `{item.member_id}`؛ الحكم السابق: {item.previous_verdict}",
        f"- الكلمة في الفرع: `{item.word}` /{read}/؛ `{item.pos}`؛ «{R2.clip(item.meaning, 150)}».",
        f"- معيار الانتخاب: الباقي بعد `LANE-A-OPEN-COMP-00242`؛ الهيكل `{skeleton}`؛ `fan_any_script.fan('{item.word}', 'greek')` أعادت 0؛ الترتيب بطول الهيكل ثم موضع الجرد.",
        f"- أقدم صورة مستعادة: {etym} [Kaikki Ancient Greek].",
        f"- الخطوة صفر: حُفظت الصورة المنشورة بلا حذف غير مسند؛ الهيكل الجاري `{skeleton}`، ولم يخترع تحليل صرف لفتح المروحة.",
        f"- درجة المقارنة: {degree}",
        "- مسح المعاني العربية: لا جذر مولدا لمسحه؛ لم يحول الصفر إلى شاهد نفي، ولم يختر مرشحا من خارج الأداة.",
        f"- المقابل من اللسان: {comparison}",
        "- مسار الصوت: لا مرشح مولدا ولا صف شبكة مطلوبا؛ لم يخترع صف ولم يعلن LAW-GAP.",
        "- حدث الحرف: لا جذر مولدا يمرر إلى `frozen_event`؛ لم يجعل غياب مدخل الاختبار حكما على العضو.",
        f"- المعنى من قاموس الفرع: قُرئت {len(item.entries)} مدخلة بطريق «{item.selection_way}»؛ المختارة `{item.word}` /{read}/ [{item.pos}] «{R2.clip(item.meaning, 145)}» [Kaikki Ancient Greek].",
        f"- المدار: {orbit}",
        filter_line,
        "- فصل المتجانسات والاقتراض: الحكم للعضو الفردي المسمى وحده؛ لا يرث متحد الرسم ولا عضو آخر حكمه.",
        "- فحص المروحة كلها: الصور=0؛ ذوات الشاهد=0؛ لم يحتكر مرشح مصدر البحث لأنه لا مرشح مولدا أصلا.",
        f"- مؤشر اليتم: العضو حاضر؛ لا يدعى حصر الأسرة `{item.family_id}`.",
        "- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ الحد بالعضو المفحوص.",
        (
            "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ "
            "سلاسل المعنى المدعومة=0؛ النقل المسمى خارج بسط الإرث."
            if transmission else
            "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ "
            "سلاسل المعنى المدعومة=0؛ لم تنتج الأداة مقابلا."
        ),
        "- جسور الاسترداد المفحوصة: الجرد؛ العضو؛ الخطوة صفر؛ المروحة؛ الشبكة؛ الحدث؛ قاموس الفرع؛ الأصل؛ القرض؛ المدار.",
    ]
    if source_line:
        lines.append(source_line)
    if blocker:
        lines.append(blocker)
    lines += [
        f"- حالة الإغلاق: {closure}.",
        f"- الحكم (استكشاف): {verdict}.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحكم السابق `{item.previous_verdict}`؛ الحكم الجديد `{verdict}`؛ السبب: {reason}",
        "- ملاحظات: عدسة الاسترداد قرأت المدخلة والمصدر ولم تجعل فراغ الأداة نفيا. عدسة التشكيك قصرت الحكم على العضو والمصدر والمطلوب المكتوب.",
    ]
    rendered, size = R6.compact_to_limit("\n".join(lines), completion_id)
    if size > R2.MAX_CARD_BYTES:
        raise AssertionError(f"تجاوزت البطاقة {completion_id} حد الحجم: {size}")
    if "—" in rendered:
        raise AssertionError(f"شرطة طويلة في {completion_id}")
    return rendered, {
        "completion_id": completion_id, "family_id": item.family_id,
        "member_id": item.member_id, "word": item.word, "read": read,
        "closure": closure, "verdict": verdict, "bytes": size,
        "candidates": 0, "skeleton_length": len(tokens),
    }


def render_all() -> tuple[list[str], list[dict]]:
    rendered, records = [], []
    for number, item in enumerate(inventory_items(), FIRST_COMPLETION):
        card, record = inventory_card(number, item)
        rendered.append(card)
        records.append(record)
    expected_ids = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected_ids:
        raise AssertionError("معرفات الجولة العاشرة غير متصلة")
    counts = Counter(record["verdict"] for record in records)
    expected = Counter({"SEMITIC-SOURCE-TRANSMISSION": 23, "TOOL-GAP": 68})
    if counts != expected:
        raise AssertionError(f"تغيرت أحكام الجولة العاشرة: {counts}")
    return rendered, records


def reading_fragment(start: int, count: int, cards: list[str] | None = None) -> str:
    if cards is None:
        cards, _ = render_all()
    if count < 1 or start < FIRST_COMPLETION or start + count - 1 > LAST_COMPLETION:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    end = start + count - 1
    boundary = FIRST_COMPLETION + BATCH_SIZE - 1
    if start <= boundary < end:
        raise AssertionError("لا تعبر قطعة القراءة حد الدفعتين")
    batch = 1 if start <= boundary else 2
    first, last = (
        (FIRST_COMPLETION, boundary)
        if batch == 1 else (boundary + 1, LAST_COMPLETION)
    )
    selected = cards[start - FIRST_COMPLETION:start - FIRST_COMPLETION + count]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND10-BATCH-{batch}:START -->", "",
            f"## اليونانية، الجولة العاشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ الترتيب بطول الهيكل ثم موضع بطاقة الجرد الأصلي.",
            "- قُرئ قاموس الفرع والمصدر لكل عضو؛ النقل السامي المسمى حُكم مستقلا عن المروحة، وبقية الصفر سميت TOOL-GAP بمطلوبها.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND10-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round10-"))
    batches = (
        (FIRST_COMPLETION, FIRST_COMPLETION + BATCH_SIZE - 1),
        (FIRST_COMPLETION + BATCH_SIZE, LAST_COMPLETION),
    )
    for first, last in batches:
        for start in range(first, last + 1, 4):
            count = min(4, last - start + 1)
            (stage / f"{start:05d}.md").write_text(
                reading_fragment(start, count, cards), encoding="utf-8",
            )
    return stage


def emit_staged_patch(stage: Path, start: int) -> str:
    resolved = stage.resolve()
    if Path(tempfile.gettempdir()).resolve() not in resolved.parents:
        raise AssertionError("مجلد المرحل خارج مجلد النظام المؤقت")
    fragment = resolved / f"{start:05d}.md"
    if not fragment.is_file():
        raise AssertionError(f"قطعة مرحلية مفقودة: {fragment}")
    marker = (
        f"### LANE-A-OPEN-COMP-{start:05d}:"
        if start == LAST_COMPLETION
        else f"LANE-A-OPEN-COMP-{start:05d}"
    )
    return R8.emit_append_patch(
        READING, fragment.read_text(encoding="utf-8"),
        marker,
    )


def report_fragment() -> str:
    _, records = render_all()
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])
    def distribution(rows: list[dict]) -> str:
        counts = Counter(row["verdict"] for row in rows)
        return "؛ ".join(
            f"`{key}`={value}" for key, value in sorted(counts.items())
        )
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND10-REPORT:START -->", "",
        f"## {DATE}، الجولة العاشرة، دفعة إتمام الجرد المفتوح 1", "",
        "- البطاقات: 46؛ المدى: `LANE-A-OPEN-COMP-00243` إلى `LANE-A-OPEN-COMP-00288`.",
        "- توزيع الأحكام: " + distribution(first) + ".",
        "- الانتقال السامي المسمى: 18؛ فجوة الأداة المسماة: 28.", "",
        f"## {DATE}، الجولة العاشرة، دفعة إتمام الجرد المفتوح 2", "",
        "- البطاقات: 45؛ المدى: `LANE-A-OPEN-COMP-00289` إلى `LANE-A-OPEN-COMP-00333`.",
        "- توزيع الأحكام: " + distribution(second) + ".",
        "- الانتقال السامي المسمى: 5؛ فجوة الأداة المسماة: 40.", "",
        "## حصيلة الجولة العاشرة", "",
        "- مجموع البطاقات المكتوبة: 91؛ دفعتان من 46 و45 بطاقة.",
        "- معيار الجرد: استنفدت الأعضاء الـ91 الباقية بعد الجولة التاسعة؛ كانت مروحتها صفرا، فقرئ مصدر كل عضو قبل الحكم.",
        "- الأحكام الكلية: `SEMITIC-SOURCE-TRANSMISSION`=23؛ `TOOL-GAP`=68.",
        "- ضبط المصدر: الانتقالات الـ23 تحمل مانحا أو وسيطا ساميا مسمى؛ لم يجعل فراغ المروحة شرطا رابعا عليها.",
        "- المطلوب المكتوب: كل واحدة من بطاقات TOOL-GAP الـ68 تسمي توليد مرشح عربي بعد تحليل صرف منشور أو توسيع أداة مرخص.",
        "- النتائج الجذرية الجديدة: 0؛ لم يحول النقل المسمى إلى ROOT-TRACE، ولم يحول الصفر إلى NO-TRACE.",
        "- توزيع أطوال الهيكل: 0=1؛ 1=11؛ 5=54؛ 6=22؛ 7=3؛ لا عضو مكرر.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والحكمين، وعدد المروحة، والمدخلة المختارة، والمصدر المستعمل، والمطلوب عند الفجوة.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "", "<!-- LANE-A-GREEK-ROUND10-REPORT:END -->", "",
        "LANE-A DONE10 91 LANE-A-OPEN-COMP-00333",
    ])


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
        marker = (
            f"### LANE-A-OPEN-COMP-{args.start:05d}:"
            if args.start == LAST_COMPLETION
            else f"LANE-A-OPEN-COMP-{args.start:05d}"
        )
        print(R8.emit_append_patch(
            READING, reading_fragment(args.start, args.count),
            marker,
        ), end="")
    elif args.report:
        print(R8.emit_append_patch(
            REPORT, report_fragment(), "LANE-A DONE10",
        ), end="")
    else:
        _, records = render_all()
        print(f"cards={len(records)} max={max(row['bytes'] for row in records)}")
        print(Counter(row["verdict"] for row in records))
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
