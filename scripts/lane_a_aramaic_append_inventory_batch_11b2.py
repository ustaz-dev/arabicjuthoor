#!/usr/bin/env python3
"""Append the final twenty-five members of lane A Aramaic window B11B."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMMON = ROOT / "scripts" / "lane_a_aramaic_append_discovery_batch_03.py"
SCAN_START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B2-SCAN:START -->"
SCAN_END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B2-SCAN:END -->"


def load_common():
    spec = importlib.util.spec_from_file_location("lane_a_aramaic_b11b2_common", COMMON)
    if spec is None or spec.loader is None:
        raise RuntimeError("تعذر تحميل مساعد المسار أ")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


C = load_common()
W = C.W
I = C.I


POSITIVES = (
    I(
        1122,
        "رنب",
        "أرنب",
        "ROOT-TRACE",
        "الصورة الرباعية الكاملة بعد إسقاط ألف الحالة",
        "الألف والراء والنون والباء هويات في الصورتين؛ لا صف إبدال لازم.",
        "الأرنب الحيوان المعروف",
        "الأرنب الحيوان المعروف للذكر والأنثى",
        "المسمى الحيواني نفسه",
        W("lisan", "الأَرْنَبُ: معروفٌ", "يعرف الأرنب بالحيوان المعروف"),
        W("taj_al_arus", "حَيَوَانٌ", "يصف الأرنب بالحيوان المعروف وسماته"),
    ),
)


WINDOW = (
    1137, 1136, 1135, 1134, 1133, 1132, 1131, 1130, 1129, 1128,
    1127, 1126, 1125, 1124, 1123, 1122, 1121, 1120, 1119, 1118,
    1117, 1116, 1115, 1114, 1113,
)


PARKED = {
    1137: "الخطأ لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1136: "الصفة المؤنثة تحمل لاحقة، ولا ترث حكم عضو آخر.",
    1135: "الصفة تحمل بناءً زائدًا، ولا تستوفي مروحتها المستقلة.",
    1134: "الصحة والاستقامة لا تلتقيان جذرًا عربيًا كاملًا بصف صوتي موقع.",
    1133: "اسم الحماقة يحمل بناءً زائدًا، ولا يرث حكم عضو آخر.",
    1132: "الصفة تحمل بناءً زائدًا، ولا تستوفي مروحتها المستقلة.",
    1131: "الحماقة لا تلتقي مروحة سكل العربية في جوار واحد مسند.",
    1130: "الفقر لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1129: "الشبع يقابل شبع العربية معنى، لكن مسار السين الآرامية ↔ الشين العربية غير موقع.",
    1128: "الشهادة تقابل شهد العربية معنى، لكن مسار السين الآرامية ↔ الشين العربية غير موقع.",
    1127: "الالتصاق لا يلتقي مروحة نقف العربية في جوار واحد مسند.",
    1126: "مدخل بديل لاسم النعناع؛ لا يصدر منه حكم مستقل.",
    1125: "اسم نبات، والمروحة العربية المتاحة لا تستوفي شاهدين قديمين مستقلين للمسمى نفسه.",
    1124: "اسم العضلة لا يلتقي مروحة عقب العربية في جوار واحد مسند.",
    1123: "اسم الفأر لا يلتقي مروحة عقب العربية في جوار واحد مسند.",
    1121: "اسم القرد لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1120: "حكم البئر والحفرة صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1119: "الغصن يقابل شوك العربية جزئيًا، لكن مسار السين الآرامية ↔ الشين العربية غير موقع.",
    1118: "الموضع لا يلتقي مروحة شوف العربية في مدار واحد مسند.",
    1117: "اسم الطاووس موسوم بمسار قرض يوناني؛ يعزل.",
    1116: "الذبح لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1115: "الذبح لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1114: "اسم العجن لا يرث حكم عضو آخر، ومروحته المستقلة غير مكتملة.",
    1113: "العجين لا يلتقي جذرًا عربيًا كاملًا بصف صوتي موقع.",
}


def append_scan() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if SCAN_START in text and SCAN_END in text:
        before, rest = text.split(SCAN_START, 1)
        _old, after = rest.split(SCAN_END, 1)
        text = before.rstrip() + "\n" + after.lstrip()
    elif SCAN_START in text or SCAN_END in text:
        raise SystemExit("حد واحد لدفعة B11B2 موجود دون الآخر")

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
        "## دفعة الجرد الآرامية أ 11B2: آخر خمسة وعشرين عضوًا من النافذة",
        "",
        "- بيان النطاق، الخطوة 14: 25 عضوًا متتاليًا من الرتبة المصدرية 1137 إلى 1113. الموجب الكامل يثبت أعلاه، وغير الصادر يسجل بسبب واحد دون اختلاق إغلاق.",
        "",
    ]
    positive_ordinals = {item.ordinal for item in POSITIVES}
    for rank, ordinal in enumerate(WINDOW, 76):
        if ordinal in positive_ordinals:
            continue
        row = rows[ordinal]
        entry_id = str(row["entry_id"])
        lines.append(
            f"- الرتبة {rank}: `{families[ordinal]}`؛ `{entry_id}`؛ "
            f"{row['headword']}، {row['pos']}، «{row['gloss']}». "
            f"عائق: النوع=OPEN-CANDIDATE؛ يتطلب={PARKED[ordinal]}؛ "
            "الحكم (استكشاف): غير صادر."
        )
    lines.extend(
        [
            "",
            "- حصيلة B11B2: صلات موجبة جديدة=1؛ إغلاق=0؛ غير صادر=24.",
            "- حصيلة B11 كاملة: صلات موجبة جديدة=7؛ إغلاق=0؛ غير صادر=93.",
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
    C.START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B2-POSITIVE:START -->"
    C.END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B2-POSITIVE:END -->"
    C.BATCH_NO = "11B2"
    C.BATCH_TITLE = "صلة واحدة من آخر خمسة وعشرين عضوًا في B11"
    C.BATCH_SCOPE = "25 عضوًا متتاليًا من الرتبة 1137 إلى 1113 بلا انتقاء؛ عضو واحد فقط استوفى المروحة والمدار والصوت."
    C.ITEMS = POSITIVES
    C.PARKED = {}
    C.main()
    append_scan()
    print("scanned=25 positives=1 closures=0 pending=24")


if __name__ == "__main__":
    main()
