# -*- coding: utf-8 -*-
"""إتمام حوض النردية وفتح حوض الإيرلندية القديمة في الجولة 21، بلا شحن."""
from __future__ import annotations

import pathlib
import re

import search_arabic_root_senses as ARS
from harvest_lane_d_round16 import (
    BT,
    COMPACT_DIR,
    FAN,
    ON_FILE,
    REPORT,
    SOURCE_DIR,
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
OI_FILE = ROOT / "04-cross-linguistic/readings/old-irish.md"
NORSE_START = "LANE-D-DONE21-OLD-NORSE:START"
NORSE_END = "LANE-D-DONE21-OLD-NORSE:END"
IRISH_START = "LANE-D-DONE21-OLD-IRISH:START"
IRISH_END = "LANE-D-DONE21-OLD-IRISH:END"
REPORT_MARKER = "## الجولة الحادية والعشرون: إتمام النردية وفتح الإيرلندية القديمة"
DONE = "LANE-D DONE21 442 PS-GC-OLD-IRISH-01847"


# الحكم خاص بالحس المثبت في بطاقة المصدر. لا يرث متحد الرسم حكمه.
NORSE_POSITIVE = {
    "PS-GC-OLD-NORSE-01530": (
        "سمر", 1, "NUCLEUS-TRACE",
        "الحكم على ساق اللون s-m بعد رد نهاية الصفة الجرمانية المنشورة، لا على راء السطح. "
        "والسمرة في الشاهد العربي منزلة بين البياض والسواد، وهي معنى darkish وswarthy نفسه.",
    ),
    "PS-GC-OLD-NORSE-01564": (
        "سوم", 1, "ROOT-ECHO",
        "السباحة مرور ممتد في حيز الماء؛ وسوم العربية يثبت المرور والاستمرار، "
        "وهو تطبيق مباشر لحدث الامتداد والذهاب في حيز بلا حد.",
    ),
    "PS-GC-OLD-NORSE-01614": (
        "تبب", 1, "ROOT-TRACE",
        "نص الفرع loss وperdition، ونص العربية الخسران والهلاك؛ "
        "واللاحقة -un منشورة في بطاقة المصدر، فبقيت ساق tapa وفتح باب المضاعف تبب.",
    ),
    "PS-GC-OLD-NORSE-01663": (
        "قرر", 1, "ROOT-TRACE",
        "calmness وcalm هما القرار والسكون؛ وتثبت الشواهد أن قر بالمكان واستقر، "
        "وأن المقارة هي أن يقر المرء مع غيره ويسكن.",
    ),
}


NORSE_PATH_OVERRIDE = {
    "PS-GC-OLD-NORSE-01530": (
        f"s↔س={BT}IDN-07{BT}؛ m↔م={BT}IDN-02{BT}؛ "
        "المقارنة نواتية بعد رد نهاية الصفة الجرمانية المنشورة، فلا تدخل راء السطح في الحكم."
    ),
    "PS-GC-OLD-NORSE-01614": (
        f"t↔ت={BT}IDN-11{BT}؛ p↔ب={BT}LAB-01{BT}؛ "
        "نص الاشتقاق يفصل -un من tapa، ثم يفتح باب المضاعف المسمى تبب."
    ),
    "PS-GC-OLD-NORSE-01663": (
        f"k↔ق={BT}GUT-01{BT}؛ r↔ر={BT}IDN-01{BT}؛ "
        "والراء الثانية تضعيف للساق المنشورة kyrr."
    ),
}


IRISH_POSITIVE = {
    "PS-GC-OLD-IRISH-00110": (
        "قبض", 1, "NUCLEUS-TRACE",
        "ترد الصورة المنشورة الدال السطحية إلى نهاية الفعل، فيبقى g-b؛ "
        "والقبض في الشاهدين أخذ الشيء والإمساك به، وهو معنى hold وgrasp وtake وseize.",
    ),
    "PS-GC-OLD-IRISH-00112": (
        "مني", 3, "NUCLEUS-TRACE",
        "ساق الفرع m-n، والمقارنة عند النواة داخل مادة مني؛ "
        "والمُنية والأمنية في العربية مطلوب النفس، وهو desire وobject of desire بلا رتوش.",
    ),
    "PS-GC-OLD-IRISH-00117": (
        "قرن", 1, "ROOT-TRACE",
        "drinking-horn هو قرن الشرب، والشاهد العربي يسمي القرن في الحيوان والرأس؛ "
        "والمانح اللاتيني المسمى غير سامي فلا يغلق المقارنة الأعمق، مع عدم عده إرثا كلتيا مستقلا.",
    ),
    "PS-GC-OLD-IRISH-00123": (
        "قرن", 1, "ROOT-TRACE",
        "تاج الرأس وموضع أعلى الرأس يلتقيان نص قرن في الجانب الأعلى من الرأس؛ "
        "والمانح اللاتيني المسمى غير سامي فلا يغلق المقارنة الأعمق، مع حفظ مسار القرض صراحة.",
    ),
    "PS-GC-OLD-IRISH-00124": (
        "نقذ", 1, "NUCLEUS-TRACE",
        "ترد الصورة السلتية المنشورة الدال السطحية إلى نهاية الفعل، فيبقى n-g؛ "
        "والإنقاذ في الشاهدين هو النجاة والتخليص، أي save في عضو الفرع نفسه.",
    ),
    "PS-GC-OLD-IRISH-00246": (
        "ملك", 1, "ROOT-ECHO",
        "country وterritory حيز يشمله ملك وسلطان؛ والمملكة أرض الحكم، "
        "فاجتمع معنى الفرع مع حدث الإمساك بقوة مع الشمول.",
    ),
    "PS-GC-OLD-IRISH-00247": (
        "بني", 1, "NUCLEUS-ECHO",
        "base وbottom موضع يقوم عليه المبني؛ والبناء في الشاهدين إقامة الشيء وإنشاؤه، "
        "فالحكم عند b-n في مدار الأساس الذي يحمل البنية لا في دعوى تطابق ثلاثي.",
    ),
}


IRISH_PATH_OVERRIDE = {
    "PS-GC-OLD-IRISH-00110": (
        f"g الفرعية تبلغ ق العربية بالسلسلة {BT}GUT-02{BT} ثم {BT}GUT-01{BT}؛ "
        f"b↔ب={BT}IDN-05{BT}؛ والدال السطحية من نهاية الفعل المنشورة فلا تدخل الحكم."
    ),
    "PS-GC-OLD-IRISH-00124": (
        f"n↔ن={BT}IDN-03{BT}؛ g الفرعية تبلغ ق العربية بالسلسلة "
        f"{BT}GUT-02{BT} ثم {BT}GUT-01{BT}؛ والدال السطحية من نهاية الفعل المنشورة."
    ),
}


IRISH_LOANWORD = {
    "PS-GC-OLD-IRISH-00129": "Latin sabbatum ← Ancient Greek σάββατον ← Biblical Hebrew שַׁבָּת",
    "PS-GC-OLD-IRISH-00252": "Latin manna ← Ancient Greek μάννα ← Hebrew מָן",
}


def parse_irish_sources() -> list[dict[str, str]]:
    heading = re.compile(
        r"^### بطاقة مسح صوتي: " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)"
        + re.escape(BT) + r" /([^/]*)/؛ (PS-GC-OLD-IRISH-\d{5})$",
        re.M,
    )
    rows: list[dict[str, str]] = []
    for path in sorted(SOURCE_DIR.glob("batch-*-old-irish.md")):
        text = path.read_text(encoding="utf-8")
        matches = list(heading.finditer(text))
        for index, match in enumerate(matches):
            end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
            body = text[match.end():end]
            meaning_match = re.search(r"معنى صف المسح «([^»]*)»", body)
            pool_match = re.search(
                r"مقام المسح: " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)", body
            )
            closest_match = re.search(
                r"أقرب مادة في المسح " + re.escape(BT) + r"([^" + re.escape(BT) + r"]+)", body
            )
            etymology_match = re.search(r"حاشية الأصل كما يقول القاموس: (.*)$", body, re.M)
            rows.append({
                "word": match.group(1),
                "roman": match.group(2),
                "source": match.group(3),
                "file": path.name,
                "body": body,
                "meaning": meaning_match.group(1) if meaning_match else "",
                "pool": pool_match.group(1) if pool_match else "",
                "closest": closest_match.group(1) if closest_match else "",
                "etymology": (
                    etymology_match.group(1)
                    if etymology_match
                    else "لا حاشية أصل في بطاقة المصدر."
                ),
            })

    ids = [row["source"] for row in rows]
    assert len(rows) == 586, len(rows)
    assert len(ids) == len(set(ids))
    compact_count = 0
    for path in sorted(COMPACT_DIR.glob("batch-*-old-irish.md")):
        compact_count += len(re.findall(r"^### بطاقة مدمجة:", path.read_text(encoding="utf-8"), re.M))
    assert compact_count == 586, compact_count
    return rows


