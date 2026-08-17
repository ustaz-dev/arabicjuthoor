# -*- coding: utf-8 -*-
"""مواصلة النردية القديمة في الجولة السابعة عشرة من غير شحن."""
from __future__ import annotations

import pathlib
import re

from harvest_lane_d_round16 import (
    BT,
    EVENT,
    FAN,
    ON_FILE,
    REPORT,
    append,
    arabic_witnesses,
    clean,
    clip,
    event_for,
    parse_norse_sources,
    remove_generated_section,
    source_path,
)


ROOT = pathlib.Path(__file__).resolve().parent.parent
START_MARKER = "LANE-D-DONE17-OLD-NORSE:START"
END_MARKER = "LANE-D-DONE17-OLD-NORSE:END"
REPORT_MARKER = "## الجولة السابعة عشرة: مواصلة النردية القديمة"
DONE = "LANE-D DONE17 100 PS-GC-OLD-NORSE-01149"


# الحكم خاص بالحس المعجمي المذكور في بطاقة المصدر. لا يرث متحد الرسم حكمه.
NORSE_POSITIVE = {
    "PS-GC-OLD-NORSE-00210": (
        "زمر", 1, "ROOT-ECHO",
        "الصغر في عضو الفرع يلتقي القلة المنصوصة في زمر؛ ويجمع الحدث ذلك في تضام الشيء واكتنازه.",
    ),
    "PS-GC-OLD-NORSE-00216": (
        "دفن", 3, "ROOT-ECHO",
        "حس الموت وحده يلتقي مواراة الميت وستر جسده في الدفن؛ أما حس النعاس المتجانس فلا يرث الحكم.",
    ),
    "PS-GC-OLD-NORSE-00217": (
        "زين", 1, "ROOT-ECHO",
        "حس الهيئة والمنظر يلتقي ما يبدو على ظاهر الشيء من زين؛ أما قوة البصر نفسها فليست موضع الحكم.",
    ),
    "PS-GC-OLD-NORSE-00224": (
        "قيل", 1, "ROOT-ECHO",
        "التسكين والتهدئة ينقلان الشيء إلى حال راحة وسكون؛ والقيلولة شاهد عربي مسمى على هذا المقر المؤقت.",
    ),
    "PS-GC-OLD-NORSE-00225": (
        "بتر", 1, "ROOT-ECHO",
        "حدة آلة القطع هي قدرتها على البتر؛ فاجتمع وصف الآلة في الفرع مع فعل القطع والحدث العربي.",
    ),
    "PS-GC-OLD-NORSE-00226": (
        "زين", 1, "ROOT-ECHO",
        "الهيئة الظاهرة والوجه يلتقيان الزين المتعلق بظاهر الشيء؛ والحكم لحس الصورة الخارجية لا لكل ظهور.",
    ),
    "PS-GC-OLD-NORSE-00227": (
        "مين", 3, "ROOT-ECHO",
        "حس الجرم والإساءة يضم الكذب بوصفه فعلا معيبا؛ والمين هو الكذب بنص المعجمين، لا مطلق الضرر.",
    ),
    "PS-GC-OLD-NORSE-00235": (
        "قلف", 3, "ROOT-TRACE",
        "القص والجز في الفرع يوافقان قطع القلفة واقتلاع الظفر في الشاهد العربي؛ فالمعنى فعل قطع مسمى.",
    ),
    "PS-GC-OLD-NORSE-01089": (
        "برج", 1, "ROOT-ECHO",
        "الصخرة والجرف نتوء مرتفع بارز، وبرج الحصن ركنه البارز؛ فاجتمع البروز القوي مع هيئة الارتفاع.",
    ),
    "PS-GC-OLD-NORSE-01101": (
        "مرد", 1, "ROOT-ECHO",
        "الأرض والتراب يلتقيان الرملة المرداء العارية من النبات؛ والحكم لهذا الحس الأرضي المحدود وحده.",
    ),
    "PS-GC-OLD-NORSE-01122": (
        "ندر", 3, "ROOT-ECHO",
        "النهاية خروج من امتداد الشيء وانقطاع عنه؛ وندر في الشاهد سقوط وخروج من بين الأشياء.",
    ),
}


