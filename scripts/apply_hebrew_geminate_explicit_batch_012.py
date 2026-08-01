#!/usr/bin/env python3
"""Issue the next explicit-root Hebrew geminate judgments."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DATE = "2026-08-01"
BATCH = "hebrew-geminate-explicit-012"
MARKER = "<!-- HEBREW-REORDERED:GEMINATE-EXPLICIT-012:BEGIN -->"


def selected(nucleus: str, reading: str, root: str, rules: list[str]) -> dict[str, Any]:
    return {
        "nucleus": nucleus,
        "reading_ar": reading,
        "status": "licensed",
        "positions": ["1-2"],
        "rule_ids": rules,
        "route_required": False,
        "arabic_root_witness": root,
        "old_arabic_sources": ["لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"],
        "omitted_branch_consonant": "none",
        "omission_basis": "The third written consonant is gemination of the second radical, not a distinct omitted radical.",
    }


CHANGES = {
    "kaikki_hebrew:11635:en-קצץ-he-verb--rRikCwv": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل q-ṣ-ṣ يقابل قصص في القطع؛ الصاد الأخيرة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان q-ṣ كاملان؛ chop/dice يحقق القطع والتسوية والتتابع في مدار قص.", selected("قص", "نوع من القطع مع التسوية والتتابع الممتد", "قصص", [])),
    },
    "kaikki_hebrew:9265:en-מצץ-he-verb-2Bw5qSPa": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل m-ṣ-ṣ يقابل مصص في المص والامتصاص؛ الصاد الأخيرة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان m-ṣ كاملان؛ suck هو أخذ المائع بالجذب فيحقق مدار مص مباشرة.", selected("مص", "استخلاص الشيء أو أخذه", "مصص", [])),
    },
    "kaikki_hebrew:14281:en-גזז-he-verb-i94pkoPx": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل g-z-z يقابل جزز في جز الشعر والصوف عبر GUT-03؛ الزاي الأخيرة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان g-z كاملان عبر GUT-03؛ shear يحقق انفصال الشعر أو الصوف عن الكتلة في مدار جز.", selected("جز", "التميز والانفصال في الكتلة", "جزز", ["GUT-03"])),
    },
    "kaikki_hebrew:5602:en-מדד-he-verb--wsYticf": {
        "root": ("ROOT-ECHO", True, "جذر الفرع الكامل m-d-d من *mdd «stretch, spread, measure» ويقابل مدد؛ القياس صدى إجرائي لمد المعيار على المقيس.", None),
        "nucleus": ("NUCLEUS-ECHO", True, "الصامتان المتميزان m-d كاملان؛ القياس يعيّن امتداد الشيء وغايته، فهو صدى إجرائي لا معنى معجمي مطابق للفعل العربي مد.", selected("مد", "الامتداد والغاية", "مدد", [])),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:GEMINATE-EXPLICIT-012:BEGIN -->

## الجرد العبري المعاد ترتيبه — المضعّف ذو الشاهد العربي الصريح، الدفعة 012 (2026-08-01)

### بطاقة: `קצץ` «to chop, dice»، العضو `kaikki_hebrew:11635:en-קצץ-he-verb--rRikCwv`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يقارن العربية `قَصَّ` من `ق-ص-ص`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `קצץ` katsáts، verb، «to chop, to dice» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `q-ṣ-ṣ`؛ لا زوائد. الصامتان المتميزان `q-ṣ` في الموضعين 1 و2؛ الصاد في الموضع 3 تضعيف للثانية، لا أصل مختلف مسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `q-ṣ-ṣ ↔ ق-ص-ص`. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `قص` «نوع من القطع مع التسوية والتتابع الممتد».
- مسح العربيّة: لسان العرب لابن منظور: «قَصَّ النسّاجُ الثوبَ: قطَع هُدْبَه»؛ تاج العروس لمرتضى الزبيدي: «قَصَّ الشَّعْرَ والظُّفُرَ يَقُصُّهُما قَصّاً: قَطَعَ منهما بالمِقَصِّ».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الموضع 3 تضعيف الثاني، فلا حذف ولا صف إبدال.
- الجسر الدلالي الصريح: chop وdice كلاهما قطع للشيء إلى أجزاء متتابعة مستوية نسبيًا؛ وهذا تحقيق مباشر لمدار `قص` من مادة `قصص` نفسها.
- المصفاة الاتجاهية: مصدر العضو يقارن العربية ولا يسمي مانحًا؛ الحكم مستقل بمروحة المعجمين.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: اكتمل الجذر المضعّف والشاهد العربي والمدار، ولم يسقط صامت أصلي.

### بطاقة: `מצץ` «to suck»، العضو `kaikki_hebrew:9265:en-מצץ-he-verb-2Bw5qSPa`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يصرح بقرابته مع العربية `مَصَّ`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `מצץ` matsáts، verb، «to suck» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `m-ṣ-ṣ`؛ لا زوائد. الصامتان المتميزان `m-ṣ` في الموضعين 1 و2؛ الصاد الثالثة تضعيف للثانية.
- حكم طبقة الجذر: ROOT-TRACE؛ `m-ṣ-ṣ ↔ م-ص-ص`. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `مص` «استخلاص الشيء أو أخذه».
- مسح العربيّة: لسان العرب لابن منظور: «مَصِصْتُ الشيءَ، بالكسر، أَمَصُّه مَصّاً وامْتَصَصْتُه»؛ تاج العروس لمرتضى الزبيدي: «مَصِصْتُه ... مَصّاً ... شَرِبْتُهُ شُرْباً رَفِيقاً» و«المَصُّ: أَخْذُ المائِعِ القَلِيلِ بجَذْبِ النَّفَسِ».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الموضع 3 تضعيف الثاني.
- الجسر الدلالي الصريح: suck هو أخذ المائع واستخلاصه بالجذب، وهو نص `مصص` العربي نفسه؛ فتتحقق قراءة `مص` بلا استعارة مادة أخرى.
- المصفاة الاتجاهية: لا مانح مسمى؛ المقارنة المنشورة لم تُعامل حكمًا حتى استقل الشاهد العربي.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: تطابق الجذر الكامل والمعنى، والتضعيف لا يمثل إسقاطًا.

### بطاقة: `גזז` «to shear»، العضو `kaikki_hebrew:14281:en-גזז-he-verb-i94pkoPx`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `גזז` gazáz، verb، «to shear, to cut hair, wool» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `g-z-z`؛ لا زوائد. الصامتان المتميزان `g-z` في الموضعين 1 و2؛ الزاي الثالثة تضعيف للثانية.
- حكم طبقة الجذر: ROOT-TRACE؛ `g-z-z ↔ ج-z-z` عبر GUT-03. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `جز` «التميز والانفصال في الكتلة».
- مسح العربيّة: لسان العرب لابن منظور: «جَزَّ الصوفَ والشَّعْرَ والنَّخْلَ والحَشِيشَ يَجُزُّه جَزّاً» و«اجْتَزَّه: قَطَعَه»؛ تاج العروس لمرتضى الزبيدي: «الجَزُّ: جَزُّ الشَّعْرِ والصُّوفِ والحَشِيشِ ونحوِه».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2؛ GUT-03 يسوي `g ↔ ج`، والموضع 3 تضعيف الثاني.
- الجسر الدلالي الصريح: shear هو قطع الشعر أو الصوف وفصله عن الجسد، والعربية تسمي الفعل نفسه جزًّا؛ فيتحقق الانفصال في مدار `جز` من `جزز`.
- المصفاة الاتجاهية: لا مانح مسمى ولا وسم قرض؛ الشاهد العربي القديم مستقل.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: اكتملت المروحة والصوت والجسر من المادة نفسها.

### بطاقة: `מדד` «to measure»، العضو `kaikki_hebrew:5602:en-מדד-he-verb--wsYticf`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يعيد الفعل إلى Proto-Semitic `*mdd` «stretch, spread, measure» ويقارن العربية `مَدَّ`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `מדד` madád، verb، «to measure: to determine the size of» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `m-d-d`؛ لا زوائد. الصامتان المتميزان `m-d` في الموضعين 1 و2؛ الدال الثالثة تضعيف للثانية.
- حكم طبقة الجذر: ROOT-ECHO؛ `m-d-d ↔ م-d-d`، والقياس صدى إجرائي للمد. حكم طبقة النواة: NUCLEUS-ECHO؛ النواة `مد` «الامتداد والغاية».
- مسح العربيّة: لسان العرب لابن منظور: «مَدَّه يَمُدُّه مَدّاً، ومَدَّ به فامتَدَّ، ومَدَّدَه فَتَمَدَّد»؛ تاج العروس لمرتضى الزبيدي: «المَدَّةُ: الجَذْبُ والمَطْلُ والزِّيادَةُ» و«مَدَّه يَمُدُّه مَدّاً».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الموضع 3 تضعيف الثاني.
- الجسر الدلالي الصريح: القياس يمد معيارًا معلومًا على الشيء ليعيّن امتداده وغايته؛ لذلك العلاقة صدى إجرائي قريب من `مدد` لا تطابقًا معجميًا مباشرًا مع الفعل العربي.
- المصفاة الاتجاهية: الاستعادة سامية والمقارنة لا تسمي مانحًا؛ خُفض الحكم إلى ECHO حفظًا للفارق الدلالي.
- الحكم (استكشاف): ROOT-ECHO وNUCLEUS-ECHO.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-ECHO وNUCLEUS-ECHO؛ السبب: أثبت المصدر وحدة `*mdd`، وأثبتت المروحة جسر المد والقياس، مع حفظه صدى لا أثرًا مباشرًا.

<!-- HEBREW-REORDERED:GEMINATE-EXPLICIT-012:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-geminate-explicit-012"
    for member_id, layers in CHANGES.items():
        row = indexed[member_id]
        for layer, (outcome, issued, basis, chosen) in layers.items():
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
                if chosen is None:
                    target.pop("selected", None)
                else:
                    target["selected"] = chosen
        row["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