def excerpt(definition: str, needles: tuple[str, ...], limit: int = 260) -> str:
    normalized = clean(re.sub(r"\s+", " ", definition))
    positions = [normalized.find(needle) for needle in needles if needle in normalized]
    if not positions:
        return clip(normalized, limit)
    position = min(positions)
    start = max(0, position - 55)
    end = min(len(normalized), start + limit)
    return ("…" if start else "") + normalized[start:end].strip() + ("…" if end < len(normalized) else "")


def external_witnesses(root: str, needles: tuple[str, ...]) -> list[tuple[str, str]]:
    matches = ARS.matches_for_roots(ROOT / "Resources", {root}, None)[root]
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for item in matches:
        name = clean(item["source"])
        definition = clean(item["definition"])
        if name in seen or not any(needle in definition for needle in needles):
            continue
        out.append((name, excerpt(definition, needles)))
        seen.add(name)
        if len(out) == 2:
            break
    assert len(out) == 2, (root, needles, out)
    return out


def witnesses_for(language: str, row: dict[str, str], root: str) -> list[tuple[str, str]]:
    source = row["source"]
    if source == "PS-GC-OLD-NORSE-01530":
        return external_witnesses(
            root,
            ("أسمر بين السمرة", "السُّمْرَةُ مَنْزِلةٌ", "لَوْنُ الأَسْمَرِ"),
        )
    if source == "PS-GC-OLD-NORSE-01564":
        return external_witnesses(
            root,
            ("سامَ أَي مَرَّ", "سامَ، أي مر", "سَوْمُ الرياح", "اسْتَمَرَّت", "استمرّت"),
        )
    if source == "PS-GC-OLD-NORSE-01614":
        return external_witnesses(root, ("الخُسْرانُ والهَلاكُ", "الخَسارُ", "الخسران والهلاك"))
    if source == "PS-GC-OLD-NORSE-01663":
        return external_witnesses(root, ("بالمكان", "استقر"))
    if source == "PS-GC-OLD-IRISH-00112":
        return external_witnesses(
            root,
            (
                "وتَمنَّى الشيءَ أَرَادَهُ",
                "الأُمْنِيَّةُ الصُّورَةُ الحاصِلَةُ",
                "جمع المُنية، وهو ما يَتَمَنَّى الرجل",
            ),
        )
    witnesses = arabic_witnesses(row["body"], root)
    assert len(witnesses) == 2, (language, source, root, witnesses)
    return witnesses


