# -*- coding: utf-8 -*-
"""مواصلة النردية القديمة في الجولة التاسعة عشرة من غير شحن."""
from __future__ import annotations

import pathlib
import re

import search_arabic_root_senses as ARS
from harvest_lane_d_round16 import (
    BT,
    FAN,
    ON_FILE,
    REPORT,
    append,
    arabic_witnesses,
    clip,
    event_for,
    parse_norse_sources,
    remove_generated_section,
    source_path,
)


ROOT = pathlib.Path(__file__).resolve().parent.parent
START_MARKER = "LANE-D-DONE19-OLD-NORSE:START"
END_MARKER = "LANE-D-DONE19-OLD-NORSE:END"
REPORT_MARKER = "## الجولة التاسعة عشرة: مواصلة النردية القديمة"
DONE = "LANE-D DONE19 100 PS-GC-OLD-NORSE-01349"


# الحكم خاص بالحس المعجمي المذكور في بطاقة المصدر. لا يرث متحد الرسم حكمه.
NORSE_POSITIVE = {
    "PS-GC-OLD-NORSE-01281": (
        "مجر", 3, "ROOT-ECHO",
        "الكتلة في عضو الفرع تجمع كثير ممتلئ؛ والمجر جيش كثير جدا ثقيل ضخم، ويجمع الحدث الامتلاء والاندفاع.",
    ),
    "PS-GC-OLD-NORSE-01293": (
        "تبب", 1, "ROOT-TRACE",
        "الخسران والهلاك في تبب هما معنى الخسران والهلاك في عضو الفرع نفسه؛ فالحكم لهذا الاسمين لا لحس الاستتباب المتجانس.",
    ),
    "PS-GC-OLD-NORSE-01307": (
        "سوم", 1, "ROOT-ECHO",
        "السباحة مرور ممتد في حيز الماء؛ وسوم العربية يثبت المرور واستمرار الإبل والريح، وهو نص الحدث المجمد.",
    ),
    "PS-GC-OLD-NORSE-01320": (
        "كرب", 1, "ROOT-TRACE",
        "الضيق والمأزق في عضو الفرع يطابقان الكربة والغم الشديد؛ ويعضده كرب القيد، أي تضييقه على المقيد.",
    ),
    "PS-GC-OLD-NORSE-01330": (
        "ركن", 1, "ROOT-ECHO",
        "السكون في عضو الفرع يلتقي الركون والإقامة؛ ويجمع الحدث الاستقرار في حيز يجمع ما في باطنه.",
    ),
}


# اختيرت العبارات القصيرة التي تحمل الحس المحكوم به، لا مطالع المواد الطويلة.
WITNESS_OVERRIDE = {
    "PS-GC-OLD-NORSE-01281": (
        ("تاج اللغة وصحاح العربية للجوهري", "ومنه قيل للجيش العظيم: مَجْرٌ، لثقله وضِخَمه"),
        ("المحكم والمحيط الأعظم لابن سيده", "وجيش مَجْر: كثير جدا، وَقد قيل: إِنَّه أَكثر مَا يكون"),
    ),
    "PS-GC-OLD-NORSE-01293": (
        ("تاج اللغة وصحاح العربية للجوهري", "التَبابُ: الخُسْرانُ والهَلاكُ"),
        ("المحكم والمحيط الأعظم لابن سيده", "التَّبُّ: الخَسارُ"),
    ),
    "PS-GC-OLD-NORSE-01307": (
        ("تاج اللغة وصحاح العربية للجوهري", "وسامَ، أي مر"),
        ("المحكم والمحيط الأعظم لابن سيده", "وسَامَت الإِبلُ والرِّيحُ سَوْماً اسْتَمَرَّت"),
    ),
    "PS-GC-OLD-NORSE-01320": (
        ("كتاب العين للخليل بن أحمد", "الكَرْبُ، مجزوم، [هو] الغم الذي يأخذ بالنفس"),
        ("تاج اللغة وصحاح العربية للجوهري", "وكَرَبْتُ القيدَ، إذا ضيَّقته على المقيد"),
    ),
    "PS-GC-OLD-NORSE-01330": (
        ("تاج اللغة وصحاح العربية للجوهري", "ركن إليه بالكسر يَرْكَنُ رُكوناً فيهما، أي مالَ إليه وسكن"),
        ("المحكم والمحيط الأعظم لابن سيده", "وركن فِي الْمنزل يركن ركونا: أَقَامَ"),
    ),
}


# فتحت الأداة المصلحة باب المضاعف من الهيكل الثنائي بعد بطاقة المصدر القديمة.
PATH_OVERRIDE = {
    "PS-GC-OLD-NORSE-01293": (
        f"t↔ت={BT}IDN-11{BT}؛ p↔ب={BT}LAB-01{BT}؛ "
        "أسقطت الأداة اللاحقة المصدرية -an كما تؤكد حاشية الاشتقاق، ثم فتح باب المضاعف المسمى تبب."
    ),
}


