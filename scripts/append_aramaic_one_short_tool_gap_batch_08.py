#!/usr/bin/env python3
"""Read the next thirty TOOL-GAP members on the Aramaic one-short queue."""
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
AUDIT = ROOT / "05-audits" / "2026-07-28-aramaic-one-short-tool-gap-batch-08-local.md"
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-08 -->"

EXPECTED = [
    "aramaic:family:ce820201d5234248399492f3",
    "aramaic:family:cecfd30a801e7f8d2b0ddc77",
    "aramaic:family:ced0ab0253d0435c181bdc83",
    "aramaic:family:cf554ccec05d0049443babe2",
    "aramaic:family:cfab578a4c7681e9813f2aa3",
    "aramaic:family:cfdf78016e6cd43fe9d4de87",
    "aramaic:family:d0e5ea44076c36fa4dba82e9",
    "aramaic:family:d188d1996384158743eb46a9",
    "aramaic:family:d1d63a9653e10f015e08f89c",
    "aramaic:family:d205735c10040334e9580b01",
    "aramaic:family:d22de5784bc78b8b01d87a4e",
    "aramaic:family:d27dbc7837a52c835290d6f2",
    "aramaic:family:d285cddab33684b43e76e077",
    "aramaic:family:d2bb9dcc7fcc0fb7a5109125",
    "aramaic:family:d2e1e5578802d111bc0af9aa",
    "aramaic:family:d3061fc0537c97476eb8b3a9",
    "aramaic:family:d31fc5d640e3275295ffc550",
    "aramaic:family:d38aa6b47b329bf8fcb2844e",
    "aramaic:family:d3f7266d8a9178d653acd2bb",
    "aramaic:family:d5152d749a6cf1175cc050ab",
    "aramaic:family:d5e174e293c7a7dba45d9459",
    "aramaic:family:d657b39008758bb583e2cb72",
    "aramaic:family:d71d5564feb3059cd66effdf",
    "aramaic:family:d797669eab331919768a1a0b",
    "aramaic:family:d7ba3b0e0b2b42e6c37704c7",
    "aramaic:family:d87e9a8853732d77bd47979c",
    "aramaic:family:d883939e41ad34136c314aa0",
    "aramaic:family:dad2135336dfed84a9c90753",
    "aramaic:family:dba5f39a52b18d0038037e3c",
    "aramaic:family:dbe7fcc2a641fa3d40e8e556",
]


def load_base():
    specification = importlib.util.spec_from_file_location("aramaic_source_base", BASE_PATH)
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Aramaic source base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


base = load_base()
gap = base.gap
positive = base.positive
terminal = base.terminal