def render_positive(
    language: str,
    row: dict[str, str],
    phase: str,
    marker: str,
    positive: dict[str, tuple[str, int, str, str]],
    path_override: dict[str, str],
) -> str:
    source = row["source"]
    comp = "COMP-" + source
    root, tier, judgment, orbit = positive[source]
    fans = FAN.fan(row["word"], "germanic" if language == "OLD-NORSE" else "latin")
    manual_fan = source in {"PS-GC-OLD-NORSE-01614", "PS-GC-OLD-NORSE-01663"}
    assert root in fans or manual_fan, (source, row["word"], root)
    path = path_override.get(source, source_path(row["body"], root))
    assert "لم يتحرر صف مسمى" not in path and "لا صف مسمى" not in path, (source, root, path)
    event = event_for(root, tier)
    witnesses = witnesses_for(language, row, root)
    witness_lines = "\n".join(f"  - {name}: «{quoted}»." for name, quoted in witnesses)
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(
            row["word"], "germanic" if language == "OLD-NORSE" else "latin"
        )
    )
    return f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- {marker}:{comp} -->

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


def render_no_trace(language: str, row: dict[str, str], phase: str, marker: str) -> str:
    source = row["source"]
    comp = "COMP-" + source
    script = "germanic" if language == "OLD-NORSE" else "latin"
    fans = FAN.fan(row["word"], script)
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(row["word"], script)
    )
    closest = row["closest"] or (fans[0] if fans else "لا مادة")
    return f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- {marker}:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: أعادت الهياكل {skeletons}؛ والمروحة الحالية {len(fans)} مادة.
