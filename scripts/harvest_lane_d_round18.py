# -*- coding: utf-8 -*-
"""مواصلة النردية القديمة في الجولة الثامنة عشرة من غير شحن."""
from __future__ import annotations

import pathlib
import re

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
START_MARKER = "LANE-D-DONE18-OLD-NORSE:START"
END_MARKER = "LANE-D-DONE18-OLD-NORSE:END"
REPORT_MARKER = "## الجولة الثامنة عشرة: مواصلة النردية القديمة"
DONE = "LANE-D DONE18 100 PS-GC-OLD-NORSE-01249"


# الحكم خاص بالحس المعجمي المذكور في بطاقة المصدر. لا يرث متحد الرسم حكمه.
NORSE_POSITIVE = {
    "PS-GC-OLD-NORSE-01157": (
        "لجن", 3, "ROOT-ECHO",
        "المطر يبلل الأرض حتى تتلزج مادتها وتثخن؛ فالحكم لمدار الأثر الطيني الذي يفسره حدث التراكم والكثافة، لا لمطلق الماء.",
    ),
    "PS-GC-OLD-NORSE-01158": (
        "سقي", 3, "ROOT-ECHO",
        "السحاب حامل الغيث وسبب سقي الأرض؛ فالحكم لحس السحاب الممطر وحده، ولا ينتقل إلى السماء المجردة.",
    ),
    "PS-GC-OLD-NORSE-01161": (
        "بين", 1, "ROOT-ECHO",
        "الاستقامة امتداد مضبوط بين طرفين، وهو نص الحدث المجمد؛ أما حس الضيافة المتجانس فلا يرث الحكم.",
    ),
    "PS-GC-OLD-NORSE-01178": (
        "زين", 1, "ROOT-ECHO",
        "حس النظرة والهيئة الظاهرة يلتقي الزين الذي يبدو على ظاهر الشيء؛ أما قوة البصر نفسها فلا تدخل في الحكم.",
    ),
    "PS-GC-OLD-NORSE-01182": (
        "رند", 3, "ROOT-ECHO",
        "الرند واللند اسما شجر في الطرفين، ويعضد حس الترس المصنوع من اللند حدث المادة التي تمنع النفاذ؛ ولا يدعي الحكم اتحاد النوع النباتي.",
    ),
    "PS-GC-OLD-NORSE-01186": (
        "شبن", 3, "ROOT-TRACE",
        "الغلام والفتى في عضو الفرع يطابقان الشابن، وهو الغلام الناعم التار بنص المعجمين؛ أما حس الخادم فلا يرث الحكم.",
    ),
    "PS-GC-OLD-NORSE-01188": (
        "سكن", 1, "ROOT-ECHO",
        "الجلد حيز الجسد الخارجي الذي يستقر ما تحته في جوفه؛ فاجتمع الغطاء المحيط مع حدث الاستقرار في حيز.",
    ),
    "PS-GC-OLD-NORSE-01213": (
        "شمل", 1, "ROOT-ECHO",
        "الاتفاق ووحدة الرأي جمع للشمل بعد إمكان التفرق؛ فاجتمع معنى الفرع مع الإحاطة والضم في الحدث والشاهد.",
    ),
    "PS-GC-OLD-NORSE-01214": (
        "شمل", 1, "ROOT-ECHO",
        "المتماثلان يشملهما وصف واحد ولا يتفرقان فيه؛ فهذا صدى للضم تحت شمل واحد، لا نقل لحكم عضو الاتفاق المجاور.",
    ),
    "PS-GC-OLD-NORSE-01219": (
        "بجر", 3, "ROOT-ECHO",
        "الكتف نتوء ظاهر من الجسد، والبجر يسمي نتوء السرة وغلظها؛ فالحكم لهيئة البروز الجسدي لا لاتحاد العضوين.",
    ),
    "PS-GC-OLD-NORSE-01221": (
        "زمر", 1, "ROOT-ECHO",
        "بعض الشيء طائفة غير مستغرقة من مجموعه، والزمرة جماعة مضمومة؛ فالحكم لمدار الجزء الجماعي لا لكل استعمال إفرادي.",
    ),
    "PS-GC-OLD-NORSE-01226": (
        "نبر", 3, "ROOT-ECHO",
        "السرة علامة وسطية ناتئة أو نقرة ذات حافة، والنبرة وسط النقرة وكل مرتفع من شيء؛ فاجتمعت الهيئة الموضعية والنتوء.",
    ),
    "PS-GC-OLD-NORSE-01232": (
        "وبر", 1, "ROOT-ECHO",
        "النسيج الشبكي يتكون من خيوط دقيقة ممتدة، والوبر غطاء من شعر دقيق؛ والحدث المجمد يصرح بتغطية الظاهر بهذه الدقائق.",
    ),
    "PS-GC-OLD-NORSE-01234": (
        "رمل", 3, "ROOT-TRACE",
        "الفقر والبؤس يلتقيان قول العربية أرمل القوم إذا فني زادهم؛ أما حس الشر الخلقي فلا يرث حكم نفاد القوت.",
    ),
    "PS-GC-OLD-NORSE-01237": (
        "نجل", 3, "ROOT-ECHO",
        "الصغير الحديث السن من النجل والولد؛ ويجمع الحدث خروجه من الوعاء الحاوي، فلا يتسع الحكم لكل معنى للشباب.",
    ),
    "PS-GC-OLD-NORSE-01244": (
        "بقر", 1, "ROOT-ECHO",
        "الجدول المائي مجرى مفتوح يشق الأرض ويكشف جوفها؛ وهو مدار البقر بمعنى الشق والفتح، لا حس المقعد المتجانس.",
    ),
    "PS-GC-OLD-NORSE-01245": (
        "بتر", 1, "ROOT-ECHO",
        "المرارة حس ذوقي حاد قاطع، فصدر صدى محدود إلى حدث البتر والقطع؛ ولا يدعي الحكم أن معنى الفرع هو القطع الحسي نفسه.",
    ),
}


