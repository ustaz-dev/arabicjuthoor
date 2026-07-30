#!/usr/bin/env python3
"""Append the first twenty unread singleton Hebrew families.

The source order is the exact-member biblical queue.  Singleton families are
selected without changing their relative queue order because each issued
member disposition completes exactly one proof-denominator family.  The cards
remain local until the third-lens review.
"""
from __future__ import annotations

import importlib.util
import json
import sqlite3
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
QUEUE = ROOT / "data" / "hebrew-biblical-priority-queue.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "2026-07-28-hebrew-biblical-singleton-batch-02-local.md"
)
BASE_PATH = ROOT / "scripts" / "append_hebrew_biblical_priority_batch_01.py"
DATE = "2026-07-28"
MARKER = "<!-- HEBREW-BIBLICAL-SINGLETON-BATCH-02 -->"


EXPECTED = [
    "hebrew:family:351fc3a8500e19fda530ea41",
    "hebrew:family:a0b93e3b99b8a03d9040e2be",
    "hebrew:family:57052fb876c05fb6fce32151",
    "hebrew:family:4e52a585bc2d36cff4160021",
    "hebrew:family:d12bd8753b27015e2ea8c2ab",
    "hebrew:family:0ac389f2529ca58a3e9c4988",
    "hebrew:family:d1e8e2393c606625049b8503",
    "hebrew:family:9f340f74923c123c78ea95ed",
    "hebrew:family:f71bbb0c19041662821d4944",
    "hebrew:family:6f6a2a80f3135eb8884f5d36",
    "hebrew:family:f3c4e4b3969dabfa9718724a",
    "hebrew:family:0dd3c5f27ca7ec1d00cebc97",
    "hebrew:family:b7035583193f5da71dc5a1ae",
    "hebrew:family:929fb41a7c37fd9b14365dfa",
    "hebrew:family:3df5148a0e2fa86c3e23c06f",
    "hebrew:family:93e4225168691022bea75211",
    "hebrew:family:cfe14ca7f9e1218392286c58",
    "hebrew:family:03b61a810b038bec26aa487f",
    "hebrew:family:727de08b027948f78272e65a",
    "hebrew:family:e6e79cf35370ae492c662b51",
]


