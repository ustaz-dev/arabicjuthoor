#!/usr/bin/env python3
"""Scan thirty unused Aramaic inventory members for lane A batch 07."""

from __future__ import annotations

import importlib.util
import sqlite3
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
TARGET = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
COMMON = ROOT / "scripts" / "lane_a_aramaic_append_discovery_batch_03.py"
SCAN_START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B07-SCAN:START -->"
SCAN_END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B07-SCAN:END -->"
BATCH_NO = "7"


def load_common():
    spec = importlib.util.spec_from_file_location("lane_a_aramaic_b07_common", COMMON)
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
    I(1919, "جرب", "جراب", "ROOT-ECHO", "الجذر الكامل", "g الآرامية ↔ ج العربية في طي التطبيع المثبت؛ الراء والباء هويتان.", "الزجاجة أو الوعاء", "الجراب الوعاء أو المزود", "الوعاء المحمول نفسه", w("kitab_al_ayn", "الجراب: وعاء", "يعرف الجراب بالوعاء"), w("al_muhkam", "الجراب: الوعاء", "يعرف الجراب بالوعاء")),
    I(2017, "زرع", "زرع", "ROOT-ECHO", "الجذر الكامل بعد عزل همزة التعدية المنشورة", "ز ر ع هويات؛ همزة البناء خارج الجذر ولا صف لازم.", "إخراج المني بوصفه بذرا تناسليا", "زرع الحب أي بذره", "إيداع البذر المنتج نفسه في المجال الحيوي", w("al_muhkam", "زرع الحب", "يعرف الزرع ببذر الحب"), w("lisan", "زرع الحب", "يعرف الزرع ببذر الحب")),
    I(2156, "نهر", "نهار", "ROOT-ECHO", "الجذر الكامل بعد عزل همزة التعدية المنشورة", "ن ه ر هويات؛ همزة البناء خارج الجذر ولا صف لازم.", "الإضاءة وإظهار النور", "النهار ضياء وانتشار ضوء", "ظهور الضوء نفسه", w("al_muhkam", "النهار: ضياء", "يعرف النهار بالضياء"), w("lisan", "النهار: ضياء", "يعرف النهار بالضياء")),
)


PARKED = {
    1808: "الحس قوي مباشر، لكن مقابلة s الآرامية بصاد حصين تحتاج صفا عابرا للفرعين غير موقع.",
    1824: "الحلاوة مباشرة، لكن الياء الفرعية مقابل الواو العربية تحتاج شاهد GLD-01 الخارجي الخاص بهذه الكلمة.",
    1850: "لم يسم مصدر الفرع مقابلا عربيا، ولم يثبت الجذر الكامل حس الراحة في مصدرين.",
    1852: "لم يثبت الجذر الكامل للغنى والوفرة مقابلا عربيا بهوية صوتية مرخصة.",
    1883: "المصدر يقارن العبرية والأكادية، ولا يسمي مقابلا عربيا لمعنى الخواء أو عدم القيمة.",
    1914: "الجذر الكامل لا يعطي في العربية حس السلب بهوية صوتية مرخصة.",
    1915: "حس الجذام لا يلتقي مقابلا عربيا في الجذر الكامل.",
    1916: "صفة الأجرب الفرعية لم يثبت لها مقابل عربي بالمسار الصوتي نفسه.",
    1917: "حس الناهب لا يلتقي مقابلا عربيا في الجذر الكامل.",
    1918: "اسم علم؛ لا يصدر منه حكم نسب معجمي.",
    1920: "صورة ثانية لحس الوعاء نفسه في الأسرة التي مثلها العضو 1919؛ لا تكرر وحدة الحكم.",
    1926: "رأس جذري مجرد بلا حس معجمي عضو مستقل.",
    1962: "حس الشهادة لا يلتقي مقابلا عربيا في الجذر الكامل.",
    1980: "المصدر يسمي أصلا فارسيا قديما؛ يعزل مسار المصدر ولا يحكم نسبا عربيا.",
    1984: "اسم علم لمدينة؛ لا يصدر منه حكم معجمي.",
    1985: "اسم شخص؛ لا يصدر منه حكم معجمي.",
    1998: "المصدر يسمي أصلا فارسيا أوسط؛ العائلة العربية إن وجدت انتقال قرض لا شاهد فرع مستقل.",
    1999: "المصدر يسمي مانحا يونانيا؛ يعزل القرض.",
    2000: "المصدر يسمي مانحا يونانيا؛ يعزل القرض.",
    2041: "أداة خطابية مركبة بلا جذر معجمي قابل للمقارنة.",
    2055: "اسم علم مقترض من الفرثية؛ يعزل القرض والاسم.",
    2056: "أداة وجود منفية مركبة؛ لا تورث حكم أجزائها.",
    2060: "اسم علم لمدينة؛ لا يصدر منه حكم معجمي.",
    2104: "الأصل السامي المنشور لا يكفي؛ المروحة العربية دثأ لا تحمل حس العشب بل مطر الصيف ونتاج الغنم.",
    2134: "اسم إقليم مركب؛ لا يرث حكم عبر أو نهر.",
    2140: "اسم حرف لا مادة معجمية؛ لا يصدر حكم نسب.",
    2142: "اسم مكان مركب؛ لا يرث حكم بيت أو لحم.",
}


