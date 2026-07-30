#!/usr/bin/env python3
"""Read the next twenty-nine TOOL-GAP members on the Aramaic one-short queue."""
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
AUDIT = ROOT / "05-audits" / "2026-07-28-aramaic-one-short-tool-gap-batch-06-local.md"
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-06 -->"

EXPECTED = [
    "aramaic:family:a75eeecd1c660814cdb75588",
    "aramaic:family:a79be5c427135ce889ad5c6e",
    "aramaic:family:a8d79a6ab5a819b41f5b45f0",
    "aramaic:family:aa80ee229b914a10ad2dc29f",
    "aramaic:family:abe4c78fc8475349f0017946",
    "aramaic:family:accadf3cc926e7c342ca060e",
    "aramaic:family:aceb6240c2605e3e0d8e13e5",
    "aramaic:family:ad9c828f9abb084328393f46",
    "aramaic:family:aea09afd44226ea3a5a75f2e",
    "aramaic:family:aee3409c1f6df8afda68e560",
    "aramaic:family:af123ec5017bd37d5c298bae",
    "aramaic:family:af19eb025e80df57ee8a66b9",
    "aramaic:family:af85bba01db7328d3e0f0fb0",
    "aramaic:family:b0101cfd66539f60c408cbb3",
    "aramaic:family:b1219089e0266d12fe608062",
    "aramaic:family:b199a1c6119e6994c2d54574",
    "aramaic:family:b306fa16fcdc192cb3b555b5",
    "aramaic:family:b31d1311749468d411d53d9a",
    "aramaic:family:b3f863ed1c74baaeeb7db84e",
    "aramaic:family:b409c7615688b89102e43031",
    "aramaic:family:b41da60cac09c66d33c96184",
    "aramaic:family:b51c44c0161900a0e16eac5b",
    "aramaic:family:b5581906d4f6609136466f1c",
    "aramaic:family:b5633ece4686a52a091aea46",
    "aramaic:family:b5c18dc37a14b667dd88200f",
    "aramaic:family:b5e084018c574964cdca6e8e",
    "aramaic:family:b69a8259a11b30049187a4e0",
    "aramaic:family:b6c88059e6b9bce329d74abb",
    "aramaic:family:b761534f556f717885b8ffcd",
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
    EXPECTED[0]: gap("LAW-GAP", "ضحك", "גחך للضحك، لكن ג ↔ ض غير موقع في الشبكة.", "لا ينشأ صف من وضوح المعنى.", "المعنى مباشر، والمسار الصوتي معلق."),
    EXPECTED[1]: gap("MORPHOLOGY-GAP", "جدل", "מגדלא للبرج، والمجدل معروف في العربية، لكن الميم وبنية الاسم لا يملكهما تحليل صرف موقع.", "GUT-03 يفتح ג ↔ ج ولا يحذف الميم.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[2]: gap("SOURCE-GAP", "ترنجل", "תרנגלא للديك، ولم تستوف المروحة أصلًا عربيًا قديمًا مستقلًا تحت هذه الصورة.", "غياب المصدر لا يصنع سالبًا.", "معنى الفرع ثابت والمقابل معلق."),
    EXPECTED[3]: positive("صلي", ("صلى",), "NUCLEUS-TRACE", "צלא وصلى في الصلاة", "الصاد واللام هويتان؛ اختلاف الرجل الضعيفة يمنع الجذر الكامل.", "مباشر في الصلاة."),
    EXPECTED[4]: positive("صور", ("الصورة", "صورة"), "ROOT-TRACE", "צורתא والصورة للشكل والهيئة", "الصاد والواو والراء هويات؛ תא لاحقة اسم.", "مباشر في الصورة والشكل."),
    EXPECTED[5]: gap("MORPHOLOGY-GAP", "بنت", "ברתא والبنت من قرابة منشورة، لكن ر الآرامية أمام ن العربية تحتاج تحليلًا صرفيًا تاريخيًا.", "لا يبدل الصامت بالتخمين.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[6]: positive("أمر", ("الأمير",), "ROOT-TRACE", "אמירא والأمير للقائد", "الهمزة والميم والراء هويات؛ ألف الحالة خارج الجذر.", "مباشر في الأمير والقائد."),
    EXPECTED[7]: gap("OPEN-CANDIDATE", "علو", "מעלתא للمدخل، وعلو العربية لا يسمي الدخول في المروحة.", "الصوامت الجزئية لا تكفي.", "لا جسر دلالي مباشر."),
    EXPECTED[8]: gap("LAW-GAP", "نخر", "נחירא للمنخر، ونخر العربية يسمي الأنف، لكن ח ↔ خ خارج النطاق الموقع للآرامية.", "لا يمد صف فرع آخر.", "المعنى مباشر والمسار معلق."),
    EXPECTED[9]: gap("OPEN-CANDIDATE", "أبل", "אביל للنائح، وأبل العربية لا تسمي الحداد في المروحة.", "التطابق الشكلي لا يكفي.", "لا جسر دلالي مباشر."),
    EXPECTED[10]: gap("LAW-GAP", "خطأ", "חטא والخطأ والخطيئة في معنى الذنب، لكن ח ↔ خ غير موقع للآرامية.", "الطاء والهمزة ظاهرتان ولا تعوضان الصف الناقص.", "المعنى مباشر والصوت معلق."),
    EXPECTED[11]: gap("OPEN-CANDIDATE", "مني", "מנא للعد، ومنى العربية للتقدير لا تسمي العد نصًا في المصدرين.", "لا يوسع المدار بلا سند.", "التقارب غير محكم."),
    EXPECTED[12]: gap("MORPHOLOGY-GAP", "ملل", "ממללא للكلام، وملل العربية يسمي الإملال والقول، لكن الميم السابقة وبناء الاسم يحتاجان تحليلًا.", "لا تنزع الميم بالتخمين.", "المعنى قريب والبنية معلقة."),
    EXPECTED[13]: gap("OPEN-CANDIDATE", "أمر", "אמורא للمتكلم، وأمر العربية للأمر والإمارة لا للمتكلم.", "هوية الجذر لا تورث المعنى.", "لا جسر دلالي مباشر."),
    EXPECTED[14]: gap("LAW-GAP", "مرو", "מריא للسادة، والمرشح يتطلب GLD-01 بشرطه الخارجي غير المتحقق لهذه البطاقة.", "لا يقلب الياء واوًا بلا الضابط المطلوب.", "المعنى العربي غير محكم."),
    EXPECTED[15]: gap("OPEN-CANDIDATE", "أصر", "אוצרא للخزانة، وأصر العربية لا تسمي الخزانة في المروحة.", "لا تكفي الصورة.", "لا جسر مباشر."),
    EXPECTED[16]: gap("SOURCE-GAP", "دد", "דדתא للعمة، ولم تستوف المروحة شاهدين عربيين قديمين لمعنى القرابة.", "الغياب ليس سالبًا.", "معنى الفرع ثابت."),
    EXPECTED[17]: gap("LAW-GAP", "خطأ", "חטיתא للخطيئة، لكن ח ↔ خ غير موقع للآرامية.", "لا يكرر الحكم من عضو قريب.", "المعنى مباشر والصوت معلق."),
    EXPECTED[18]: positive("سفن", ("السفينة", "سفينة"), "ROOT-TRACE", "ספינתא والسفينة للمركب نفسه، ولا يسمي المصدر مانحًا خارجيًا", "السين والفاء والنون هويات؛ תא لاحقة اسم.", "مباشر في السفينة؛ وculture word بلا مانح خارجي ليست قرضًا بحكم قاعدة عمق القرض."),
    EXPECTED[19]: gap("LAW-GAP", "سلب", "שלף للتجريد والنزع، وسلب العربية للأخذ، لكن פ ↔ ب يحتاج صفًا موقعًا.", "SIB-01 يرخص ש ↔ س ولا يرخص بقية الرجل.", "المعنى قريب والصوت معلق."),
    EXPECTED[20]: gap("OPEN-CANDIDATE", "نشق", "נושקתא للقبلة، ونشق العربية للشم والاستنشاق، ولا تسم المروحة القبلة.", "تقارب الفم والأنف لا يكفي.", "لا جسر مباشر."),
    EXPECTED[21]: gap("MORPHOLOGY-GAP", "سنديان", "סדינא للبلوط، وسنديان العربية له، لكن النون الزائدة وهوية البنية غير محللتين.", "لا تضف النون أو تحذفها.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[22]: positive("قدس", ("القدس", "التقديس"), "ROOT-TRACE", "קודשא والقدس في الطهارة والتقديس", "القاف والدال هويتان وSIB-01 يرخص ש ↔ س؛ ألف الحالة خارج الجذر.", "مباشر في القداسة."),
    EXPECTED[23]: positive("دقل", ("الدقل", "النخل"), "ROOT-TRACE", "דקלא والدقل لنوع من النخل", "الدال والقاف واللام هويات؛ ألف الحالة خارج الجذر.", "مباشر في النخل."),
    EXPECTED[24]: terminal("FUNCTION-WORD", "إن", "العضو جواب إثبات بمعنى نعم لا مادة معجمية أصلية في مقام الأسر.", "يعزل في جرد الأدوات."),
    EXPECTED[25]: gap("LAW-GAP", "وقد", "יקדתא للنار المشتعلة، ووقد العربية للاشتعال، لكن GLD-01 يحتاج ضابطه الخارجي لهذه البطاقة.", "لا يقلب الواو ياء بلا شاهد الشرط.", "المعنى مباشر والمسار معلق."),
    EXPECTED[26]: gap("OPEN-CANDIDATE", "زدن", "זדון للرجل العنيف، ولم تسم المروحة العنف تحت الجذر المرشح.", "الصورة لا تكفي.", "لا جسر مباشر."),
    EXPECTED[27]: gap("LAW-GAP", "ثقل", "שקל للأخذ والرفع، وثقل العربية للوزن، لكن مسار ש ↔ ث موسوم scope-gap.", "لا يرقى الصف غير الموقع.", "المعنى قريب والصوت معلق."),
    EXPECTED[28]: gap("MORPHOLOGY-GAP", "صيد", "מְצוּדְתָּא للشبكة، وصيد العربية للصيد، لكن الميم والواو والياء واللاحقة تحتاج تحليلًا منشورًا.", "لا تنزع البنية المركبة.", "المعنى مباشر والبنية معلقة."),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short TOOL-GAP batch 06: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = [
        item
        for item in report["languages"]["aramaic"]["one_member_short"]
        if item["current_state"] == "TOOL-GAP"
    ][:29]
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
            f"## حملة المقام الآرامية، فك TOOL-GAP 1 إلى 29 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو أول تسعة وعشرين عضوًا حرفيًا من قائمة TOOL-GAP بعد إصلاح ربط العائق بالعضو. مرت كلها بالمروحة بلا انتقاء.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-06:END -->",
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
                "# حملة المقام الآرامية، فك TOOL-GAP 1 إلى 29",
                "",
                "## النطاق",
                "",
                "قُرئ أول تسعة وعشرين عضوًا بعد إصلاح ربط العائق الحي بالعضو.",
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
