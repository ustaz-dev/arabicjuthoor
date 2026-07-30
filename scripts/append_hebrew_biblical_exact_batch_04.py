#!/usr/bin/env python3
"""Read exact Hebrew biblical-queue ranks 11 through 50 not already written."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
BASE_PATH = ROOT / "scripts" / "append_hebrew_biblical_priority_batch_01.py"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-hebrew-biblical-exact-ranks-11-50-local.md"
)
DATE = "2026-07-28"
MARKER = "<!-- HEBREW-BIBLICAL-EXACT-BATCH-04 -->"
EXPECTED_EXISTING_RANKS = {11, 13, 15, 27, 29, 33, 37, 39, 41, 46, 48, 49}


def load_base():
    specification = importlib.util.spec_from_file_location(
        "hebrew_biblical_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Hebrew biblical base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


base = load_base()


def open_spec(root: str, reason: str, sound: str, bridge: str):
    return {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": root,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


def gap_spec(
    state: str, root: str, reason: str, sound: str, bridge: str
):
    return {
        "kind": "gap",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


def terminal_spec(state: str, root: str, reason: str, bridge: str):
    return {
        "kind": "terminal",
        "state": state,
        "root": root,
        "reason": reason,
        "sound": "العزل مسمى من المصدر؛ لا يستعمل صف صوت لإنتاج حكم نسب.",
        "bridge": bridge,
    }


def positive_spec(
    root: str,
    terms: tuple[str, ...],
    verdict: str,
    reason: str,
    sound: str,
    bridge: str,
):
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


def family(rank: int) -> str:
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    return str(queue["unread_biblical_lexical_queue"][rank - 1]["family_id"])


SPECS: dict[int, dict[str, object]] = {
    12: gap_spec(
        "SOURCE-GAP",
        "دلي",
        "דלה ودلى يتفقان في إنزال الدلو واستخراج الماء، لكن المروحة لا تسمي هذا المعنى في مصدرين مستقلين قديمين",
        "النواة د־ل هوية، والرجل الضعيفة الأخيرة لا تحول إلى حكم قبل اكتمال المصدرين.",
        "المعنى مباشر في إرسال الدلو أو جذب الماء، وعائقه توثيقي لا سلبي.",
    ),
    14: terminal_spec(
        "LOANWORD",
        "نتر",
        "المصدر يسمي المصرية nṯrj مانحًا للعضو العبري",
        "مانح مصري خارجي مسمى، فيعزل العضو من المقام الأصلي.",
    ),
    16: positive_spec(
        "سبي",
        ("سَبَى", "السَّبْي"),
        "ROOT-TRACE",
        "שבי والسبي حال الأسر نفسها",
        "SIB-01 يرخص ש ↔ س؛ الباء والياء هويتان.",
        "مباشر في الأسر والسبي.",
    ),
    17: open_spec(
        "ثقل",
        "סכל للحمق وثقل العربية للوزن؛ وصف البليد بالثقيل جسر مجازي غير مسمى في المصدر",
        "DENT-02 يرخص ס ↔ ث، والقاف واللام هويتان، ولا يصنع الصوت معنى.",
        "التثاقل والحمق تقارب وصفي محتمل لا حكم.",
    ),
    18: positive_spec(
        "زني",
        ("زَنَى", "الزنا"),
        "NUCLEUS-TRACE",
        "זנה وزنى في فعل الفجور نفسه، والنواة ز־ن محفوظة",
        "الزاي والنون هويتان؛ اختلاف الهاء والياء الضعيفتين يمنع ادعاء الجذر الكامل.",
        "مباشر في الزنا.",
    ),
    19: open_spec(
        "ثقم",
        "שכם للكتف، ولم تسم مروحة ثقم العربية هذا العضو",
        "DENT-02 يرخص ש ↔ ث؛ القاف والميم هويتان، ولا يكفي السطح.",
        "لا جسر دلالي مباشر.",
    ),
    20: open_spec(
        "فسخ",
        "פסח اسم القربان الفصحي، وفسخ العربية للنقض والإزالة",
        "SIB-01 يرخص ש ↔ س وLAB-07 يرخص פ ↔ ف؛ المعنى غير مباشر.",
        "المقارنة المنشورة تحفظ مرشحًا، ولا تجعل القربان فعل فسخ.",
    ),
    21: open_spec(
        "هري",
        "הרה للحبل والحمل، ولم تسم المروحة العربية لهذا الجذر معنى الحمل",
        "الهاء والراء ظاهرتان، والرجل الضعيفة لا تعوض غياب المعنى.",
        "لا جسر دلالي مباشر.",
    ),
    22: open_spec(
        "تمك",
        "תמך للدعم، والمرشح الآلي طبق لا يحمل المعنى نفسه",
        "لا جذر عربي مطابق مرخص للعضو في الجرد.",
        "الدعم معلوم في العبرية، والمقابل العربي غير معين.",
    ),
    23: positive_spec(
        "دبق",
        ("دَبِق", "الالتصاق", "لزق"),
        "ROOT-TRACE",
        "דבק ودبق في الالتصاق واللزوق",
        "الدال والباء والقاف هويات، ولا يلزم صف إبدال.",
        "مباشر في الالتصاق.",
    ),
    24: open_spec(
        "مثل",
        "משל للحكم والسلطان، ومثل العربية للشبه والنموذج",
        "DENT-02 يرخص ש ↔ ث؛ الميم واللام هويتان.",
        "الحاكم نموذج أو صاحب سلطة جسر محتمل غير مسمى.",
    ),
    25: terminal_spec(
        "FORM-OF-ISOLATED",
        "سوم",
        "المصدر يسمي שום مصدرًا مجردًا للفعل שם",
        "صورة صرفية محالة إلى لمتها، لا لمة مستقلة.",
    ),
    26: terminal_spec(
        "FORM-OF-ISOLATED",
        "توم",
        "المصدر يسمي תום صورة بديلة من תאום",
        "صورة بديلة محالة إلى لمتها، لا لمة مستقلة.",
    ),
    28: terminal_spec(
        "FORM-OF-ISOLATED",
        "نكي",
        "المصدر يسمي הוכה صيغة مبنية للمجهول من נכה",
        "صورة صرفية محالة إلى فعلها، لا لمة مستقلة.",
    ),
    30: gap_spec(
        "SOURCE-GAP",
        "قني",
        "קנה للقصبة قديمة، لكن حقل الأصل يسمي علاقة اليونانية بالأكدية ولا يحسم مسار العضو العبري",
        "القاف والنون ظاهرتان، والرجل الضعيفة لا تحسم طريق النقل.",
        "المعنى مباشر في القصبة، ومسار الأصل أو الاقتراض غير مسمى للعضو.",
    ),
    31: open_spec(
        "فزع",
        "פצע للجرح، وفزع العربية للخوف والذعر",
        "SIB-03 يرخص צ ↔ ز وLAB-07 يرخص פ ↔ ف؛ العين هوية.",
        "أثر الجرح قد يسبب الفزع، لكنه ليس معنى العضو نفسه.",
    ),
    32: open_spec(
        "سيح",
        "שיח للمحادثة، وسيح العربية للجريان والذهاب",
        "SIB-01 يرخص ש ↔ س؛ الياء والحاء هويتان.",
        "جريان الكلام استعارة ممكنة غير مسماة.",
    ),
    34: positive_spec(
        "سبت",
        ("السَّبْت", "قطع"),
        "ROOT-ECHO",
        "שבת للتوقف عن العمل، وسبت العربية للقطع والسكون في معنى السبت",
        "SIB-01 يرخص ש ↔ س؛ الباء والتاء هويتان.",
        "خطوة واحدة: قطع العمل هو التوقف والراحة.",
    ),
    35: positive_spec(
        "لوز",
        ("اللَّوْز", "اللوز"),
        "ROOT-ECHO",
        "לוז للبندق واللوز العربية لثمرة شجرية مسماة في المقارنة المنشورة",
        "اللام والواو والزاي هويات.",
        "انتقال قريب داخل أسماء الثمار القشرية، لا تطابق نوع نباتي تام.",
    ),
    36: positive_spec(
        "كبش",
        ("الكَبْش", "فحل الضأن"),
        "ROOT-TRACE",
        "כבש والكبش للضأن نفسه",
        "الكاف والباء والشين هويات في الجذر التاريخي.",
        "مباشر في الكبش والضأن.",
    ),
    38: open_spec(
        "قشر",
        "קשר للربط، وقشر العربية لنزع القشرة",
        "SIB-01 يرخص ש ↔ ش في هذا المرشح؛ القاف والراء هويتان.",
        "الربط والنزع حدثان متقابلان، لا جسر مباشر.",
    ),
    40: gap_spec(
        "SOURCE-GAP",
        "صنح",
        "المصدر يصرح بانعدام مقابل سامي معروف ويذكر إعادة تشكيل المعنى حديثًا",
        "لا يبنى حكم من مرشحات مولدة لا يسميها المصدر.",
        "سقوط الحرارة معنى حديث للعضو، فلا ينقل إلى الاستعمال القديم.",
    ),
    42: open_spec(
        "بحر",
        "בחן لبرج المراقبة، وبحر العربية للماء الواسع",
        "الباء والحاء ظاهرتان، والنون والراء مختلفتان بلا جسر.",
        "لا جسر دلالي مباشر.",
    ),
    43: open_spec(
        "شمخ",
        "שמח للفرح، وشمخ العربية للعلو ورفع الرأس",
        "GUT-05 يرخص ח ↔ خ؛ الشين والميم هويتان.",
        "رفع الرأس قد يصاحب الفرح أو الفخر، لكنه مدار غير مسمى.",
    ),
    44: terminal_spec(
        "INTRA-HOUSE-TRANSFER",
        "نزل",
        "المصدر يرجح الأكدية manzaltum مانحًا للعضو",
        "انتقال داخل البيت من مانح أكدي مسمى، فلا يعد شاهد فرع مستقلًا.",
    ),
    45: positive_spec(
        "قني",
        ("اكتسب", "اتخذ"),
        "NUCLEUS-TRACE",
        "קנה وقنى في الاكتساب والاقتناء، والنواة ق־ن محفوظة",
        "القاف والنون هويتان؛ اختلاف الهاء والياء الضعيفتين يمنع ادعاء الجذر الكامل.",
        "مباشر في الاكتساب والاتخاذ.",
    ),
    47: open_spec(
        "جلس",
        "גלש للانزلاق، وجلس العربية للثبات في المقعد",
        "GUT-03 يرخص ג ↔ ج وSIB-01 يرخص ש ↔ س؛ اللام هوية.",
        "الحركة والانقطاع عنها ضدان، ولا يكفي التقابل حكمًا.",
    ),
    50: open_spec(
        "شمس",
        "שמה للخراب والقفر، وشمس العربية للجرم أو التعرض للشمس",
        "المرشح يحتاج صفًا للعين الضعيفة فوق SIB-04، ولا يحمل المعنى نفسه.",
        "لا جسر دلالي مباشر.",
    ),
}


def main() -> int:
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical exact batch 04: already present")
        return 0
    payload = json.loads(QUEUE.read_text(encoding="utf-8"))
    queue = payload["unread_biblical_lexical_queue"]
    slice_items = list(enumerate(queue[10:50], 11))
    existing = {
        rank
        for rank, item in slice_items
        if f"### بطاقة: `{item['family_id']}`" in text
    }
    if existing != EXPECTED_EXISTING_RANKS:
        raise ValueError(
            f"existing-rank set drifted: {sorted(existing)}"
        )
    selected = [
        (rank, item) for rank, item in slice_items if rank not in existing
    ]
    if set(SPECS) != {rank for rank, _ in selected}:
        raise ValueError("spec ranks do not cover the exact unread remainder")
    base.SPECS = {family(rank): SPECS[rank] for rank, _ in selected}
    fans = base.fan_map()
    cards = []
    connection = sqlite3.connect(DB)
    try:
        for rank, item in selected:
            family_id = str(item["family_id"])
            cards.append(
                base.render_card(
                    rank,
                    item,
                    base.SPECS[family_id],
                    base.members_for(connection, family_id),
                    base.roots_for(connection, str(item["entry_id"])),
                    fans,
                )
            )
    finally:
        connection.close()
    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## العبريّة التوراتية، إتمام الرتب 11 إلى 50 ({DATE}، محلية)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "أعيد المرور على الرتب 11 إلى 50 من الطابور العضوي نفسه حرفيًا. كانت 12 رتبة قد قُرئت في دفعات محلية سابقة، فحُفظت إحالةً ولم تكرر بطاقاتها، وكتبت بطاقات الرتب الثماني والعشرين الباقية بترتيبها.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-EXACT-BATCH-04:END -->",
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
                "# العبريّة التوراتية، إتمام الرتب 11 إلى 50",
                "",
                "## بيان النطاق",
                "",
                "مر المرور على الرتب 11 إلى 50 حرفيًا. أحيلت 12 رتبة إلى بطاقاتها المحلية السابقة، وكتبت 28 بطاقة لم تكن مقروءة.",
                "",
                "## الرقمان المفصولان",
                "",
                f"- الصلات الموجبة الجديدة: {positives}.",
                f"- الإغلاقات النهائية الجديدة: {closures}.",
                "",
                "## الباقي",
                "",
                f"- فجوات أو مرشحات بلا حكم: {held}.",
                "- لا سالب مصنوع، ولا صف صوت جديد.",
                "",
                "## الحالة",
                "",
                "- الدفعة محلية للمراجعة المضادة الثالثة.",
                "- لا سجل مركزي ولا تشغيل لخط البرهان.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "queue_ranks": "11-50",
                "referred_existing": len(existing),
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