def render_card(row: dict[str, str], index: int) -> str:
    source = row["source"]
    comp = "COMP-" + source
    phase = "الدفعة الأولى" if index <= 50 else "الدفعة الثانية"
    fans = FAN.fan(row["word"], "germanic")
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(row["word"], "germanic")
    )
    common = f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- LANE-D-DONE17-OLD-NORSE:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: {BT}fan_any_script.oe_skeletons(word, "germanic"){BT} أعادت {skeletons}؛ والمروحة الحالية {len(fans)} مادة.
"""
    if source not in NORSE_POSITIVE:
        closest = row["closest"] or (fans[0] if fans else "لا مادة")
        return common + f"""- أقرب ما أعادته المروحة: {BT}{closest}{BT}؛ قرئت مواد المروحة وأحداثها وشواهدها في بطاقة المصدر.
- المدار المكتوب باليد: لم يثبت اجتماع رجل الصوت مع حدث مجمد يشرح معنى «{clip(row['meaning'], 240)}» وشاهد عربي صريح؛ فالتشابه الشكلي وحده لا يكفي.
- المصفاة: {clip(row['etymology'], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: لم يرث هذا الحس حكم مادة أو معنى آخر لمجرد الرسم، وبقيت الصلات الصادرة القديمة بلا مساس.
- حالة الإغلاق: CLOSED-NO-TRACE.
- الحكم (استكشاف): {BT}NO-TRACE{BT}.
"""

    root, tier, judgment, orbit = NORSE_POSITIVE[source]
    assert root in fans, (source, row["word"], root)
    path = source_path(row["body"], root)
    assert "لم يتحرر صف مسمى" not in path, (source, root, path)
    assert "لا صف مسمى" not in path, (source, root, path)
    witnesses = arabic_witnesses(row["body"], root)
    assert len(witnesses) == 2, (source, root, witnesses)
    event = event_for(root, tier)
    witness_lines = "\n".join(
        f"  - {name}: «{quoted}»." for name, quoted in witnesses
    )
    return common + f"""- المقابل المختار: {BT}{root}{BT}؛ مسار الصوت: {path}
- الحدث المجمد المختار من جميع الدرجات: الدرجة {tier} ({event.tier_ar}): «{event.text}» [{event.source}].
- مسح المعاني العربية: قرئت الشواهد الكاملة في بطاقة المصدر، ونقل هنا شاهدان مسميان:
{witness_lines}
- المدار المكتوب باليد: {orbit}
- المصفاة: {clip(row['etymology'], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: الحكم للحس المذكور وحده، ولا ينتقل إلى معنى آخر لمجرد الرسم.
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{judgment}{BT}.
"""


def append_round() -> list[dict[str, str]]:
    rows = parse_norse_sources()[56:156]
    assert len(rows) == 100
    assert len({row["source"] for row in rows}) == 100
    assert rows[0]["source"] == "PS-GC-OLD-NORSE-00205"
    assert rows[49]["source"] == "PS-GC-OLD-NORSE-01099"
    assert rows[50]["source"] == "PS-GC-OLD-NORSE-01100"
    assert rows[-1]["source"] == "PS-GC-OLD-NORSE-01149"
    assert set(NORSE_POSITIVE) <= {row["source"] for row in rows}

    text = ON_FILE.read_text(encoding="utf-8")
    if START_MARKER in text:
        remove_generated_section(ON_FILE, START_MARKER, END_MARKER)

    first = rows[:50]
    second = rows[50:]
    first_positive = sum(row["source"] in NORSE_POSITIVE for row in first)
    second_positive = sum(row["source"] in NORSE_POSITIVE for row in second)
    parts = [
        f"""<!-- {START_MARKER} -->

## الجولة السابعة عشرة: مواصلة النردية القديمة بالأداة المصلحة

- النطاق: 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-00204{BT} بحسب ترتيب ملفات المسح، في دفعتين من 50 و50.
- الدفعة الأولى: من {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT}؛ الموجب {first_positive}، و{BT}NO-TRACE{BT} عدد {50 - first_positive}.
- الدفعة الثانية: من {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT}؛ الموجب {second_positive}، و{BT}NO-TRACE{BT} عدد {50 - second_positive}.
- تقفز المعرفات بعد {BT}PS-GC-OLD-NORSE-00236{BT} إلى {BT}PS-GC-OLD-NORSE-01082{BT} مع انتقال ملف المصدر؛ لم تسقط بطاقة من ترتيب المسح النردي.
- البطاقات التالية ناسخة للحكم فقط وتذكر معرف المصدر؛ بطاقات المسح الأصلية والصلات الصادرة القديمة باقية بلا تعديل.

### الدفعة الأولى
"""
    ]
    for index, row in enumerate(first, 1):
        parts.append(render_card(row, index))
    parts.append("\n### الدفعة الثانية\n")
    for index, row in enumerate(second, 51):
        parts.append(render_card(row, index))
    parts.append(
        f"""
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 1، و{BT}ROOT-ECHO{BT} عدد 10، و{BT}NO-TRACE{BT} عدد 89.
- الضبط: نقاء الشحنة {BT}CLEAN{BT}؛ ولا بطاقة مغلقة بوسم مخترع؛ وكاشف انضباط النواة بقي عند خط أساسه التاريخي، 20 ملاحظة بلا زيادة من الجولة.
- لم تشغل أداة الشحن ولم ينشأ إيداع.

{DONE}

<!-- {END_MARKER} -->"""
    )
    append(ON_FILE, "\n".join(parts))
    return rows


def append_report(rows: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    if REPORT_MARKER in text:
        REPORT.write_text(
            text[:text.index(REPORT_MARKER)].rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
    first = rows[:50]
    second = rows[50:]
    first_positive = sum(row["source"] in NORSE_POSITIVE for row in first)
    second_positive = sum(row["source"] in NORSE_POSITIVE for row in second)
    report = f"""{REPORT_MARKER}

- الوقت: 2026-08-17، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}، باستدعاء الخط {BT}germanic{BT} صراحة.
- المقام: أول 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-00204{BT} بحسب ترتيب ملفات المسح، من غير عد النسخ المدمجة المرآتية.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | {first_positive} | {50 - first_positive} |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | {second_positive} | {50 - second_positive} |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | {first_positive + second_positive} | {100 - first_positive - second_positive} |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 1، و{BT}ROOT-ECHO{BT} عدد 10؛ وكل موجب يثبت مسار الصوت المسمى والحدث المجمد وشاهدين عربيين والمدار.
- القفزة من {BT}PS-GC-OLD-NORSE-00236{BT} إلى {BT}PS-GC-OLD-NORSE-01082{BT} انتقال بين ملفي مصدر في الترتيب نفسه، لا فجوة عمل.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل، وفصلت الأحاسيس المتجانسة في {BT}dofinn{BT} و{BT}sýn{BT} و{BT}mein{BT} وغيرها.
- الضبط: فحص نقاء الشحنة {BT}CLEAN{BT}؛ وفحص مفردات الإغلاق لم يجد بطاقة مغلقة بوسم مخترع؛ وكاشف انضباط النواة بقي عند خط أساسه السابق، 20 ملاحظة تاريخية بلا ملاحظة جديدة من الدفعتين.
- كل بطاقة إتمام دون 5120 بايت، ولم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    on = ON_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    section = on[on.index(f"<!-- {START_MARKER} -->"):]
    assert section.count("LANE-D-DONE17-OLD-NORSE:COMP-") == 100
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"(?!NO-TRACE)",
        section,
        re.M,
    )) == 11
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"NO-TRACE",
        section,
        re.M,
    )) == 89
    cards = re.split(r"(?=^### بطاقة إتمام:)", section, flags=re.M)[1:]
    assert len(cards) == 100
    assert max(len(card.encode("utf-8")) for card in cards) <= 5120
    assert section.rstrip().endswith(f"<!-- {END_MARKER} -->")
    assert report.rstrip().endswith(DONE)
    for addition in (section, report[report.index(REPORT_MARKER):]):
        assert "—" not in addition
        assert not re.search(r"[٠-٩]", addition)


def main() -> None:
    rows = append_round()
    append_report(rows)
    verify()
    print(DONE)


if __name__ == "__main__":
    main()
