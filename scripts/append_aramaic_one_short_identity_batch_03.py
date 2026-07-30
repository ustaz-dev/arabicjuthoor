#!/usr/bin/env python3
"""Read identity-candidate Aramaic families 51 through 100."""
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
BASE_PATH = ROOT / "scripts" / "append_aramaic_one_short_identity_batch_02.py"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-aramaic-one-short-identity-batch-03-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- ARAMAIC-ONE-SHORT-IDENTITY-BATCH-03 -->"


EXPECTED = [
    "aramaic:family:59ed49fca21432ba59ce7d21",
    "aramaic:family:5e7543ce49881d3755b5c904",
    "aramaic:family:5f0c91c55d50a7e369642678",
    "aramaic:family:5f902c6474107b2353e1e135",
    "aramaic:family:6102659935e1fde3210986ba",
    "aramaic:family:6125bf2b58fe0c57e250d39c",
    "aramaic:family:6371de6e30c7c3c3c3788f22",
    "aramaic:family:642cbe0f70dc3dd6f8120746",
    "aramaic:family:647628b99d2ceadd05c66bfb",
    "aramaic:family:64d062ebffd7a09bb04b8e41",
    "aramaic:family:6a91e60127b84edf40a86dea",
    "aramaic:family:72182310bbb0c2e3272a237e",
    "aramaic:family:749789e9d6ecbc3105172458",
    "aramaic:family:7515ef0e7a146593cdcc7022",
    "aramaic:family:75fffbd5ceb76d569d27f8a0",
    "aramaic:family:762ab2eb31b4bba1bb3cf2ff",
    "aramaic:family:76ffbd6a734fba25d641842b",
    "aramaic:family:7bb52f744c13616aeebd89e2",
    "aramaic:family:7c1e5940ab94d9e81b36bbd9",
    "aramaic:family:7f2e27e81bbf419cad765d3f",
    "aramaic:family:83f661de398bdbbe67c15d7c",
    "aramaic:family:888bf726eeab18923fb7efd7",
    "aramaic:family:8d833e6d1df4a5abd1cbf798",
    "aramaic:family:8eafac9e777187b033b85fe4",
    "aramaic:family:8f4fc0af99aa51a6aa2a644a",
    "aramaic:family:909fea16c096925a05397927",
    "aramaic:family:945cea7e359a6a3c1b09dede",
    "aramaic:family:955268673e6b1c2bcca2f7b2",
    "aramaic:family:96db8f3f485bd863a793cada",
    "aramaic:family:97173d8a268247bb9a56a351",
    "aramaic:family:9792cc54f7a561cf89032103",
    "aramaic:family:9ae2eb59ee841c9776f34106",
    "aramaic:family:9e80eb3a90d70043e5fba257",
    "aramaic:family:9fc495b23eeacacad97473f9",
    "aramaic:family:a1f7285789496bc47dfded6c",
    "aramaic:family:a3746429e56db866498af8d3",
    "aramaic:family:a3a3534f2f510abf1c02c059",
    "aramaic:family:a46b3477645faeeb2110cdac",
    "aramaic:family:a78f9a54d0951c59ef5cdcd7",
    "aramaic:family:a7e56f766e0554c878359243",
    "aramaic:family:a981d04b6563d157de90804e",
    "aramaic:family:a9a077be26fea20e99491414",
    "aramaic:family:ab3546d30faa6838593b21b6",
    "aramaic:family:b49aee16989db1400d845ee5",
    "aramaic:family:b6abc6d2e059b90c4a16c79c",
    "aramaic:family:b7ca2103184389978357601a",
    "aramaic:family:b8602d39c7cbb881ef22fbf4",
    "aramaic:family:b932fce2b4e4532eba141367",
    "aramaic:family:bcc7daf26b3ac0fb337f5652",
    "aramaic:family:c0c644fb67d7c0e1c35070f2",
]