SPECS = {
    EXPECTED[0]: gap("SOURCE-GAP", "صأى", "צאתא للقذر، ولم تستوف المروحة معنى القذر تحت المقابل المرشح.", "لا يصنع التشابه سالبًا أو موجبًا.", "معنى الفرع ثابت والمقابل معلق."),
    EXPECTED[1]: gap("OPEN-CANDIDATE", "حنك", "חנוכתא للتدشين، وحنك العربية للتحنيك والحنك، ولا تسم المروحة الافتتاح.", "الصوامت لا تكفي.", "لا جسر مباشر."),
    EXPECTED[2]: terminal("FUNCTION-WORD", "بعد", "العضو ظرف ربط بمعنى بعد ذلك.", "يعزل في جرد الأدوات والظروف النحوية."),
    EXPECTED[3]: gap("SOURCE-GAP", "سمق", "סומק للأحمر، ولم تسم مروحة سمق الحمرة في مصدرين مستقلين.", "غياب المعنى في المروحة ليس سالبًا.", "المعنى العربي غير موثق."),
    EXPECTED[4]: gap("OPEN-CANDIDATE", "بوأ", "ביא للتعزية، وبوأ العربية للإنزال والتهيئة، ولا جسر مباشر.", "لا يكفي التشابه.", "المعنى مفترق."),
    EXPECTED[5]: gap("OPEN-CANDIDATE", "تلي", "תלא للتعليق، وتلا العربية للاتباع والقراءة.", "اختلاف الرجل الضعيفة لا يعالج افتراق المعنى.", "لا جسر مباشر."),
    EXPECTED[6]: positive("تين", ("التين", "تين"), "NUCLEUS-TRACE", "תאנתא والتين للثمر نفسه من *tiʔin-", "التاء والنون محفوظتان؛ اختلاف الرجل الضعيفة يمنع الجذر الكامل وתא لاحقة اسم.", "مباشر في التين."),
    EXPECTED[7]: positive("سلط", ("السلطان",), "ROOT-TRACE", "שלט وسلط في الحكم والقوة", "SIB-01 يرخص ש ↔ س؛ اللام والطاء هويتان.", "مباشر في السلطان."),
    EXPECTED[8]: positive("حبس", ("الحبس",), "ROOT-TRACE", "חבש وحبس في السجن والمنع", "الحاء والباء هويتان وSIB-01 يرخص ש ↔ س.", "مباشر في الحبس."),
    EXPECTED[9]: gap("OPEN-CANDIDATE", "دحل", "דחלתא للخوف، ودحل العربية لا تسمي الخوف في المروحة.", "الصورة لا تكفي.", "لا جسر مباشر."),
    EXPECTED[10]: gap("LAW-GAP", "وقر", "איקרא للشرف، ووقر العربية للكرامة، لكن GLD-01 يحتاج ضابطًا خارجيًا لهذه البطاقة.", "لا يقلب الواو ياء بلا الشرط.", "المعنى مباشر والمسار معلق."),
    EXPECTED[11]: gap("OPEN-CANDIDATE", "مشل", "משליא للشوكة، ولم تسم المروحة أداة الأكل تحت الجذر.", "لا يكفي تقارب الصورة.", "لا جسر مباشر."),
    EXPECTED[12]: terminal("LOANWORD", "نركس", "المصدر وحقل اللفظ يسميان النرجس اليوناني مانحًا خارجيًا.", "قرض يوناني معزول."),
    EXPECTED[13]: positive("لبن", ("اللبان",), "ROOT-TRACE", "לבונתא واللبان للبخور نفسه", "اللام والباء والنون هويات؛ الواو واللاحقة من بنية الاسم.", "مباشر في اللبان والبخور."),
    EXPECTED[14]: gap("MORPHOLOGY-GAP", "بؤبؤ", "בבתא لبؤبؤ العين، لكن تكرار المقاطع والهمزتين في العربية لا يفسره تحليل موقع.", "لا تضاعف البنية بالتخمين.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[15]: gap("MORPHOLOGY-GAP", "صبو", "צבינא للرغبة، وصبوة العربية للهوى، لكن النون اللاحقة والرجل الضعيفة تحتاجان تحليلًا.", "لا تنزع النون أو تنقل الواو.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[16]: gap("MORPHOLOGY-GAP", "لبأ", "לביה لأنثى الأسد من *labiʾ-، ولبؤة العربية لها، لكن الياء والهمزة والتاء تحتاج تحليلًا.", "لا يعاد بناء الكلمة من المعنى وحده.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[17]: terminal("FORM-OF-ISOLATED", "زمن", "العضو معرّف صراحة بأنه حالة مطلقة لصورة أخرى في المصدر.", "يحفظ رابط الصورة ولا يعد شاهدًا معجميًا مستقلًا."),
    EXPECTED[18]: gap("OPEN-CANDIDATE", "شخب", "מִשְׁכַּב للسرير، وشخب العربية لا تسمي الفراش.", "لا يكفي الهيكل.", "لا جسر مباشر."),
    EXPECTED[19]: gap("LAW-GAP", "أثر", "אתרא للبلد من *ʔaṯar-، وأثر العربية للمكان الباقي، لكن ת ↔ ث يحتاج صفًا موقعًا لهذا العضو.", "المعنى لا يرخص الصامت.", "المكان والأثر قريبان والمسار معلق."),
    EXPECTED[20]: positive("معي", ("المعى",), "ROOT-TRACE", "מעיא والمعى للأمعاء", "الميم والعين والياء هويات؛ ألف الحالة خارج الجذر.", "مباشر في المِعى."),
    EXPECTED[21]: positive("أكل", ("الأكل", "الطعام"), "ROOT-TRACE", "אוכלא والأكل والطعام من *ʾakal-", "الهمزة والكاف واللام هويات؛ الواو وألف الحالة من صورة الاسم.", "مباشر في الأكل والطعام."),
    EXPECTED[22]: positive("قني", ("القنية",), "ROOT-TRACE", "קנינא والقنية للملك والمال المقتنى", "القاف والنون والياء هويات؛ النون واللاحقة من بناء الاسم.", "مباشر في القنية والملكية."),
    EXPECTED[23]: positive("ليل", ("الليل",), "ROOT-TRACE", "ליליא والليل للزمن نفسه من *layl-", "اللام والياء واللام هويات؛ الياء وألف الحالة صرف الاسم.", "مباشر في الليل."),
    EXPECTED[24]: terminal("OUT-OF-SCOPE", "أرم", "ארמיותא اسم مجتمع مشتق من اسم الآراميين، لا مادة أصلية مستقلة.", "يعزل اشتقاق النسبة من المقام الأصلي ولا يرث المشتق حكم اسم القوم."),
    EXPECTED[25]: terminal("LOANWORD", "أرغن", "المصدر يسمي اليونانية ὄργανον مانحًا مباشرًا.", "قرض يوناني خارجي معزول."),
    EXPECTED[26]: gap("SOURCE-GAP", "سكين", "סכינא للسكين، لكن المروحة لا تملك جذرًا عربيًا مستقلًا صالحًا للصورة الرباعية.", "هوية الكلمة لا تعوض شرط الجذر والمصدر.", "المعنى مباشر وعائقه توثيقي صرفي."),
    EXPECTED[27]: gap("OPEN-CANDIDATE", "ريق", "ריקא للفراغ، وريق العربية للعاب، ولا تسم المروحة الفراغ.", "المصدر يقارن العبرية والأكدية لا العربية.", "لا جسر عربي مباشر."),
    EXPECTED[28]: gap("MORPHOLOGY-GAP", "حمم", "חומא للحرارة، وحمم العربية للنار والحر، لكن الواو والتضعيف يحتاجان تحليلًا.", "لا يرد الصامت الضعيف أو يضاعف الميم بالتخمين.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[29]: positive("دمع", ("الدمع",), "ROOT-TRACE", "דמעתא والدمع للقطرة نفسها", "الدال والميم والعين هويات؛ תא لاحقة اسم.", "مباشر في الدمع."),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short TOOL-GAP batch 08: already present")
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
    families = {item["family_id"]: item for item in population["languages"]["aramaic"]["families"]}
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
            f"## حملة المقام الآرامية، فك TOOL-GAP 70 إلى 99 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو الثلاثون عضوًا التالية حرفيًا من قائمة TOOL-GAP. مرت كلها بالمروحة بلا انتقاء.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-08:END -->",
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
                "# حملة المقام الآرامية، فك TOOL-GAP 70 إلى 99",
                "",
                "## النطاق",
                "",
                "قُرئ الثلاثون عضوًا التالية من قائمة TOOL-GAP في الأسر الناقصة واحدًا.",
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
