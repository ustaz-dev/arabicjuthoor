#!/usr/bin/env python3
"""Revoke sound-root nuclei that skip an available full triliteral."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DATE = "2026-08-01"
BATCH = "hebrew-sound-full-root-discipline-015"
MARKER = "<!-- HEBREW-REORDERED:SOUND-FULL-ROOT-DISCIPLINE-015:BEGIN -->"


CHANGES = {
    "kaikki_hebrew:561:en-זרע-he-verb-8hYCr1Os": {
        "root": ("ROOT-TRACE", True, "z-r-ʕ يقابل ز-r-ʕ كاملًا في بذر الحب؛ الجذر السالم متاح."),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت زع المنتقاة من الموضعين 1 و3 لأنها أسقطت الراء الأصلية مع توفر زرع كاملًا."),
    },
    "kaikki_hebrew:596:en-ברך-he-verb-g4vsx5Df": {
        "root": ("ROOT-TRACE", True, "b-r-k يقابل ب-r-k كاملًا في البروك على الركبة."),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت بك المنتقاة من الموضعين 1 و3 لأنها أسقطت الراء الأصلية من برك."),
    },
    "kaikki_hebrew:2274:en-פתח-he-verb-HCS1YmVi": {
        "root": ("ROOT-TRACE", True, "p-t-ḥ يقابل ف-t-ḥ كاملًا بنص التأثيل في فتح الشيء."),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت بح: أسقطت التاء الأصلية من פתח، وأخذت الصورة من בוח والمعنى من فتح؛ الجذر فتح متاح."),
    },
    "kaikki_hebrew:2377:en-קטל-he-verb-9W9eC7bx": {
        "root": ("ROOT-TRACE", True, "q-ṭ-l يقابل ق-t-l كاملًا في القتل مع مسار الإطباق المنشور."),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت قت لأنها أسقطت اللام الأصلية من الجذر السالم قتل المتاح كاملًا."),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:SOUND-FULL-ROOT-DISCIPLINE-015:BEGIN -->

## الجرد العبري المعاد ترتيبه — السالم بعد الأجوف والمضعّف والمعتل (2026-08-01)

### بطاقة: `זרע`، العضو `kaikki_hebrew:561:en-זרע-he-verb-8hYCr1Os`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `זרע` zaráʿ، verb، «to seed, to sow» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: From Proto-Semitic *zarʕ- (“seed”). Cognate with Arabic زَرَعَ (zaraʕa, “to sow”) and Aramaic זְרַע (zəraʿ, “to sow”).
- الخطوةُ صفر (التعرية بصرف الفرع): جذر الفرع `z-r-ʕ` كامل في المواضع 1-2-3. النواة السابقة `z-ʕ` أخذت 1 و3 وأسقطت الراء الأصلية بلا تعرية؛ رُدت.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `z-r-ʕ ↔ ز-r-ʕ`؛ لا حكم نووي صادر.
- مسحُ المعاني العربيّة: لسان العرب لابن منظور: «الزرع نبات كل شيء يحرث، وقيل: الزرع طرح البذر»؛ تاج العروس لمرتضى الزبيدي: «زَرَعَ، كَمَنَعَ، يَزْرَعُ زَرْعَاً وزِراعَةً: طَرَحَ البَذْرَ».
- المقابلُ من اللسان: `زرع` في طرح البذر والإنبات.
- مسارُ الصوت: تطابق الصوامت الثلاثة؛ لا صف إبدال لازم ولا صامت مسقط.
- المعنى من قاموس الفرع: `זרע` «to seed, to sow» [Kaikki Hebrew].
- المدار: بذر الحب للإنبات في الطرفين من مادة `زرع` نفسها.
- المصفاة: نص التأثيل يصرح بالمقابل العربي ولا يسمي مانحًا؛ لا وراثة لمتجانس.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: الفعل وحده؛ اسم البذر يحتاج شاهده المستقل.
- جسورُ الاسترداد المفحوصة: إعادة البناء؛ الصوامت الثلاثة؛ المصدران العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-TRACE + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: فعل الزرع وبذر الحب وحده.
- إشعاع الأسرة في العربية: مادة `زرع` في طرح البذر وحده.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ نُسخت `زع` لإسقاطها الراء الأصلية.
- ملاحظات: السابق root=ROOT-TRACE وnucleus=NUCLEUS-TRACE؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

### بطاقة: `ברך`، العضو `kaikki_hebrew:596:en-ברך-he-verb-g4vsx5Df`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `ברך` barákh، verb، «kneeled» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: From Proto-Semitic *birk-, *bark- (“knee”); الشاهد القديم Psalms 95:6.
- الخطوةُ صفر (التعرية بصرف الفرع): جذر الفرع `b-r-k` كامل في المواضع 1-2-3. النواة السابقة `b-k` أخذت 1 و3 وأسقطت الراء الأصلية؛ رُدت.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `b-r-k ↔ ب-r-k`؛ لا حكم نووي صادر.
- مسحُ المعاني العربيّة: لسان العرب لابن منظور: «وهو من بَرَكَ البعير إذا أناخ في موضع فلزمه»؛ تاج العروس لمرتضى الزبيدي: «وَهُوَ من بَرَكَ البَعِيرُ: إِذا أَناخَ فِي مَوضِعٍ فلَزِمَه».
- المقابلُ من اللسان: `برك` في البروك والوقوع على الركبتين.
- مسارُ الصوت: الباء والراء والكاف محفوظة؛ لا صامت مسقط ولا صف جديد.
- المعنى من قاموس الفرع: `ברך` «kneeled» [Kaikki Hebrew].
- المدار: الركوع والبروك على الركبتين في الفعل العبري ومادة `برك`.
- المصفاة: لا مانح خارجي؛ البركة والدعاء لا يرثان حكم حركة الركبة.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: فعل الركوع وحده؛ لا وراثة لحس البركة أو لاسم الركبة.
- جسورُ الاسترداد المفحوصة: الجذر الكامل؛ الصوامت الثلاثة؛ المصدران العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-TRACE + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: فعل الركوع `ברך` وحده.
- إشعاع الأسرة في العربية: `برك` في إناخة البعير ولزومه وحده.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ نُسخت `بك` لإسقاطها الراء الأصلية.
- ملاحظات: السابق root=ROOT-TRACE وnucleus=NUCLEUS-TRACE؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

### بطاقة: `פתח`، العضو `kaikki_hebrew:2274:en-פתח-he-verb-HCS1YmVi`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `פתח` patákh، verb، «to open (something)» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: From Proto-Semitic *pataḥ- (“to open”). Cognate with Akkadian petûm and Arabic فَتَحَ (fataḥa).
- الخطوةُ صفر (التعرية بصرف الفرع): جذر الفرع `p-t-ḥ` كامل في 1-2-3. النواة السابقة `b-ḥ` أخذت 1 و3 بعد صف، وأسقطت التاء الأصلية؛ رُدت.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `p-t-ḥ ↔ f-t-ḥ`؛ لا حكم نووي صادر.
- مسحُ المعاني العربيّة: تاج العروس لمرتضى الزبيدي: «فَتَحَ البَابَ يَفْتَحُه فَتْحاً فانفتحَ: ضِدُّ أَغلقَ»؛ المحكم والمحيط الأعظم لابن سيده: «الفَتْحُ: نقيض الإغلاق. فتَحه يفْتَحه فَتْحا».
- المقابلُ من اللسان: `فتح` في فتح الباب ونقيض الإغلاق.
- مسارُ الصوت: المقابلة الجذرية الكاملة المنشورة؛ `p ↔ f` داخل الزوج المسمى، والتاء والحاء محفوظتان.
- المعنى من قاموس الفرع: `פתח` «to open (something)» [Kaikki Hebrew].
- المدار: إزالة الإغلاق عن الشيء في الطرفين من مادة `فتح` نفسها.
- المصفاة: التأثيل يصرح بالإرث؛ نواة `بح` مرفوضة أيضًا لأنها أخذت صورتها من `بوح` ومدارها من الفتح.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: فعل الفتح وحده؛ لا يرثه اسم الباحة أو مادة `بوح`.
- جسورُ الاسترداد المفحوصة: إعادة البناء؛ الجذر الكامل؛ المصدران العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-TRACE + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: الفعل `פתח` في إزالة الإغلاق وحده.
- إشعاع الأسرة في العربية: مادة `فتح` في نقيض الإغلاق وحده.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ نُسخت `بح` لإسقاط التاء وخلط مادة الصورة بمادة المعنى.
- ملاحظات: السابق root=ROOT-TRACE وnucleus=NUCLEUS-ECHO؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

### بطاقة: `קטל`، العضو `kaikki_hebrew:2377:en-קטל-he-verb-9W9eC7bx`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `קטל` katál، verb، «to kill, slay» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: From Proto-West Semitic *ḳatal- and therefore cognate with Arabic قَتَلَ (qatala) and Aramaic קְטַל (qəṭal).
- الخطوةُ صفر (التعرية بصرف الفرع): جذر الفرع `q-ṭ-l` كامل في 1-2-3. النواة السابقة `q-t` أخذت 1 و2 وأسقطت اللام الأصلية؛ رُدت.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `q-ṭ-l ↔ ق-t-l`؛ لا حكم نووي صادر.
- مسحُ المعاني العربيّة: لسان العرب لابن منظور: «قَتَله إِذا أَماته بضرْب أَو حجَر أَو سُمّ أَو علَّة»؛ تاج العروس لمرتضى الزبيدي: «أماتَه بضَربٍ أَو حجَرٍ أَو سَمٍّ أَو عِلّةٍ».
- المقابلُ من اللسان: `قتل` في الإماتة.
- مسارُ الصوت: الصوامت الثلاثة محفوظة؛ أثر الإطباق في الطاء منشور بعد القاف ولا يجيز إسقاط اللام.
- المعنى من قاموس الفرع: `קטל` «to kill, slay» [Kaikki Hebrew].
- المدار: إحداث الموت في الفعل العبري ومادة `قتل` العربية نفسها.
- المصفاة: التأثيل يصرح بالمقابل العربي؛ لا مانح خارجي ولا مادة ثانية.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: فعل القتل وحده؛ الاسم الاصطلاحي الصرفي لا يرث الحكم.
- جسورُ الاسترداد المفحوصة: إعادة البناء؛ الجذر الكامل؛ مسار الإطباق؛ المصدران العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-TRACE + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: فعل القتل والإماتة وحده.
- إشعاع الأسرة في العربية: مادة `قتل` في الإماتة وحدها.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ نُسخت `قت` لإسقاطها اللام الأصلية.
- ملاحظات: السابق root=ROOT-TRACE وnucleus=NUCLEUS-TRACE؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

<!-- HEBREW-REORDERED:SOUND-FULL-ROOT-DISCIPLINE-015:END -->
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
    missing = sorted(set(CHANGES) - set(indexed))
    if missing:
        raise RuntimeError(f"coverage members missing: {missing}")

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-sound-full-root-discipline-015"
    for member_id, layers in CHANGES.items():
        row = indexed[member_id]
        for layer, (outcome, issued, basis) in layers.items():
            target = row[f"{layer}_layer"]
            previous = str(target.get("outcome"))
            if previous != outcome:
                record = {
                    "schema": "lane-a-judgment-supersession-v1",
                    "date": DATE,
                    "member_id": member_id,
                    "layer": layer,
                    "previous_outcome": previous,
                    "new_outcome": outcome,
                    "reason": basis,
                    "evidence": evidence,
                }
                history = row.setdefault("judgment_supersessions", [])
                if not any(item.get("layer") == layer and item.get("evidence") == evidence for item in history):
                    history.append(record)
            target["outcome"] = outcome
            target["issued"] = issued
            target["basis"] = basis
            if layer == "nucleus":
                target.pop("selected", None)
        row["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