- أقرب ما أعادته المروحة: {BT}{closest}{BT}؛ قرئت مواد المروحة وأحداثها وشواهدها في بطاقة المصدر.
- المدار المكتوب باليد: لم يثبت اجتماع رجل الصوت مع حدث مجمد يشرح معنى «{clip(row['meaning'], 240)}» وشاهد عربي صريح؛ فالتشابه الشكلي وحده لا يكفي.
- المصفاة: {clip(row['etymology'], 320)} لم تجعل حاشية الأصل بوابة، ولا يغلق القرض إلا مانح سامي مسمى.
- فصل المتجانسات: لم يرث هذا الحس حكم مادة أو معنى آخر لمجرد الرسم، وبقيت الصلات الصادرة القديمة بلا مساس.
- حالة الإغلاق: CLOSED-NO-TRACE.
- الحكم (استكشاف): {BT}NO-TRACE{BT}.
"""


def render_loanword(row: dict[str, str], phase: str) -> str:
    source = row["source"]
    comp = "COMP-" + source
    route = IRISH_LOANWORD[source]
    fans = FAN.fan(row["word"], "latin")
    skeletons = "؛ ".join(
        f"{'-'.join(skeleton)} ({note})"
        for skeleton, note in FAN.oe_skeletons(row["word"], "latin")
    )
    return f"""### بطاقة إتمام: {BT}{row['word']}{BT} /{row['roman']}/؛ {BT}{comp}{BT}
<!-- LANE-D-DONE21-OLD-IRISH:{comp} -->

- إصدار البروتوكول: {BT}RECOVERY-v2{BT}؛ المرحلة: {phase}؛ الطبقة: استكشاف.
- بطاقة المصدر: {BT}{source}{BT} في {BT}phonetic-sweep-germanic-celtic/{row['file']}{BT}؛ بقيت بلا تعديل.
- مقام المصدر: {BT}{row['pool']}{BT}؛ معنى صف المسح: «{clip(row['meaning'], 420)}».
- الأداة المصلحة: أعادت الهياكل {skeletons}؛ والمروحة الحالية {len(fans)} مادة، وبقيت القراءة محفوظة.
- المصفاة الحاسمة: سمى المورد طريق الانتقال {BT}{route}{BT}؛ فالمانح السامي مسمى صراحة ولا يحسب اللفظ أثرا كلتيا مستقلا.
- فصل المتجانسات: الحكم لهذا العضو وحده، ولا ينتقل إلى متحد رسم أو معنى آخر.
- حالة الإغلاق: LOANWORD.
- الحكم (استكشاف): {BT}LOANWORD{BT}.
"""


def append_norse() -> list[dict[str, str]]:
    rows = parse_norse_sources()
    start = next(index for index, row in enumerate(rows) if row["source"] == "PS-GC-OLD-NORSE-01450")
    chosen = rows[start:]
    assert len(chosen) == 342, len(chosen)
    assert chosen[0]["source"] == "PS-GC-OLD-NORSE-01450"
    assert chosen[-1]["source"] == "PS-GC-OLD-NORSE-01791"
    assert set(NORSE_POSITIVE) <= {row["source"] for row in chosen}

    text = ON_FILE.read_text(encoding="utf-8")
    if NORSE_START in text:
        remove_generated_section(ON_FILE, NORSE_START, NORSE_END)

    parts = [f"""<!-- {NORSE_START} -->

