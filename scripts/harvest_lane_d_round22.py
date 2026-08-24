# -*- coding: utf-8 -*-
"""مواصلة الإيرلندية القديمة بدفعتين من خمسين في الجولة 22، بلا شحن."""
from __future__ import annotations

import pathlib
import re

from harvest_lane_d_round16 import (
    BT,
    FAN,
    append,
    clean,
    clip,
    event_for,
    remove_generated_section,
    source_path,
)
from harvest_lane_d_round21 import (
    OI_FILE,
    external_witnesses,
    parse_irish_sources,
    render_no_trace,
)


ROOT = pathlib.Path(__file__).resolve().parent.parent
REPORT = ROOT / "_inbox/lane-reports/2026-08-16-D.md"
START = "LANE-D-DONE22-OLD-IRISH:START"
END = "LANE-D-DONE22-OLD-IRISH:END"
MARKER = "LANE-D-DONE22-OLD-IRISH"
REPORT_MARKER = "## الجولة الثانية والعشرون: مواصلة الإيرلندية القديمة"
DONE = "LANE-D DONE22 100 PS-GC-OLD-IRISH-01947"


# الحكم خاص بالحس المثبت في بطاقة المصدر. لا يرث متحد الرسم حكمه.
POSITIVE = {
    "PS-GC-OLD-IRISH-01867": (
        "ثبر", 1, "ROOT-TRACE",
        "الثبرة في الشاهدين حفرة أو نقرة تمسك الماء ويجتمع فيها، وهي well أو spring في معنى الفرع؛ "
        "واجتمع المعنى الصريح مع حدث الحبس والتجمع من غير زيادة شرط رابع.",
    ),
    "PS-GC-OLD-IRISH-01878": (
        "نمم", 1, "ROOT-ECHO",
        "الحكم على حس reputation وrepute وrenown وحده: ما ينقل عن المرء ويرتفع عنه ينتشر بين الناس، "
        "وهو رفع الحديث على وجه الإشاعة في العربية وحدث الانتشار إلى الظاهر.",
    ),
    "PS-GC-OLD-IRISH-01879": (
        "صلب", 1, "ROOT-ECHO",
        "الجبل والسلسلة الجبلية جرم شديد متماسك ممتد؛ والشاهد العربي يجمع الصلب بمعنى الظهر المتصل "
        "ومعنى الشديد، وهما صورة الحدث المجمد نفسها.",
    ),
    "PS-GC-OLD-IRISH-01890": (
        "برج", 1, "ROOT-ECHO",
        "الحكم لهذا الحس وحده: blister وbubble وpuffball وbud أشياء تبرز من ظاهر ما يكتنفها؛ "
        "ويعضد مدار البرعم نص تباريج النبات أزاهيره، فلا ينتقل الحكم إلى bolg البطن والكيس.",
    ),
    "PS-GC-OLD-IRISH-01895": (
        "برم", 1, "ROOT-ECHO",
        "جذر النبات يلأم النبات بالتربة ويمسكه فلا يتسيب؛ والشاهدان يصفان إبرام الحبل بجمع مفتولين "
        "وإحكام فتلهما، وهو حدث اللأم الشديد نفسه لا دعوى ترادف اسمي.",
    ),
    "PS-GC-OLD-IRISH-01899": (
        "فكر", 1, "ROOT-ECHO",
        "الكلمة وعاء معنى ذهني وناتج ترتيب المعاني وتقليبها؛ والشاهدان يسميان التأمل وإعمال الخاطر، "
        "فثبت صدى الوظيفة لا دعوى أن word مرادف للفكر.",
    ),
    "PS-GC-OLD-IRISH-01911": (
        "فرق", 1, "ROOT-ECHO",
        "الشوكة أو الرمح المشعب ينقسم إلى شعبتين أو أكثر؛ والفرق في الشاهدين خلاف الجمع وفصل بين شيئين، "
        "فاجتمع معنى التشعب مع حدث الفصل إلى العمق.",
    ),
    "PS-GC-OLD-IRISH-01929": (
        "برق", 1, "ROOT-ECHO",
        "الكذب إظهار صورة لا حقيقة لها؛ والشاهد العربي يسمي برق الخلب الذي يلمع ولا مطر فيه، "
        "فالتقى falsehood وdeception مع البروز اللامع الخادع من غير مساواة بين كل برق وكل كذب.",
    ),
    "PS-GC-OLD-IRISH-01946": (
        "كلب", 1, "ROOT-TRACE",
        "الحكم على claw وtalon وحدهما: الشاهدان يسميان كلاليب البازي مخالبه، والحدث هو العض والإمساك "
        "الشديد الذي لا يفلت؛ ولا يرث gyrfalcon أو griffin هذا الحكم لمجرد اتحاد المدخلة.",
    ),
}


