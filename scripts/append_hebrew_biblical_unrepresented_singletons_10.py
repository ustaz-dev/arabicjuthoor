#!/usr/bin/env python3
"""Read the first 180 unrepresented biblical singleton families in queue order."""
from __future__ import annotations

import hashlib
import json
import re
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path

from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = ROOT / "05-audits" / "2026-07-28-hebrew-biblical-unrepresented-singletons-10-local.md"
MARKER = "<!-- HEBREW-BIBLICAL-UNREPRESENTED-SINGLETONS-10 -->"
DATE = "2026-07-28"
EXPECTED_SHA256 = "491e34a236065be3c6dd1c4059a3b833170aacb2203af254575e747f4c79c931"

POSITIVE = {
    "kaikki_hebrew:1939:en-תל-he-noun-vYUjGnPZ": {
        "root": "تلل", "terms": ("التل",), "verdict": "ROOT-TRACE",
        "reason": "תל والتل للربوة الترابية نفسها من *tall-",
        "sound": "التاء واللامان هويات؛ لا صف لازم.",
        "bridge": "مباشر في التل.",
    },
    "kaikki_hebrew:1879:en-אפרוח-he-noun-cBkMWDeY": {
        "root": "فرخ", "terms": ("الفرخ",), "verdict": "NUCLEUS-TRACE",
        "reason": "אפרוח والفرخ لصغير الطائر بنص المقارنة المنشورة",
        "sound": "LAB-07 يرخص פ ↔ ف؛ نواة ف־ر محفوظة، ولا يدعى جذر كامل مع بقية البنية.",
        "bridge": "مباشر في فرخ الطائر.",
    },
    "kaikki_hebrew:8679:en-מזמור-he-noun-hNwM1ZTl": {
        "root": "زمر", "terms": ("المزمور", "الصوت"), "verdict": "ROOT-ECHO",
        "reason": "מזמור للمزمور ومزمار العربية للصوت الموسيقي بنص المصدر",
        "sound": "الزاي والميم والراء الجذرية هويات؛ الميمان من بناء الاسم.",
        "bridge": "الأغنية المقدسة والصوت المزمارى سلسلة موسيقية واحدة.",
    },
    "kaikki_hebrew:11370:en-מנהרה-he-noun-~SgrGB6E": {
        "root": "نهر", "terms": ("النهر",), "verdict": "ROOT-ECHO",
        "reason": "المصدر يرد מנהרה إلى נהר، والنهر العربي للماء الجاري",
        "sound": "النون والهاء والراء هويات؛ الميم واللاحقة من بناء الاسم المسمى.",
        "bridge": "الوادي ذو الجدول يحمل النهر داخله بنص شرح المصدر.",
    },
    "kaikki_hebrew:4075:en-גר-he-noun-D7VZONtf": {
        "root": "جور", "terms": ("الجار",), "verdict": "ROOT-ECHO",
        "reason": "גר للغريب المقيم وجار العربية للمجاور والمستجير",
        "sound": "GUT-03 يرخص ג ↔ ج؛ الواو رجل الجذر الأجوف والراء هوية.",
        "bridge": "الإقامة بجوار القوم مدار الغريب المستجير.",
    },
    "kaikki_hebrew:7170:en-מעצר-he-noun-mafCRX-6": {
        "root": "عصر", "terms": ("عصر",), "verdict": "ROOT-ECHO",
        "reason": "المصدر يرد מעצר إلى ע־צ־ר، وعصر العربية للضغط والحبس",
        "sound": "العين والصاد والراء هويات؛ الميم من بناء الاسم.",
        "bridge": "الضغط والمنع مدار الاعتقال.",
    },
    "kaikki_hebrew:1852:en-קריאה-he-noun-4BFMC~GO": {
        "root": "قرأ", "terms": ("القراءة",), "verdict": "NUCLEUS-TRACE",
        "reason": "קריאה والقراءة للفعل نفسه",
        "sound": "القاف والراء نواة محفوظة؛ الهمزة والياء وبنية الاسم تمنع ادعاء الجذر الكامل.",
        "bridge": "مباشر في القراءة.",
    },
    "kaikki_hebrew:8547:en-נמנע-he-verb-IHXxgACi": {
        "root": "منع", "terms": ("امتنع",), "verdict": "ROOT-TRACE",
        "reason": "المصدر يسمي נמנע مبنيًا من מנע، وامتنع العربية للفعل نفسه",
        "sound": "الميم والنون والعين الجذرية هويات؛ النون السابقة من المبني المتوسط المسمى.",
        "bridge": "مباشر في الامتناع.",
    },
    "kaikki_hebrew:930:en-מאכל-he-noun-a1wWUFQn": {
        "root": "أكل", "terms": ("المأكل", "الطعام"), "verdict": "ROOT-TRACE",
        "reason": "מאכל والمأكل للطعام من جذر أكل",
        "sound": "الهمزة والكاف واللام هويات؛ الميم من بناء الاسم.",
        "bridge": "مباشر في الطعام والمأكل.",
    },
    "kaikki_hebrew:16791:en-דומן-he-noun-NMDd5I-s": {
        "root": "دمن", "terms": ("الدمن",), "verdict": "ROOT-TRACE",
        "reason": "דומן والدمن للسرجين بنص المقارنة المنشورة",
        "sound": "الدال والميم والنون هويات؛ الواو من بنية الاسم.",
        "bridge": "مباشر في الدمن والسماد.",
    },
    "kaikki_hebrew:9822:en-גיבור-he-adj-RjXn2ziv": {
        "root": "جبر", "terms": ("الجبار", "القوة"), "verdict": "ROOT-ECHO",
        "reason": "גיבור للقوي والمصدر يقارنه بجبار العربية",
        "sound": "GUT-03 يرخص ג ↔ ج؛ الباء والراء هويتان.",
        "bridge": "القوة والجبروت مدار واحد.",
    },
    "kaikki_hebrew:14542:en-ביכורים-he-noun-85Uvaya~": {
        "root": "بكر", "terms": ("البكر", "أول"), "verdict": "ROOT-TRACE",
        "reason": "ביכורים للبواكير وبكر العربية للأول والمتقدم",
        "sound": "الباء والكاف والراء الجذرية هويات؛ صيغة الجمع لا تورث حكمًا خارج العضو.",
        "bridge": "مباشر في أول الثمر.",
    },
    "kaikki_hebrew:764:en-מרכבה-he-noun-ltV5itJH": {
        "root": "ركب", "terms": ("الركوب",), "verdict": "ROOT-TRACE",
        "reason": "מרכבה ومركبة العربية للعربة بنص المصدر",
        "sound": "الراء والكاف والباء الجذرية هويات؛ الميم واللاحقة من بناء الاسم.",
        "bridge": "مباشر في المركبة والركوب.",
    },
    "kaikki_hebrew:13578:en-רחום-he-adj-qjZNV25E": {
        "root": "رحم", "terms": ("الرحمة",), "verdict": "ROOT-TRACE",
        "reason": "רחום ورحيم العربية في الرحمة",
        "sound": "الراء والحاء والميم هويات؛ الواو من بناء الصفة.",
        "bridge": "مباشر في الرحمة.",
    },
    "kaikki_hebrew:10678:en-נקבר-he-verb-7becSydY": {
        "root": "قبر", "terms": ("القبر",), "verdict": "ROOT-TRACE",
        "reason": "נקבר للمبني للمجهول من קבר وقبر العربية للدفن",
        "sound": "القاف والباء والراء الجذرية هويات؛ النون من المبني للمجهول في المصدر.",
        "bridge": "مباشر في القبر والدفن.",
    },
}