## الجولة الحادية والعشرون: إتمام حوض النردية القديمة

- النطاق: جميع معرفات المصدر الفريدة الباقية بعد {BT}PS-GC-OLD-NORSE-01449{BT}، من {BT}PS-GC-OLD-NORSE-01450{BT} إلى {BT}PS-GC-OLD-NORSE-01791{BT}؛ عددها 342.
- تمام الحوض: 798 بطاقة مصدر كاملة و798 بطاقة مدمجة مرآة، أي 1,596 بطاقة فيزيائية؛ الحكم غير المكرر على 798 معرف مصدر.
- البطاقات التالية ناسخة للحكم فقط، وبطاقات المسح الأصلية والصلات الصادرة القديمة باقية بلا تعديل.
"""]
    for row in chosen:
        if row["source"] in NORSE_POSITIVE:
            parts.append(render_positive(
                "OLD-NORSE", row, "خاتمة الحوض", "LANE-D-DONE21-OLD-NORSE",
                NORSE_POSITIVE, NORSE_PATH_OVERRIDE,
            ))
        else:
            parts.append(render_no_trace("OLD-NORSE", row, "خاتمة الحوض", "LANE-D-DONE21-OLD-NORSE"))
    parts.append(f"""
- حصيلة خاتمة الحوض: 342 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 1، و{BT}NUCLEUS-TRACE{BT} عدد 1، و{BT}NO-TRACE{BT} عدد 338.
- اكتمل بذلك مقام النردية غير المكرر كله: 798 معرف مصدر، ومع مراياه 1,596 بطاقة فيزيائية.
- لم تشغل أداة الشحن ولم ينشأ إيداع.

<!-- {NORSE_END} -->""")
    append(ON_FILE, "\n".join(parts))
    return chosen


def append_irish() -> list[dict[str, str]]:
    rows = parse_irish_sources()
    chosen = rows[:100]
    first = chosen[:50]
    second = chosen[50:]
    assert first[0]["source"] == "PS-GC-OLD-IRISH-00110"
    assert first[-1]["source"] == "PS-GC-OLD-IRISH-01797"
    assert second[0]["source"] == "PS-GC-OLD-IRISH-01798"
    assert second[-1]["source"] == "PS-GC-OLD-IRISH-01847"
    assert set(IRISH_POSITIVE) | set(IRISH_LOANWORD) <= {row["source"] for row in chosen}

    text = OI_FILE.read_text(encoding="utf-8")
    if IRISH_START in text:
        remove_generated_section(OI_FILE, IRISH_START, IRISH_END)

    parts = [f"""<!-- {IRISH_START} -->

## الجولة الحادية والعشرون: فتح أحكام المسح الإيرلندي القديم

- الجرد: 586 بطاقة مصدر كاملة ذات معرفات فريدة، ومعها 586 بطاقة مدمجة مرآة؛ فالمجموع الفيزيائي 1,172، ومقام الحكم غير المكرر 586 معرفا.
- هذه الجولة دفعتان من 50 و50: الأولى من {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT}، والثانية من {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT}.
- البطاقات التالية ناسخة للحكم فقط، وبطاقات المسح الأصلية والصلات الصادرة القديمة باقية بلا تعديل.

### الدفعة الأولى
"""]
    for row in first:
        if row["source"] in IRISH_POSITIVE:
            parts.append(render_positive(
                "OLD-IRISH", row, "الدفعة الأولى", "LANE-D-DONE21-OLD-IRISH",
                IRISH_POSITIVE, IRISH_PATH_OVERRIDE,
            ))
        elif row["source"] in IRISH_LOANWORD:
            parts.append(render_loanword(row, "الدفعة الأولى"))
        else:
            parts.append(render_no_trace("OLD-IRISH", row, "الدفعة الأولى", "LANE-D-DONE21-OLD-IRISH"))

    parts.append("\n### الدفعة الثانية\n")
    for row in second:
        if row["source"] in IRISH_POSITIVE:
            parts.append(render_positive(
                "OLD-IRISH", row, "الدفعة الثانية", "LANE-D-DONE21-OLD-IRISH",
                IRISH_POSITIVE, IRISH_PATH_OVERRIDE,
            ))
        elif row["source"] in IRISH_LOANWORD:
            parts.append(render_loanword(row, "الدفعة الثانية"))
        else:
            parts.append(render_no_trace("OLD-IRISH", row, "الدفعة الثانية", "LANE-D-DONE21-OLD-IRISH"))

    parts.append(f"""
