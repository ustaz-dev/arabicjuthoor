#!/usr/bin/env python3
"""Read every one-member-short Aramaic family with an explicit Arabic etymon.

The selection is structural and reproducible: it is the complete intersection
of the official one-member-short list and entries whose pinned Kaikki
etymology names Arabic.  Positives require a named sense in two independent
old Arabic dictionaries.  All verdict-bearing cards remain local for the
third-lens review.
"""
from __future__ import annotations

import json
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path

from search_arabic_root_senses import (
    ARABIC_MARKS,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-one-short-source-rich-batch-01-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-SOURCE-RICH-BATCH-01 -->"


EXPECTED = [
    "aramaic:family:0ff542a2384f3360e90c5b40",
    "aramaic:family:1a890e63f45b4449cef87e5c",
    "aramaic:family:23f81542a00c2859d88d6eb1",
    "aramaic:family:2bd6a0a9b036c1dad78bf7f7",
    "aramaic:family:2be3b50c1e966a5d5cf7f7cc",
    "aramaic:family:3a0bbc9b0fd69f5c0a719f08",
    "aramaic:family:3acfaab83edcd56496806c01",
    "aramaic:family:3da792c0fc5bfa0690932c03",
    "aramaic:family:43f7c91e0b4982c1fe3893b4",
    "aramaic:family:48d23ddf0e187a89467b383d",
    "aramaic:family:4a4dd1641d49e22345d7a3f7",
    "aramaic:family:5f3f53683c0fb8f5cbdedf6e",
    "aramaic:family:730fc88ca7c2656c9838f0b5",
    "aramaic:family:73273f7bb69714f75cdaa58d",
    "aramaic:family:74e9e12931f01f52979fc1a4",
    "aramaic:family:75d7f175de698608e9ba8c23",
    "aramaic:family:7832ace12a2ea664c89197e2",
    "aramaic:family:80659d373be421ba81b08593",
    "aramaic:family:83290ab4b380834a44d38ff8",
    "aramaic:family:885cb9289136bd3bbf442bbf",
    "aramaic:family:8d0293bf5ec2d64692c4d03f",
    "aramaic:family:913d5f184855940dcf696eed",
    "aramaic:family:a17f05b84dcb81bf7a0ff71a",
    "aramaic:family:a1f89d7b6eb867f4c7a4f009",
    "aramaic:family:a5a89efc24bc0d43a9bf4356",
    "aramaic:family:a6cbcf8972aa67c42f78fa39",
    "aramaic:family:ad89772a971261d33bf61ab7",
    "aramaic:family:b21e3cd2ae60deea1e172227",
    "aramaic:family:b4f0c2ac3a96201754010f25",
    "aramaic:family:bd8dfd3e1e9023047342464f",
    "aramaic:family:c13db91f4cab656bb2264218",
    "aramaic:family:c1ae2ef8f567bad81ecd2397",
    "aramaic:family:c5f0f61b5c8e7e881d5a0dd4",
    "aramaic:family:c6320b89ac58142fc13351b7",
    "aramaic:family:c9a9af0ddaebb695a06af50e",
    "aramaic:family:d6be29c3c4d421102f117408",
    "aramaic:family:d846c5d0ec83120fc003540b",
    "aramaic:family:de095018e1918bca0b72a167",
    "aramaic:family:e5f427b88b5e365b305674d7",
    "aramaic:family:f1f96dcc82a49b45322f3373",
    "aramaic:family:fae22766f0684165c24ad6ca",
    "aramaic:family:fbce46241e7244d3c68004b3",
    "aramaic:family:fc412a8b40d5542cdca29cf5",
]


def positive(
    root: str,
    terms: tuple[str, ...],
    verdict: str,
    reason: str,
    sound: str,
    bridge: str,
) -> dict[str, object]:
    return {
        "kind": "positive",
        "state": "READY",
        "root": root,
        "terms": terms,
        "verdict": verdict,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


def gap(
    state: str,
    root: str,
    reason: str,
    sound: str,
    bridge: str,
) -> dict[str, object]:
    return {
        "kind": "gap",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


def terminal(
    state: str,
    root: str,
    reason: str,
    bridge: str,
) -> dict[str, object]:
    return {
        "kind": "terminal",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": "العزل مسمى في المصدر؛ لا يستعمل صف صوت لإنتاج حكم نسب.",
        "bridge": bridge,
    }


SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: positive("رحم", ("الرحمن", "الرحمة"), "ROOT-TRACE", "רחמן والرحمن من جذر الرحمة نفسه", "الراء والحاء والميم هويات؛ اللاحقة ־ן في الصفة مسماة بعد الجذر ר־ח־מ.", "مباشر في الرحمة والاسم الوصفي."),
    EXPECTED[1]: positive("برد", ("البرد",), "ROOT-TRACE", "ברדא وبرد للحال نفسه", "الباء والراء والدال هويات؛ ألف الحالة الآرامية لا تدخل الجذر.", "مباشر في البرد النازل من السماء."),
    EXPECTED[2]: positive("عمد", ("العمود",), "ROOT-TRACE", "עמודא وعمود للركيزة القائمة نفسها", "العين والميم والدال هويات؛ الواو حركة مد وألف الحالة خارج الجذر.", "مباشر في العمود والدعامة."),
    EXPECTED[3]: gap("LAW-GAP", "خبر", "المصدر يقارن خبر العربية، لكن المعنى العربي القديم للخبر لا يطابق الجمع والمصاحبة الآرامية، وGUT-05 غير نافذ هنا", "لا صف موقع يحسم ח أمام خ في هذا العضو.", "الصوت والمعنى كلاهما غير مكتملين."),
    EXPECTED[4]: gap("LAW-GAP", "أخذ", "المصدر يعيد *ʔaḫaḏ- ويقارن أخذ في الأخذ نفسه، لكن انعكاسي ח وד أمام خ وذ يحتاجان صفين نافذين", "لا يختلق صف من المقارنة المنشورة.", "المعنى مباشر، والرجل الصوتية معلقة."),
    EXPECTED[5]: gap("OPEN-CANDIDATE", "رزز", "רזא للسر، والمقابل العربي المسمى في المصدر لا تعطيه المروحة معنى السر", "التقارب الشكلي وحده لا يكفي.", "لا جسر دلالي مباشر."),
    EXPECTED[6]: positive("أمم", ("الأمة",), "ROOT-TRACE", "אומתא وأمة لجماعة الناس نفسها تحت الجذر السامي المنشور", "الهمزة والميمان هويات؛ ת־א لاحقة الاسم الآرامية لا تدخل الجذر.", "مباشر في الأمة والجماعة."),
    EXPECTED[7]: terminal("INTRA-HOUSE-TRANSFER", "قهو", "المصدر يسمي العربية قهوة مانحًا مباشرًا", "انتقال متأخر داخل البيت، لا شاهد فرع مستقل."),
    EXPECTED[8]: terminal("FUNCTION-WORD", "بعد", "العضو أداة ربط بمعنى بعد لا مادة معجمية أصلية في المقام", "يعزل في جرد الأدوات مع بقاء المقارنة الوصفية."),
    EXPECTED[9]: gap("MORPHOLOGY-GAP", "أيي", "אתא للعلامة يعاد إلى *awayat- ويقارن آية، لكن تحليل الصوامت الضعيفة بين الصورتين غير موقع", "لا تحذف الواو أو تقلب الهمزة والياء بلا قانون صرف منشور.", "المعنى مباشر، والعائق صرفي صوتي."),
    EXPECTED[10]: gap("OPEN-CANDIDATE", "كرز", "כרז للمناداة، وكرز العربية المسمى في المصدر لا تثبت مروحته المناداة", "تقارب الجذر لا يحكم مع افتراق المعنى.", "لا جسر دلالي مباشر."),
    EXPECTED[11]: gap("LAW-GAP", "ثدي", "תדא والثدي معنى واحد ومن أصل منشور، لكن الصامت الضعيف الأخير مختلف بلا صف موقع", "DENT-01 يرخص ת أمام ث، ولا يفسر א أمام ي.", "المعنى مباشر والرجل الأخيرة معلقة."),
    EXPECTED[12]: positive("نسم", ("النسمة", "النفس"), "ROOT-TRACE", "נשמתא ونسمة يلتقيان في النفس والروح", "SIB-01 يرخص ש ↔ س؛ النون والميم هويتان، وתא لاحقة اسم.", "مباشر في النفس والروح والنسمة."),
    EXPECTED[13]: positive("جدي", ("الجدي",), "ROOT-TRACE", "גדיא وجدي لصغير الماعز نفسه", "GUT-03 يرخص ג ↔ ج؛ الدال والياء هويتان وألف الحالة خارج الجذر.", "مباشر في الجدي."),
    EXPECTED[14]: gap("MORPHOLOGY-GAP", "عنكب", "עכביתא تقارن عنكبوت، لكن النون والبنية اللاحقية لا يفسرهما تحليل موقع", "لا ترد النون أو تسقط الشين والتاء بالتخمين.", "مباشر في العنكبوت، والبنية معلقة."),
    EXPECTED[15]: gap("LAW-GAP", "ملك", "מלאכא وملك في الملاك متقاربان، لكن الهمزة الداخلية الآرامية لا تفسرها الشبكة", "لا تسقط א من الجذر بلا صف أو تحليل منشور.", "المعنى مباشر والرجل الصوتية معلقة."),
    EXPECTED[16]: gap("MORPHOLOGY-GAP", "خنزير", "חזירא والخنزير للحيوان نفسه، لكن نون العربية الزائدة لا تفسرها بطاقة صرف منشورة", "لا تضاف النون ولا تحذف من غير قانون.", "مباشر في الخنزير."),
    EXPECTED[17]: terminal("LOANWORD", "تاج", "المصدر يسمي الأصل الفرثي *tāg ويذكر أن العربية والأرمنية اقترضتاه أيضًا", "مانح إيراني خارجي مسمى."),
    EXPECTED[18]: gap("LAW-GAP", "حمض", "חמע والتخمر والحموضة في حدث واحد، لكن ע أمام ض بلا صف موقع", "المعنى لا يرخص الصامت وحده.", "خطوة واحدة من التخمير إلى الحموضة."),
    EXPECTED[19]: positive("قدس", ("التقديس", "القدس"), "ROOT-TRACE", "קדיש وقدس في التقديس والتنزيه", "SIB-01 يرخص ש ↔ س؛ القاف والدال هويتان، وبنية الفعل داخلية.", "مباشر في التقديس."),
    EXPECTED[20]: terminal("FUNCTION-WORD", "ثمم", "العضو ظرف مكان بمعنى هناك", "يعزل في جرد الأدوات والظروف غير المعجمية للمقام."),
    EXPECTED[21]: positive("أمر", ("الإمر",), "ROOT-TRACE", "אמרא وإمر للحمل الصغير نفسه", "الهمزة والميم والراء هويات؛ ألف الحالة خارج الجذر.", "مباشر في الحمل الصغير."),
    EXPECTED[22]: gap("OPEN-CANDIDATE", "قصع", "קצע للقطع، والمصدر يسرد عدة جذور عربية متقاربة بلا تعيين واحد", "تعدد المقابلات يمنع اختيار أجملها حكمًا.", "حقل القطع مباشر لكن هوية الجذر غير محسومة."),
    EXPECTED[23]: terminal("LOANWORD", "فاثر", "المصدر يسمي السومرية أصلًا نهائيًا عبر الأكدية", "مسار اقتراض خارجي مسمى."),
    EXPECTED[24]: terminal("FUNCTION-WORD", "ذا", "العضو أداة ربط بمعنى أن", "يعزل في جرد الأدوات مع بقاء المقارنة الوصفية."),
    EXPECTED[25]: positive("أتى", ("جئت",), "NUCLEUS-TRACE", "אתא وأتى للمجيء نفسه، والنواة أت محفوظة في الصورتين", "النواة א־ת ↔ أ־ت هوية؛ الصامت الضعيف الأخير مختلف فلا يدعى جذر كامل.", "مباشر في المجيء."),
    EXPECTED[26]: positive("عنب", ("العنب",), "ROOT-TRACE", "ענבתא وعنب للثمر نفسه", "العين والنون والباء هويات؛ תא لاحقة اسم.", "مباشر في العنب."),
    EXPECTED[27]: positive("دبق", ("دبق", "لزق"), "ROOT-TRACE", "דבק ودبق في الالتصاق", "الدال والباء والقاف هويات.", "مباشر في اللزوق والالتصاق."),
    EXPECTED[28]: positive("عظم", ("العظم",), "ROOT-TRACE", "טמא وعظم من إعادة البناء المنشورة *ʕaṯ̣m- وللعضو نفسه", "DENT-08 بشروطه من ظ العربية إلى ט الآرامية، وهذه إحدى مرساته المنصوصة؛ لا صف آخر.", "مباشر في العظم."),
    EXPECTED[29]: gap("LAW-GAP", "زرع", "דרעא للبذر ويقارن زرع، لكن ד أمام ز لا يملك صفًا موقعًا لهذا العضو", "DENT-03 يولد ذرع لا زرع؛ لا يستبدل المرشح بالمقارنة يدويًا.", "مباشر في البذر، والرجل الصوتية معلقة."),
    EXPECTED[30]: positive("بكي", ("البكاء", "بكى"), "NUCLEUS-TRACE", "בכא وبكى للبكاء نفسه، والنواة بك محفوظة", "الباء والكاف هويتان؛ اختلاف الهمزة والياء الأخيرة يمنع ادعاء الجذر الكامل.", "مباشر في البكاء."),
    EXPECTED[31]: gap("OPEN-CANDIDATE", "لحم", "לחמא خبز ولحم العربية لحم، والمصدر يقارن اللفظين مع افتراق الطعامين", "الجذر متطابق، ولا يكفي ذلك للحكم.", "لا جسر واحد مسمى بين الخبز واللحم."),
    EXPECTED[32]: positive("بوب", ("الباب",), "ROOT-TRACE", "בבא وباب للمدخل نفسه", "الباءان من الجذر ب־و־ب، والاحتكاك الآرامي وألف الحالة من صرف الفرع.", "مباشر في الباب والمدخل."),
    EXPECTED[33]: positive("حمي", ("حماه", "حماية"), "NUCLEUS-ECHO", "חמא للحضانة على البيض وحمى للحماية يلتقيان في الحفظ", "النواة ح־م هوية؛ اختلاف الصامت الضعيف الأخير يمنع الجذر الكامل.", "خطوة مدارية واحدة: الحضن حماية للبيض."),
    EXPECTED[34]: positive("قيظ", ("القيظ", "الحر"), "ROOT-TRACE", "קיטא والقيظ للصيف الحار نفسه", "DENT-08 من ظ العربية إلى ט الآرامية مع مرساة *ṯ̣ الشمالية؛ القاف والياء هويتان.", "مباشر في حر الصيف."),
    EXPECTED[35]: gap("OPEN-CANDIDATE", "علم", "עלמא للأبد والعالم العربية للخلق أو الدنيا", "الجذر المرشح لا يحسم المعنى.", "تقارب الدهر والعالم محتمل وغير مباشر."),
    EXPECTED[36]: positive("ثقل", ("الثقل",), "ROOT-ECHO", "תקל للتعثر من أصل الثقل والعبء المنشور", "DENT-01 يرخص ת ↔ ث؛ القاف واللام هويتان.", "خطوة واحدة مسماة: الثقل والعبء يسببان التعثر."),
    EXPECTED[37]: gap("MORPHOLOGY-GAP", "خنزير", "חזירתא مؤنث الخنزير، ونون العربية لا يفسرها تحليل موقع", "لا تضاف النون ولا تحذف من غير قانون.", "مباشر في أنثى الخنزير."),
    EXPECTED[38]: gap("LAW-GAP", "غراب", "עורבא والغراب من *ḡurayb-، لكن انعكاس الغين في ע الآرامية غير مجدول", "لا صف موقع لـע ↔ غ في هذا العضو.", "مباشر في الغراب."),
    EXPECTED[39]: positive("برك", ("البركة",), "ROOT-TRACE", "ברכתא وبركة للبركة نفسها", "الباء والراء والكاف هويات؛ תא لاحقة اسم.", "مباشر في البركة."),
    EXPECTED[40]: gap("OPEN-CANDIDATE", "مسح", "ܡܫܝܚܐ لقب المسيح، ومسار انتقال اللقب بين الآرامية والعبرية والعربية غير مسمى في المصدر", "لا يحول التشابه إلى شاهد مستقل قبل ضبط النقل.", "المعنى الديني مطابق، ومسار الاتصال معلق."),
    EXPECTED[41]: positive("مسح", ("الدهن", "مسح"), "ROOT-ECHO", "משח للدهن ومسح العربية لإمرار اليد والدهن", "SIB-01 يرخص ש ↔ س؛ الميم والحاء هويتان.", "خطوة واحدة مسماة: الدهن يكون بالمسح."),
    EXPECTED[42]: positive("دبب", ("الدب",), "ROOT-TRACE", "דבא ودب للحيوان نفسه من *dubb-", "الدال والباءان هويات؛ ألف الحالة خارج الجذر.", "مباشر في الدب."),
}


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def fold(value: str) -> str:
    value = ARABIC_MARKS.sub("", unicodedata.normalize("NFKC", value))
    return " ".join(value.split())


def excerpt(definition: str, terms: tuple[str, ...]) -> str:
    value = fold(definition)
    positions = [value.find(fold(term)) for term in terms if value.find(fold(term)) >= 0]
    if not positions:
        raise ValueError(f"named sense absent: {terms}")
    start = max(0, min(positions) - 55)
    end = min(len(value), min(positions) + 220)
    return value[start:end]


def fans() -> dict[str, dict[str, object]]:
    roots = {str(item["root"]) for item in SPECS.values()}
    matches = matches_for_roots(DEFAULT_RESOURCES, roots, None)
    result = {}
    for root in roots:
        fan = independent_fan(matches[root])
        result[root] = {
            "ready": bool(fan["judgment_ready"]),
            "sources": [
                {
                    "source": str(row["source_label"]),
                    "definition": str(row["definition"]),
                }
                for row in fan["selected_sources"]
            ],
        }
    return result


def render_card(
    rank: int,
    family: str,
    entry: dict[str, object],
    specification: dict[str, object],
    fan_map: dict[str, dict[str, object]],
) -> str:
    root = str(specification["root"])
    fan = fan_map[root]
    kind = str(specification["kind"])
    source_notes = []
    if kind == "positive":
        rows = list(fan["sources"])
        if not fan["ready"] or len(rows) < 2:
            raise ValueError(f"{family}: incomplete positive fan for {root}")
        terms = tuple(specification["terms"])
        source_notes = [
            f"  - {row['source']}: «{excerpt(str(row['definition']), terms)}»"
            for row in rows[:2]
        ]
        scan = (
            f"مروحة `{root}` مكتملة من {rows[0]['source']} + "
            f"{rows[1]['source']}، والمعنى المسمى حاضر في كليهما."
        )
        verdict = (
            f"{specification['verdict']}؛ العضو `{entry['entry_id']}` وحده؛ "
            f"{specification['reason']}."
        )
    else:
        rows = list(fan["sources"])
        scan = (
            f"مروحة `{root}` أعادت {len(rows)} مصدر مستقل؛ لا يصدر منها حكم آلي."
            if rows
            else f"لم يجد المسح مدخلًا مستقلًا للجذر `{root}`؛ الغياب ليس سالبًا."
        )
        verdict = (
            f"غير صادر؛ {specification['state']} للعضو `{entry['entry_id']}`؛ "
            f"{specification['reason']}."
            if kind == "terminal"
            else f"غير صادر؛ {specification['reason']}."
        )
    etymology = str(entry["etymology"]).strip() or "لا أصل منشور في الحقل"
    source_lines = "\n".join(source_notes)
    return "\n".join(
        [
            f"### بطاقة: `{family}`، {entry['headword']}، دفعة المقام الآرامية 1، الرتبة {rank}",
            f"- عائق: النوع={specification['state']}؛ يتطلب="
            + (
                "المراجعة المضادة الثالثة قبل الإيداع."
                if kind == "positive"
                else f"{specification['reason']}."
            )
            + f"؛ العضو=`{entry['entry_id']}`.",
            "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
            f"- الكلمةُ في الفرع: {entry['headword']} `{entry['romanization'] or 'بلا رومنة'}`، {entry['pos']}، «{entry['gloss']}» [Kaikki Aramaic، `{entry['entry_id']}`].",
            f"- أقدمُ صورةٍ مستعادة: {etymology}.",
            "- الخطوةُ صفر (التعرية بصرف الفرع): في الآرامية لا تدخل ألف الحالة واللواحق المسماة في المصدر الجذر؛ لا تنزع زيادة أخرى بالتخمين، والعضو المسمى وحده وحدة الحكم.",
            "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف، ثم النواة، ثم المدار؛ لا يقفز الحكم فوق درجة ناجحة.",
            f"- مسحُ المعاني العربيّة: {scan}",
            *([source_lines] if source_lines else []),
            f"- المقابلُ من اللسان: `{root}`؛ المروحة أعلاه هي سند المعنى لا مولد الحكم.",
            f"- مسارُ الصوت: {specification['sound']}",
            f"- المعنى من قاموس الفرع: «{entry['gloss']}» [Kaikki Aramaic، `{entry['entry_id']}`].",
            f"- المدار: {specification['bridge']}",
            "- المصفاة: الأصل المنشور أعلاه فُحص قبل الحكم؛ لا يرث القريب حكم المقترض أو الأداة أو المتجانس.",
            f"- فصلُ المتجانسات والاقتراض: العضو `{entry['entry_id']}` وحده؛ loan_hint={'نعم' if entry['loan_hint'] else 'لا'}؛ لكل عضو حق نقض مستقل.",
            "- مؤشر اليتم: الأسرة أحادية العضو في لقطة السكان المثبتة.",
            "- إشعاع الأسرة في الفرع: عضو واحد وسلسلة معنى واحدة، بلا وراثة.",
            "- إشعاع الأسرة في العربية: المعنى المستشهد به وحده، بلا وراثة للمروحة كلها.",
            "- جسورُ الاسترداد المفحوصة: الأصل المنشور؛ الجذر؛ الأجوف؛ النواة؛ المدار؛ مروحة المعجمين؛ الصفوف اللازمة؛ القرض؛ المتجانس.",
            f"- حالةُ الإغلاق: {specification['state']}.",
            f"- الحكم (استكشاف): {verdict}",
            "- عدسة الاسترداد: حفظت المقارنة المنشورة والدرجات كلها ولم تحصر البحث في مرشح آلي واحد.",
            "- عدسة التشكيك: اختبرت القانون الصوتي والصرف والقرض والمتجانس، ومنعت صناعة سالب من فجوة.",
            "- ملاحظات: محلي للمراجعة المضادة الثالثة؛ لا سجل مركزي ولا خط برهان.",
            "",
        ]
    )


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short source-rich batch 01: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    one_short = report["languages"]["aramaic"]["one_member_short"]
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        selected = []
        for item in one_short:
            row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
                "FROM entries WHERE entry_id=?",
                (item["missing_entry_id"],),
            ).fetchone()
            if row and "Arabic" in str(row["etymology"] or ""):
                selected.append((str(item["family_id"]), dict(row)))
    finally:
        connection.close()
    families = [family for family, _ in selected]
    if families != EXPECTED:
        raise ValueError(f"source-rich one-short selection drifted: {families}")
    fan_map = fans()
    cards = [
        render_card(rank, family, entry, SPECS[family], fan_map)
        for rank, (family, entry) in enumerate(selected, 1)
    ]
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## حملة المقام الآرامية، الأسر الناقصة عضوًا واحدًا ذات المقابل المنشور ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو التقاطع الكامل، لا عينة منتقاة، بين قائمة الأسر الآرامية الرسمية الناقصة عضوًا واحدًا وبين الأعضاء التي يسمي حقل أصلها في لقطة Kaikki العربية صراحة. دخلت الصلات والفجوات والقروض والأدوات معًا، ولم يغلق نقص الشاهد سلبًا.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-SOURCE-RICH-BATCH-01:END -->",
            "",
        ]
    )
    atomic_write(READING, text.rstrip() + "\n" + block)
    positive_count = sum(spec["kind"] == "positive" for spec in SPECS.values())
    closure_count = sum(spec["kind"] == "terminal" for spec in SPECS.values())
    held_count = len(SPECS) - positive_count - closure_count
    atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المقام الآرامية، دفعة المصدر العربي الصريح المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئ التقاطع الكامل بين الأسر الناقصة عضوًا واحدًا والأعضاء التي تسمي العربية صراحة في حقل الأصل المنشور. لم ينتق موجب ويترك خلافه.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positive_count}.",
                f"- الإغلاقات النهائية: {closure_count}.",
                "",
                "## الباقي",
                "",
                f"- فجوات أو مرشحات بلا حكم: {held_count}.",
                f"- مجموع البطاقات: {len(SPECS)}.",
                "",
                "## الحالة",
                "",
                "- كل البطاقات محلية للمراجعة المضادة الثالثة.",
                "- لا NO-TRACE مصنوع من فجوة، ولا سجل مركزي، ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": len(SPECS),
                "positive_connections": positive_count,
                "terminal_closures": closure_count,
                "held": held_count,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