TRANSFER = {
    "kaikki_hebrew:811:en-אנוש-he-noun-Q8tDejKq": (
        "INTRA-HOUSE-TRANSFER",
        "المصدر يسمي الآرامية مانحًا قديمًا للصورة؛ يحال إلى زوج المانح ولا يعد شاهد فرع مستقلًا.",
    )
}

FORM_MARKERS = (
    "defective spelling of ",
    "alternative form of ",
    "bare infinitive of ",
    "to-infinitive of ",
    "singular form of ",
    "plural form of ",
    "first-person ",
    "second-person ",
    "third-person ",
    "masculine singular present participle",
    "feminine singular present participle",
)


def fold(value: str) -> str:
    return " ".join(
        ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value)).split()
    )


def atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def structural_state(pos: str, headword: str, gloss: str) -> tuple[str, str] | None:
    lowered = gloss.lower()
    if lowered.startswith(FORM_MARKERS) or any(
        marker in lowered
        for marker in (
            " vav-consecutive ",
            ": third-person ",
            ": second-person ",
            ": first-person ",
            " with suffix indicating ",
        )
    ):
        return "FORM-OF-ISOLATED", "نص المعنى يصرح بأنها صورة صرفية."
    if pos == "name":
        return "PROPER-NAME-ISOLATED", "المصدر يصنفها اسم علم."
    if pos in {"conj", "particle", "prep"}:
        return "FUNCTION-WORD", "المصدر يصنفها أداة نحوية."
    if pos in {"phrase", "proverb"} or " " in headword:
        return "COMPOUND-BOUNDARY", "العضو مركب نصي لا يرث حكم رأسه."
    return None


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew unrepresented biblical singletons 10: already present")
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
            if count != 1:
                continue
            selected.append(item)
            if len(selected) == 180:
                break
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
                str(witness["reference"]) for witness in item["biblical_witnesses"]
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
                        for term in terms if definition.find(fold(term)) >= 0
                    ]
                    if not positions:
                        raise ValueError(f"{entry_id}: named sense absent in fan")
                    start = max(0, min(positions) - 55)
                    end = min(len(definition), min(positions) + 220)
                    fan_lines.append(
                        f"  - {source['source_label']}: «{definition[start:end]}»"
                    )
                state = str(spec["verdict"])
                outcome = (
                    f"{state}؛ العضو `{entry_id}` وحده؛ {spec['reason']}."
                )
                scan = (
                    f"مروحة `{root}` مكتملة من "
                    f"{sources[0]['source_label']} + {sources[1]['source_label']}، "
                    "والمعنى المسمى حاضر في المصدرين."
                )
                sound = str(spec["sound"])
                bridge = str(spec["bridge"])
                counts["positive"] += 1
            elif entry_id in TRANSFER:
                state, reason = TRANSFER[entry_id]
                root = "غير مستعمل"
                outcome = f"غير صادر؛ {state} للعضو `{entry_id}`؛ {reason}"
                scan = "غير مشغل؛ طريق النقل المنشور يسبق المقارنة."
                sound = "لا يستعمل صف صوت لإنتاج حكم نسب من عضو منقول."
                bridge = reason
                counts["closure"] += 1
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
                sound = (
                    "المرشحات الآلية لا تحكم؛ كل صف يبقى في نطاقه الموقع."
                )
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
                        f"### بطاقة: `{item['family_id']}`، {headword}، الطابور التوراتي الأحادي 10، الرتبة {rank}",
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
            f"## العبريّة التوراتية، أول 180 أسرة أحادية غير ممثّلة ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو أول 180 أسرة أحادية غير ممثلة في طابور الشاهد التوراتي، ببصمة ترتيب ثابتة. لكل أسرة بطاقة، والصور الصرفية معزولة ولا تدخل المقام.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-UNREPRESENTED-SINGLETONS-10:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# العبريّة التوراتية، أول 180 أسرة أحادية غير ممثلة",
                "",
                "## النطاق",
                "",
                f"- بصمة الترتيب: `{EXPECTED_SHA256}`.",
                "- كل أسرة من أول 180 حملت بطاقة.",
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
                "cards": 180,
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
