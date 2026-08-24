# -*- coding: utf-8 -*-
"""مواصلة الإيرلندية القديمة بدفعتين من خمسين في الجولة 23، بلا شحن."""
from __future__ import annotations

import pathlib
import re

from harvest_lane_d_round16 import (
    BT,
    FAN,
    append,
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
START = "LANE-D-DONE23-OLD-IRISH:START"
END = "LANE-D-DONE23-OLD-IRISH:END"
MARKER = "LANE-D-DONE23-OLD-IRISH"
REPORT_MARKER = "## الجولة الثالثة والعشرون: مواصلة الإيرلندية القديمة"
DONE = "LANE-D DONE23 100 PS-GC-OLD-IRISH-02047"


# الحكم خاص بالحس المثبت في بطاقة المصدر. لا يرث متحد الرسم حكمه.
# NO-TRACE حكم كامل؛ لذلك لم تدخل medc ولا scaraid ولا engach مع قرب المعنى.
POSITIVE = {
    "PS-GC-OLD-IRISH-01960": (
        "جرن",
        3,
        "ROOT-TRACE",
        "الحكم على حس dish أو receptacle وحده: الجرن العربي حجر منقور يصب فيه الماء، "
        "فهو وعاء حجري صريح؛ واجتمع معنى الاحتواء مع حدث النواة الذي ينتهي بحبس النون في الجوف.",
    ),
    "PS-GC-OLD-IRISH-01961": (
        "قرن",
        1,
        "ROOT-ECHO",
        "الحكم على حس victory وtriumph وحده: أقرن للأمر إذا أطاقه وقوي عليه، "
        "ومن غلب قرنه علا وبرز في مقدمة المقارنة؛ فلا يرث حس الوعاء هذا الحكم.",
    ),
    "PS-GC-OLD-IRISH-01998": (
        "قرن",
        1,
        "ROOT-ECHO",
        "نقطة السلاح نتوء حاد في مقدمه، والقرن نتوء المقدمة نفسه؛ "
        "وتثبت العربية أن أسنة الرماح صنعت من القرون، فالحكم لصدى الهيئة والوظيفة لا لترادف الاسمين.",
    ),
    "PS-GC-OLD-IRISH-02004": (
        "مني",
        3,
        "NUCLEUS-TRACE",
        "اشتقاق الفرع يرد الصفة إلى mían مع اللاحقة -ach؛ والمُنية ما يتمناه المرء ويريده، "
        "وهو desirous وeager وwishful مباشرة، لكن الحكم يبقى في طبقة النواة البعيدة m-n.",
    ),
    "PS-GC-OLD-IRISH-02028": (
        "دبل",
        3,
        "ROOT-TRACE",
        "الدبل في العربية جدول ماء مصلح منقى، والجمع دُبول؛ "
        "وهو مجرى الماء أو river في معنى الفرع، ويوافق جريان اللام الممتد في الحدث المجمد.",
    ),
    "PS-GC-OLD-IRISH-02038": (
        "تبل",
        3,
        "ROOT-TRACE",
        "الموت والفناء في الفرع هما ما تصفه العربية بقولها تبلهم الدهر وأتبلهم أي أفناهم؛ "
        "والحدث المجمد ذهاب غلظ الشيء وضعف تجمعه حتى الفناء.",
    ),
}


PATH_OVERRIDE = {
    "PS-GC-OLD-IRISH-01998": (
        f"g الفرعية تبلغ ق العربية بالسلسلة {BT}GUT-02{BT} ثم {BT}GUT-01{BT}؛ "
        f"r↔ر={BT}IDN-01{BT}؛ n↔ن={BT}IDN-03{BT}."
    ),
    "PS-GC-OLD-IRISH-02004": (
        f"اشتقاق الفرع المنشور يفصل {BT}-ach{BT} من {BT}mían{BT}؛ "
        f"ومرساة العائلة المثبتة في {BT}COMP-PS-GC-OLD-IRISH-00112{BT} تعطي "
        f"m↔م={BT}IDN-02{BT} وn↔ن={BT}IDN-03{BT}، ثم يثبت باب المعتل المسمى ياء الآخر؛ "
        "فالحكم نواتي لا جذري."
    ),
    "PS-GC-OLD-IRISH-02038": (
        f"t↔ت={BT}IDN-11{BT}؛ b↔ب={BT}IDN-05{BT}؛ "
        f"والأداة تجمع {BT}LL{BT} في صامت واحد ثم l↔ل={BT}IDN-04{BT}."
    ),
}


WITNESS_NEEDLES = {
    "PS-GC-OLD-IRISH-01960": (
        "حجر منقور",
        "A hollowed stone",
    ),
    "PS-GC-OLD-IRISH-01961": (
        "أطاقها وغلبها",
        "أطاق وقوى واعتلى",
        "غلبناه",
    ),
    "PS-GC-OLD-IRISH-01998": (
        "رمح مقرون: سنانه من قرن",
        "أسنة رماحهم من قُرُون",
        "القَرْنُ للثَور",
    ),
    "PS-GC-OLD-IRISH-02004": (
        "وتَمنَّى الشيءَ أَرَادَهُ",
        "الأُمْنِيَّةُ الصُّورَةُ الحاصِلَةُ",
        "جمع المُنية، وهو ما يَتَمَنَّى الرجل",
    ),
    "PS-GC-OLD-IRISH-02028": (
        "دُبول أَي جَداول ماء",
        "الجَداوِلُ دُبُولاً",
    ),
    "PS-GC-OLD-IRISH-02038": (
        "تَبَلَهُمُ الدهرُ وأَتْبَلَهُمْ، أي أفناهم",
        "رَماهم بصُروفِ الموت",
    ),
}


def render_positive(row: dict[str, str], phase: str) -> str:
    source = row["source"]
    comp = "COMP-" + source
    root, tier, judgment, orbit = POSITIVE[source]
    fans = FAN.fan(row["word"], "latin")
    assert root in fans or source == "PS-GC-OLD-IRISH-02004", (
        source,
        row["word"],
        root,
    )
    path = PATH_OVERRIDE.get(source, source_path(row["body"], root))
    assert "لم يتحرر صف مسمى" not in path and "لا صف مسمى" not in path, (
        source,
        root,
        path,
    )
    event = event_for(root, tier)
    witnesses = external_witnesses(root, WITNESS_NEEDLES[source])
    assert len(witnesses) == 2
    witness_lines = "\n".join(
        f"  - {name}: «{quoted}»." for name, quoted in witnesses
    )
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(row["word"], "latin")
    )
    morphology = (
        "؛ وفتحت حاشية الاشتقاق مرساة mían بعد فصل -ach"
        if source == "PS-GC-OLD-IRISH-02004"
        else ""
    )
    return f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- {MARKER}:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: أعادت الهياكل {skeletons}؛ والمروحة الحالية {len(fans)} مادة{morphology}، وقُرئت أحداثها وشواهدها.
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
    chosen = rows[200:300]
    first = chosen[:50]
    second = chosen[50:]
    assert len(first) == len(second) == 50
    assert first[0]["source"] == "PS-GC-OLD-IRISH-01948"
    assert first[-1]["source"] == "PS-GC-OLD-IRISH-01997"
    assert second[0]["source"] == "PS-GC-OLD-IRISH-01998"
    assert second[-1]["source"] == "PS-GC-OLD-IRISH-02047"
    assert set(POSITIVE) <= {row["source"] for row in chosen}

    text = OI_FILE.read_text(encoding="utf-8")
    if START in text:
        remove_generated_section(OI_FILE, START, END)

    parts = [f"""<!-- {START} -->

## الجولة الثالثة والعشرون: مواصلة أحكام المسح الإيرلندي القديم

- موضع البدء: أول معرف مصدر فريد بعد {BT}PS-GC-OLD-IRISH-01947{BT} بحسب ترتيب بطاقات المسح.
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
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 3، و{BT}ROOT-ECHO{BT} عدد 2، و{BT}NUCLEUS-TRACE{BT} عدد 1، و{BT}NO-TRACE{BT} عدد 94.
- ضبط القرار السلبي: بقي {BT}medc{BT} مع {BT}مذق{BT} بلا موجب لأن whey ليست اللبن الممزوج بالماء ولأن الحدث لم يجاوز الدرجة الرابعة، وبقي {BT}scaraid{BT} مع {BT}شرد{BT} و{BT}engach{BT} مع {BT}نجخ{BT} بلا موجب لغياب صف صوتي جامع.
- انضباط النواة: حكم {BT}míanach{BT} عند مرساة {BT}mían{BT} وفي طبقة النواة البعيدة، ولم يرق إلى الجذر الكامل.
- آخر موضع في ذيل هذا الملف: {BT}PS-GC-OLD-IRISH-02047{BT}.
- لم تشغل أداة الشحن ولم ينشأ إيداع.

{DONE}

<!-- {END} -->""")
    append(OI_FILE, "\n".join(parts))
    return chosen