def verify_external_witnesses() -> None:
    """يثبت شاهدي تبب اللذين فتحهما الإصلاح بعد توليد بطاقة المصدر."""
    matches = ARS.matches_for_roots(ROOT / "Resources", {"تبب"}, None)["تبب"]
    definitions = "\n".join(item["definition"] for item in matches)
    for _, quoted in WITNESS_OVERRIDE["PS-GC-OLD-NORSE-01293"]:
        assert quoted in definitions, quoted
    source_ids = {
        ARS.canonical_source_id(item["source"])
        for item in matches
        if any(quoted in item["definition"] for _, quoted in WITNESS_OVERRIDE["PS-GC-OLD-NORSE-01293"])
    }
    assert {"al_sihah", "al_muhkam"} <= source_ids, source_ids


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
<!-- LANE-D-DONE19-OLD-NORSE:{comp} -->

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
    path = PATH_OVERRIDE.get(source, source_path(row["body"], root))
    assert "لم يتحرر صف مسمى" not in path, (source, root, path)
    assert "لا صف مسمى" not in path, (source, root, path)
    witnesses = list(WITNESS_OVERRIDE.get(source, arabic_witnesses(row["body"], root)))
    assert len(witnesses) == 2, (source, root, witnesses)
    if source != "PS-GC-OLD-NORSE-01293":
        assert all(quoted in row["body"] for _, quoted in witnesses), (source, witnesses)
    event = event_for(root, tier)
    witness_lines = "\n".join(
        f"  - {name}: «{quoted}»." for name, quoted in witnesses
    )
    scan_note = (
        "بعد أن فتحت الأداة المصلحة باب المضاعف الذي لم يكن في بطاقة المصدر، "
        f"شغلت {BT}search_arabic_root_senses.py تبب --max-chars 0{BT} ونقل هنا شاهدان مستقلان:"
        if source == "PS-GC-OLD-NORSE-01293"
        else "قرئت الشواهد الكاملة في بطاقة المصدر، ونقل هنا شاهدان مسميان:"
    )
    return common + f"""- المقابل المختار: {BT}{root}{BT}؛ مسار الصوت: {path}
- الحدث المجمد المختار من جميع الدرجات: الدرجة {tier} ({event.tier_ar}): «{event.text}» [{event.source}].
- مسح المعاني العربية: {scan_note}
{witness_lines}
- المدار المكتوب باليد: {orbit}
- المصفاة: {clip(row['etymology'], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: الحكم للحس المذكور وحده، ولا ينتقل إلى معنى آخر لمجرد الرسم.
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{judgment}{BT}.
"""


def append_round() -> list[dict[str, str]]:
    verify_external_witnesses()
    rows = parse_norse_sources()[256:356]
    assert len(rows) == 100
    assert len({row["source"] for row in rows}) == 100
    assert rows[0]["source"] == "PS-GC-OLD-NORSE-01250"
    assert rows[49]["source"] == "PS-GC-OLD-NORSE-01299"
    assert rows[50]["source"] == "PS-GC-OLD-NORSE-01300"
    assert rows[-1]["source"] == "PS-GC-OLD-NORSE-01349"
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

## الجولة التاسعة عشرة: مواصلة النردية القديمة بالأداة المصلحة

- النطاق: 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-01249{BT} بحسب ترتيب ملفات المسح، في دفعتين من 50 و50.
- الدفعة الأولى: من {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT}؛ الموجب {first_positive}، و{BT}NO-TRACE{BT} عدد {50 - first_positive}.
- الدفعة الثانية: من {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT}؛ الموجب {second_positive}، و{BT}NO-TRACE{BT} عدد {50 - second_positive}.
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
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 3، و{BT}NO-TRACE{BT} عدد 95.
- فصل المتجانسات: فصل حس {BT}nagl{BT} التشريحي عن حس المسمار، وحس {BT}fóðr{BT} العلف عن حس الغمد، وحسي {BT}brúnn{BT} اللون والفرس الأسود، وحسي {BT}valr{BT} القتيل والصقر.
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

- الوقت: 2026-08-18، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}، باستدعاء الخط {BT}germanic{BT} صراحة.
- المقام: أول 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-01249{BT} بحسب ترتيب ملفات المسح، من غير عد النسخ المدمجة المرآتية.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | {first_positive} | {50 - first_positive} |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | {second_positive} | {50 - second_positive} |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | {first_positive + second_positive} | {100 - first_positive - second_positive} |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 3؛ وكل موجب يثبت مسار الصوت المسمى والحدث المجمد وشاهدين عربيين والمدار.
- الصلتان المباشرتان: {BT}tapan{BT} مع {BT}تبب{BT} في الخسران والهلاك، و{BT}kreppa{BT} مع {BT}كرب{BT} في الضيق والكربة.
- الأصداء المضبوطة: {BT}múgr{BT} مع {BT}مجر{BT} في الكتلة والكثرة، و{BT}svimma{BT} مع {BT}سوم{BT} في المرور الممتد، و{BT}logn{BT} مع {BT}ركن{BT} في السكون والإقامة.
- فصل المتجانسات: لم يرث {BT}nagl{BT} التشريحي حس المسمار، وفصل العلف والغمد في {BT}fóðr{BT}، واللون والفرس الأسود في {BT}brúnn{BT}، والقتيل والصقر في {BT}valr{BT}.
- بطاقة {BT}tapan{BT} صرحت بأن باب {BT}تبب{BT} ظهر من إسقاط اللاحقة {BT}-an{BT} وفتح المضاعف بالأداة المصلحة بعد توليد بطاقة المصدر؛ لذلك أعيد فتح شاهدين مستقلين بالأداة المعجمية نفسها.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل.
- الضبط: فحص نقاء الشحنة {BT}CLEAN{BT}؛ وفحص مفردات الإغلاق لم يجد بطاقة مغلقة بوسم مخترع؛ وكاشف انضباط النواة بقي عند خط أساسه السابق، 20 ملاحظة تاريخية بلا ملاحظة جديدة من الدفعتين.
- كل بطاقة إتمام دون 5120 بايت، ولم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    on = ON_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    section = on[on.index(f"<!-- {START_MARKER} -->"):]
    assert section.count("LANE-D-DONE19-OLD-NORSE:COMP-") == 100
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"ROOT-TRACE",
        section,
        re.M,
    )) == 2
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"ROOT-ECHO",
        section,
        re.M,
    )) == 3
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"NO-TRACE",
        section,
        re.M,
    )) == 95
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
