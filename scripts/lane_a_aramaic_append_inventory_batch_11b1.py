#!/usr/bin/env python3
"""Append the first twenty-five members of lane A Aramaic window B11B."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMMON = ROOT / "scripts" / "lane_a_aramaic_append_discovery_batch_03.py"
SCAN_START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B1-SCAN:START -->"
SCAN_END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B1-SCAN:END -->"


def load_common():
    spec = importlib.util.spec_from_file_location("lane_a_aramaic_b11b1_common", COMMON)
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
        1150,
        "مثل",
        "مثل",
        "ROOT-TRACE",
        "الجذر الكامل بعد إسقاط ألف الحالة",
        "ת الآرامية ↔ ث العربية على DENT-01؛ الميم واللام هويتان.",
        "المثل والحكاية التي تقام للمقارنة والاعتبار",
        "المثل قول يشبه قولًا في شيء آخر، والمثل والشبه بمعنى",
        "جوار التشبيه الذي يصير قولًا سائرًا أو حكاية اعتبار",
        W("lisan", "المَثَلُ", "يعرف المثل بما يضرب من الأمثال والشبه"),
        W("taj_al_arus", "المَثَلُ", "يسند المثل إلى الشبه والقول السائر"),
    ),
    I(
        1149,
        "مثل",
        "مثل",
        "ROOT-TRACE",
        "الجذر الكامل",
        "ת الآرامية ↔ ث العربية على DENT-01؛ الميم واللام هويتان.",
        "مقارنة الشيء بغيره",
        "ماثله أي شابهه، ومثل الشيء بالشيء سواه به",
        "حدث المقابلة على الشبه نفسه",
        W("lisan", "ماثله", "ينص على أن ماثله بمعنى شابهه"),
        W("taj_al_arus", "مَثَّلَهُ به", "ينص على التشبيه والتمثيل بالشيء"),
    ),
)


WINDOW = (
    1162, 1161, 1160, 1159, 1158, 1157, 1156, 1155, 1154, 1153,
    1152, 1151, 1150, 1149, 1148, 1147, 1146, 1145, 1144, 1143,
    1142, 1141, 1140, 1139, 1138,
)


PARKED = {
    1162: "شدة القوة لا تلتقي مروحة عرى العربية في مدار واحد.",
    1161: "اسم شجرة، ولا تسند المروحة العربية المسمى النباتي بمصدرين قديمين مستقلين.",
    1160: "حكم الذبح والقربان صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1159: "حكم الذبح والقربان صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1158: "الصفير لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1157: "الصفة المؤنثة تحمل لاحقة، ولا ترث حكم عضو آخر.",
    1156: "الصفة تحمل بناءً زائدًا، ولا تستوفي مروحتها المستقلة.",
    1155: "العدل لا يلتقي جذرًا عربيًا كاملًا بصف صوتي موقع.",
    1154: "الفهم والحس لا يلتقيان مروحة سكل العربية في مدار واحد.",
    1153: "اسم المعرفة لا يرث حكم فعل العلم، ومروحته المستقلة غير مكتملة.",
    1152: "اسم مكان؛ يعزل عن الحكم المعجمي.",
    1151: "اسم علم شخصي؛ يعزل عن الحكم المعجمي.",
    1148: "المصدر يقارن شرط العربية، لكن مسار س الآرامية ↔ ش العربية غير موقع.",
    1147: "الخنق يقابل خنق العربية معنى، لكن مسار الحاء الآرامية ↔ الخاء العربية غير موقع لهذا الفرع.",
    1146: "مدخل بديل لاسم الفلفل ومسار قرض؛ لا يصدر منه حكم نسب مستقل.",
    1145: "الحد يقابل تخوم العربية، لكن مسار الحاء الآرامية ↔ الخاء العربية غير موقع لهذا الفرع.",
    1144: "حكم الحمل والولادة صادر في سجل سابق؛ لا يحسب مرة ثانية.",
    1143: "فعل المعرفة لا يستوفي شاهدين عربيين قديمين مستقلين في المروحة المتاحة.",
    1142: "الغرق لا يلتقي مروحة طبع العربية في جوار واحد مسند.",
    1141: "النبع لا يلتقي جذرًا عربيًا كاملًا بالمسار نفسه.",
    1140: "المصدر يصف كنس العربية بأنها مقترضة من الآرامية؛ لا شاهد فرع مستقل.",
    1139: "اسم الفقر ذو بناء زائد، ولا يرث حكم عضو آخر.",
    1138: "الضرر يقابل خبل العربية في المصدر، لكن مسار الحاء الآرامية ↔ الخاء العربية غير موقع لهذا الفرع.",
}


def append_scan() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if SCAN_START in text and SCAN_END in text:
        before, rest = text.split(SCAN_START, 1)
        _old, after = rest.split(SCAN_END, 1)
        text = before.rstrip() + "\n" + after.lstrip()
    elif SCAN_START in text or SCAN_END in text:
        raise SystemExit("حد واحد لدفعة B11B1 موجود دون الآخر")

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
        "## دفعة الجرد الآرامية أ 11B1: أول خمسة وعشرين عضوًا من النصف الثاني",
        "",
        "- بيان النطاق، الخطوة 14: 25 عضوًا متتاليًا من الرتبة المصدرية 1162 إلى 1138. الموجب الكامل يثبت أعلاه، وغير الصادر يسجل بسبب واحد دون اختلاق إغلاق.",
        "",
    ]
    positive_ordinals = {item.ordinal for item in POSITIVES}
    for rank, ordinal in enumerate(WINDOW, 51):
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
            "- حصيلة B11B1: صلات موجبة جديدة=2؛ إغلاق=0؛ غير صادر=23.",
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
    C.START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B1-POSITIVE:START -->"
    C.END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B11B1-POSITIVE:END -->"
    C.BATCH_NO = "11B1"
    C.BATCH_TITLE = "صلتان من أول خمسة وعشرين عضوًا في النصف الثاني من B11"
    C.BATCH_SCOPE = "25 عضوًا متتاليًا من الرتبة 1162 إلى 1138 بلا انتقاء؛ عضوان فقط استوفيا المروحة والمدار والصوت."
    C.ITEMS = POSITIVES
    C.PARKED = {}
    C.main()
    append_scan()
    print("scanned=25 positives=2 closures=0 pending=23")


if __name__ == "__main__":
    main()
