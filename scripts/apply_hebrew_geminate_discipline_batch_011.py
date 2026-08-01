#!/usr/bin/env python3
"""Re-audit inherited Hebrew geminates under the explicit nucleus discipline."""

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
BATCH = "hebrew-geminate-discipline-011"
MARKER = "<!-- HEBREW-REORDERED:GEMINATE-DISCIPLINE-011:BEGIN -->"


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
        "omission_basis": "The final written consonant repeats the second radical as gemination; no distinct radical is omitted.",
    }


CHANGES = {
    "kaikki_hebrew:710:en-עזז-he-verb-aZpQHPdF": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل ʕ-z-z يقابل عزز في القوة والتقوية؛ الزاي الثالثة تضعيف الثانية.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان ʕ-z كاملان؛ القوة تحقق مدار عز في التماسك والاشتداد، ولا صامت أصلي مسقط.", selected("عز", "تماسك الأثناء والاشتداد", "عزز", [])),
    },
    "kaikki_hebrew:1886:en-ענן-he-noun-VmgQELdT": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل ʕ-n-n يقابل عنن/عنان في اسم السحاب؛ النون الأخيرة تضعيف لا جذر ثالث مختلف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان ʕ-n كاملان؛ السحاب العربي عنان يحقق اعتراض الشيء وظهوره في الجو في مدار عن.", selected("عن", "اعتراض شيء أو ظهوره مع لطف قد يتمثل في الغموض", "عنن", [])),
    },
    "kaikki_hebrew:3186:en-גנן-he-verb-nPJEdrS-": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل g-n-n يقابل جنن في الستر والحماية عبر GUT-03؛ النون الثالثة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان g-n كاملان، ويسوي GUT-03 g↔ج؛ الحماية بالستر تحقق مدار جن مباشرة.", selected("جن", "الستر والكثافة", "جنن", ["GUT-03"])),
    },
    "kaikki_hebrew:9517:en-לבב-he-noun-zt-xvj90": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل l-b-b يقابل لبب في القلب واللب؛ الباء الثالثة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان المتميزان l-b كاملان؛ القلب واللب باطن الشيء ومركزه فيحققان مدار لب بلا إسقاط.", selected("لب", "اللزوم أي التلازم والتداخل", "لبب", [])),
    },
    "kaikki_hebrew:1545:en-חנן-he-verb-5yNhmldV": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل ḥ-n-n يقابل حنن في الرحمة والتعطف؛ النون الثالثة تضعيف.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت نواة حن: الرحمة تثبت الجذر الكامل، لكنها لا تحقق القراءة المجمدة «جوف الشيء القوي أو أثنائه»؛ والجسر القديم «الرقة النابعة من الداخل» مصنوع.", None),
    },
    "kaikki_hebrew:16206:en-שנן-he-verb-j1MXsU72": {
        "root": ("ROOT-TRACE", True, "جذر الفرع الكامل š-n-n تقابله مادة سنن العربية المصرح بها في مصدر العضو عبر SIB-01؛ النون الثالثة تضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "نُسخت نواة شن المصنوعة إلى سن: الصامتان المتميزان š-n كاملان، وSIB-01 يجيز š↔س، وسن السكين شحذه فيحقق الحدة والدقة مباشرة.", selected("سن", "الامتداد (أو النفاذ) مع حدة أو دقة", "سنن", ["SIB-01"])),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:GEMINATE-DISCIPLINE-011:BEGIN -->

## الجرد العبري المعاد ترتيبه — تدقيق موجبات المضعّف، الدفعة 011 (2026-08-01)

### بطاقة: `עזז` «to make strong»، العضو `kaikki_hebrew:710:en-עזז-he-verb-aZpQHPdF`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يقارن العربية `عَزَّ`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `עזז` azáz، verb، «to make strong» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `ʕ-z-z`؛ لا سابقة ولا لاحقة. الصامتان المتميزان `ʕ-z` في الموضعين 1 و2؛ الزاي في الموضع 3 تكرار صريح للثانية في الجذر المضعّف، لا صامت مختلف أُسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʕ-z-z ↔ ع-z-z`. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `عز` «تماسك الأثناء والاشتداد».
- مسح العربيّة: لسان العرب لابن منظور: «العِزُّ في الأَصل: القوة والشدة والغلبة»؛ تاج العروس لمرتضى الزبيدي: «عَزَزْتُ القومَ وأَعْزَزْتُهم وعَزَّزْتُهم: قَوَّيْتُهم وشدَّدْتُهم».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الثالث مضعّف الثاني، فلا حذف ولا صف إبدال.
- الجسر الدلالي الصريح: جعل الشيء قويًا هو نقله إلى الشدة والتماسك؛ فهذا تحقيق مباشر لمدار `عز` من مادة `عزز` نفسها.
- المصفاة الاتجاهية: مصدر العضو يعرض مقارنة عربية ولا يسمي مانحًا؛ لا تكفي المقارنة وحدها، وقد قام الحكم على مروحة `عزز` المستقلة.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: الحكم السابق باقٍ في الدرجتين؛ نُسخت بينته الناقصة ببينة تذكر الجذر الكامل والموضعين والتضعيف، من غير إسقاط صامت أصلي.

### بطاقة: `ענן` «cloud»، العضو `kaikki_hebrew:1886:en-ענן-he-noun-VmgQELdT`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يقارن الآرامية والعربية `عَنَان`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `ענן` ʿanán، noun، «cloud» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `ʕ-n-n`؛ لا زوائد. الصامتان المتميزان `ʕ-n` في الموضعين 1 و2؛ النون الثالثة تضعيف للثانية، لا أصل مختلف مسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʕ-n-n ↔ ع-n-n`. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `عن` «اعتراض شيء أو ظهوره مع لطف قد يتمثل في الغموض».
- مسح العربيّة: لسان العرب لابن منظور: «العانَّة والعَنَانةُ: السَّحابة، وجمعها عَنانٌ»؛ تاج العروس لمرتضى الزبيدي: «العَنانُ، كسَحابٍ: السَّحابُ».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الموضع 3 تضعيف للثاني لا حذفًا.
- الجسر الدلالي الصريح: السحاب المعترض الظاهر في صفحة السماء هو `عنان` في العربية وهو معنى الفرع نفسه؛ فيحقق الاعتراض والظهور في مدار `عن` من المادة نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ ذكر الآرامية أختًا لا يصنع الحكم، والشاهد العربي المستقل هو الحاكم.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: الحكم السابق باقٍ؛ نُسخت بينة المواضع `1-2,1-3` ببينة أدق: الزوج المتميز واحد في 1 و2، والثالث تضعيف الثاني.

### بطاقة: `גנן` «to protect, defend»، العضو `kaikki_hebrew:3186:en-גנן-he-verb-nPJEdrS-`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو نفسه يقارن العربية `جَنَّ` «ستر»، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `גנן` ganán، verb، «to protect, to defend» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `g-n-n`؛ لا زوائد. الصامتان المتميزان `g-n` في الموضعين 1 و2؛ النون الثالثة تضعيف للثانية.
- حكم طبقة الجذر: ROOT-TRACE؛ `g-n-n ↔ ج-n-n` عبر GUT-03. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `جن` «الستر والكثافة».
- مسح العربيّة: لسان العرب لابن منظور: «جَنَّ الشيءَ يَجُنُّه جَنّاً: سَتَره»؛ تاج العروس لمرتضى الزبيدي: «جَنَّ الشيءَ يَجُنُّه جَنّاً: سَتَره».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2؛ GUT-03 يسوي `g ↔ ج`، والموضع 3 تضعيف للثاني.
- الجسر الدلالي الصريح: حماية الشيء منع وصول الأذى إليه، والعربية تسمي هذا الفعل سترًا وتسمّي ما يستر ويقي جُنّة؛ فهذا تحقيق مباشر لمدار `جن` من `جنن`.
- المصفاة الاتجاهية: لا مانح مسمى؛ المقارنة المنشورة قُرئت ثم اختُبرت بالمادة العربية المستقلة.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: الحكم السابق باقٍ؛ أضيف GUT-03 الذي أغفلته البيانات القديمة، ونُسخت بينة المواضع لتصرح بأن الثالث تضعيف لا صامت ساقط.

### بطاقة: `לבב` «heart»، العضو `kaikki_hebrew:9517:en-לבב-he-noun-zt-xvj90`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يعيد الاسم إلى الجذر `l-b-b` وإلى *libb-، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `לבב` leváv، noun، «a heart» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `l-b-b`؛ الصامتان المتميزان `l-b` في الموضعين 1 و2؛ الباء الثالثة تضعيف للثانية، لا أصل محذوف.
- حكم طبقة الجذر: ROOT-TRACE؛ `l-b-b ↔ ل-b-b`. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `لب` «اللزوم أي التلازم والتداخل».
- مسح العربيّة: لسان العرب لابن منظور: «اللُّبُّ: خالِصُ كلِّ شيء وخِيارُه»؛ تاج العروس لمرتضى الزبيدي: «اللُّبُّ: خالِصُ كلِّ شيء كاللُّباب» و«لُبُّ النخلة: قلبُها».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2 بهوية الصوت؛ الموضع 3 تضعيف للثاني.
- الجسر الدلالي الصريح: القلب هو الباطن المركزي في الجسد، واللب خالص الشيء وباطنه وقلبه؛ فيتحقق التداخل واللزوم المركزي في مدار `لب` من مادة `لبب` نفسها.
- المصفاة الاتجاهية: المصدر يعرض استعادة سامية ولا مانحًا؛ الشاهد العربي القديم مستقل.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: الحكم السابق باقٍ؛ نُسخت بينة المواضع القديمة ببينة الجذر الكامل والتضعيف، وقُيّد الجسر بلفظ المعجم لا باستعارة معنى خارجي.

### بطاقة: `חנן` «to pardon»، العضو `kaikki_hebrew:1545:en-חנן-he-verb-5yNhmldV`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يقارن العربية `ح-ن-ن`، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `חנן` khanán، verb، «to pardon, grant amnesty» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `ḥ-n-n`؛ الصامتان المتميزان `ḥ-n` في الموضعين 1 و2؛ النون الثالثة تضعيف الثانية.
- حكم طبقة الجذر: ROOT-TRACE؛ `ḥ-n-n ↔ ح-n-n` في الرحمة والتعطف المؤديين إلى العفو. حكم طبقة النواة: OPEN-CANDIDATE؛ لا موجب صادر.
- مسح العربيّة: لسان العرب لابن منظور: «الحَنَّانُ ... ذو الرَّحمة والتعطُّف»؛ تاج العروس لمرتضى الزبيدي: «الحَنَّان الرَّحِيمُ مِنَ الحَنانِ، وَهُوَ الرَّحْمةُ».
- مسار الصوت: الجذر الكامل متطابق؛ فحص النواة تناول الصامتين في الموضعين 1 و2، والثالث تضعيف، لكن تمام الصورة لا يكفي دون مدار دلالي.
- الجسر الدلالي الصريح للجذر: العفو فعل ناشئ عن الرحمة والتعطف، ولذلك تثبت `حنن` كاملة. أمّا القراءة المجمدة للنواة `حن` فهي «جوف الشيء القوي أو أثنائه»، ولا تصل الرحمة بهذا المدار جملة معجمية واحدة.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة مصدر العضو على المقارنة الجذرية لا تمنح النواة حكمًا.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق NUCLEUS-ECHO بـ`حن`؛ الجديد OPEN-CANDIDATE؛ السبب: الجسر «الرقة النابعة من الداخل» مصنوع ولا تحقق الرحمة القراءة المجمدة للنواة. حكم الجذر السابق باقٍ.

### بطاقة: `שנן` «to sharpen»، العضو `kaikki_hebrew:16206:en-שנן-he-verb-j1MXsU72`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ مصدر العضو يقارن الآرامية ويصرح بالعربية `سَنَّ` «to sharpen»، وليس من صفّ طابور المسار 2.
- كلمة الفرع: `שנן` shanán، verb، «to be sharp, to sharpen, whet» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `š-n-n`؛ الصامتان المتميزان `š-n` في الموضعين 1 و2؛ النون الثالثة تضعيف الثانية.
- حكم طبقة الجذر: ROOT-TRACE؛ `š-n-n ↔ س-n-n` عبر SIB-01. حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `سن` «الامتداد أو النفاذ مع حدة أو دقة».
- مسح العربيّة: لسان العرب لابن منظور: «سَنَّ السِّكِّينَ يَسُنُّها سَنّاً»؛ تاج العروس لمرتضى الزبيدي: «سَنَّ السِّكِّينَ يَسُنُّه سَنّاً، فهو مَسْنُونٌ وسَنينٌ».
- مسار الصوت: أُخذ الصامتان في الموضعين 1 و2؛ SIB-01 يسوي `š ↔ س` في المقارنة المنشورة، والموضع 3 تضعيف للثاني.
- الجسر الدلالي الصريح: شحذ السكين إكساب حدها دقةً وقدرةً على النفاذ؛ فهذا يحقق الحدة والدقة في مدار `سن` من مادة `سنن` نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ الآرامية المذكورة أخت لا دليل كافٍ، والشاهد العربي المستقل يطابق الفعل.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق NUCLEUS-ECHO بـ`شن` وشاهد `شنن`؛ الجديد NUCLEUS-TRACE بـ`سن` وشاهد `سنن` عبر SIB-01؛ السبب: المصدر نفسه يصرح بـ`سَنَّ`، والجسر القديم من «برادة الشحذ» مصنوع من مادة أخرى. حكم الجذر باقٍ مع تصحيح مادته الصريحة.

<!-- HEBREW-REORDERED:GEMINATE-DISCIPLINE-011:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-geminate-discipline-011"
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