def load_base():
    specification = importlib.util.spec_from_file_location(
        "aramaic_identity_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Aramaic identity base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


base = load_base()
open_spec = base.open_spec
gap_spec = base.gap_spec
terminal_spec = base.terminal_spec
positive_spec = base.positive_spec


SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: positive_spec("كتف", ("الكتف",), "ROOT-TRACE", "כתפא وكتف للعضو نفسه", "LAB-07 يرخص פ ↔ ف؛ الكاف والتاء هويتان وألف الحالة خارج الجذر.", "مباشر في الكتف."),
    EXPECTED[1]: positive_spec("فسق", ("خرج", "فسق"), "ROOT-ECHO", "פסק للانقطاع والابتعاد، وفسق للخروج", "LAB-07 يرخص פ ↔ ف؛ السين والقاف هويتان.", "خطوة واحدة: الانقطاع خروج عن الموضع أو الأمر."),
    EXPECTED[2]: open_spec("شرق", "שרק للصفير، وشرق العربية للشروق أو الاختناق."),
    EXPECTED[3]: open_spec("نكف", "נכף للحياء، ونكف العربية للامتناع والاستنكاف."),
    EXPECTED[4]: positive_spec("سفن", ("السفان", "السفينة"), "ROOT-TRACE", "ספנא ربان السفينة، والسفان صاحب السفينة في المعجمين", "LAB-07 يرخص פ ↔ ف؛ السين والنون هويتان وألف الصفة خارج الجذر.", "مباشر في ربان السفينة."),
    EXPECTED[5]: open_spec("صفح", "צפח للمفاجأة، وصفح العربية للعفو أو جانب الشيء."),
    EXPECTED[6]: open_spec("دقق", "דקק للتفحص، ودقق العربية للكسر والسحق؛ اصطلاح التدقيق المتأخر لا يكفي."),
    EXPECTED[7]: open_spec("عند", "ענד للانتهاء والمغادرة، وعند العربية للحضور والقرب."),
    EXPECTED[8]: positive_spec("نسر", ("النسر",), "ROOT-TRACE", "נשרא ونسر للطائر نفسه", "SIB-01 يرخص ש ↔ س؛ النون والراء هويتان وألف الحالة خارج الجذر.", "مباشر في النسر."),
    EXPECTED[9]: open_spec("قوب", "קופא للقرد، وقوب العربية لا تسمي القرد."),
    EXPECTED[10]: open_spec("طعم", "טעם للمرسوم، وطعم العربية للذوق؛ المتجانس الآرامي لا يرث معنى الذوق."),
    EXPECTED[11]: open_spec("بلل", "בלל للتشويش، وبلل العربية للندى والماء."),
    EXPECTED[12]: open_spec("برم", "פרם للشق، وبرم العربية للفتل أو الضجر."),
    EXPECTED[13]: open_spec("جنب", "גנב للسرقة، وجنب العربية للجانب أو الإبعاد."),
    EXPECTED[14]: open_spec("فقد", "פקד للأمر، وفقد العربية للغياب."),
    EXPECTED[15]: open_spec("نكل", "נכלא للمكر، ونكل العربية للعقوبة أو الامتناع."),
    EXPECTED[16]: open_spec("هبب", "הבב للإزهار، وهبب العربية للهبوب."),
    EXPECTED[17]: gap_spec("LAW-GAP", "نفخ", "נפח والنفخ معنى واحد من *napaḫ-، لكن ח أمام خ خارج نطاق GUT-05 النافذ.", "لا يمد صف عبري إلى الآرامية بلا توقيع."),
    EXPECTED[18]: positive_spec("عصر", ("عصر العنب", "عصر"), "ROOT-ECHO", "עצר للدوس، وعصر للضغط والاستخراج", "العين والصاد والراء هويات.", "خطوة واحدة: الدوس ضغط بالقدم."),
    EXPECTED[19]: positive_spec("ثلج", ("الثلج",), "ROOT-TRACE", "תלגא وثلج للمادة نفسها", "DENT-01 يرخص ת ↔ ث وGUT-03 يرخص ג ↔ ج؛ اللام هوية.", "مباشر في الثلج."),
    EXPECTED[20]: positive_spec("نفس", ("النفس", "الروح"), "ROOT-TRACE", "נפשא ونفس للروح والذات", "LAB-07 يرخص פ ↔ ف وSIB-01 يرخص ש ↔ س؛ النون هوية.", "مباشر في النفس والروح."),
    EXPECTED[21]: open_spec("سبت", "סבתא للجدة، وسبت العربية لليوم أو القطع."),
    EXPECTED[22]: open_spec("علل", "עלל للدخول، وعلل العربية للشرب المتكرر أو العلة."),
    EXPECTED[23]: open_spec("صور", "צורא للعنق، وصور العربية لا تسمي العنق في مصدرين مستقلين."),
    EXPECTED[24]: open_spec("رتت", "רתת للارتجاف، ورتت العربية لعقدة اللسان والعجلة في الكلام."),
    EXPECTED[25]: open_spec("كسب", "כספא للفضة، وكسب العربية للتحصيل."),
    EXPECTED[26]: open_spec("حضر", "חדר للتجول، وحضر العربية لنقيض الغياب."),
    EXPECTED[27]: positive_spec("عتل", ("الغليظ", "الشديد"), "ROOT-TRACE", "עטל للصلابة والعناد، وعتل للغليظ الشديد", "العين والتاء واللام هويات في هذا العضو.", "مباشر في الغلظ والشدة."),
    EXPECTED[28]: terminal_spec("FUNCTION-WORD", "صيد", "العضو حرف جر بمعنى مع."),
    EXPECTED[29]: open_spec("قضب", "גדף للتجديف، وقضب العربية للقطع."),
    EXPECTED[30]: open_spec("شرر", "שרר للصحة واليقين، وشرر العربية لشرر النار."),
    EXPECTED[31]: open_spec("حصب", "חצף للتقشير، وحصب العربية للرمي بالحصباء."),
    EXPECTED[32]: gap_spec("LAW-GAP", "قطن", "כתנא للكتان، وقطن لمادة ليفية، لكن כ־ת أمام ق־ط تحتاج صفين ومسار المعنى غير مباشر.", "لا تكفي هوية التطبيع التي طوت التمييزين."),
    EXPECTED[33]: open_spec("قطر", "כתר للتطويق، وقطر العربية للناحية أو التقطير."),
    EXPECTED[34]: open_spec("قرش", "קרש للتجمد، وقرش العربية للجمع أو العض."),
    EXPECTED[35]: open_spec("تلي", "תליא للتعليق، وتلي العربية للاتباع."),
    EXPECTED[36]: positive_spec("زجج", ("الزجاج",), "ROOT-TRACE", "זגגא صانع الزجاج، وزجج أصل الزجاج", "GUT-03 يرخص ג ↔ ج في الموضعين؛ الزاي هوية وألف الصفة خارج الجذر.", "مباشر في صناعة الزجاج."),
    EXPECTED[37]: open_spec("بعر", "בער للحرق، وبعر العربية لفضلة الحيوان."),
    EXPECTED[38]: open_spec("سحر", "סהרא للقمر، وسحر العربية لآخر الليل أو السحر."),
    EXPECTED[39]: open_spec("حبك", "הפך للقلب، وحبك العربية للإحكام والنسج."),
    EXPECTED[40]: open_spec("سوف", "סופא للنهاية، وسوف العربية للاستقبال أو المماطلة."),
    EXPECTED[41]: open_spec("رحب", "רחף للحضانة، ورحب العربية للسعة."),
    EXPECTED[42]: open_spec("حدق", "חדקא للشوك، وحدق العربية للعين أو البستان."),
    EXPECTED[43]: gap_spec("MORPHOLOGY-GAP", "صيد", "צוד للصيد نفسه، لكن الواو الآرامية أمام ياء العربية لا يجيزها GLD-01 في هذا الاتجاه.", "لا يعكس اتجاه الصف الموقّع."),
    EXPECTED[44]: positive_spec("طلق", ("تركها", "انطلق"), "ROOT-ECHO", "טלק للزوال، وطلق للانطلاق وترك البلاد", "الطاء واللام والقاف هويات.", "خطوة واحدة: الانطلاق مغادرة وزوال عن الموضع."),
    EXPECTED[45]: open_spec("جلل", "גלל للدحرجة، وجلل العربية للتغطية أو العظم."),
    EXPECTED[46]: positive_spec("صوت", ("الصوت",), "ROOT-ECHO", "צות للإصغاء، وصوت لما يسمع", "الصاد والواو والتاء هويات.", "خطوة واحدة: الإصغاء إدراك الصوت."),
    EXPECTED[47]: positive_spec("بدل", ("تغييره", "غيره"), "ROOT-ECHO", "בדל للفصل، وبدل لتغيير الشيء وإحلال غيره", "الباء والدال واللام هويات.", "خطوة واحدة: الفصل يتيح الإبدال والتغيير."),
    EXPECTED[48]: open_spec("طبع", "טבע للغرق، وطبع العربية للطبع والملء؛ المروحة لا تسمي الغرق في المصدرين."),
    EXPECTED[49]: open_spec("قوت", "כותא للنافذة، وقوت العربية للطعام والقوة."),
}


