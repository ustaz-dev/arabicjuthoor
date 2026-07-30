#!/usr/bin/env python3
"""Resolve source-named Hebrew biblical one-short members conservatively."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from collections import Counter

from append_hebrew_biblical_unrepresented_singletons_10 import (
    DB,
    DEFAULT_RESOURCES,
    QUEUE,
    READING,
    atomic_write,
    fold,
    independent_fan,
    matches_for_roots,
    structural_state,
)


ROOT = READING.parents[2]
REPORT = ROOT / "data" / "proof-eligible-families.json"
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-biblical-one-short-source-named-12-local.md"
MARKER = "<!-- HEBREW-BIBLICAL-ONE-SHORT-SOURCE-NAMED-12 -->"
DATE = "2026-07-28"
EXPECTED_SHA256 = "8e309ff361a3a42ec56864e15e1a1dd7db5b791a7c01ec8170e089be9a008342"


def item(
    root: str,
    term: str,
    verdict: str,
    reason: str,
    sound: str,
    bridge: str,
) -> dict[str, object]:
    return {
        "root": root,
        "terms": (term,),
        "verdict": verdict,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


POSITIVE = {
    "kaikki_hebrew:14767:en-פול-he-noun-F4rsQAxj": item(
        "فول", "فول", "ROOT-TRACE",
        "المصدر يصرح بعربية فول والمسمى الفول نفسه",
        "LAB-07 يرخص פ ↔ ف؛ الواو واللام هويتان.",
        "مباشر في الفول.",
    ),
    "kaikki_hebrew:14406:en-חוח-he-noun-iIaYM8MT": item(
        "خوخ", "خوخة", "ROOT-TRACE",
        "المصدر يصرح بعربية خوخة للفتحة",
        "GUT-05 يرخص ח ↔ خ في الطرفين؛ الواو هوية.",
        "مباشر في الفتحة والكوة.",
    ),
    "kaikki_hebrew:834:en-עקב-he-verb-VJFniUBy": item(
        "عقب", "عاقب", "ROOT-TRACE",
        "المصدر يصرح بعربية عاقب في الاتباع عند العقب",
        "العين والقاف والباء هويات؛ لا صف لازم.",
        "مباشر في الاتباع والتعقب.",
    ),
    "kaikki_hebrew:10999:en-כיפר-he-verb-HmfwMVjo": item(
        "كفر", "ستر", "ROOT-TRACE",
        "المصدر يصرح بعربية كفر للستر والتغطية",
        "LAB-07 يرخص פ ↔ ف؛ الكاف والراء هويتان.",
        "مباشر في الستر والتغطية.",
    ),
    "kaikki_hebrew:12672:en-קטורת-he-noun-ZWUioDqG": item(
        "قتر", "قتار", "ROOT-ECHO",
        "المصدر يرد الاسم إلى ק־ט־ר للدخان ويقارن بقتار العربية",
        "القاف والتاء والراء هويات؛ بناء الاسم خارج الجذر.",
        "الدخان ورائحة الشواء مدار البخور.",
    ),
    "kaikki_hebrew:8195:en-נם-he-verb-RNXsstRu": item(
        "نوم", "نوم", "NUCLEUS-TRACE",
        "المصدر يقارن נם بنام العربية",
        "نواة النون والميم هوية؛ الواو رجل الجذر الأجوف العربية.",
        "مباشر في النوم والنعاس.",
    ),
    "kaikki_hebrew:97:en-חרא-he-noun-Vl6I3-kk": item(
        "خرأ", "خرء", "ROOT-TRACE",
        "المصدر يرد اللفظين إلى *ḫarʔ- بالمدلول نفسه",
        "GUT-05 يرخص ח ↔ خ؛ الراء والهمزة هويتان.",
        "مباشر في الخرء.",
    ),
    "kaikki_hebrew:16383:en-כתית-he-noun-uuge068x": item(
        "كتت", "كت", "ROOT-TRACE",
        "المصدر يصرح بأنه مشتق من כתת للدق، وكت العربية للدق والكسر",
        "الكاف والتاءان هويات؛ الياء من بناء الاسم.",
        "مباشر في الزيت المدقوق.",
    ),
    "kaikki_hebrew:1706:en-עלוקה-he-noun-Vmu6V1Bk": item(
        "علق", "علقة", "ROOT-TRACE",
        "المصدر يقارن עלוקה بعلقة العربية",
        "العين واللام والقاف هويات؛ بناء الاسم خارج الجذر.",
        "مباشر في العلقة ودودة الدم.",
    ),
    "kaikki_hebrew:5906:en-שחפת-he-noun-6J2myiK0": item(
        "سحف", "سحاف", "ROOT-TRACE",
        "المصدر يصرح بعربية سحاف للسل",
        "SIB-01 يرخص س ↔ ש، وLAB-07 يرخص פ ↔ ف؛ الحاء هوية والتاء لاحقة.",
        "مباشر في السحاف والسل.",
    ),
    "kaikki_hebrew:11104:en-כליה-he-noun-HfH8w8ta": item(
        "كلو", "كلوة", "NUCLEUS-TRACE",
        "المصدر يصرح بعربية كلوة وكلية للعضو نفسه",
        "نواة الكاف واللام هوية؛ الرجل الضعيفة تتناوب واوًا وياءً في المصدر.",
        "مباشر في الكلية.",
    ),
    "kaikki_hebrew:6485:en-ראם-he-noun-FLvUnuD3": item(
        "ريم", "ريم", "NUCLEUS-ECHO",
        "المصدر يقارن ראם بريم أو رئم العربية للحيوان الوحشي",
        "نواة الراء والميم هوية؛ الرجل الضعيفة لا تدخل حكم النواة.",
        "الثور الوحشي والمها انتقال نوعي داخل الحيوان الوحشي سماه المصدر.",
    ),
    "kaikki_hebrew:2788:en-עורב-he-noun-CSzaOQtH": item(
        "غرب", "غراب", "ROOT-TRACE",
        "المصدر يرد עורב إلى *ḡurayb- ويصرح بعربية غراب",
        "الغين عضوية مثبتة في الأصل المنشور وفق قرار بطاقات الغين؛ الراء والباء هويتان ولا صف جديد.",
        "مباشر في الغراب.",
    ),
    "kaikki_hebrew:8773:en-בכי-he-noun-Y-AxJblo": item(
        "بكي", "بكاء", "NUCLEUS-TRACE",
        "المصدر يقارن בכי ببكاء العربية",
        "نواة الباء والكاف هوية؛ الرجل الضعيفة لا تدخل حكم النواة.",
        "مباشر في البكاء.",
    ),
    "kaikki_hebrew:16413:en-גידף-he-verb-I6OewsnE": item(
        "جدف", "جدف", "ROOT-TRACE",
        "المصدر يصرح بعربية جدف في السب والتجديف",
        "GUT-03 يرخص ג ↔ ج، وLAB-07 يرخص פ ↔ ف؛ الدال هوية.",
        "مباشر في التجديف والسب.",
    ),
    "kaikki_hebrew:16052:en-יחמור-he-noun-7F7ZdyBc": item(
        "حمر", "يحمور", "ROOT-TRACE",
        "المصدر يصرح بعربية يحمور للحيوان نفسه",
        "الحاء والميم والراء الجذرية هويات؛ الياء وبناء الاسم موثقان في السطحين.",
        "مباشر في اليحمور.",
    ),
    "kaikki_hebrew:3479:en-אמש-he-adv-i2S-nVmX": item(
        "أمس", "أمس", "ROOT-TRACE",
        "المصدر يصرح بعربية أمس للزمن نفسه",
        "SIB-01 يرخص س ↔ ש؛ الهمزة والميم هويتان.",
        "مباشر في أمس والليلة الماضية.",
    ),
    "kaikki_hebrew:1821:en-אזור-he-noun-PHLksQBz": item(
        "أزر", "إزار", "ROOT-TRACE",
        "المصدر يصرح بعربية إزار للمنطقة نفسها",
        "الهمزة والزاي والراء هويات؛ الواو من بناء الاسم.",
        "مباشر في الإزار والمنطقة.",
    ),
    "kaikki_hebrew:15990:en-שיבה-he-noun-~c-TPZrM": item(
        "شيب", "شيب", "ROOT-TRACE",
        "שיבה وشيب العربية لبياض الشعر مع الكبر",
        "الشين والياء والباء هويات؛ اللاحقة من بناء الاسم.",
        "مباشر في الشيب.",
    ),
    "kaikki_hebrew:987:en-דבק-he-noun-mVUt6ZmK": item(
        "دبق", "دبق", "ROOT-TRACE",
        "المصدر يصرح بعربية دبق للصمغ والالتصاق",
        "الدال والباء والقاف هويات؛ لا صف لازم.",
        "مباشر في الدبق والصمغ.",
    ),
    "kaikki_hebrew:1574:en-דין-he-noun-Cuqm2RNC": item(
        "دين", "دين", "ROOT-ECHO",
        "المصدر يصرح بعربية دين في الحكم والقانون والجزاء",
        "الدال والياء والنون هويات؛ لا صف لازم.",
        "القانون والحكم والجزاء سلسلة دين واحدة.",
    ),
    "kaikki_hebrew:8329:en-חסר-he-adj-YPQ8ztrY": item(
        "خسر", "خسر", "ROOT-ECHO",
        "المصدر يقارن חסר بخسر العربية",
        "GUT-05 يرخص ח ↔ خ؛ السين والراء هويتان.",
        "المفقود هو ما خسره صاحبه، خطوة دلالية واحدة.",
    ),
    "kaikki_hebrew:4139:en-מגן-he-noun-PVtCaUz~": item(
        "مجن", "مجن", "ROOT-TRACE",
        "المصدر يصرح بعربية مجن للترس نفسه",
        "GUT-03 يرخص ג ↔ ج؛ الميم والنون هويتان.",
        "مباشر في المجن والترس.",
    ),
    "kaikki_hebrew:11725:en-נעם-he-verb-VCJemZbR": item(
        "نعم", "نعم", "ROOT-ECHO",
        "المصدر يقارن נעם بنعم العربية في الطيب والبركة",
        "النون والعين والميم هويات؛ لا صف لازم.",
        "الطيب والرضا والإرضاء سلسلة معنى واحدة.",
    ),
}

SPECIAL_CLOSURES = {
    "kaikki_hebrew:2719:en-ריבה-he-noun-kd0gKxkB": (
        "OUT-OF-SCOPE",
        "المصدر يصرح بأن اللفظ صاغه إليعازر بن يهودا حديثًا.",
    ),
    "kaikki_hebrew:2321:en-בורג-he-noun-RwK7THlQ": (
        "LOAN-ROUTE-ISOLATED",
        "المصدر يسمي طريق العربية من التركية العثمانية مانحًا خارجيًا.",
    ),
    "kaikki_hebrew:13321:en-שטר-he-noun-xLHbBk1z": (
        "INTRA-HOUSE-TRANSFER",
        "المصدر يسمي الأكادية مانحًا؛ يحال إلى زوج المانح ولا يعد شاهد فرع مستقلًا.",
    ),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical one-short source-named 12: already present")
        return 0
    proof = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["unread_biblical_lexical_queue"]
    biblical = {str(item["entry_id"]): item for item in queue}
    candidates = [
        row
        for row in proof["languages"]["hebrew"]["one_member_short"]
        if row["missing_entry_id"] in biblical
    ]
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        selected = []
        for row in candidates:
            entry_id = str(row["missing_entry_id"])
            entry = connection.execute(
                "SELECT headword,pos,gloss,etymology FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if entry is None:
                raise ValueError(f"missing entry: {entry_id}")
            structural = structural_state(
                str(entry["pos"]), str(entry["headword"]), str(entry["gloss"])
            )
            if str(entry["pos"]) in {"intj", "pron"}:
                structural = ("FUNCTION-WORD", "المصدر يصنف العضو أداة أو ضميرًا.")
            if entry_id in POSITIVE or entry_id in SPECIAL_CLOSURES or structural:
                selected.append((row, entry, structural))
        digest = hashlib.sha256(
            "\n".join(str(row["missing_entry_id"]) for row, _, _ in selected).encode(
                "utf-8"
            )
        ).hexdigest()
        if digest != EXPECTED_SHA256:
            raise ValueError(f"one-short selection drifted: {len(selected)} {digest}")

        roots_needed = {str(spec["root"]) for spec in POSITIVE.values()}
        matches = matches_for_roots(DEFAULT_RESOURCES, roots_needed, None)
        fans = {root: independent_fan(matches[root]) for root in roots_needed}
        cards = []
        counts: Counter[str] = Counter()
        for rank, (row, entry, structural) in enumerate(selected, 1):
            entry_id = str(row["missing_entry_id"])
            queue_item = biblical[entry_id]
            headword = str(entry["headword"])
            pos = str(entry["pos"])
            gloss = str(entry["gloss"])
            etymology = str(entry["etymology"] or "").strip() or "لا أصل مسمى في الحقل"
            references = "؛ ".join(
                str(witness["reference"])
                for witness in queue_item["biblical_witnesses"]
                if witness["entry_id"] == entry_id
            )
            if not references:
                raise ValueError(f"{entry_id}: exact biblical witness missing")

            fan_lines: list[str] = []
            if entry_id in POSITIVE:
                spec = POSITIVE[entry_id]
                root = str(spec["root"])
                fan = fans[root]
                sources = list(fan["selected_sources"])
                if not fan["judgment_ready"] or len(sources) < 2:
                    raise ValueError(f"{entry_id}: incomplete fan")
                for source in sources[:2]:
                    definition = fold(str(source["definition"]))
                    positions = [
                        definition.find(fold(term))
                        for term in spec["terms"]
                        if definition.find(fold(term)) >= 0
                    ]
                    if not positions:
                        raise ValueError(
                            f"{entry_id}: named sense absent in {source['source_label']}"
                        )
                    start = max(0, min(positions) - 55)
                    end = min(len(definition), min(positions) + 220)
                    fan_lines.append(
                        f"  - {source['source_label']}: «{definition[start:end]}»"
                    )
                state = str(spec["verdict"])
                root_text = root
                outcome = f"{state}؛ العضو `{entry_id}` وحده؛ {spec['reason']}."
                scan = (
                    f"مروحة `{root}` مكتملة من "
                    f"{sources[0]['source_label']} + {sources[1]['source_label']}، "
                    "والمعنى المسمى حاضر في المصدرين."
                )
                sound = str(spec["sound"])
                bridge = str(spec["bridge"])
                counts["positive"] += 1
            else:
                state, reason = SPECIAL_CLOSURES.get(entry_id, structural)
                root_text = "غير مستعمل"
                outcome = f"غير صادر؛ {state} للعضو `{entry_id}`؛ {reason}"
                scan = "غير مشغل؛ الإغلاق المسمى سابق للمقارنة."
                sound = "لا يستعمل صف صوت في الإغلاق."
                bridge = reason
                counts["closure"] += 1

            cards.append(
                "\n".join(
                    [
                        f"### بطاقة: `{row['family_id']}`، {headword}، إتمام الأسرة التوراتية 12، الرتبة {rank}",
                        f"- عائق: النوع={state}؛ يتطلب=المراجعة الثالثة؛ العضو=`{entry_id}`.",
                        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                        f"- الكلمةُ في الفرع: {headword}، {pos}، «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- أقدمُ صورةٍ مستعادة: شاهد توراتي للعضو نفسه: {references}؛ الأصل المنشور: {etymology}.",
                        "- الخطوةُ صفر (التعرية بصرف الفرع): لم تنزع زيادة إلا بنص المصدر؛ وكل عضو يحكم وحده.",
                        "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف والنواة والمدار.",
                        f"- مسارُ الجذر الكامل أولًا: `{root_text}`؛ لا يحكم المرشح الآلي.",
                        f"- مسحُ المعاني العربيّة: {scan}",
                        *fan_lines,
                        f"- المقابلُ من اللسان: `{root_text}`.",
                        f"- مسارُ الصوت: {sound}",
                        f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- المدار: {bridge}",
                        "- المصفاة: الزمن والأصل والقرض والعلم والصورة والمركب فُحصت قبل الحكم.",
                        f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا وراثة.",
                        "- مؤشر اليتم: عضو واحد راقد كان يسقط الأسرة كلها.",
                        "- إشعاع الأسرة في الفرع: لا يرث هذا العضو حكم عضو آخر.",
                        "- إشعاع الأسرة في العربية: المعنى المستشهد به وحده، أو صفر عند الإغلاق.",
                        "- جسورُ الاسترداد المفحوصة: الشاهد؛ الأصل؛ الجذر؛ الأجوف؛ النواة؛ المدار؛ الصفوف؛ الصورة؛ القرض.",
                        f"- حالةُ الإغلاق: {state}.",
                        f"- الحكم (استكشاف): {outcome}",
                        "- عدسة الاسترداد: استعملت الشاهد والمروحة والمصدر المسمى.",
                        "- عدسة التشكيك: منعت وراثة الحكم والسالب المصنوع والصف الجديد.",
                        "- ملاحظات: محلي للمراجعة الثالثة؛ لا خط برهان ولا سجل مركزي.",
                        "",
                    ]
                )
            )
    finally:
        connection.close()

    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## إتمام الأسر التوراتية ذات المصدر المسمى ({DATE}، محلي)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو كل عضو راقد واحد في أسرة ممثلة وله شاهد توراتي، واقتصر التنفيذ على مقابل عربي سماه المصدر أو إغلاق بنيوي أو نقلي صريح.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-ONE-SHORT-SOURCE-NAMED-12:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# إتمام الأسر العبرية التوراتية ذات المصدر المسمى",
                "",
                "## النطاق",
                "",
                f"- بطاقات تغير المصير: {len(selected)}.",
                f"- بصمة الترتيب: `{EXPECTED_SHA256}`.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {counts['positive']}.",
                f"- الإغلاقات النهائية: {counts['closure']}.",
                "",
                "## الحالة",
                "",
                "- محلي للمراجعة الثالثة.",
                "- بقيت الاحتمالات غير المسماة معلقة.",
                "- لا خط برهان ولا سجل مركزي.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": len(selected),
                "positive_connections": counts["positive"],
                "terminal_closures": counts["closure"],
                "selection_sha256": EXPECTED_SHA256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