def append_pending_cards() -> None:
    text = TARGET.read_text(encoding="utf-8")
    if SCAN_START in text and SCAN_END in text:
        before, rest = text.split(SCAN_START, 1)
        _old, after = rest.split(SCAN_END, 1)
        text = before.rstrip() + "\n" + after.lstrip()
    con = sqlite3.connect(DB)
    con.row_factory = sqlite3.Row
    entries = {}
    families = {}
    for ordinal in PARKED:
        row = con.execute(
            "select entry_id,headword,romanization,pos,gloss,etymology,loan_hint "
            "from entries where entry_id glob ?",
            (f"kaikki_aramaic:{ordinal}:*",),
        ).fetchone()
        if row is None:
            raise SystemExit(f"مدخل مفقود: {ordinal}")
        entries[ordinal] = row
        fam = con.execute(
            "select family_id from family_members where entry_id=?", (row["entry_id"],)
        ).fetchone()
        if fam is None:
            raise SystemExit(f"أسرة مفقودة: {ordinal}")
        families[ordinal] = fam["family_id"]
    con.close()
    lines = [
        SCAN_START,
        "",
        f"## دفعة الجرد الآرامية أ {BATCH_NO}: {len(PARKED)} مصيرًا غير صادر",
        "",
        f"- بيان النطاق، الخطوة 14: نافذة من ثلاثين عضوًا غير مستعمل بلا انتقاء للروائع. أصدرت {len(POSITIVES)} أحكام في كتلة أ {BATCH_NO} الإيجابية، وهذه البطاقات تسجل سبب عدم الإصدار دون اختلاق سالب.",
        "",
    ]
    for rank, ordinal in enumerate(PARKED, len(POSITIVES) + 1):
        row = entries[ordinal]
        eid = str(row["entry_id"])
        head = str(row["headword"])
        rom = str(row["romanization"] or "بلا رومنة منشورة")
        gloss = str(row["gloss"])
        reason = PARKED[ordinal]
        lines.extend(
            [
                f"### بطاقة: `{families[ordinal]}`، {head}، دفعة الجرد الآرامية أ {BATCH_NO}، الرتبة {rank}، العضو `{eid}`",
                f"- عائق: النوع=OPEN-CANDIDATE؛ يتطلب={reason}؛ العضو=`{eid}`.",
                "- إصدارُ البروتوكول: RECOVERY-v2 (2026-07-14)",
                f"- الصورة الصامتة في الفرع: `{head}`؛ الرومنة المنشورة: `{rom}`.",
                f"- الكلمةُ في الفرع: {head} `{rom}`، {row['pos']}، «{gloss}» [Kaikki Aramaic، `{eid}`].",
                f"- أقدمُ صورة أو مقارنة منشورة: {row['etymology'] or 'لا إحالة اشتقاقية منشورة في المدخل'}.",
                "- الخطوةُ صفر: فُحص نوع المدخل والصرف والاسم والقرض قبل أي تعرية.",
                "- درجةُ المقارنة: بدأ الفحص بالجذر الكامل؛ لم تنجح درجة أدنى مسندة.",
                "- مسحُ المعاني العربيّة: لم يصدر شاهدان بالمعنى العضوي نفسه؛ السبب مسمى في سطر العائق.",
                "- المقابلُ من اللسان: غير صادر.",
                "- مسارُ الصوت: غير صادر؛ لا صف مخترع.",
                f"- المعنى من قاموس الفرع: «{gloss}» [Kaikki Aramaic، `{eid}`].",
                f"- المدار: جوار المعنى في الفرع: {gloss}؛ جوار المعنى في العربية: غير مثبت بشاهدين؛ موضع الالتقاء: غير صادر.",
                f"- المصفاة: loan_hint={'نعم' if row['loan_hint'] else 'لا'}؛ الاسم والقرض والمتجانس مفصولة في سبب البطاقة.",
                f"- فصلُ المتجانسات والاقتراض: العضو `{eid}` وحده؛ لا وراثة.",
                "- إشعاع الأسرة في الفرع: العضو المسمى وحده.",
                "- إشعاع الأسرة في العربية: غير صادر.",
                "- جسورُ الاسترداد المفحوصة: المصدر؛ الجذر؛ المدار؛ القرض؛ نوع المدخل.",
                "- حالةُ الإغلاق: OPEN-CANDIDATE.",
                f"- الحكم (استكشاف): غير صادر؛ OPEN-CANDIDATE للعضو `{eid}`؛ {reason}",
                "- عدسة الاسترداد: بدأت بالجذر الكامل ولم تفرض مقابلا.",
                "- عدسة التشكيك: منعت الاسم والقرض أو غياب المدار من التحول إلى صلة.",
                "- ملاحظات: محلي للمراجعة المضادة الثالثة؛ لا سجل مركزي ولا خط برهان.",
                "",
            ]
        )
    lines.extend([SCAN_END, ""])
    TARGET.write_text(text.rstrip() + "\n\n" + "\n".join(lines), encoding="utf-8", newline="\n")


def main() -> None:
    C.START = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B07-POSITIVE:START -->"
    C.END = "<!-- LANE-A-ARAMAIC-INVENTORY-2026-07-29-B07-POSITIVE:END -->"
    C.BATCH_NO = "7"
    C.BATCH_TITLE = "ثلاث صلات من ثلاثين عضوًا متتاليًا"
    C.BATCH_SCOPE = "ثلاثة أعضاء فقط من نافذة الجرد التالية استوفت الجذر والمدار والشاهدين؛ بقية النافذة تسجل مصائر غير صادرة في الكتلة اللاحقة."
    C.ITEMS = POSITIVES
    C.PARKED = {}
    C.main()
    append_pending_cards()
    print("scanned=30 positives=3 closures=0 pending=27")


if __name__ == "__main__":
    main()
