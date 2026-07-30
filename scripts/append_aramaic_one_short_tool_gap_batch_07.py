#!/usr/bin/env python3
"""Read the next forty TOOL-GAP members on the Aramaic one-short queue."""
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
AUDIT = ROOT / "05-audits" / "2026-07-28-aramaic-one-short-tool-gap-batch-07-local.md"
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-07 -->"

EXPECTED = [
    "aramaic:family:b82dba34dba0baee82bce5e2",
    "aramaic:family:b9cf059381436c49d1f73bda",
    "aramaic:family:baa04b46dba7e657e4feb972",
    "aramaic:family:baacfb3df06eeae6f43d2174",
    "aramaic:family:bb618c44441b645fa0ac4a02",
    "aramaic:family:bb9efd5331833f8dca617f42",
    "aramaic:family:bbdc93ea29944f4a8e8aa439",
    "aramaic:family:bd07624db39ea5d36a91f779",
    "aramaic:family:bd2b433504bea4d873d37624",
    "aramaic:family:bd2bbe54f70576ce8ace58bd",
    "aramaic:family:bd7f28b8128917381b577693",
    "aramaic:family:be13b91e1c1b9f55d0fc9043",
    "aramaic:family:bfb916880e6448ad9490f6dc",
    "aramaic:family:c099c7bb17ff41be6887995c",
    "aramaic:family:c0a0eeb29319a998e75c3c71",
    "aramaic:family:c14988e5e6252869b9a706b2",
    "aramaic:family:c1d31b5ab0386af50afff707",
    "aramaic:family:c1e1c46e9ad17df1460b69fa",
    "aramaic:family:c2303c6bc4213ab219a33d0c",
    "aramaic:family:c24620b64a1438e593c8ae69",
    "aramaic:family:c26709f7f496e0c16955d192",
    "aramaic:family:c26bb7b03530c1da2b5076af",
    "aramaic:family:c30a1df320d1fb272e53b880",
    "aramaic:family:c34d1618da2a363de51f8e59",
    "aramaic:family:c371d23e54d96f280b36d9c0",
    "aramaic:family:c38ac408831893547b34bd4f",
    "aramaic:family:c50fa4e5811644cc7b255ee4",
    "aramaic:family:c60ff26a379045eb64810e2d",
    "aramaic:family:c82ad0c26a0c33f12aae875d",
    "aramaic:family:c88fc1e6e4aef3e8e33de933",
    "aramaic:family:c8c2c6dffc7f8cc0b4493107",
    "aramaic:family:c8e7ab66a65bf1abf977d3e5",
    "aramaic:family:ca334c6273365d0619828182",
    "aramaic:family:ca759ecd052938e14bf057bf",
    "aramaic:family:ca9b546fd81650ecdab2fa0e",
    "aramaic:family:ca9d3402f6e3499a44474599",
    "aramaic:family:cc471f4d8558c3596da7920a",
    "aramaic:family:cc9c4dc88aa70f614f7c4591",
    "aramaic:family:cd103ace492bdd8a477c7970",
    "aramaic:family:ce64b5b0eb71c98da698b177",
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
    EXPECTED[0]: gap("MORPHOLOGY-GAP", "أمم", "אמא للأم من *ʔimm-، لكن رد الصورة الثنائية إلى جذر أمم يحتاج قانون صرف موقعًا.", "الميم ظاهرة، ولا يضاعف الصامت بالتخمين.", "المعنى مباشر، وهوية الجذر معلقة."),
    EXPECTED[1]: gap("LAW-GAP", "تخم", "תחם للحد، وتخم العربية للحد نفسه، لكن ח ↔ خ غير موقع للآرامية.", "لا يمد صف فرع آخر إلى هذا العضو.", "المعنى مباشر، والمسار الصوتي معلق."),
    EXPECTED[2]: positive("كتب", ("الكتابة", "الكتاب"), "ROOT-TRACE", "כתבתא والكتابة من الجذر نفسه", "الكاف والتاء والباء هويات؛ תא لاحقة اسم.", "مباشر في الكتابة والخط."),
    EXPECTED[3]: gap("LAW-GAP", "قسط", "קושטא للحقيقة من جذر الاستقامة، لكن שط لا يملك تحليلًا موقعًا يرده إلى سط العربية.", "لا يكفي قرب الاستقامة والعدل لاختراع صف.", "المعنى قريب والمسار معلق."),
    EXPECTED[4]: gap("OPEN-CANDIDATE", "دمو", "דמיא للسعر والقيمة، ولم تعط المروحة معنى الثمن تحت الجذر المرشح.", "الصوامت وحدها لا تكفي.", "لا جسر دلالي مباشر."),
    EXPECTED[5]: positive("زني", ("الزنا",), "ROOT-TRACE", "זנא والزنا للفعل نفسه", "الزاي والنون هويتان؛ اختلاف الرجل الضعيفة لا يحجب الجذر السامي المنشور.", "مباشر في الزنا."),
    EXPECTED[6]: gap("OPEN-CANDIDATE", "دلق", "דלקא للنار، ودلق العربية للصب والاندفاع، ولم تسم المروحة اللهب.", "التطابق الصامت لا يحكم مع افتراق المعنى.", "لا جسر مباشر إلى النار."),
    EXPECTED[7]: gap("SOURCE-GAP", "ندن", "נדוניא للمهر، ولم تستوف المروحة مصدرين عربيين قديمين لمعنى المهر تحت هذا الجذر.", "لا يصنع غياب المصدر سالبًا.", "المعنى معلوم في الفرع والمقابل العربي غير موثق."),
    EXPECTED[8]: positive("جنن", ("الجنة", "البستان"), "ROOT-TRACE", "גינתא والجنة للبستان نفسه", "GUT-03 يرخص ג ↔ ج؛ النونان محفوظتان وתא لاحقة اسم.", "مباشر في البستان."),
    EXPECTED[9]: terminal("INTRA-HOUSE-TRANSFER", "جهنم", "المصدر يسمي العبرية גיהנום مانحًا مباشرًا.", "انتقال داخل البيت، فلا يعد شاهد فرع مستقل."),
    EXPECTED[10]: gap("LAW-GAP", "نقش", "נקש للطرق، ونقش العربية للحفر، ولا صف موقع ولا معنى مباشر يكملان الرجلين.", "لا يستبدل المرشح الآلي بمرشح أجمل.", "الطرق والحفر قد يتجاوران ولا يتطابقان."),
    EXPECTED[11]: gap("OPEN-CANDIDATE", "نكت", "נכת للعض واللسع، ونكت العربية للوخز، لكن المروحة لم تسم العض في مصدرين.", "التقارب الحدثي لا يكفي وحده.", "خطوة محتملة من الوخز إلى اللسع، غير محكمة."),
    EXPECTED[12]: gap("OPEN-CANDIDATE", "قبع", "קבע للتثبيت، وقبع العربية لا تسمي التثبيت في المروحة.", "التطابق الصامت لا يكفي.", "لا جسر دلالي مباشر."),
    EXPECTED[13]: terminal("FUNCTION-WORD", "أو", "العضو صوت نداء وتأوه لا مادة معجمية أصلية في مقام الأسر.", "يعزل في جرد الأدوات مع بقاء وصفه."),
    EXPECTED[14]: positive("سلط", ("السلطان",), "ROOT-TRACE", "שולטנא والسلطان للقوة والسلطة", "SIB-01 يرخص ש ↔ س؛ اللام والطاء هويتان واللاحقة خارج الجذر.", "مباشر في الحكم والسلطان."),
    EXPECTED[15]: gap("OPEN-CANDIDATE", "عدو", "עדה للجماعة، ولم تسم المروحة اجتماع الناس تحت الجذر المرشح.", "المعنى لا يستخرج من التشابه.", "لا جسر مباشر."),
    EXPECTED[16]: gap("MORPHOLOGY-GAP", "نبأ", "נבא للتنبؤ ونبأ العربية للإخبار، لكن اشتقاق وظيفة النبوة من الجذر يحتاج تحليلًا موقعًا.", "النون والباء والهمزة ظاهرة، والصرف هو العائق.", "المعنى قريب في الإخبار بالغيب."),
    EXPECTED[17]: gap("MORPHOLOGY-GAP", "دين", "מדינתא للإقليم من جذر الحكم، ومدينة العربية مطابقة في الصورة والمعنى، لكن الميم واللاحقة تحتاجان قانون اشتقاق.", "لا تنزع الميم واللاحقة بالتخمين.", "المعنى مباشر، والبنية معلقة."),
    EXPECTED[18]: positive("رحم", ("الرحمة",), "ROOT-TRACE", "רחמנותא والرحمة من الجذر نفسه", "الراء والحاء والميم هويات؛ اللاحقة الآرامية خارج الجذر.", "مباشر في الرحمة."),
    EXPECTED[19]: positive("وهب", ("الهبة", "وهب"), "ROOT-TRACE", "מוהבתא والهبة من جذر وهب نفسه", "الميم واللاحقة صرف اسمي، والواو والهاء والباء محفوظة.", "مباشر في الهدية والهبة."),
    EXPECTED[20]: gap("OPEN-CANDIDATE", "عرفل", "ערפלא للضباب، ولم تسم المروحة الضباب في الجذر المرشح.", "لا يحكم التقارب الشكلي.", "لا جسر دلالي مباشر."),
    EXPECTED[21]: gap("OPEN-CANDIDATE", "ترس", "תרסי للإطعام، ولم تسم المروحة التغذية تحت ترس في مصدرين.", "الصوامت لا تكفي.", "لا جسر مباشر."),
    EXPECTED[22]: gap("OPEN-CANDIDATE", "ثرد", "תרודא للملعقة، وثرد العربية للطعام المفتوت، ولا يثبت أحدهما الآخر.", "لا يكفي تقارب أداة الطعام والطعام.", "المدار بعيد وغير محكم."),
    EXPECTED[23]: gap("SOURCE-GAP", "أشر", "אשרנא لبناء أو كسوة جدار ومعناه في المصدر نفسه مشكوك فيه.", "اضطراب معنى الفرع يمنع الحكم.", "لا جسر قبل تثبيت المعنى."),
    EXPECTED[24]: gap("LAW-GAP", "شفه", "סיפתא للشفة من *śapat-، لكن انعكاسات الصفير والتاء والهاء لا يجمعها صف موقع لهذه البطاقة.", "لا تصنع المقارنة الأم قانونًا تنفيذيًا.", "المعنى مباشر، والصوت معلق."),
    EXPECTED[25]: gap("MORPHOLOGY-GAP", "ربو", "רבותא للعدد عشرة آلاف، وربو العربية للزيادة، لكن بناء اسم العدد غير موقع.", "لا تورث الجذر معنى العدد بالتخمين.", "الكثرة قريبة والبنية معلقة."),
    EXPECTED[26]: positive("ربب", ("عظم",), "ROOT-ECHO", "רבה للكبير ورب العربية يسمي العظم والزيادة", "الراء والباء محفوظتان؛ تضعيف الباء من بنية الجذر العربي.", "خطوة واحدة من العظم إلى الكبر."),
    EXPECTED[27]: positive("سفر", ("أشرق", "حسن"), "ROOT-ECHO", "שפר للجمال وسفر الوجه في العربية لإشراقه وحسنه", "SIB-01 يرخص ש ↔ س؛ الفاء والراء هويتان.", "إشراق الوجه وحسنه مدار واحد."),
    EXPECTED[28]: gap("LAW-GAP", "ردي", "רדיא للجريان، ورضو هو المرشح الآلي المشروط، ولا قانون موقع يثبت المقابل الدلالي.", "لا يبدل الصامت طلبًا للمعنى.", "المعنى العربي غير محكم."),
    EXPECTED[29]: gap("SOURCE-GAP", "حوح", "חוחא للشوك، ولم تستوف المروحة شاهدين لمعنى الشوك تحت الجذر المرشح.", "الغياب التوثيقي ليس سالبًا.", "معنى الفرع ثابت والمقابل معلق."),
    EXPECTED[30]: gap("SOURCE-GAP", "أيل", "אילתא لأنثى الأيل، لكن مروحة أيل لم تسم الحيوان في مصدرين مستقلين مختارين.", "هوية الصورة لا تعوض شرط المصدرين.", "المعنى مباشر وعائقه توثيقي."),
    EXPECTED[31]: positive("سبع", ("الأسبوع", "سبعة"), "ROOT-TRACE", "שבועא والأسبوع مبنيان على السبعة", "SIB-01 يرخص ש ↔ س؛ الباء والعين هويتان وألف الحالة خارج الجذر.", "مباشر في أسبوع الأيام السبعة."),
    EXPECTED[32]: gap("SOURCE-GAP", "دردس", "דרדס للحذاء ومعناه وأصله موصوفان بعدم اليقين في المصدر.", "لا حكم مع اضطراب الأصل.", "لا جسر موثوق."),
    EXPECTED[33]: positive("ثني", ("ثنى", "كرر"), "NUCLEUS-TRACE", "תנא للتكرار وثنى العربية للتكرير والرد", "DENT-01 يرخص ת ↔ ث؛ النون محفوظة واختلاف الرجل الضعيفة يمنع الجذر الكامل.", "مباشر في التكرار."),
    EXPECTED[34]: positive("كأب", ("الكآبة", "الحزن"), "ROOT-ECHO", "כאבא للألم وكأب العربية للحزن والكآبة", "الكاف والهمزة والباء هويات؛ ألف الحالة خارج الجذر.", "خطوة واحدة من الألم إلى الكآبة."),
    EXPECTED[35]: positive("علو", ("علا", "ارتفع"), "NUCLEUS-TRACE", "עלא للصعود وعلا العربية للارتفاع", "العين واللام هويتان؛ اختلاف الرجل الضعيفة يمنع الجذر الكامل.", "مباشر في العلو والصعود."),
    EXPECTED[36]: gap("MORPHOLOGY-GAP", "حور", "חיורא للأبيض وحور العربية للبياض، لكن الياء الداخلية وبنية الصفة الآرامية تحتاجان تحليلًا موقعًا.", "لا تسقط الياء لمجرد وضوح المعنى.", "المعنى مباشر والبنية معلقة."),
    EXPECTED[37]: terminal("LOANWORD", "ملففن", "المصدر يسمي اليونانية μηλοπέπων مانحًا مباشرًا.", "قرض يوناني خارجي معزول."),
    EXPECTED[38]: gap("OPEN-CANDIDATE", "رحم", "רחמותא للصداقة، ومروحة رحم تسمي الرحمة لا الصداقة نصًا في المصدرين.", "لا يورث عضو الرحمة حكم عضو الصداقة.", "التقارب الوجداني لا يكفي."),
    EXPECTED[39]: gap("LAW-GAP", "حفي", "יחף للحفاء وحفي العربية للحفاء، لكن الياء الأولى الآرامية والفاء الأخيرة لا يفسرهما صف موقع.", "لا ينقل الحرف الضعيف أو يرخص פ ↔ ف بلا قانون.", "المعنى مباشر، والمسار الصوتي معلق."),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short TOOL-GAP batch 07: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    queue = [
        item
        for item in report["languages"]["aramaic"]["one_member_short"]
        if item["current_state"] == "TOOL-GAP"
    ][:40]
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
            f"## حملة المقام الآرامية، فك TOOL-GAP 30 إلى 69 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو الأربعون عضوًا التالية حرفيًا من قائمة الأسر الناقصة واحدًا التي كانت حالتها TOOL-GAP. مرت الأربعون بالمروحة، ولم ينتق موجب ويترك خلافه.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-TOOL-GAP-BATCH-07:END -->",
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
                "# حملة المقام الآرامية، فك TOOL-GAP 30 إلى 69",
                "",
                "## النطاق",
                "",
                "قُرئ الأربعون عضوًا التالية من قائمة TOOL-GAP في الأسر الناقصة واحدًا.",
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