SPECS: dict[str, dict[str, object]] = {
    EXPECTED[0]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "وسع",
        "reason": "בצע كسب وربح جائر، ووسع العربية لا تسمي هذا المعنى",
        "sound": "المرشح الآلي لا يكفي؛ لا مسار حكم مباشر مسمى.",
        "bridge": "لا جسر دلالي مباشر بعد المروحة.",
    },
    EXPECTED[1]: {
        "kind": "terminal",
        "state": "FORM-OF-ISOLATED",
        "root": "رعع",
        "reason": "العضو إحالة صريحة إلى רַע «حطم» وليس لمة مستقلة",
        "sound": "لا يصدر مسار صوت من صورة إحالة.",
        "bridge": "العزل صرفي بنص المصدر.",
    },
    EXPECTED[2]: {
        "kind": "terminal",
        "state": "FORM-OF-ISOLATED",
        "root": "رعع",
        "reason": "العضو إحالة صريحة إلى רֵעַ «صديق» وليس لمة مستقلة",
        "sound": "لا يصدر مسار صوت من صورة إحالة.",
        "bridge": "العزل صرفي بنص المصدر.",
    },
    EXPECTED[3]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "عرج",
        "reason": "ערך في التنظيم والترتيب، ومروحة عرج لا تسميهما",
        "sound": "المرشح يحتاج صفوف الجرد فقط ولا ينتج حكمًا بالهيكل.",
        "bridge": "لا جسر دلالي مباشر.",
    },
    EXPECTED[4]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "شمخ",
        "reason": "שמח للفرح، وشمخ العربية للعلو والأنفة",
        "sound": "تقارب الصوامت لا يعوض افتراق المعنى.",
        "bridge": "لا مدار مسمى يجمع الفرح والشمخ.",
    },
    EXPECTED[5]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "بسط",
        "reason": "פשט لنزع الثوب، وبسط العربية للنشر والمد",
        "sound": "المسار الصوتي المرشح لا يحكم قبل جسر المعنى.",
        "bridge": "احتمال نشر الثوب قبل نزعه غير مسمى في المصدر.",
    },
    EXPECTED[6]: {
        "kind": "law-gap",
        "state": "LAW-GAP",
        "root": "ثلم",
        "reason": "المصدر يقارن العربية ثلم، لكن نطاق ת العبرية أمام ث العربية غير موقع لهذا العضو",
        "sound": "DENT-01 مسمى في الشبكة للعربية والآرامية؛ لا يوسع إلى العبرية بلا توقيع.",
        "bridge": "الأخدود والثلمة متقاربان، والرجل الصوتية معلقة.",
    },
    EXPECTED[7]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "نوم",
        "reason": "מום عيب ونقص، ونوم العربية لا يسميهما",
        "sound": "المرشح الهيكلي وحده لا يثبت الصلة.",
        "bridge": "لا جسر دلالي مباشر.",
    },
    EXPECTED[8]: {
        "kind": "law-gap",
        "state": "LAW-GAP",
        "root": "قزح",
        "reason": "المصدر يقارن العربية قزح في اسم النبات، لكن مسار צ أمام ز غير موقع",
        "sound": "لا يستعار صف من تشابه نباتي؛ يلزم صف موقع للصامت الأوسط.",
        "bridge": "مباشر في الحبة السوداء بنص الأصل المنشور.",
    },
    EXPECTED[9]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "شعع",
        "reason": "שעה للنظر، وشع العربية لا تثبت فعل النظر في مروحة مصدرين",
        "sound": "الهيكل لا يكفي مع غياب المعنى المسمى.",
        "bridge": "لا جسر مباشر مثبت.",
    },
    EXPECTED[10]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "عرر",
        "reason": "ערל للتحريم، وعر العربية لا تسمي التحريم",
        "sound": "تغير اللام والراء لا يستعمل بلا معنى مطابق.",
        "bridge": "لا جسر دلالي مباشر.",
    },
    EXPECTED[11]: {
        "kind": "terminal",
        "state": "INTRA-HOUSE-TRANSFER",
        "root": "تبن",
        "reason": "المصدر يسمي الآرامية طريق العربية تبن؛ يحال شاهد الانتقال إلى زوج المانح",
        "sound": "لا يستعمل تطابق الرسم شاهد فرع مستقل مع مانح أخت مسمى.",
        "bridge": "المعنى مطابق للتبن، وقاعدة عمق القرض تحكم تصنيفه.",
    },
    EXPECTED[12]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "كسل",
        "reason": "גזל للسرقة، وكسل العربية للفتور لا الأخذ",
        "sound": "مرشح الصوت لا يثبت صلة دلالية.",
        "bridge": "لا جسر مباشر.",
    },
    EXPECTED[13]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "صوح",
        "reason": "סוכה كوخ ومظلة، وصوح العربية لا يسمي هذا المسكن في مصدرين",
        "sound": "المسار المرشح لا يصدر حكمًا مع فجوة المعنى.",
        "bridge": "مدار الستر محتمل لكنه غير مسمى في المصدر.",
    },
    EXPECTED[14]: {
        "kind": "positive",
        "state": "READY",
        "root": "طحن",
        "terms": ("طحن", "الطحن"),
        "verdict": "ROOT-TRACE",
        "reason": "טחן والعربية طحن متطابقان في الصوامت وفعل السحق والطحن",
        "sound": "ט ↔ ط وח ↔ ح وנ ↔ ن هويات سامية في هذا الزوج؛ لا صف إبدال لازم.",
        "bridge": "مباشر في الطحن والسحق.",
    },
    EXPECTED[15]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "فسح",
        "reason": "פסח للعبور والتجاوز، وفسح العربية للتوسعة والإخلاء",
        "sound": "LAB-07 يرخص פ ↔ ف؛ بقية الرجل لا تكمل المعنى.",
        "bridge": "احتمال إخلاء الطريق للعبور غير مسمى في المصدر.",
    },
    EXPECTED[16]: {
        "kind": "positive",
        "state": "READY",
        "root": "سكن",
        "terms": ("استقر", "سكنت"),
        "verdict": "ROOT-TRACE",
        "reason": "שכן والعربية سكن متطابقان في الإقامة والسكن",
        "sound": "SIB-01 يرخص ש ↔ س؛ כ ↔ ك والنون هويتان.",
        "bridge": "مباشر في الإقامة والسكن.",
    },
    EXPECTED[17]: {
        "kind": "positive",
        "state": "READY",
        "root": "حرث",
        "terms": ("العمل في الأرض", "الزرع"),
        "verdict": "ROOT-TRACE",
        "reason": "חרש والعربية حرث متطابقان في حراثة الأرض",
        "sound": "DENT-02 يرخص ש ↔ ث؛ الحاء والراء هويتان.",
        "bridge": "مباشر في الحرث والزراعة.",
    },
    EXPECTED[18]: {
        "kind": "open",
        "state": "MORPHOLOGY-GAP",
        "root": "بكي",
        "reason": "المصدر يقارن בכי ببكاء، لكن هوية جذر الاسم العبري مع جذر بكى تحتاج تحليل الصيغة قبل الحكم",
        "sound": "الباء والكاف هويتان؛ الصامت الضعيف الأخير لا يحسم من اسم السطح.",
        "bridge": "مباشر في البكاء، والعائق صرفي لا دلالي.",
    },
    EXPECTED[19]: {
        "kind": "open",
        "state": "OPEN-CANDIDATE",
        "root": "بثث",
        "reason": "משתה وليمة، وبث العربية لا يسمي الوليمة",
        "sound": "المرشحات الآلية لا تنتج حكمًا مع افتراق المعنى.",
        "bridge": "لا جسر دلالي مباشر.",
    },
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
        print("Hebrew biblical singleton batch 02: already present")
        return 0

    queue = json.loads(QUEUE.read_text(encoding="utf-8"))
    connection = sqlite3.connect(DB)
    try:
        batch = []
        for item in queue["unread_biblical_lexical_queue"]:
            family = str(item["family_id"])
            member_count = connection.execute(
                "SELECT COUNT(*) FROM family_members WHERE family_id=?",
                (family,),
            ).fetchone()[0]
            if member_count == 1:
                batch.append(item)
            if len(batch) == len(EXPECTED):
                break
        families = [str(item["family_id"]) for item in batch]
        if families != EXPECTED:
            raise ValueError(f"singleton queue order drifted: {families}")
        if any(family in text for family in EXPECTED):
            raise ValueError("a singleton batch family is already present")

        base.SPECS = SPECS
        fans = base.fan_map()
        cards = []
        for rank, item in enumerate(batch, 1):
            family = str(item["family_id"])
            cards.append(
                base.render_card(
                    rank,
                    item,
                    SPECS[family],
                    base.members_for(connection, family),
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
            f"## العبريّة التوراتية، دفعة الأسر الأحادية 2 ({DATE}، محلية للمراجعة الثالثة)",
            "",
            "### بيان النطاق، الخطوة 14",
            "",
            "الدفعة هي أول عشرين أسرة أحادية العضو من طابور الشاهد التوراتي الصريح، مع حفظ ترتيبها النسبي في الطابور. معيار الأحادية بنيوي معلن لأنه يجعل كل حكم أو إغلاق مصيرًا كاملًا لأسرة واحدة، ولم تنتق الصلات بحسب جمالها.",
            "",
            *cards,
            "<!-- HEBREW-BIBLICAL-SINGLETON-BATCH-02:END -->",
            "",
        ]
    )
    base.atomic_write(READING, text.rstrip() + "\n" + block)
    base.atomic_write(
        AUDIT,
        "\n".join(
            [
                "# العبريّة التوراتية، دفعة الأسر الأحادية 2 المحلية",
                "",
                "## بيان النطاق",
                "",
                "قُرئت أول عشرين أسرة أحادية العضو من طابور الشاهد التوراتي، مع حفظ ترتيبها النسبي. الأحادية معيار عائد بنيوي لا انتقاء دلالي.",
                "",
                "## الرقمان المفصولان",
                "",
                "- الصلات الموجبة: 3، وهي טחן ↔ طحن، שכן ↔ سكن، חרש ↔ حرث.",
                "- الإغلاقات النهائية: 3، وهي إحالتا רעה الصرفيتان، وתבן انتقالًا داخل البيت.",
                "",
                "## الفجوات الصادقة",
                "",
                "- مرشحات مفتوحة بلا حكم: 11.",
                "- فجوتا قانون صوتي: 2.",
                "- فجوة صرفية: 1.",
                "- المجموع: 20 بطاقة، من غير سالب مختلق.",
                "",
                "## الحالة",
                "",
                "- البطاقات محلية للمراجعة المضادة الثالثة.",
                "- لم يشغل خط البرهان ولم يجدد سجل الاسترداد المركزي.",
                "- الأعداد محاسبية داخلية لا تصلح للنشر.",
                "",
            ]
        ),
    )
    print(
        json.dumps(
            {
                "cards": 20,
                "positive_connections": 3,
                "terminal_closures": 3,
                "open_candidates": 11,
                "law_gaps": 2,
                "morphology_gaps": 1,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