WITNESS_NEEDLES = {
    "ثبر": ("تمسك الماء", "يَجتمعُ فِيهَا الماءُ", "يجتمع فيها الماء", "الحفرة في الأرض"),
    "نمم": ("رفع الحديث على وجه الإشاعة", "نمَّ الحديث", "نَمَّ الحديث", "النميمة"),
    "صلب": ("الصُّلْبُ: الظَّهر", "الصُّلْبُ والصَليب: الشديد", "الشديد"),
    "برج": ("تباريج النَّبَات", "تباريج النبات", "بُرْجُ الحِصن", "بروج المدينة"),
    "برم": ("أَبْرَمَ الحَبْلَ", "أبرمت الحبل", "الحبل الذي جُمع بين مفتولين"),
    "فكر": ("إِعْمَال الخاطر", "إعمال الخاطر", "التَفَكُّرُ: التأمل", "التأمل"),
    "فرق": ("فَرَقْتُ بين الشيئين", "خلاف الْجمع", "خلاف الجمع", "شققناه"),
    "برق": ("بَرْقُ الخُلَّب", "بَرْقُ خُلَّب", "ليس فيه مطر", "الوعد الكاذب"),
    "كلب": ("كَلَالِيبُ البازي", "كلاليب البازي", "مخالبه", "شيء يمسك به"),
}


def render_positive(row: dict[str, str], phase: str) -> str:
    source = row["source"]
    comp = "COMP-" + source
    root, tier, judgment, orbit = POSITIVE[source]
    fans = FAN.fan(row["word"], "latin")
    assert root in fans, (source, row["word"], root)
    path = source_path(row["body"], root)
    assert "لم يتحرر صف مسمى" not in path and "لا صف مسمى" not in path, (source, root, path)
    event = event_for(root, tier)
    witnesses = external_witnesses(root, WITNESS_NEEDLES[root])
    assert len(witnesses) == 2
    witness_lines = "\n".join(f"  - {name}: «{quoted}»." for name, quoted in witnesses)
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(row["word"], "latin")
    )
    return f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- {MARKER}:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: أعادت الهياكل {skeletons}؛ والمروحة الحالية {len(fans)} مادة، وقُرئت أحداثها وشواهدها.
- المقابل المختار: {BT}{root}{BT}؛ مسار الصوت: {path}
- الحدث المجمد المختار من جميع الدرجات: الدرجة {tier} ({event.tier_ar}): «{event.text}» [{event.source}].
- مسح المعاني العربية: قرئت الشواهد كاملة، ونقل هنا الشاهدان المستعملان وحدهما:
{witness_lines}
- المدار المكتوب باليد: {orbit}
- المصفاة: {clip(row['etymology'], 320)} لا يغلق القرض إلا مانح سامي مسمى، وحفظ خبر الأصل صراحة.
- فصل المتجانسات: الحكم للحس المذكور وحده، ولا ينتقل إلى معنى آخر لمجرد الرسم.
- حالة الإغلاق: READY.
- الحكم (استكشاف): {BT}{judgment}{BT}.
"""


def append_irish() -> list[dict[str, str]]:
    rows = parse_irish_sources()
    chosen = rows[100:200]
    first = chosen[:50]
    second = chosen[50:]
    assert len(first) == len(second) == 50
    assert first[0]["source"] == "PS-GC-OLD-IRISH-01848"
    assert first[-1]["source"] == "PS-GC-OLD-IRISH-01897"
    assert second[0]["source"] == "PS-GC-OLD-IRISH-01898"
    assert second[-1]["source"] == "PS-GC-OLD-IRISH-01947"
    assert set(POSITIVE) <= {row["source"] for row in chosen}

    text = OI_FILE.read_text(encoding="utf-8")
    if START in text:
        remove_generated_section(OI_FILE, START, END)

    parts = [f"""<!-- {START} -->

## الجولة الثانية والعشرون: مواصلة أحكام المسح الإيرلندي القديم

- موضع البدء: أول معرف مصدر فريد بعد {BT}PS-GC-OLD-IRISH-01847{BT} بحسب ترتيب بطاقات المسح.
- هذه الجولة دفعتان فقط من 50 و50: الأولى من {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT}، والثانية من {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT}.
- البطاقات التالية ناسخة للحكم فقط، وبطاقات المسح الأصلية والصلات الصادرة القديمة باقية بلا تعديل.

### الدفعة الأولى
"""]
    for row in first:
        if row["source"] in POSITIVE:
            parts.append(render_positive(row, "الدفعة الأولى"))
        else:
            parts.append(render_no_trace("OLD-IRISH", row, "الدفعة الأولى", MARKER))

    parts.append("\n### الدفعة الثانية\n")
    for row in second:
        if row["source"] in POSITIVE:
            parts.append(render_positive(row, "الدفعة الثانية"))
        else:
            parts.append(render_no_trace("OLD-IRISH", row, "الدفعة الثانية", MARKER))

    parts.append(f"""
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 7، و{BT}NO-TRACE{BT} عدد 91.
- ضبط المتجانسات: لم يرث {BT}bolg{BT} البطن والكيس حكم {BT}bolg{BT} البثرة والبرعم، ولم يرث السمك {BT}brecc{BT} معنى اللون، وقصر حكم {BT}gríb{BT} على المخلب دون الطائر الخرافي.
- انضباط الرجل الثالثة: بقي {BT}grán{BT} مع {BT}جرن{BT} بلا موجب لأن الحدث المجمد لم يفسر الحَب، وبقي {BT}brecc{BT} مع {BT}برق{BT} بلا موجب لأن هيكل {BT}CC{BT} لم يحرر له صف صوتي كامل.
- آخر موضع في ذيل هذا الملف: {BT}PS-GC-OLD-IRISH-01947{BT}.
- لم تشغل أداة الشحن ولم ينشأ إيداع.