def main() -> int:
    source_base = base.load_base()
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Aramaic one-short identity batch 03: already present")
        return 0
    report = json.loads(REPORT.read_text(encoding="utf-8"))
    one_short = {
        item["family_id"]: item
        for item in report["languages"]["aramaic"]["one_member_short"]
    }
    if any(family not in one_short for family in EXPECTED):
        missing = [family for family in EXPECTED if family not in one_short]
        raise ValueError(f"target no longer one-member-short: {missing}")
    population = json.loads(POPULATION.read_text(encoding="utf-8"))
    families = {
        item["family_id"]: item
        for item in population["languages"]["aramaic"]["families"]
    }
    selected = []
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for family_id in EXPECTED:
            member = families[family_id]["members"][0]
            row = connection.execute(
                "SELECT entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
                "FROM entries WHERE entry_id=?",
                (member["entry_id"],),
            ).fetchone()
            if row is None:
                raise ValueError(f"missing inventory entry: {member['entry_id']}")
            selected.append((family_id, dict(row)))
    finally:
        connection.close()
    source_base.SPECS = SPECS
    fan_map = source_base.fans()
    cards = [
        source_base.render_card(rank, family, entry, SPECS[family], fan_map)
        for rank, (family, entry) in enumerate(selected, 51)
    ]
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## حملة المقام الآرامية، دفعة المطابقة الذاتية 3 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "النطاق هو الأسر 51 إلى 100 من قائمة المطابقة الذاتية المثبتة قبل بدء الأحكام، وكلها كانت ناقصة عضوًا واحدًا. دخلت الخمسون بلا انتقاء موجب.",
            "",
            *cards,
            "<!-- ARAMAIC-ONE-SHORT-IDENTITY-BATCH-03:END -->",
            "",
        ]
    )
    source_base.atomic_write(READING, text.rstrip() + "\n" + block)
    positives = sum(item["kind"] == "positive" for item in SPECS.values())
    closures = sum(item["kind"] == "terminal" for item in SPECS.values())
    held = len(SPECS) - positives - closures
    source_base.atomic_write(
        AUDIT,
        "\n".join(
            [
                "# حملة المقام الآرامية، دفعة المطابقة الذاتية 3 المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئت الأسر 51 إلى 100 من قائمة المطابقة الذاتية المثبتة، وكلها ناقصة عضوًا واحدًا.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة: {positives}.",
                f"- الإغلاقات النهائية: {closures}.",
                "",
                "## الباقي",
                "",
                f"- فجوات أو مرشحات بلا حكم: {held}.",
                "- لا NO-TRACE مصنوع من فجوة.",
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
