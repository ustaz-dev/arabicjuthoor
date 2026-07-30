#!/usr/bin/env python3
"""Append singleton Hebrew families 21 through 50 from the biblical queue."""
from __future__ import annotations

import importlib.util
import json
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-hebrew-biblical-singleton-batch-03-local.md"
)
BASE_PATH = ROOT / "scripts" / "append_hebrew_biblical_priority_batch_01.py"
DATE = "2026-07-28"
MARKER = "<!-- HEBREW-BIBLICAL-SINGLETON-BATCH-03 -->"


EXPECTED = [
    "hebrew:family:46895add6e40002d6c25f632",
    "hebrew:family:d10c3541e0d2c1bf7fa75373",
    "hebrew:family:48f271f53e29961b58150d41",
    "hebrew:family:caa94f640607878a623576d0",
    "hebrew:family:656772233c686a991ea34210",
    "hebrew:family:d530911dade9bfdac93b7886",
    "hebrew:family:3dca5cd6e9cf6eedf32da92a",
    "hebrew:family:f1ea06ac1277b5e91614784e",
    "hebrew:family:cda8bb8a89ef32ec056bedf5",
    "hebrew:family:d9c1c2e56bdedb68656ce8d8",
    "hebrew:family:ae1ac68f9f6da3a5181addc4",
    "hebrew:family:7b33a7c2943d3aea322c6162",
    "hebrew:family:a48066058a73043e76972fb5",
    "hebrew:family:8101fe76a5485ea60764e8f3",
    "hebrew:family:ee5d852655833a96aa0f3c71",
    "hebrew:family:6959247d927863a8ea629dd6",
    "hebrew:family:20be5cf9847818119540dda1",
    "hebrew:family:2436e26210511f9e9074b99a",
    "hebrew:family:dd6e5f7e1575e28a5ab0df14",
    "hebrew:family:b3596fabaa8fbd3770045108",
    "hebrew:family:ed534f9950f773aa430bc986",
    "hebrew:family:ea77e1f80da36055a7afe22a",
    "hebrew:family:8b111932a42a1bd67ed435a8",
    "hebrew:family:bd3bd9095f7ac262d9c3e786",
    "hebrew:family:81e75c7767582e07f9ef0d47",
    "hebrew:family:0c61b68f4e816a19709f306e",
    "hebrew:family:690c0aa49194455a2c1c1854",
    "hebrew:family:6c1b6627d2ae4c1c5d850835",
    "hebrew:family:1102f15a63de998c664d1a54",
    "hebrew:family:93166af9ac408a3ff0b45707",
]


def open_spec(root: str, reason: str, sound: str, bridge: str):
    return {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": root,
        "reason": reason,
        "sound": sound,
        "bridge": bridge,
    }


def gap_spec(state: str, root: str, reason: str, sound: str, bridge: str):
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


SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: terminal_spec(
        "LOANWORD",
        "بهت",
        "المصدر يسمي الحجر مقتبسًا من المصرية jbhtj",
        "طريق مانح أجنبي مسمى؛ لا يدخل المقام الأصلي.",
    ),
    EXPECTED[1]: open_spec(
        "شحح",
        "שכח للنسيان وشح العربية للبخل والمنع",
        "المرشح الصوتي لا يكفي مع افتراق المعنى.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[2]: terminal_spec(
        "INTRA-HOUSE-TRANSFER",
        "شطر",
        "المصدر يسمي الأكدية satālu مانحًا للكنعانية",
        "انتقال داخل البيت، لا شاهد فرع مستقل.",
    ),
    EXPECTED[3]: gap_spec(
        "LAW-GAP",
        "ضحك",
        "المصدر يقارن العربية ضحك في معنى الضحك نفسه، لكن المسار الصوتي الكامل غير موقع",
        "لا صف موقع يجمع ש־ח־ק مع ض־ح־ك في هذا العضو.",
        "المعنى مباشر، والرجل الصوتية وحدها معلقة.",
    ),
    EXPECTED[4]: positive_spec(
        "نهق",
        ("صوت الحمار", "نهيق"),
        "ROOT-TRACE",
        "נהק والعربية نهق متطابقان في الصوامت وصوت الحمار",
        "النون والهاء والقاف هويات سامية؛ لا صف إبدال لازم.",
        "مباشر في نهيق الحمار.",
    ),
    EXPECTED[5]: open_spec(
        "نشق",
        "נשק للتقبيل، ونشق العربية للاستنشاق",
        "تقارب الصوامت لا يثبت صلة من غير جسر.",
        "ملامسة الفم ليست مدارًا مسمى في المصدر.",
    ),
    EXPECTED[6]: open_spec(
        "نتن",
        "נתן للعطاء، والمصدر لا يذكر إلا احتمال تضييق إلى إعطاء الرائحة الكريهة في نتن",
        "التاء والنونان متقاربة، والاحتمال المنشور لا يصير حكمًا.",
        "إعطاء الشيء وإفراز الرائحة جسر محتمل غير محسوم.",
    ),
    EXPECTED[7]: open_spec(
        "ركع",
        "רקה للصدغ، وركع العربية للانحناء",
        "المرشح الصوتي لا يحمل معنى العضو.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[8]: gap_spec(
        "MORPHOLOGY-GAP",
        "سمك",
        "דגה اسم للسمك يحيل إلى דג، لكن الأسرة المصدرية لم تربطه بلمته الأم",
        "لا يستعاد جذر من اسم مشتق قبل تثبيت التحليل الصرفي.",
        "المعنى معلوم، وهوية الأسرة الصرفية معلقة.",
    ),
    EXPECTED[9]: positive_spec(
        "ليث",
        ("الأسد",),
        "ROOT-TRACE",
        "ליש والعربية ليث من الأصل السامي المنشور نفسه ومعناهما الأسد",
        "DENT-02 يرخص ש ↔ ث؛ اللام والياء هويتان.",
        "مباشر في الأسد.",
    ),
    EXPECTED[10]: open_spec(
        "سحل",
        "שחל للأسد، وسحل العربية لا تسمي الأسد",
        "SIB-01 يرخص المرشح ولا يثبت المعنى.",
        "لا جسر دلالي مباشر.",
    ),
    EXPECTED[11]: positive_spec(
        "كنف",
        ("ناحية", "الجانب"),
        "ROOT-ECHO",
        "כנף جناح، والعربية كنف جانب وناحية تحت أصل سامي منشور واحد",
        "LAB-07 يرخص פ ↔ ف؛ الكاف والنون هويتان.",
        "خطوة مدارية واحدة: الجناح جانب الجسم الممتد.",
    ),
    EXPECTED[12]: positive_spec(
        "شمس",
        ("الشمس",),
        "ROOT-TRACE",
        "שמש والعربية شمس من الاسم السامي نفسه للجرم المعروف",
        "الشين والميم هويتان، وSIB-01 يرخص ש النهائية أمام س.",
        "مباشر في الشمس.",
    ),
    EXPECTED[13]: terminal_spec(
        "FORM-OF-ISOLATED",
        "اتي",
        "المصدر يسمي العضو تصريفًا توراتيًا للفعل הביא مع لواحقه",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[14]: terminal_spec(
        "FORM-OF-ISOLATED",
        "اخذ",
        "المصدر يسمي العضو تصريفًا توراتيًا للفعل לקח مع لواحقه",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[15]: terminal_spec(
        "FORM-OF-ISOLATED",
        "راي",
        "المصدر يسمي العضو تصريفًا توراتيًا للفعل ראה مع لواحقه",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[16]: terminal_spec(
        "FORM-OF-ISOLATED",
        "جرش",
        "المصدر يسمي العضو تصريفًا توراتيًا للفعل גרש مع لواحقه",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[17]: open_spec(
        "ابب",
        "אביב للربيع، والمصدر لا يسمي إلا احتمال صلة بأب العربية للمرعى",
        "لا صف زائد؛ العائق في تعيين المعنى القديم.",
        "خضرة الربيع والمرعى مدار محتمل غير محسوم.",
    ),
    EXPECTED[18]: open_spec(
        "كمز",
        "כומז حلي مجهول التفصيل، والمصدر يجعل صلته بكمز العربية احتمالية",
        "الرسم قريب، لكن الأصل نفسه موسوم غير مؤكد.",
        "شكل دائري أو كرات صغيرة تفسير محتمل لا حكم.",
    ),
    EXPECTED[19]: gap_spec(
        "SOURCE-GAP",
        "لقش",
        "מלקוש للمطر المتأخر ولا أصل عربي مقارن مسمى في المصدر",
        "لا يصدر مسار صوت بلا مقابل منشور ومروحة.",
        "المعنى الفرعي معلوم، والمقابل العربي غير مثبت.",
    ),
    EXPECTED[20]: terminal_spec(
        "FORM-OF-ISOLATED",
        "وري",
        "المصدر يسمي العضو تصريفًا للفعل הורה مع ضمير",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[21]: terminal_spec(
        "FORM-OF-ISOLATED",
        "دبر",
        "المصدر يسمي العضو مصدرًا مضافًا من דיבר",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[22]: terminal_spec(
        "FORM-OF-ISOLATED",
        "اخو",
        "المصدر يسمي العضو صيغة ملكية ناقصة الرسم من אחות",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[23]: terminal_spec(
        "FORM-OF-ISOLATED",
        "بنت",
        "المصدر يسمي العضو جمع ملكية ناقص الرسم من בת",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[24]: terminal_spec(
        "FORM-OF-ISOLATED",
        "عبد",
        "المصدر يسمي العضو صيغة ملكية ناقصة الرسم من עבודה",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[25]: terminal_spec(
        "FORM-OF-ISOLATED",
        "نعر",
        "المصدر يسمي العضو جمع ملكية ناقص الرسم من נערה",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[26]: terminal_spec(
        "FORM-OF-ISOLATED",
        "رجل",
        "المصدر يسمي العضو صيغة ملكية ماسورية من רגל",
        "صورة صرفية، لا لمة مستقلة.",
    ),
    EXPECTED[27]: gap_spec(
        "LAW-GAP",
        "نحاس",
        "المصدر يقارن נחושת بالعربية نحاس، لكن الصامتين شين وتاء لا يفسرهما صف موقع أو تحليل صرفي",
        "النون والحاء هويتان؛ بقية البنية لا تختزل بلا قانون.",
        "مباشر في النحاس، والرجل الصوتية معلقة.",
    ),
    EXPECTED[28]: gap_spec(
        "SOURCE-GAP",
        "ارم",
        "ארמון للقصر وأصله موسوم غير مؤكد بلا مقابل عربي منشور",
        "لا يصدر مسار صوت من أصل غير معلوم.",
        "المعنى الفرعي مثبت، والمقابل غير مسمى.",
    ),
    EXPECTED[29]: terminal_spec(
        "FORM-OF-ISOLATED",
        "ولد",
        "المصدر يسمي العضو مصدرًا مع ضمير من ילד",
        "صورة صرفية، لا لمة مستقلة.",
    ),
}


def load_base():
    specification = importlib.util.spec_from_file_location(
        "hebrew_priority_batch_base", BASE_PATH
    )
    if specification is None or specification.loader is None:
        raise RuntimeError("cannot load Hebrew batch base")
    module = importlib.util.module_from_spec(specification)
    specification.loader.exec_module(module)
    return module


def main() -> int:
    base = load_base()
    text = READING.read_text(encoding="utf-8")
    if MARKER in text:
        print("Hebrew biblical singleton batch 03: already present")
        return 0
    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    connection = sqlite3.connect(DB)
    try:
        singletons = []
        for item in queue["unread_biblical_lexical_queue"]:
            count = connection.execute(
                "SELECT COUNT(*) FROM family_members WHERE family_id=?",
                (str(item["family_id"]),),
            ).fetchone()[0]
            if count == 1:
                singletons.append(item)
        batch = singletons[20:50]
        families = [str(item["family_id"]) for item in batch]
        if families != EXPECTED:
            raise ValueError(f"singleton queue order drifted: {families}")
        if any(family in text for family in EXPECTED):
            raise ValueError("a singleton batch family is already present")
        base.SPECS = SPECS
        fans = base.fan_map()
        cards = [
            base.render_card(
                rank,
                item,
                SPECS[str(item["family_id"])],
                base.members_for(connection, str(item["family_id"])),
                base.roots_for(connection, str(item["entry_id"])),
                fans,
            )
            for rank, item in enumerate(batch, 21)
        ]
    finally:
        connection.close()

    block = "\n".join(
        [
            "",
            MARKER,
            "",
            f"## العبريّة التوراتية، دفعة الأسر الأحادية 3 ({DATE}، محلية للمراجعة الثالثة)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "الدفعة هي الأسر الأحادية من الرتبة 21 إلى 50 في طابور الشاهد التوراتي، من غير تخط أو انتقاء موجب. لكل عضو مصير مستقل، والصور الصرفية تعزل بنص المصدر.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-SINGLETON-BATCH-03:END -->",
            "",
        ]
    )
    base.atomic_write(READING, text.rstrip() + "\n" + block)
    base.atomic_write(
        AUDIT,
        "\n".join(
            [
                "# العبريّة التوراتية، دفعة الأسر الأحادية 3 المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئت الأسر الأحادية 21 إلى 50 من طابور الشاهد التوراتي مع حفظ الترتيب، من غير انتقاء دلالي.",
                "",
                "## الرقمان المفصولان",
                "",
                "- الصلات الموجبة: 4، وهي נהק ↔ نهق، ליש ↔ ليث، כנף ↔ كنف، שמש ↔ شمس.",
                "- الإغلاقات النهائية: 14، منها 12 صورة صرفية، وقرض مصري، وانتقال أكدي داخل البيت.",
                "",
                "## الفجوات الصادقة",
                "",
                "- مرشحات مفتوحة بلا حكم: 7.",
                "- فجوتا قانون: 2.",
                "- فجوة صرف: 1.",
                "- فجوتا مصدر: 2.",
                "- المجموع: 30 بطاقة.",
                "",
                "## الحالة",
                "",
                "- البطاقات محلية للمراجعة المضادة الثالثة.",
                "- لم يشغل خط البرهان ولم يجدد السجل المركزي.",
                "- الأعداد محاسبية داخلية لا تصلح للنشر.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": 30,
                "positive_connections": 4,
                "terminal_closures": 14,
                "open_candidates": 7,
                "law_gaps": 2,
                "morphology_gaps": 1,
                "source_gaps": 2,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