{DONE}

<!-- {END} -->""")
    append(OI_FILE, "\n".join(parts))
    return chosen


def append_report(chosen: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    if REPORT_MARKER in text:
        REPORT.write_text(
            text[:text.index(REPORT_MARKER)].rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
    first = chosen[:50]
    second = chosen[50:]
    report = f"""{REPORT_MARKER}

- الوقت: 2026-08-18، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}، باستدعاء الخط {BT}latin{BT} صراحة.
- المقام: أول 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-IRISH-01847{BT} بحسب ترتيب ملفات المسح، من غير عد النسخ المدمجة المرآتية.
- انضباط الحجم: دفعتان فقط من 50 و50، وكل دفعة داخل الحد الملزم 40 إلى 60.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | 5 | 45 |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | 4 | 46 |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | 9 | 91 |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 7؛ وكل موجب يثبت مسار الصوت المسمى والحدث المجمد وشاهدين عربيين والمدار المكتوب باليد.
- الصلتان المباشرتان: {BT}topar{BT} مع {BT}ثبر{BT} في حفرة الماء، و{BT}gríb{BT} مع {BT}كلب{BT} في كلاليب البازي ومخالبه.
- الأصداء المضبوطة: {BT}ainmm{BT} مع {BT}نمم{BT} في انتشار الذكر، و{BT}slíab{BT} مع {BT}صلب{BT} في الجرم الشديد الممتد، و{BT}bolg{BT} مع {BT}برج{BT} في البروز، و{BT}frém{BT} مع {BT}برم{BT} في اللأم المحكم، و{BT}focul{BT} مع {BT}فكر{BT} في المعنى الذهني، و{BT}forc{BT} مع {BT}فرق{BT} في التشعب، و{BT}bréc{BT} مع {BT}برق{BT} في برق الخلب.
- فصل المتجانسات: قصر حكم {BT}bolg{BT} على البثرة والبرعم دون البطن والكيس، وقصر حكم {BT}gríb{BT} على المخلب دون الطائر؛ ولم يرث السمك {BT}brecc{BT} معنى اللون.
- فحص الجودة السلبي: لم ترق {BT}grán{BT} مع {BT}جرن{BT} رغم الشاهد المعجمي لأن رجل الحدث لم يفسر الحَب، ولم ترق {BT}brecc{BT} مع {BT}برق{BT} رغم المعنى لأن {BT}CC{BT} بقي بلا صف صوتي كامل، ولم يقرأ مركب {BT}lepaid{BT} جذرا واحدا عابرا لحده الصرفي.
- ألحقت الدفعتان بذيل {BT}04-cross-linguistic/readings/old-irish.md{BT}، وآخر موضع فيهما {BT}PS-GC-OLD-IRISH-01947{BT}.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل، وكل بطاقة جديدة دون 5120 بايت.
- الضبط: نقاء الشحنة {BT}CLEAN{BT}؛ لا وسم إغلاق مخترع؛ وكاشف انضباط النواة بلا زيادة جديدة من الجولة.
- لم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع ولم يحدث دفع.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    irish = OI_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    section = irish[irish.index(f"<!-- {START} -->"):]
    assert section.count(f"{MARKER}:COMP-") == 100
    assert section.count(f"- الحكم (استكشاف): {BT}ROOT-TRACE{BT}.") == 2
    assert section.count(f"- الحكم (استكشاف): {BT}ROOT-ECHO{BT}.") == 7
    assert section.count(f"- الحكم (استكشاف): {BT}NO-TRACE{BT}.") == 91
    assert section.count("### الدفعة الأولى") == 1
    assert section.count("### الدفعة الثانية") == 1
    cards = re.split(r"(?=^### بطاقة إتمام:)", section, flags=re.M)[1:]
    assert len(cards) == 100
    assert max(len(card.encode("utf-8")) for card in cards) <= 5120
    assert section.rstrip().endswith(f"<!-- {END} -->")
    assert report.rstrip().endswith(DONE)
    for addition in (section, report[report.index(REPORT_MARKER):]):
        assert "—" not in addition
        assert not re.search(r"[٠-٩]", addition)


def main() -> None:
    chosen = append_irish()
    append_report(chosen)
    verify()
    print(DONE)


if __name__ == "__main__":
    main()
