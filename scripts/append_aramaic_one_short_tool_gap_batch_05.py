#!/usr/bin/env python3
"""Read the first thirty TOOL-GAP members on the Aramaic one-short queue."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
REPORT = ROOT / "data" / "proof-eligible-families.json"
POPULATION = ROOT / "data" / "proof-family-population.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
BASE_PATH = ROOT / "scripts" / "append_aramaic_one_short_source_rich_batch_01.py"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-one-short-tool-gap-batch-05-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-05 -->"

EXPECTED = [
    "aramaic:family:01690ebf9f03a1e80b30971a",
    "aramaic:family:0973cfd715e4ab71a83a0160",
    "aramaic:family:0eb6e7df69ea709a41b31bbe",
    "aramaic:family:0fa6c2a005d02213b579cc49",
    "aramaic:family:11c703ac211c15de318ec19e",
    "aramaic:family:1be7e5d307df55935ecbf2ed",
    "aramaic:family:1e2d834711b569e2c6e91c44",
    "aramaic:family:6433686305c2d8f229da140d",
    "aramaic:family:697f310a5b126bb25f596a37",
    "aramaic:family:70fdd4acf63c86516b8f85c7",
    "aramaic:family:7108ba4a8aff266ef4276e8e",
    "aramaic:family:710aecf8404ae85976ecc01f",
    "aramaic:family:742ffa5ef59dfad7caf29da4",
    "aramaic:family:75d7f175de698608e9ba8c23",
    "aramaic:family:7b21aa5e55121f7990ecd4aa",
    "aramaic:family:7bdc1e2a6a3d48fb901ce22d",
    "aramaic:family:7bf401b726adf04afd06aa10",
    "aramaic:family:816e4874931b467ab9999450",
    "aramaic:family:818a75fd5ecb73fb731781cd",
    "aramaic:family:86b713daa4c92c38f46f223e",
    "aramaic:family:872c4b6da768c131ee3b6752",
    "aramaic:family:90fcf738efda6cd3825567cd",
    "aramaic:family:9208d5d1817d1dd2d8125061",
    "aramaic:family:94530a5f0dbd9357265748ee",
    "aramaic:family:98d39cc5b9cbfda020005159",
    "aramaic:family:9c269e1d60d5fbda13594c81",
    "aramaic:family:9d6d8980dac2bb7b7d4d1864",
    "aramaic:family:9f928ab5bc0f9121f4c217b3",
    "aramaic:family:a0904d3a5855a572eecd600c",
    "aramaic:family:a258e9ce6c831328ced3acc5",
]


def load_base():
    specification = importlib.util.spec_from_file_location(
        "aramaic_source_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Aramaic source base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


base = load_base()
gap = base.gap
positive = base.positive

SPECS = {
    EXPECTED[0]: gap(
        "SOURCE-GAP", "نعنع",
        "ננעא للنعناع، لكن المروحة لم تستوف مصدرين عربيين قديمين مستقلين لهذا الجذر",
        "الصوامت الرباعية قريبة بعد رد ألف الحالة، ولا يعوض الصوت نقص المصدر.",
        "مباشر في النعناع، وعائقه توثيقي.",
    ),
    EXPECTED[1]: gap(
        "SOURCE-GAP", "بئر",
        "בארא والبئر من *biʔr-، لكن المروحة المحلية لم تستوف مصدرين مستقلين",
        "الباء والهمزة والراء هويات تاريخية، وألف الحالة خارج الجذر.",
        "مباشر في البئر، وعائقه توثيقي.",
    ),
    EXPECTED[2]: gap(
        "OPEN-CANDIDATE", "شمل",
        "סמלא لجهة اليسار، وشمل العربية للجمع والإحاطة",
        "SIB-01 يفتح شمل، ولا يكفي مع افتراق المعنى.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[3]: gap(
        "MORPHOLOGY-GAP", "سني",
        "שניא جمع السنوات، ويلزم رد الجمع الآرامي إلى لمته قبل مقارنة سنة أو سنين",
        "لا تسقط اللاحقة ولا تعين الرجل الضعيفة بالتخمين.",
        "المعنى معلوم، والبنية الصرفية معلقة.",
    ),
    EXPECTED[4]: gap(
        "OPEN-CANDIDATE", "توج",
        "תגג للتتويج، وتاج العربية اسم التاج؛ البنية الصرفية والصامت الأوسط غير محسومين",
        "DENT-01 وGUT-03 لا يثبتان وحدهما رد التضعيف إلى الواو.",
        "المعنى قريب، والتحليل غير مكتمل.",
    ),
    EXPECTED[5]: positive(
        "لوز", ("اللوز",), "ROOT-TRACE",
        "לוזא واللوز للثمر نفسه",
        "اللام والواو والزاي هويات؛ ألف الحالة خارج الجذر.",
        "مباشر في اللوز.",
    ),
    EXPECTED[6]: gap(
        "MORPHOLOGY-GAP", "ثني",
        "תרי للاثنين، لكن رد الراء والياء إلى بنية اثنين يحتاج تحليل عدد منشور",
        "DENT-01 وحده لا يحل بقية الصوامت.",
        "المعنى مباشر، والبنية معلقة.",
    ),
    EXPECTED[7]: positive(
        "كيس", ("الكيس",), "ROOT-TRACE",
        "כיסא والكيس للوعاء نفسه",
        "الكاف والياء والسين هويات؛ ألف الحالة خارج الجذر.",
        "مباشر في الكيس.",
    ),
    EXPECTED[8]: positive(
        "زرع", ("الزرع", "زرع"), "ROOT-TRACE",
        "אזדרע صيغة من جذر זרع، وزرع العربية في بذر الأرض",
        "الزاي والراء والعين هويات؛ السابقة والبنية الداخلية مسماة في حقل الجذر.",
        "مباشر في الزرع والبذر.",
    ),
    EXPECTED[9]: gap(
        "OPEN-CANDIDATE", "حدو",
        "חדותא للفرح، وحدو العربية لا تسمي الفرح في المروحة",
        "الحاء والدال ظاهرتان، واللاحقة خارج المرشح.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[10]: gap(
        "MORPHOLOGY-GAP", "يمن",
        "ימא للحلف، ويمين العربية للحلف، لكن النون وبنية الاسم غير ظاهرتين في الفعل الآرامي",
        "لا ترد النون بالتخمين.",
        "المعنى مباشر، والبنية معلقة.",
    ),
    EXPECTED[11]: gap(
        "LAW-GAP", "عصي",
        "אעא للخشب من *ʕiṣ́-، ومقابل العربية يحتاج انعكاس الصفير الأم وتعيين اللمة",
        "لا صف موقع يحسم الصامت الأوسط لهذا العضو.",
        "المعنى قريب، والرجل الصوتية معلقة.",
    ),
    EXPECTED[12]: positive(
        "دجل", ("الدجل", "الكذب"), "ROOT-TRACE",
        "דגל ودجل في الكذب والخداع",
        "GUT-03 يرخص ג ↔ ج؛ الدال واللام هويتان.",
        "مباشر في الكذب والخداع.",
    ),
    EXPECTED[13]: gap(
        "LAW-GAP", "ملأك",
        "מלאכא وملاك العربية للملك السماوي نفسه، لكن الهمزة الداخلية والبنية لم يوقع مسارهما",
        "لا تسقط الهمزة أو تنقلها بلا تحليل موقع.",
        "المعنى مباشر، والصرف الصوتي معلق.",
    ),
    EXPECTED[14]: positive(
        "رعي", ("الرعي", "رعى"), "NUCLEUS-TRACE",
        "רעא ورعى في إطعام الماشية ورعيها، والنواة ر־ع محفوظة",
        "الراء والعين هويتان؛ اختلاف الرجل الضعيفة الأخيرة يمنع الجذر الكامل.",
        "مباشر في الرعي.",
    ),
    EXPECTED[15]: positive(
        "سلم", ("السلام", "التحية"), "ROOT-TRACE",
        "שלמא والسلام في التحية والسلم",
        "SIB-01 يرخص ש ↔ س؛ اللام والميم هويتان وألف الحالة خارج الجذر.",
        "مباشر في السلام والتحية.",
    ),
    EXPECTED[16]: positive(
        "رحى", ("الرحى",), "NUCLEUS-TRACE",
        "רחיא والرحى لآلة الطحن نفسها، والنواة ر־ح محفوظة",
        "الراء والحاء هويتان؛ اختلاف الرجل الضعيفة وألف الحالة يمنع الجذر الكامل.",
        "مباشر في الرحى.",
    ),
    EXPECTED[17]: gap(
        "OPEN-CANDIDATE", "يدع",
        "ידע للعلم، والمرشحات الآلية لا تسمي علم العربية بهذا الجذر",
        "لا يقلب مسار الواو المشروط معنى المعرفة إلى حكم.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[18]: positive(
        "يمن", ("اليمين",), "ROOT-TRACE",
        "ימינא واليمين للجهة نفسها",
        "الياء والميم والنون هويات؛ ألف الحالة خارج الجذر.",
        "مباشر في جهة اليمين.",
    ),
    EXPECTED[19]: positive(
        "حيو", ("الحياة", "حي"), "ROOT-TRACE",
        "חיא وحيي في الحياة",
        "الحاء والياءان من بنية الحياة السامية؛ ألف الحالة خارج الجذر.",
        "مباشر في الحياة.",
    ),
    EXPECTED[20]: positive(
        "نبح", ("نبح", "النباح"), "ROOT-TRACE",
        "נבח ونبح لصوت الكلب نفسه",
        "النون والباء والحاء هويات؛ لا صف إبدال لازم.",
        "مباشر في النباح.",
    ),
    EXPECTED[21]: gap(
        "LAW-GAP", "أذن",
        "אדנא والأذن من *ʔuḏn-، لكن DENT-04 لا يسمي الآرامية في نطاقه",
        "لا يمد صف عبري أكدي إلى الآرامية بلا توقيع.",
        "مباشر في الأذن، والمسار الصوتي معلق.",
    ),
    EXPECTED[22]: positive(
        "سأل", ("سأل", "السؤال"), "ROOT-TRACE",
        "שאל وسأل في الطلب والاستفهام",
        "SIB-01 يرخص ש ↔ س؛ الهمزة واللام هويتان.",
        "مباشر في السؤال.",
    ),
    EXPECTED[23]: positive(
        "دم", ("الدم",), "ROOT-TRACE",
        "דמא ودم للمادة نفسها",
        "الدال والميم هويتان؛ ألف الحالة خارج الجذر.",
        "مباشر في الدم.",
    ),
    EXPECTED[24]: gap(
        "LAW-GAP", "خمر",
        "חמירא للخمير، وخمر العربية للتخمر، لكن GUT-05 لا يسمي الآرامية",
        "لا يمد صف خ ↔ ح العبري إلى الآرامية بلا توقيع.",
        "المعنى مباشر، والمسار الصوتي معلق.",
    ),
    EXPECTED[25]: gap(
        "MORPHOLOGY-GAP", "أنس",
        "אנשא للإنسان، وأنس العربية قريب، لكن النون الثانية وبنية إنسان تحتاجان تحليلًا",
        "لا تسقط الصامت أو تورث المتجانس.",
        "المعنى مباشر، والبنية معلقة.",
    ),
    EXPECTED[26]: gap(
        "MORPHOLOGY-GAP", "أمن",
        "הימן للإيمان، وأمن العربية للثقة، لكن الهاء السابقة وبنية الفعل تحتاجان تحليلًا منشورًا",
        "لا تنزع الهاء لمجرد قرب المعنى.",
        "المعنى مباشر، والبنية معلقة.",
    ),
    EXPECTED[27]: gap(
        "SOURCE-GAP", "نبأ",
        "נביא والنبي للوظيفة نفسها، لكن المروحة لم تثبت معنى النبي في مصدرين تحت الجذر المختار",
        "النون والباء ظاهرتان، والرجل الأخيرة تحتاج تحليلًا.",
        "المعنى مباشر، وعائق المصدر والصرف باق.",
    ),
    EXPECTED[28]: gap(
        "LAW-GAP", "صدق",
        "זדק للبر والصلاح، وصدق العربية للحق، لكن ז أمام ص غير موقع",
        "لا يستعمل SIB-03 الداخلي العربي صفًا آراميًا.",
        "المعنى قريب، والمسار الصوتي معلق.",
    ),
    EXPECTED[29]: positive(
        "أرز", ("الأرز", "الأرزة"), "ROOT-TRACE",
        "ארזא والأرز للشجر نفسه",
        "الهمزة والراء والزاي هويات؛ ألف الحالة خارج الجذر.",
        "مباشر في شجر الأرز.",
    ),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short TOOL-GAP batch 05: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = [
        item
        for item in report["languages"]["aramaic"]["one_member_short"]
        if item["current_state"] == "TOOL-GAP"
    ][:30]
    families_in_queue = [item["family_id"] for item in queue]
    if families_in_queue != EXPECTED:
        raise ValueError(f"TOOL-GAP queue drifted: {families_in_queue}")
    population = json.loads(POPULATION.read_text(encoding="utf-8"))
    families = {
        item["family_id"]: item
        for item in population["languages"]["aramaic"]["families"]
    }
    base.SPECS = SPECS
    fan_map = base.fans()
    selected = []
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for item in queue:
            entry_id = item["missing_entry_id"]
            row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,"
                "loan_hint FROM entries WHERE entry_id=?",
                (entry_id,),
            ).fetchone()
            if row is None:
                raise ValueError(f"missing inventory entry: {entry_id}")
            if families[item["family_id"]]["member_count"] < 1:
                raise ValueError(f"empty family: {item['family_id']}")
            selected.append((item["family_id"], dict(row)))
    finally:
        connection.close()
    cards = [
        base.render_card(rank, family_id, entry, SPECS[family_id], fan_map)
        for rank, (family_id, entry) in enumerate(selected, 1)
    ]
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## حملة المقام الآرامية، فك TOOL-GAP 1 إلى 30 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو أول ثلاثين عضوًا حرفيًا من قائمة الأسر الناقصة واحدًا التي كانت حالتها TOOL-GAP. مرت الثلاثون بالمروحة، ولم ينتق موجب ويترك خلافه.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-05:END -->",
            "",
        ]
    )
    base.atomic_write(READING, text.rstrip() + "\n" + block)
    positives = sum(item["kind"] == "positive" for item in SPECS.values())
    closures = sum(item["kind"] == "terminal" for item in SPECS.values())
    held = len(SPECS) - positives - closures
    base.atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المقام الآرامية، فك TOOL-GAP 1 إلى 30",
                "",
                "## النطاق",
                "",
                "قُرئ أول ثلاثين عضوًا من قائمة TOOL-GAP في الأسر الناقصة واحدًا.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positives}.",
                f"- الإغلاقات النهائية: {closures}.",
                "",
                "## الباقي",
                "",
                f"- فجوات بأسبابها الحقيقية بعد المروحة: {held}.",
                "",
                "## الحالة",
                "",
                "- البطاقات محلية للمراجعة المضادة الثالثة.",
                "- لا سجل مركزي ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": len(SPECS),
                "positive_connections": positives,
                "terminal_closures": closures,
                "held": held,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