- حصيلة الدفعتين: 100 بطاقة إتمام؛ {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 1، و{BT}NUCLEUS-TRACE{BT} عدد 3، و{BT}NUCLEUS-ECHO{BT} عدد 1، و{BT}LOANWORD{BT} عدد 2، و{BT}NO-TRACE{BT} عدد 91.
- فصل المتجانسات: لم يرث متحد الرسم ولا الحس الصرفي حكم غيره؛ وحفظت القروض اللاتينية غير السامية في المصفاة، وأغلق {BT}sabbait{BT} و{BT}mann{BT} وحدهما لورود المانح العبري صراحة.
- آخر موضع في ذيل هذا الملف: {BT}PS-GC-OLD-IRISH-01847{BT}.
- لم تشغل أداة الشحن ولم ينشأ إيداع.

{DONE}

<!-- {IRISH_END} -->""")
    append(OI_FILE, "\n".join(parts))
    return chosen


def append_report(norse: list[dict[str, str]], irish: list[dict[str, str]]) -> None:
    text = REPORT.read_text(encoding="utf-8")
    if REPORT_MARKER in text:
        REPORT.write_text(text[:text.index(REPORT_MARKER)].rstrip() + "\n", encoding="utf-8", newline="\n")
    first = irish[:50]
    second = irish[50:]
    report = f"""{REPORT_MARKER}

- الوقت: 2026-08-18، توقيت القاهرة.
- الأداة الحاكمة: {BT}scripts/fan_any_script.py{BT} بعد الإصلاح {BT}0ebb1e9{BT}؛ استدعاء {BT}germanic{BT} للنردية و{BT}latin{BT} للإيرلندية صراحة.

### إتمام النردية القديمة

- أتمت الجولة جميع معرفات المصدر الفريدة الباقية من {BT}{norse[0]['source']}{BT} إلى {BT}{norse[-1]['source']}{BT}: عددها 342.
- اكتمل الحوض كله: 798 بطاقة مصدر و798 مرآة مدمجة، أي 1,596 بطاقة فيزيائية. آخر معرف المصدر هو {BT}PS-GC-OLD-NORSE-01791{BT}، ولذلك كان 1,596 عددا للحوض لا رقما لآخر معرف.
- الأحكام: {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 1، و{BT}NUCLEUS-TRACE{BT} عدد 1، و{BT}NO-TRACE{BT} عدد 338.
- الصلات: {BT}sámr{BT} مع {BT}سمر{BT} في السمرة، و{BT}svima{BT} مع {BT}سوم{BT} في المرور الممتد، و{BT}tǫpun{BT} مع {BT}تبب{BT} في الخسران والهلاك، و{BT}kyrra{BT} مع {BT}قرر{BT} في القرار والسكون.

### فتح الإيرلندية القديمة

- جرد الحوض: 586 بطاقة مصدر و586 مرآة مدمجة، أي 1,172 بطاقة فيزيائية، والحكم غير المكرر على 586 معرفا.

| الدفعة | أول بطاقة وآخر بطاقة | المفحوص | الموجب | {BT}LOANWORD{BT} | {BT}NO-TRACE{BT} |
|---|---|---:|---:|---:|---:|
| 1 | {BT}{first[0]['source']}{BT} إلى {BT}{first[-1]['source']}{BT} | 50 | 7 | 2 | 41 |
| 2 | {BT}{second[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 50 | 0 | 0 | 50 |
| المجموع | {BT}{first[0]['source']}{BT} إلى {BT}{second[-1]['source']}{BT} | 100 | 7 | 2 | 91 |

- الأحكام الموجبة: {BT}ROOT-TRACE{BT} عدد 2، و{BT}ROOT-ECHO{BT} عدد 1، و{BT}NUCLEUS-TRACE{BT} عدد 3، و{BT}NUCLEUS-ECHO{BT} عدد 1.
- أبرز الصلات: {BT}gaibid{BT} مع نواة {BT}قبض{BT} في الأخذ والإمساك، و{BT}corn{BT} و{BT}corann{BT} مع {BT}قرن{BT} في القرن وتاج الرأس، و{BT}aingid{BT} مع نواة {BT}نقذ{BT} في الإنجاء، و{BT}mruig{BT} مع {BT}ملك{BT} في الإقليم المشمول، و{BT}bun{BT} مع نواة {BT}بني{BT} في الأساس الحامل للبناء.
- أغلق {BT}sabbait{BT} و{BT}mann{BT} وحدهما {BT}LOANWORD{BT} لأن المورد سمى العبرية في طريق الانتقال؛ ولم تجعل القروض غير السامية شرطا رابعا.
- ألحقت الدفعتان بذيل {BT}04-cross-linguistic/readings/old-irish.md{BT}، وآخر موضع فيهما {BT}PS-GC-OLD-IRISH-01847{BT}.
- بطاقات المصدر والصلات الصادرة القديمة بقيت بلا تعديل، وكل بطاقة جديدة دون 5120 بايت.
- الضبط: نقاء الشحنة {BT}CLEAN{BT}؛ لا وسم إغلاق مخترع؛ وكاشف انضباط النواة بلا زيادة جديدة.
- لم تشغل {BT}scripts/ship.py{BT}، ولم ينشأ إيداع ولم يحدث دفع.

{DONE}"""
    append(REPORT, report)


def verify() -> None:
    norse = ON_FILE.read_text(encoding="utf-8")
    irish = OI_FILE.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    norse_section = norse[norse.index(f"<!-- {NORSE_START} -->"):]
    irish_section = irish[irish.index(f"<!-- {IRISH_START} -->"):]
    assert norse_section.count("LANE-D-DONE21-OLD-NORSE:COMP-") == 342
    assert irish_section.count("LANE-D-DONE21-OLD-IRISH:COMP-") == 100
    assert norse_section.count(f"- الحكم (استكشاف): {BT}NO-TRACE{BT}.") == 338
    assert irish_section.count(f"- الحكم (استكشاف): {BT}NO-TRACE{BT}.") == 91
    assert irish_section.count(f"- الحكم (استكشاف): {BT}LOANWORD{BT}.") == 2
    assert sum(
        norse_section.count(f"- الحكم (استكشاف): {BT}{label}{BT}.")
        for label in ("ROOT-TRACE", "ROOT-ECHO", "NUCLEUS-TRACE", "NUCLEUS-ECHO")
    ) == 4
    assert sum(
        irish_section.count(f"- الحكم (استكشاف): {BT}{label}{BT}.")
        for label in ("ROOT-TRACE", "ROOT-ECHO", "NUCLEUS-TRACE", "NUCLEUS-ECHO")
    ) == 7
    norse_cards = re.split(r"(?=^### بطاقة إتمام:)", norse_section, flags=re.M)[1:]
    irish_cards = re.split(r"(?=^### بطاقة إتمام:)", irish_section, flags=re.M)[1:]
    assert len(norse_cards) == 342 and len(irish_cards) == 100
    assert max(len(card.encode("utf-8")) for card in norse_cards + irish_cards) <= 5120
    assert norse_section.rstrip().endswith(f"<!-- {NORSE_END} -->")
    assert irish_section.rstrip().endswith(f"<!-- {IRISH_END} -->")
    assert report.rstrip().endswith(DONE)
    for addition in (norse_section, irish_section, report[report.index(REPORT_MARKER):]):
        assert "—" not in addition
        assert not re.search(r"[٠-٩]", addition)


def main() -> None:
    norse = append_norse()
    irish = append_irish()
    append_report(norse, irish)
    verify()
    print(DONE)


if __name__ == "__main__":
    main()
