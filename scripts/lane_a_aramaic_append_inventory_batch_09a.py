#!/usr/bin/env python3
"""Append the first twenty-five members of lane A Aramaic window B09."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMMON = ROOT / "scripts" / "lane_a_aramaic_append_discovery_batch_03.py"
SCAN_START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B09A-SCAN:START -->"
SCAN_END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B09A-SCAN:END -->"


def load_common():
    spec = importlib.util.spec_from_file_location("lane_a_aramaic_b09a_common", COMMON)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل مساعد المسار أ")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C = load_common()
W = C.W
I = C.I


def w(source_id: str, anchor: str, reading: str):
    return W(source_id, anchor, reading)


POSITIVES = (
    I(
        1418,
        "تمر",
        "تمرة",
        "ROOT-TRACE",
        "الجذر الكامل، مع تطابق صيغة المفرد المؤنث",
        "ت م ر هويات؛ تاء المفرد المؤنث ظاهرة في الصورتين، وألف الحالة الآرامية خارج المقارنة.",
        "ثمرة التمر المأكولة",
        "التمرة، واحدة التمر وحمل النخل",
        "المسمى الثمري نفسه، لا مجرد جوار الفاكهة",
        w("lisan", "التمر", "ينص على أن التمر حمل النخل وأن واحدته تمرة"),
        w("taj_al_arus", "التمر", "ينص على أن التمر حمل النخل وأن واحدته تمرة"),
    ),
)


WINDOW = (
    1430,
    1429,
    1426,
    1425,
    1424,
    1423,
    1422,
    1421,
    1420,
    1419,
    1418,
    1417,
    1416,
    1415,
    1414,
    1413,
    1412,
    1411,
    1410,
    1409,
    1408,
    1407,
    1406,
    1405,
    1404,
)


PARKED = {
    1430: "لم يثبت للجذر الكامل في حس الخروج مقابل عربي بشاهدين ومسار مرخص.",
    1429: "سلسلة الدمع نفسها ممثلة بحكم العضو 1428؛ لا يكرر الاسم حكم الحدث.",
    1426: "ظرف توكيد وظيفي، ولا جذر معجمي مستقل منشور في المدخل.",
    1425: "صفة صرفية من حس العرج نفسه، ولا مقابل عربي بالهيكل المرخص.",
    1424: "صفة صرفية من حس العرج نفسه، ولا مقابل عربي بالهيكل المرخص.",
    1423: "حس العرج لا يلتقي جذرًا عربيًا كاملًا بالمسار الصوتي نفسه.",
    1422: "ظرف معناه معًا، ولا يثبت المدخل تحليل أجزائه حتى لا يرث حكم مركب.",
    1421: "الحكم العضوي ענבתא ↔ عنب صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1420: "حس السجن واعد مع حبس، لكن المدخل لا ينشر أصل حבש، والسطح يحتاج إسقاط واو وصفير غير موثقين.",
    1419: "متجانس السفرجل منفصل عن حس السجن، ولا مقابل عربي كامل صادر له.",
    1417: "الرباعي ترجم يحتاج حسم مسار الانتقال بين الأختين قبل عده شاهد نسب مستقل.",
    1416: "حس الترتيب لا يلتقي مقابلا عربيًا رباعيًا بالمسار نفسه.",
    1415: "حس الولادة مباشر، لكن حقل المدخل لا ينشر اشتقاقه من ילד، فلا تنزع حروف الصيغة بالتخمين.",
    1414: "المصدر يسمي مانحًا يونانيًا؛ يعزل القرض.",
    1413: "اللعاب والمخاط لا يلتقيان جذرًا عربيًا كاملًا مرخصًا.",
    1412: "ريق قريب معنى، لكن مقابلة الواو بالياء هنا ليست في موضع GLD-01 الأول.",
    1411: "الحكم العضوي כף ↔ كف صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1410: "حرف جر ملتحم بضمير، ولا يرث حكم جزأيه.",
    1409: "اسم القصدير يفتقر إلى مسار تأثيلي منشور يفصل المشترك من المنقول.",
    1408: "المصدر يسمي مانحًا فارسيًا أوسط؛ يعزل القرض.",
    1407: "حس الكراهة يحتاج ס آرامية ↔ ش عربية، وليس هو صف SIB-01 الموقع.",
    1406: "الصيغة الثانية من حس الكراهة تعترضها فجوة الصفير نفسها.",
    1405: "متجانس الشجيرة والشوك مفصول عن صفة المكروه، ولا مقابل كامل صادر.",
    1404: "فعل الكراهة يحتاج ס آرامية ↔ ش عربية وصفه غير موقع.",
}


def append_scan() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if SCAN_START in text and SCAN_END in text:
        before, rest = text.split(SCAN_START, 1)
        _old, after = rest.split(SCAN_END, 1)
        text = before.rstrip() + "\n" + after.lstrip()
    elif SCAN_START in text or SCAN_END in text:
        raise SystemExit("حد واحد لدفعة B09A موجود دون الآخر")

    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    rows = {}
    families = {}
    for ordinal in WINDOW:
        row = con.execute(
            "select entry_id,headword,pos,gloss from entries where entry_id glob ?",
            (f"kaikki_aramaic:{ordinal}:*",),
        ).fetchone()
        if row is None:
            raise SystemExit(f"مدخل مفقود: {ordinal}")
        rows[ordinal] = row
        family = con.execute(
            "select family_id from family_members where entry_id=?", (row["entry_id"],)
        ).fetchone()
        if family is None:
            raise SystemExit(f"أسرة مفقودة: {ordinal}")
        families[ordinal] = family["family_id"]
    con.close()

    lines = [
        SCAN_START,
        "",
        "## دفعة الجرد الآرامية أ 9A: أول 25 عضوًا من نافذة المئة",
        "",
        "- بيان النطاق، الخطوة 14: أول 25 عضوًا متتاليًا من الرتبة المصدرية 1430 نزولًا، بعد استبعاد أعضاء دفعات أ السابقة فقط. البطاقة الموجبة كاملة أعلاه، وغير الصادر يسجل بسطر عائقه كما يجيز القسم 23.",
        "",
    ]
    positive_ordinals = {item.ordinal for item in POSITIVES}
    rank_map = {ordinal: rank for rank, ordinal in enumerate(WINDOW, 1)}
    for ordinal in WINDOW:
        if ordinal in positive_ordinals:
            continue
        row = rows[ordinal]
        entry_id = str(row["entry_id"])
        reason = PARKED[ordinal]
        lines.append(
            f"- الرتبة {rank_map[ordinal]}: `{families[ordinal]}`؛ "
            f"`{entry_id}`؛ {row['headword']}، {row['pos']}، «{row['gloss']}». "
            f"عائق: النوع=OPEN-CANDIDATE؛ يتطلب={reason}؛ "
            "الحكم (استكشاف): غير صادر."
        )
    lines.extend(
        [
            "",
            "- حصيلة B09A: صلة موجبة جديدة=1؛ إغلاق=0؛ غير صادر=24.",
            "",
            SCAN_END,
            "",
        ]
    )
    TARGET.write_text(
        text.rstrip() + "\n\n" + "\n".join(lines),
        encoding="utf-8",
        newline="\n",
    )


def main() -> None:
    C.START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B09A-POSITIVE:START -->"
    C.END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B09A-POSITIVE:END -->"
    C.BATCH_NO = "9A"
    C.BATCH_TITLE = "صلة التمرة من أول 25 عضوًا"
    C.BATCH_SCOPE = "أول 25 عضوًا متتاليًا من نافذة B09؛ لم يصدر حكم جديد إلا للعضو 1418 بعد مروحة كاملة، ولم تعد الصلات السابقة."
    C.ITEMS = POSITIVES
    C.PARKED = {}
    C.main()
    append_scan()
    print("scanned=25 positives=1 closures=0 pending=24")


if __name__ == "__main__":
    main()