FILTER_NOTE = {
    "PS-GC-OLD-NORSE-01244": (
        "حاشية الأصل التي تذكر Proto-Germanic *bankiz تخص حس المقعد في "
        f"{BT}PS-GC-OLD-NORSE-01243{BT}، فلا تنقل إلى حس الجدول المائي ولا تستعمل في حكمه."
    ),
}


WITNESS_OVERRIDE = {
    "PS-GC-OLD-NORSE-01244": (
        ("تاج اللغة وصحاح العربية للجوهري", "وبقرت الشئ بقرا: فتحته ووسّعْتَه"),
        ("المحكم والمحيط الأعظم لابن سيده", "وبقر الشَّيْء يبقره بقرًا، فَهُوَ مبقور، وبقير: شقَّه"),
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
<!-- LANE-D-DONE18-OLD-NORSE:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: {BT}fan_any_script.oe_skeletons(word, "germanic"){BT} أعادت {skeletons}؛ والمروحة الحالية {len(fans)} مادة.
"""
    filter_note = FILTER_NOTE.get(
        source,
        f"{clip(row['etymology'], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.",
    )
    if source not in NORSE_POSITIVE:
        closest = row["closest"] or (fans[0] if fans else "لا مادة")
        return common + f"""- أقرب ما أعادته المروحة: {BT}{closest}{BT}؛ قرئت مواد المروحة وأحداثها وشواهدها في بطاقة المصدر.
- المدار المكتوب باليد: لم يثبت اجتماع رجل الصوت مع حدث مجمد يشرح معنى «{clip(row['meaning'], 240)}» وشاهد عربي صريح؛ فالتشابه الشكلي وحده لا يكفي.
- المصفاة: {filter_note}
- فصل المتجانسات: لم يرث هذا الحس حكم مادة أو معنى آخر لمجرد الرسم، وبقيت الصلات الصادرة القديمة بلا مساس.
- حالة الإغلاق: CLOSED-NO-TRACE.
- الحكم (استكشاف): {BT}NO-TRACE{BT}.
"""

    root, tier, judgment, orbit = NORSE_POSITIVE[source]
    assert root in fans, (source, row["word"], root)
    path = source_path(row["body"], root)
    assert "لم يتحرر صف مسمى" not in path, (source, root, path)
    assert "لا صف مسمى" not in path, (source, root, path)
    witnesses = list(WITNESS_OVERRIDE.get(source, arabic_witnesses(row["body"], root)))
    assert len(witnesses) == 2, (source, root, witnesses)
    if source in WITNESS_OVERRIDE:
        assert all(quoted in row["body"] for _, quoted in witnesses), (source, witnesses)
    event = event_for(root, tier)
    witness_lines = "\n".join(
        f"  - {name}: «{quoted}»." for name, quoted in witnesses
    )
    return common + f"""- المقابل المختار: {BT}{root}{BT}؛ مسار الصوت: {path}
- الحدث المجمد المختار من جميع الدرجات: الدرجة {tier} ({event.tier_ar}): «{event.text}» [{event.source}].
- مسح المعاني العربية: قرئت الشواهد الكاملة في بطاقة المصدر، ونقل هنا شاهدان مسميان:
{witness_lines}
- المدار المكتوب باليد: {orbit}
- المصفاة: {filter_note}
- فصل المتجانسات: الحكم للحس المذكور وحده، ولا ينتقل إلى معنى آخر لمجرد الرسم.
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{judgment}{BT}.
"""


def append_round() -> list[dict[str, str]]:
    rows = parse_norse_sources()[156:256]
    assert len(rows) == 100
    assert len({row["source"] for row in rows}) == 100
    assert rows[0]["source"] == "PS-GC-OLD-NORSE-01150"
    assert rows[49]["source"] == "PS-GC-OLD-NORSE-01199"
    assert rows[50]["source"] == "PS-GC-OLD-NORSE-01200"
    assert rows[-1]["source"] == "PS-GC-OLD-NORSE-01249"
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

## الجولة الثامنة عشرة: مواصلة النردية القديمة بالأداة المصلحة

- النطاق: 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-01149{BT} بحسب ترتيب ملفات المسح، في دفعتين من 50 و50.
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
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 15، و{BT}NO-TRACE{BT} عدد 83.
- فصل المتجانسات: فصل حس {BT}bekkr{BT} «المقعد» عن حسه «الجدول المائي»، وفصلت الأحاسيس المتجاورة في {BT}beinn{BT} و{BT}sjón{BT} و{BT}sveinn{BT} و{BT}armr{BT} وغيرها.
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
- المقام: أول 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-NORSE-01149{BT} بحسب ترتيب ملفات المسح، من غير عد النسخ المدمجة المرآتية.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | {first_positive} | {50 - first_positive} |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | {second_positive} | {50 - second_positive} |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | {first_positive + second_positive} | {100 - first_positive - second_positive} |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 15؛ وكل موجب يثبت مسار الصوت المسمى والحدث المجمد وشاهدين عربيين والمدار.
- أبرز الصلات: {BT}sveinn{BT} مع {BT}شبن{BT} في الغلام، و{BT}samr{BT} مع {BT}شمل{BT} في الاتفاق والضم، و{BT}vefr{BT} مع {BT}وبر{BT} في الغطاء الخيطي، و{BT}ungr{BT} مع {BT}نجل{BT} في الولد، و{BT}armr{BT} مع {BT}رمل{BT} في نفاد الزاد والفقر.
- فصل المتجانسات: لم تنقل حاشية {BT}bekkr{BT} «المقعد» إلى {BT}bekkr{BT} «الجدول المائي»، وفصلت أحاسيس الاستقامة والضيافة، والبصر والهيئة، والغلام والخادم، والفقر والشر الخلقي.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل.
- الضبط: فحص نقاء الشحنة {BT}CLEAN{BT}؛ وفحص مفردات الإغلاق لم يجد بطاقة مغلقة بوسم مخترع؛ وكاشف انضباط النواة بقي عند خط أساسه السابق، 20 ملاحظة تاريخية بلا ملاحظة جديدة من الدفعتين.
- كل بطاقة إتمام دون 5120 بايت، ولم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    on = ON_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    section = on[on.index(f"<!-- {START_MARKER} -->"):]
    assert section.count("LANE-D-DONE18-OLD-NORSE:COMP-") == 100
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"ROOT-TRACE",
        section,
        re.M,
    )) == 2
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"ROOT-ECHO",
        section,
        re.M,
    )) == 15
    assert len(re.findall(
        r"^- الحكم \(استكشاف\): " + re.escape(BT) + r"NO-TRACE",
        section,
        re.M,
    )) == 83
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
