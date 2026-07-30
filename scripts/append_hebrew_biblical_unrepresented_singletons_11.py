#!/usr/bin/env python3
"""Read every remaining unrepresented biblical singleton family in queue order."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
from collections import Counter

from append_hebrew_biblical_unrepresented_singletons_10 import (
    ARABIC_MARKS,
    AUDIT as _OLD_AUDIT,
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


del ARABIC_MARKS, _OLD_AUDIT

ROOT = READING.parents[2]
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-biblical-unrepresented-singletons-11-local.md"
MARKER = "<!-- HEBREW-BIBLICAL-UNREPRESENTED-SINGLETONS-11 -->"
DATE = "2026-07-28"
EXPECTED_COUNT = 156
EXPECTED_SHA256 = "537ce9fd4288f91b6112a4076d4658c8c738a696da10b2a094ae1210b2b836d0"

POSITIVE = {
    "kaikki_hebrew:9027:en-צרור-he-noun-mHCV5Wlk": {
        "root": "صرر",
        "terms": ("صرة",),
        "verdict": "ROOT-TRACE",
        "reason": "צרור للحزمة وصرة العربية لما يشد ويجمع",
        "sound": "الصاد والراءان هويات؛ الواو من كتابة الاسم ولا تنشئ رجل جذر.",
        "bridge": "الحزمة والصرة شيء مجموع مشدود.",
    },
    "kaikki_hebrew:16042:en-חופן-he-noun-mwX08tL7": {
        "root": "حفن",
        "terms": ("حفنة",),
        "verdict": "ROOT-TRACE",
        "reason": "חופן والحفنة لملء الكف",
        "sound": "الحاء والفاء والنون هويات؛ لا صف لازم.",
        "bridge": "مباشر في الحفنة وملء الكف.",
    },
    "kaikki_hebrew:182:en-סם-he-noun-whOXjfv7": {
        "root": "سمم",
        "terms": ("سم",),
        "verdict": "NUCLEUS-ECHO",
        "reason": "المصدر يقارن סם بسم العربية، والمروحة تسمي السم والمادة المؤثرة",
        "sound": "نواة السين والميم هوية؛ التضعيف العربي يمنع ادعاء الجذر الكامل.",
        "bridge": "العقار المخدر والسم مادتان مؤثرتان في البدن ضمن السلسلة المنشورة.",
    },
    "kaikki_hebrew:3937:en-כיתת-he-verb-QPqPpQ~Z": {
        "root": "كتت",
        "terms": ("كت",),
        "verdict": "ROOT-TRACE",
        "reason": "כיתת وكت العربية للكسر والدق والسحق",
        "sound": "الكاف والتاءان هويات؛ الياء من بناء السطح.",
        "bridge": "مباشر في الدق والسحق.",
    },
    "kaikki_hebrew:5998:en-בכה-he-verb-wRoM3Ceh": {
        "root": "بكي",
        "terms": ("بكاء",),
        "verdict": "NUCLEUS-TRACE",
        "reason": "المصدر يقارن בכה ببكى العربية والفعل واحد",
        "sound": "نواة الباء والكاف هوية؛ الرجل الضعيفة تختلف سطحًا فلا يدعى جذر كامل.",
        "bridge": "مباشر في البكاء.",
    },
    "kaikki_hebrew:1008:en-תאנה-he-noun-h14w0itV": {
        "root": "تين",
        "terms": ("تين",),
        "verdict": "NUCLEUS-TRACE",
        "reason": "المصدر يرد תאנה إلى *tiʔin- ويصرح بعربية تين",
        "sound": "نواة التاء والنون محفوظة؛ الهمزة والبنية الاسمية موثقتان في الصورة الأم.",
        "bridge": "مباشر في شجرة التين وثمرها.",
    },
    "kaikki_hebrew:9880:en-בכור-he-noun-pj88CW4J": {
        "root": "بكر",
        "terms": ("بكر",),
        "verdict": "ROOT-TRACE",
        "reason": "المصدر يقارن בכור ببكر العربية في الأول والمتقدم",
        "sound": "الباء والكاف والراء الجذرية هويات؛ الواو من بناء الاسم.",
        "bridge": "مباشر في البكر وأول المواليد.",
    },
    "kaikki_hebrew:1144:en-שבעים-he-num-qw5LGng5": {
        "root": "سبع",
        "terms": ("سبعون", "سبعة"),
        "verdict": "ROOT-TRACE",
        "reason": "שבעים وسبعون من جذر العدد سبع وصورته الأم المنشورة",
        "sound": "SIB-01 يرخص س ↔ ש؛ الباء والعين هويتان، ولا صف زائد.",
        "bridge": "مباشر في عقد السبعين.",
    },
    "kaikki_hebrew:6835:en-צדקה-he-noun-6wucYc79": {
        "root": "صدق",
        "terms": ("صدقة",),
        "verdict": "ROOT-TRACE",
        "reason": "المصدر يصرح بعربية صدقة، والمعنى للعطاء الخيري",
        "sound": "الصاد والدال والقاف هويات؛ اللاحقة من بناء الاسم.",
        "bridge": "مباشر في الصدقة والعمل الخيري.",
    },
    "kaikki_hebrew:12193:en-אשם-he-verb-WkTzTYny": {
        "root": "أثم",
        "terms": ("إثم",),
        "verdict": "ROOT-ECHO",
        "reason": "אשם للوقوع في الذنب وإثم العربية للذنب",
        "sound": "DENT-02 يرخص ث ↔ ש؛ الهمزة والميم هويتان.",
        "bridge": "الذنب وحالة المذنب سلسلة معنى واحدة.",
    },
    "kaikki_hebrew:12192:en-אשם-he-noun-W5f7Q8JH": {
        "root": "أثم",
        "terms": ("إثم",),
        "verdict": "ROOT-TRACE",
        "reason": "אשם للإثم وإثم العربية للذنب نفسه",
        "sound": "DENT-02 يرخص ث ↔ ש؛ الهمزة والميم هويتان.",
        "bridge": "مباشر في الإثم والذنب.",
    },
    "kaikki_hebrew:4062:en-פחם-he-noun-bRFMlfv1": {
        "root": "فحم",
        "terms": ("فحم",),
        "verdict": "ROOT-TRACE",
        "reason": "المصدر يقارن פחם بفحم العربية والمسمى واحد",
        "sound": "LAB-07 يرخص פ ↔ ف؛ الحاء والميم هويتان.",
        "bridge": "مباشر في الفحم.",
    },
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew unrepresented biblical singletons 11: already present")
        return 0
    seen = set(re.findall(r"hebrew:family:[0-9a-f]+", text))
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))["unread_biblical_lexical_queue"]
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        selected = []
        for item in queue:
            family = str(item["family_id"])
            if family in seen:
                continue
            count = connection.execute(
                "SELECT COUNT(*) FROM family_members WHERE family_id=?", (family,)
            ).fetchone()[0]
            if count == 1:
                selected.append(item)
        if len(selected) != EXPECTED_COUNT:
            raise ValueError(f"remaining singleton count drifted: {len(selected)}")
        digest = hashlib.sha256(
            "\n".join(
                str(item["family_id"]) + "|" + str(item["entry_id"])
                for item in selected
            ).encode("utf-8")
        ).hexdigest()
        if digest != EXPECTED_SHA256:
            raise ValueError(f"singleton queue drifted: {digest}")

        positive_roots = {str(spec["root"]) for spec in POSITIVE.values()}
        matches = matches_for_roots(DEFAULT_RESOURCES, positive_roots, None)
        fans = {root: independent_fan(matches[root]) for root in positive_roots}
        cards = []
        counts: Counter[str] = Counter()
        for rank, item in enumerate(selected, 1):
            entry_id = str(item["entry_id"])
            row = connection.execute(
                "SELECT headword,pos,gloss,etymology FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"missing entry: {entry_id}")
            roots = [
                {
                    "form": candidate[0],
                    "status": candidate[1],
                    "rules": json.loads(candidate[2]),
                }
                for candidate in connection.execute(
                    """
                    SELECT DISTINCT form,status,rule_ids_json
                    FROM candidates
                    WHERE entry_id=? AND kind='root'
                    ORDER BY route_flag,status,form,rule_ids_json
                    """,
                    (entry_id,),
                )
            ]
            headword = str(row["headword"])
            pos = str(row["pos"])
            gloss = str(row["gloss"])
            etymology = str(row["etymology"] or "").strip() or "لا أصل مسمى في الحقل"
            references = "؛ ".join(
                str(witness["reference"])
                for witness in item["biblical_witnesses"]
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
                terms = tuple(spec["terms"])
                for source in sources[:2]:
                    definition = fold(str(source["definition"]))
                    positions = [
                        definition.find(fold(term))
                        for term in terms
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
                outcome = f"{state}؛ العضو `{entry_id}` وحده؛ {spec['reason']}."
                scan = (
                    f"مروحة `{root}` مكتملة من "
                    f"{sources[0]['source_label']} + {sources[1]['source_label']}، "
                    "والمعنى المسمى حاضر في المصدرين."
                )
                sound = str(spec["sound"])
                bridge = str(spec["bridge"])
                counts["positive"] += 1
            elif (structural := structural_state(pos, headword, gloss)) is not None:
                state, reason = structural
                root = "غير مستعمل"
                outcome = f"غير صادر؛ {state} للعضو `{entry_id}`؛ {reason}"
                scan = "غير مشغل؛ الإغلاق البنيوي سابق للمقارنة."
                sound = "لا يستعمل صف صوت في الإغلاق البنيوي."
                bridge = reason
                counts["closure"] += 1
            else:
                state = "OPEN-CANDIDATE"
                root = str(roots[0]["form"]) if roots else "غير مولد"
                outcome = (
                    f"غير صادر؛ OPEN-CANDIDATE للعضو `{entry_id}`؛ "
                    "ثبت الشاهد التوراتي ومعنى الفرع، ولم يكتمل مقابل عربي "
                    "مرخص في هذا المرور."
                )
                scan = (
                    "لم تصدر مروحة موجبة؛ تحفظ مرشحات الجرد ولا يصنع "
                    "من غياب الحكم سالب."
                )
                sound = "المرشحات الآلية لا تحكم؛ كل صف يبقى في نطاقه الموقع."
                bridge = "لا جسر دلالي محكم مسمى في هذا المرور."
                counts["gap"] += 1

            root_text = (
                "؛ ".join(
                    f"`{candidate['form']}` ({candidate['status']}؛ "
                    f"{','.join(candidate['rules']) or 'هوية'})"
                    for candidate in roots
                )
                or "لا جذر كامل مولد في الجرد."
            )
            cards.append(
                "\n".join(
                    [
                        f"### بطاقة: `{item['family_id']}`، {headword}، الطابور التوراتي الأحادي 11، الرتبة {rank}",
                        f"- عائق: النوع={state}؛ يتطلب=المراجعة الثالثة أو استكمال الفجوة المسماة؛ العضو=`{entry_id}`.",
                        "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                        f"- الكلمةُ في الفرع: {headword}، {pos}، «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- أقدمُ صورةٍ مستعادة: شاهد توراتي للعضو نفسه: {references}؛ الأصل المنشور: {etymology}.",
                        "- الخطوةُ صفر (التعرية بصرف الفرع): لم تنزع زيادة إلا إذا سماها المصدر؛ والصورة الصرفية تغلق بصفتها صورة لا شاهدًا مستقلًا.",
                        "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف والنواة والمدار؛ لا يقفز الحكم فوق درجة ناجحة.",
                        f"- مسارُ الجذر الكامل أولًا: {root_text}",
                        f"- مسحُ المعاني العربيّة: {scan}",
                        *fan_lines,
                        f"- المقابلُ من اللسان: `{root}`؛ لا يحكم المرشح الآلي.",
                        f"- مسارُ الصوت: {sound}",
                        f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Hebrew، `{entry_id}`].",
                        f"- المدار: {bridge}",
                        "- المصفاة: الأصل المنشور والعلم والصورة والمركب فُحصت قبل الحكم.",
                        f"- فصلُ المتجانسات والاقتراض: العضو `{entry_id}` وحده؛ لا وراثة.",
                        "- مؤشر اليتم: الأسرة أحادية العضو في لقطة السكان المثبتة.",
                        "- إشعاع الأسرة في الفرع: عضو واحد وسلسلة معنى واحدة.",
                        "- إشعاع الأسرة في العربية: المعنى المستشهد به وحده، أو صفر عند الإغلاق والفجوة.",
                        "- جسورُ الاسترداد المفحوصة: الشاهد التوراتي؛ الأصل؛ الجذر؛ الأجوف؛ النواة؛ المدار؛ الصفوف؛ الصورة؛ القرض.",
                        f"- حالةُ الإغلاق: {state}.",
                        f"- الحكم (استكشاف): {outcome}",
                        "- عدسة الاسترداد: حفظت الشاهد والجذور والدرجة الأدنى الممكنة.",
                        "- عدسة التشكيك: منعت وراثة الصيغة، والقرض بلا مانح، والسالب من فجوة.",
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
            f"## العبريّة التوراتية، بقية الأسر الأحادية غير الممثلة ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو كل الأسر الأحادية غير الممثلة الباقية في طابور الشاهد التوراتي، ببصمة ترتيب ثابتة. لكل أسرة بطاقة، والصور الصرفية معزولة ولا تدخل المقام.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-UNREPRESENTED-SINGLETONS-11:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# العبريّة التوراتية، بقية الأسر الأحادية غير الممثلة",
                "",
                "## النطاق",
                "",
                f"- العدد: {EXPECTED_COUNT}.",
                f"- بصمة الترتيب: `{EXPECTED_SHA256}`.",
                "- كل أسرة باقية حملت بطاقة.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {counts['positive']}.",
                f"- الإغلاقات النهائية: {counts['closure']}.",
                "",
                "## الباقي",
                "",
                f"- فجوات صادقة: {counts['gap']}.",
                "",
                "## الحالة",
                "",
                "- محلي للمراجعة الثالثة.",
                "- لا خط برهان ولا سجل مركزي.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": EXPECTED_COUNT,
                "positive_connections": counts["positive"],
                "terminal_closures": counts["closure"],
                "held": counts["gap"],
                "order_sha256": EXPECTED_SHA256,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
