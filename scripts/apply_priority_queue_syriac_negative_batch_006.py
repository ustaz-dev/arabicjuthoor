#!/usr/bin/env python3
"""Read the two Syriac negative-direction rows left in the priority queue."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
MARKER = "<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-006-SYRIAC-NEGATIVE:BEGIN -->"
BATCH = "priority-queue-aramaic-006-syriac-negative"


CARDS = r'''

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-006-SYRIAC-NEGATIVE:BEGIN -->

## طابور المسار الثاني — صفا السريانية الاتجاهيان (2026-08-01)

### بطاقة: `ימא`، العضو `kaikki_aramaic:190:en-ימא-arc-noun-SmnxnIwm`
- أصل المرشح: طابور المسار 2، صف `سريانيّة: البحر ↔ اليمّ` في `arabic-school-loan-negative.md`؛ نص ملاحظته: «عن ابن قتيبة. لفظةٌ قرآنيّة. لم يرتضِه ابنُ دريدٍ في الجمهرة، فهي مواضعُ نزاع».
- كلمة الفرع: `ימא`، noun، «sea» [Kaikki Aramaic]. بعد تعرية ألف الحالة يبقى الجذع كاملًا `y-m(m)`؛ التضعيف صفة للميم، ولا صامت ثالث مستقل.
- لا زوج منتقى بإسقاط أصل: الصامتان المتميزان `y-m` كاملان. لكن سؤال البطاقة اتجاهي قبل أن يكون صوتيًا: مصدر العضو يسمي اللفظ ابتكارًا ساميًا شماليًّا غربيًّا، ومدرسة عربية نسبت `اليمّ` إلى السريانية، وابن دريد خالف.
- حكم طبقة الجذر: OPEN-CANDIDATE؛ لا يصدر حكم إرث في موضع النزاع، ولا يُحسم النقل من ملخص الدعوى وحده. حكم طبقة النواة: TOOL-GAP؛ لا مدخل `يم` في الفهرس المجمد.
- مسح العربية: لسان العرب لابن منظور: «اليَمُّ: البحر»؛ تاج العروس لمرتضى الزبيدي: «اليَمُّ: البَحْرُ».
- الجسر الدلالي الصريح: المعنى واحد، فـ`ימא` و`اليمّ` يسمّيان البحر؛ وحدة المعنى والصورة لا تحسم هل العربية ورثت أم تلقت.
- المصفاة الاتجاهية: الدعوى `سرياني → عربي` مثبتة النسب إلى قائلها ومخالفتها مثبتة؛ لذلك لا تحول المطابقة إلى إرث ولا المخالفة إلى رد.
- الحكم محفوظ: root=OPEN-CANDIDATE وnucleus=TOOL-GAP؛ لا سطر نسخ لأن درجتي الحكم لم تتغيرا.

### بطاقة: `איר`، العضو `kaikki_aramaic:1454:en-איר-arc-name-jHj-W5k2`
- أصل المرشح: طابور المسار 2، صف `ܐܝܪ (ayyār) ↔ أيّار` في `arabic-school-loan-negative.md`؛ نص ملاحظته: «شهرٌ جارٍ في العربيّةِ إلى اليوم، وأصلُه أبعدُ من السريانيّة».
- كلمة الفرع: `איר` ʾīyār، name، «May» [Kaikki Aramaic]. مصدر العضو ينص: `From Akkadian Ayyārum`؛ الاسم منقول، لا جذر موروث تستخرج منه نواة.
- صوامت الفرع السطحية كاملة `ʔ-y-r`؛ لم يؤخذ زوج ولم يسقط صامت. التشابه العربي `أيّار` واقع داخل سلسلة اسم شهر رحّال.
- حكم طبقة الجذر: DIRECTIONAL-TRANSMISSION. حكم طبقة النواة: SEMITIC-SOURCE-TRANSMISSION؛ لا نواة من اسم منقول.
- المصفاة الاتجاهية: السلسلة المنشورة تبدأ من الأكادية إلى الآرامية، وصف المسار الثاني يثبت أن الأصل العربي أبعد من السريانية؛ فلا تُعد المطابقة إرثًا عربيًا.
- الحكم محفوظ في الطبقتين؛ لا سطر نسخ لأن الحكم الاتجاهي السابق لم يتغير.

<!-- PATH2-PRIORITY-QUEUE:ARAMAIC-006-SYRIAC-NEGATIVE:END -->
'''


def atomic_write(path: Path, text: str) -> None:
    descriptor, name = tempfile.mkstemp(prefix=path.name + ".", dir=path.parent)
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(unicodedata.normalize("NFC", text), encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def main() -> int:
    rows = [json.loads(line) for line in COVERAGE.read_text(encoding="utf-8").splitlines() if line.strip()]
    indexed = {row["member_id"]: row for row in rows}
    sea_id = "kaikki_aramaic:190:en-ימא-arc-noun-SmnxnIwm"
    ayyar_id = "kaikki_aramaic:1454:en-איר-arc-name-jHj-W5k2"
    missing = [member for member in (sea_id, ayyar_id) if member not in indexed]
    if missing:
        raise RuntimeError(f"coverage members missing: {missing}")

    sea = indexed[sea_id]
    sea["root_layer"]["basis"] = "اتحاد ימא واليم في البحر ظاهر، لكن نسبة العربية إلى السريانية منازع فيها؛ لا حكم إرث قبل حسم الاتجاه."
    sea["nucleus_layer"]["basis"] = "الجذع y-m كامل، لكن لا مدخل يم في الفهرس المجمد؛ لا حكم من فراغ الأداة."
    sea["direction_class"] = "DISPUTED-SYRIAC-TO-ARABIC"
    sea["batch_number"] = BATCH

    ayyar = indexed[ayyar_id]
    ayyar["root_layer"]["basis"] = "Akkadian Ayyārum → Aramaic/Syriac ʾīyār → Arabic أيار سلسلة نقل، لا نسب جذري."
    ayyar["nucleus_layer"]["basis"] = "اسم الشهر المنقول لا يصدر نواة، وإن تشابهت صوامته في اللغتين."
    ayyar["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
