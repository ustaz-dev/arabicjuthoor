#!/usr/bin/env python3
"""Read final-weak Hebrew roots at the full-root layer before any nucleus."""

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
BATCH = "hebrew-weak-full-roots-014"
MARKER = "<!-- HEBREW-REORDERED:WEAK-FULL-ROOTS-014:BEGIN -->"


CHANGES = {
    "kaikki_hebrew:656:en-בנה-he-verb-2PtFP41d": {
        "root": ("ROOT-TRACE", True, "*b-n-y يقابل ب-ن-ي كاملًا في البناء؛ الياء أصل في *banay- ولا تسقط إلى بن."),
        "nucleus": ("OPEN-CANDIDATE", False, "الجذر الثلاثي *b-n-y متاح ومصرح به؛ نُقض تجاوزُه إلى نواة بن."),
    },
    "kaikki_hebrew:4719:en-קנה-he-verb-gpJd3tGU": {
        "root": ("ROOT-ECHO", True, "q-n-h يقابل ق-n-y في الاكتساب والاقتناء؛ اختلاف الضعيف الثالث يمنع TRACE ولا يمنع الصدى الجذري الكامل."),
        "nucleus": ("OPEN-CANDIDATE", False, "المقارنة الثلاثية q-n-h ↔ q-n-y متاحة؛ لا تُسقط الهاء والياء لإصدار قن."),
    },
    "kaikki_hebrew:5998:en-בכה-he-verb-wRoM3Ceh": {
        "root": ("ROOT-ECHO", True, "المصدر يقارن بכה مباشرة ببكى في البكاء؛ حفظ الضعيف الثالث يجعلها مقارنة جذرية كاملة من رتبة ECHO."),
        "nucleus": ("OPEN-CANDIDATE", False, "لا تُختزل المقارنة b-k-y إلى b-k ما دام الضعيف الثالث ظاهرًا في المقارنة المنشورة."),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:WEAK-FULL-ROOTS-014:BEGIN -->

## الجرد العبري المعاد ترتيبه — سائر المعتل بعد الأجوف والمضعّف (2026-08-01)

### بطاقة: `בנה`، العضو `kaikki_hebrew:656:en-בנה-he-verb-2PtFP41d`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `בנה` baná، verb، «to build, to construct, to raise, to erect (a building, structure, or the like)» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: From Proto-Semitic *banay- (“to build”). Cognate with Arabic بَنَى (banā), Akkadian 𒆕 (banûm), Aramaic בְּנָא (bənā), Ugaritic 𐎁𐎐𐎊 (bny).
- الخطوةُ صفر (التعرية بصرف الفرع): جذر الفرع بصوامته التاريخية كاملة `b-n-y`؛ الصوامت 1-2-3 مستعملة. الياء أصل منصوص في `*banay-`، فلا تسقط لإصدار `b-n`.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `*b-n-y ↔ ب-n-y`؛ النواة مفحوصة استقلالًا ولم تصدر.
- مسحُ المعاني العربيّة: لسان العرب لابن منظور: «نما قضى أنه من الياء لأن بنى يبني أكثر في كلامهم من يبنو»؛ المحكم والمحيط الأعظم لابن سيده: «البني نقيض الهدم بناه بنيا وبناء وبنيانا وبنية وبناية وابتناه وبناه».
- المقابلُ من اللسان: `بنى` من مادة `بني` في البناء نفسه.
- مسارُ الصوت: الباء والنون والياء محفوظة صامتًا صامتًا في إعادة البناء والمقابل العربي؛ لا صف جديد.
- المعنى من قاموس الفرع: `בנה` «to build, to construct, to raise, to erect» [Kaikki Hebrew].
- المدار: البناء والإنشاء في العضو العبري وفي مادة `بني` العربية نفسها.
- المصفاة: نص التأثيل يصرح بالإرث السامي وبالمقابل العربي؛ لا مانح خارجي ولا مادة ثانية للمعنى.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: الحكم لهذا الفعل وحده؛ لا ترثه صور الأمر والمستقبل أو متجانس `בן`.
- جسورُ الاسترداد المفحوصة: إعادة البناء؛ الجذر الكامل؛ النصان العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-TRACE + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: الفعل `בנה` في حس البناء وحده؛ لا وراثة للصيغ.
- إشعاع الأسرة في العربية: مادة `بني` في حس البناء ونقيض الهدم وحده.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE؛ نُسخ NUCLEUS-TRACE لأن الثلاثي `b-n-y` متاح.
- ملاحظات: السابق root=ROOT-TRACE وnucleus=NUCLEUS-TRACE؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

### بطاقة: `קנה`، العضو `kaikki_hebrew:4719:en-קנה-he-verb-gpJd3tGU`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `קנה` kaná، verb، «to buy, to purchase» [Kaikki Hebrew]؛ مدخل الجذر `ק־נ־ה` «Forming words pertaining to buying».
- أقدمُ صورةٍ مستعادة: Cognate with Aramaic קְנָא (“to acquire”); سطح الجذر العبري `q-n-h` محفوظ كاملًا.
- الخطوةُ صفر (التعرية بصرف الفرع): صوامت الفرع `q-n-h` في المواضع 1-2-3؛ المقابل العربي `q-n-y`. لم يؤخذ زوج، ولم تسقط الهاء أو الياء الضعيفة.
- درجةُ المقارنة: الجذر الكامل أولًا؛ `q-n-h ↔ q-n-y` صدى كامل باختلاف الضعيف الثالث؛ النواة غير صادرة.
- مسحُ المعاني العربيّة: تاج العروس لمرتضى الزبيدي: «القنية بالكسر، والضم: ما اكتسب»؛ المحكم والمحيط الأعظم لابن سيده: «القنية: ما اكتسب. والجمع: قنى. وقد قنى المال قنيا».
- المقابلُ من اللسان: `قني` في الاكتساب والاقتناء.
- مسارُ الصوت: القاف والنون هويتان، والهاء العبرية والياء العربية ضعيفان مختلفان؛ لذلك ROOT-ECHO لا TRACE.
- المعنى من قاموس الفرع: `קנה` «to buy, to purchase» [Kaikki Hebrew].
- المدار: الاكتساب والاتخاذ في الكلمة العبرية ومادة `قني` نفسها.
- المصفاة: لا وسم قرض أو مانح؛ اختلاف الضعيف محفوظ ولا يتحول إلى حذف نووي.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: الفعل المقصود وحده؛ اسم العصا `קנה` لا يرث الحكم.
- جسورُ الاسترداد المفحوصة: الجذر الكامل؛ اختلاف الضعيف؛ النصان العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-ECHO + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: الفعل `קנה` في الشراء وحده.
- إشعاع الأسرة في العربية: مادة `قني` في الاكتساب وحده.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE؛ نُسخ NUCLEUS-TRACE لأن المقارنة الثلاثية متاحة.
- ملاحظات: السابق root=OPEN-CANDIDATE وnucleus=NUCLEUS-TRACE؛ الجديد ROOT-ECHO وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

### بطاقة: `בכה`، العضو `kaikki_hebrew:5998:en-בכה-he-verb-wRoM3Ceh`
- إصدارُ البروتوكول: RECOVERY-v2 (2026-08-01).
- الكلمةُ في الفرع: `בכה` bakhá، verb، «To cry, weep» [Kaikki Hebrew].
- أقدمُ صورةٍ مستعادة: Compare Aramaic ܒܵܟ݂ܹܐ (bāḳē), Arabic بَكَى (bakā), Ge'ez በከየ (bäkäyä), Maltese beka, Akkadian 𒁀𒆪𒌑𒌝 (bakûm).
- الخطوةُ صفر (التعرية بصرف الفرع): المقارنة المنشورة تحفظ `b-k-y` في العربية والجعزية قبالة الفعل العبري النهائي الضعيف؛ استُعملت الصوامت الثلاثة ولم يُنتق `b-k`.
- درجةُ المقارنة: الجذر الكامل أولًا؛ المقارنة الثلاثية النهائية الضعيفة ROOT-ECHO؛ النواة غير صادرة.
- مسحُ المعاني العربيّة: تاج العروس لمرتضى الزبيدي: «بكى الرجل يبكي بكاء وبكى»؛ المحكم والمحيط الأعظم لابن سيده: «بكى بكاء، وبكى. قال الخليل: من قصره ذهب به إلى معنى الحزن».
- المقابلُ من اللسان: `بكى` من مادة `بكي` في البكاء والحزن وإسالة الدمع.
- مسارُ الصوت: الباء والكاف محفوظتان، والضعيف الثالث محفوظ في المقارنة المنشورة؛ لا إسقاط لإصدار نواة.
- المعنى من قاموس الفرع: `בכה` «To cry, weep» [Kaikki Hebrew].
- المدار: البكاء نفسه في الفعل العبري ومادة `بكي` العربية.
- المصفاة: النص يقارن العربية ولا يسمي مانحًا؛ الصورة والمعنى من مادة `بكي` نفسها.
- مؤشر اليتم: غير حاسم؛ لا يرفع اليتم درجة الحكم.
- فصلُ المتجانسات والاقتراض: الفعل المعجمي وحده؛ الرسم الناقص التابع لا يرث الحكم.
- جسورُ الاسترداد المفحوصة: المقارنة المنشورة؛ الصوامت الثلاثة؛ النصان العربيان؛ المدار؛ القرض؛ المتجانس؛ النواة.
- حالةُ الإغلاق: ROOT-ECHO + OPEN-CANDIDATE.
- إشعاع الأسرة في الفرع: الفعل `בכה` في البكاء وحده.
- إشعاع الأسرة في العربية: مادة `بكي` في البكاء وحده.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE؛ لا يُتجاوز الضعيف الثالث إلى `b-k`.
- ملاحظات: السابق root=OPEN-CANDIDATE وnucleus=AUTHOR-RESERVED-SOUND-GAP؛ الجديد ROOT-ECHO وOPEN-CANDIDATE؛ لا تغيير لخط البرهان.

<!-- HEBREW-REORDERED:WEAK-FULL-ROOTS-014:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-weak-full-roots-014"
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