def append_report(chosen: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    if REPORT_MARKER in text:
        REPORT.write_text(
            text[: text.index(REPORT_MARKER)].rstrip() + "\n",
            encoding="utf-8",
            newline="\n",
        )
    first = chosen[:50]
    second = chosen[50:]
    report = f"""{REPORT_MARKER}

- الوقت: 2026-08-24، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}، باستدعاء الخط {BT}latin{BT} صراحة.
- المقام: أول 100 معرف مصدر فريد بعد {BT}PS-GC-OLD-IRISH-01947{BT} بحسب ترتيب ملفات المسح، من غير عد النسخ المدمجة المرآتية.
- انضباط الحجم: دفعتان فقط من 50 و50، وكل دفعة داخل الحد الملزم 40 إلى 60.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | 2 | 48 |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | 4 | 46 |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | 6 | 94 |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 3، و{BT}ROOT-ECHO{BT} عدد 2، و{BT}NUCLEUS-TRACE{BT} عدد 1؛ وكل موجب يثبت مسار الصوت المسمى أو مرساة العائلة، والحدث المجمد، وشاهدين عربيين، والمدار المكتوب باليد.
- الصلات المباشرة: {BT}cern{BT} مع {BT}جرن{BT} في الوعاء الحجري، و{BT}dobur{BT} مع {BT}دبل{BT} في جدول الماء، و{BT}atbaill{BT} مع {BT}تبل{BT} في الموت والفناء.
- الأصداء المضبوطة: {BT}cern{BT} مع {BT}قرن{BT} في الغلبة على القرين، و{BT}grinne{BT} مع {BT}قرن{BT} في نقطة السلاح والقرن الناتئ؛ وقرأ {BT}míanach{BT} مع {BT}مني{BT} عند النواة البعيدة ومرساة {BT}mían{BT} المثبتة.
- فحص الجودة السلبي: لم ترق {BT}medc{BT} مع {BT}مذق{BT} لأن whey غير اللبن الممزوج بالماء ولأن الحدث لم يجاوز الدرجة الرابعة، ولم ترق {BT}scaraid{BT} مع {BT}شرد{BT} ولا {BT}engach{BT} مع {BT}نجخ{BT} رغم قرب المعنى لغياب صف صوتي جامع.
- ألحقت الدفعتان بذيل {BT}04-cross-linguistic/readings/old-irish.md{BT}، وآخر موضع فيهما {BT}PS-GC-OLD-IRISH-02047{BT}؛ وبقي حوض الإيرلندية متاحا فلم يلزم الانتقال إلى القوطية.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل، وكل بطاقة جديدة دون 5120 بايت.
- الضبط: نقاء الشحنة {BT}CLEAN{BT}؛ لا وسم إغلاق مخترع؛ وكاشف انضباط النواة بلا زيادة جديدة من الجولة.
- لم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع ولم يحدث دفع، ولم تستعمل أوامر git.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    irish = OI_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    section = irish[irish.index(f"<!-- {START} -->") :]
    assert section.count(f"{MARKER}:COMP-") == 100
    assert section.count(f"- الحكم (استكشاف): {BT}ROOT-TRACE{BT}.") == 3
    assert section.count(f"- الحكم (استكشاف): {BT}ROOT-ECHO{BT}.") == 2
    assert section.count(f"- الحكم (استكشاف): {BT}NUCLEUS-TRACE{BT}.") == 1
    assert section.count(f"- الحكم (استكشاف): {BT}NO-TRACE{BT}.") == 94
    assert section.count("### الدفعة الأولى") == 1
    assert section.count("### الدفعة الثانية") == 1
    cards = re.split(r"(?=^### بطاقة إتمام:)", section, flags=re.M)[1:]
    assert len(cards) == 100
    assert max(len(card.encode("utf-8")) for card in cards) <= 5120
    assert section.rstrip().endswith(f"<!-- {END} -->")
    assert report.rstrip().endswith(DONE)
    for addition in (section, report[report.index(REPORT_MARKER) :]):
        assert "—" not in addition
        assert not re.search(r"[٠-٩]", addition)


def main() -> None:
    chosen = append_irish()
    append_report(chosen)
    verify()
    print(DONE)


if __name__ == "__main__":
    main()
