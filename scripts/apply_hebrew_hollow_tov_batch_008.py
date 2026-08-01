#!/usr/bin/env python3
"""Re-read the five טוב member-senses in the hollow-first Hebrew order."""

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
BATCH = "hebrew-hollow-tov-008"
MARKER = "<!-- HEBREW-REORDERED:HOLLOW-TOV-008:BEGIN -->"


TOV_NUCLEUS: dict[str, Any] = {
    "nucleus": "طب",
    "reading_ar": "الجودة والإحكام والتغطية",
    "status": "licensed",
    "positions": ["1-3"],
    "rule_ids": ["GLD-01"],
    "route_required": False,
    "arabic_root_witness": "طيب",
    "old_arabic_sources": ["لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"],
    "omitted_branch_consonant": "none",
    "omission_basis": "The member source reconstructs Proto-Semitic *ṭāb- with two consonants; ו writes the long vowel /o/, not an original third root consonant.",
}


CHANGES = {
    "kaikki_hebrew:341:en-טוב-he-noun-tqyBORS9": {
        "root": ("ROOT-ECHO", True, "*ṭāb- وطيب صلة مصرح بها في الخير، لكن اختلاف بناء الضعيف يمنع TRACE جذريًا كاملًا.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "جذر الفرع التاريخي ثنائي الصامت ṭ-b؛ الجودة والخيرية تحقق مدار طب مباشرة بلا إسقاط صامت أصلي.", TOV_NUCLEUS),
    },
    "kaikki_hebrew:342:en-טוב-he-adj-GwpOY2mq": {
        "root": ("ROOT-ECHO", True, "*ṭāb- وطيب صلة مصرح بها في الجيد والحسن، مع اختلاف بناء الضعيف.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان ṭ-b كاملان في *ṭāb-، ومعنى good/fair/fine يحقق الجودة والإحكام في طب.", TOV_NUCLEUS),
    },
    "kaikki_hebrew:343:en-טוב-he-adv-WVrIndxm": {
        "root": ("ROOT-ECHO", True, "الظرف well/good من *ṭāb- المصرح بقرابته مع طيب؛ الصلة محفوظة بدرجة ECHO لا TRACE.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الاستعمال الظرفي فرع نحوي من صفة good؛ لم يصدر له حكم نووي مستقل كي لا تتكرر الأسرة آليًا.", None),
    },
    "kaikki_hebrew:344:en-טוב-he-intj-x9WrdUzF": {
        "root": ("ROOT-ECHO", True, "الاستعمال ok/right امتداد تداولي من good في العضو ذي التأثيل *ṭāb- ↔ طيب؛ لا TRACE كامل.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "الإقرار التداولي مشتق من good، ولا يكفي لإصدار نواة مستقلة أو توريث حكم الصفة.", None),
    },
    "kaikki_hebrew:345:en-טוב-he-noun-1rZjgL3x": {
        "root": ("OPEN-CANDIDATE", False, "المعنى goodness/virtue قريب، لكن العضو نفسه بلا تأثيل منشور؛ لا يرث حكم الأعضاء الأخرى." , None),
        "nucleus": ("OPEN-CANDIDATE", False, "غياب سند العضو يمنع توريث نواة طب من المتجانسات أو الحواس القريبة." , None),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:HOLLOW-TOV-008:BEGIN -->

## الجرد العبري المعاد ترتيبه — أسرة `טוב` الأجوفة (2026-08-01)

### بطاقة: `טוב` «goodness, fairness»، العضو `kaikki_hebrew:341:en-טוב-he-noun-tqyBORS9`
- أصل المرشح: جرد العبريّة بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح كلاين 1987 في مادة `טוב`: `ṭwb/ṭāb ↔ طاب`.
- كلمة الفرع: `טוב` tov، noun، «goodness, fairness» [Kaikki Hebrew]. مصدر العضو يعيده إلى `*ṭāb-` «good» ويصرح بقرابته مع العربية `طَيِّب`.
- جذر الفرع كاملًا بعد التحليل: `ṭ-b` ثنائي الصامت في `*ṭāb-`؛ الواو الكتابية حامل للصائت الطويل /o/، لا صامت جذر ثالث.
- الصامتان المأخوذان `ṭ-b` هما الموضعان الصامتيان 1 و2؛ وفي الرسم موضعا 1 و3 لأن الواو علة كتابية. لم يسقط صامت أصلي.
- حكم طبقة الجذر: ROOT-ECHO؛ `*ṭāb- ↔ ط-y-b` مع اختلاف بناء الضعيف. حكم طبقة النواة: NUCLEUS-TRACE؛ `طب` «الجودة والإحكام والتغطية».
- مسح العربية من مادة واحدة للصورة والمعنى، `طيب`: لسان العرب لابن منظور: «الطَّيِّبُ خلاف الخَبيث»؛ تاج العروس لمرتضى الزبيدي: «طَابَ: لذَّ وزَكَا» و«الطَّابُ: الطَّيِّبُ».
- مسار الصوت: في الرسم أُخذ الموضعان 1 و3؛ ما بينهما الواو علة كتابية للصائت /o/، ومصدر العضو يستعيد صامتين `*ṭ-b` لا ثلاثة.
- الجسر الدلالي الصريح: goodness وfairness هما تحقق الجودة والاستحسان والصلاح؛ وهذا هو حس `طيب` وخلاف الخبيث ومدار `طب` في الجودة والإحكام.
- إشعاع الأسرة: الحكم لهذا الاسم وحده؛ لم يرثه الظرف أو النداء أو الاسم غير المؤثل أدناه.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة كلاين ليست حكمًا، والمقابل العربي من المادة نفسها في الصورة والمعنى.
- الحكم (استكشاف): ROOT-ECHO وNUCLEUS-TRACE.
- سطر النسخ: السابق root=ROOT-TRACE وnucleus=OPEN-CANDIDATE؛ الجديد ROOT-ECHO وNUCLEUS-TRACE؛ السبب: خُفض الجذر لحفظ اختلاف الضعيف، وصدر اللب الثنائي لأن الواو ليست صامتًا أصليًا والمدار مباشر.

### بطاقة: `טוב` «good, fair, fine»، العضو `kaikki_hebrew:342:en-טוב-he-adj-GwpOY2mq`
- أصل المرشح: جرد العبريّة بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح كلاين 1987 في مادة `טוב`.
- كلمة الفرع: `טוב` tov، adj، «good, fair, fine» [Kaikki Hebrew]. مصدر العضو يعيده إلى `*ṭāb-` ويصرح بقرابته مع `طَيِّب`.
- جذر الفرع كاملًا `ṭ-b`؛ الواو علامة الصائت /o/ وليست ثالثًا. الصامتان المأخوذان هما كامل الجذر، ولم يسقط أصل.
- حكم طبقة الجذر: ROOT-ECHO لاختلاف بناء الضعيف. حكم طبقة النواة: NUCLEUS-TRACE؛ `طب` «الجودة والإحكام والتغطية».
- مسح العربية من مادة `طيب`: لسان العرب لابن منظور: «الطَّيِّبُ خلاف الخَبيث»؛ تاج العروس لمرتضى الزبيدي: «طَابَ: لذَّ وزَكَا» و«الطَّابُ: الطَّيِّبُ».
- مسار الصوت: في الرسم أُخذ الموضعان 1 و3؛ الواو علة كتابية، والمستعاد `*ṭ-b` ثنائي الصامت.
- الجسر الدلالي الصريح: الصفة good/fair/fine تصف الشيء بالجودة والاستحسان؛ فهي تحقق مدار `طب` نفسه بلا استعارة معنى من مادة أخرى.
- إشعاع الأسرة: هذا الحس الوصفي مقروء بذاته؛ لا توريث آلي لبقية الأعضاء.
- المصفاة الاتجاهية: لا قرض ولا مانح مسمى؛ كلاين أصل المرشح لا الحكم.
- الحكم (استكشاف): ROOT-ECHO وNUCLEUS-TRACE.
- سطر النسخ: السابق root=ROOT-ECHO وnucleus=OPEN-CANDIDATE؛ الجديد ROOT-ECHO وNUCLEUS-TRACE؛ السبب: ثبت أن الواو ليست ثالثًا أصليًا وأن الحس يحقق مدار الجودة مباشرة.

### بطاقة: `טוב` «well, good»، العضو `kaikki_hebrew:343:en-טוב-he-adv-WVrIndxm`
- أصل المرشح: جرد العبريّة بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح كلاين 1987 في مادة `טוב`.
- كلمة الفرع: `טוב` tov، adv، «well, good» [Kaikki Hebrew]؛ مصدر العضو يعيده إلى `*ṭāb-` ويقارنه بـ`طَيِّب`.
- جذر الفرع كاملًا `ṭ-b`؛ الواو علة كتابية لا صامت ثالث. لا زوج منتقى بإسقاط أصل.
- حكم طبقة الجذر: ROOT-ECHO؛ المادة الوصفية واحدة مع اختلاف الضعيف. حكم طبقة النواة: OPEN-CANDIDATE؛ لا يرث الظرف حكم الصفة.
- مسح العربية: لسان العرب لابن منظور: «الطَّيِّبُ خلاف الخَبيث»؛ تاج العروس لمرتضى الزبيدي: «طَابَ: لذَّ وزَكَا» و«الطَّابُ: الطَّيِّبُ».
- الجسر الدلالي الصريح: well هو وقوع الفعل على وجه جيد؛ يجاور `طيب` في الجودة، لكن التحويل النحوي إلى ظرف لا يصدر عضوًا نوويًا مستقلًا بلا شاهد خاص.
- المصفاة الاتجاهية: لا مانح مسمى؛ فُصل حكم العضو عن الصفة.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-ECHO؛ السبب: تأثيل العضو نفسه يصرح بالقرابة ومعناه يحقق الجودة. النواة بقيت مفتوحة منعًا للتوريث.

### بطاقة: `טוב` «ok, right»، العضو `kaikki_hebrew:344:en-טוב-he-intj-x9WrdUzF`
- أصل المرشح: جرد العبريّة بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح كلاين 1987 في مادة `טוב`.
- كلمة الفرع: `טוב` tov، interj، «ok, right» [Kaikki Hebrew]؛ مصدر العضو يعيده إلى `*ṭāb-` ويقارنه بـ`طَيِّب`.
- جذر الفرع كاملًا `ṭ-b`؛ الواو علة كتابية، ولا صامت أصلي مسقط.
- حكم طبقة الجذر: ROOT-ECHO للامتداد التداولي من «جيد». حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «الطَّيِّبُ خلاف الخَبيث»؛ تاج العروس لمرتضى الزبيدي: «طَابَ: لذَّ وزَكَا» و«الطَّابُ: الطَّيِّبُ».
- الجسر الدلالي الصريح: قول «حسن/جيد» يتحول تداوليًا إلى الإقرار «حسنًا/موافق»؛ هذا يفسر الصدى، لكنه لا يجعل أداة الخطاب شاهدًا نوويًا مستقلًا.
- المصفاة الاتجاهية: لا قرض؛ لم يرث النداء حكم الاسم أو الصفة.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE؛ الجديد ROOT-ECHO؛ السبب: تأثيل العضو نفسه ومعناه التداولي يثبتان الصدى. النواة بقيت مفتوحة.

### بطاقة: `טוב` «goodness, virtue»، العضو `kaikki_hebrew:345:en-טוב-he-noun-1rZjgL3x`
- أصل المرشح: جرد العبريّة بالأجوف أولًا؛ الرسم داخل صف كلاين، لكن هذا العضو نفسه لا يحمل تأثيلًا منشورًا في Kaikki.
- كلمة الفرع: `טוב` tuv، noun، «goodness, virtue» [Kaikki Hebrew]. جذر الفرع الظاهر بعد التحليل `ṭ-b` مع واو صائتية، لكن غاب سند العضو التاريخي المستقل.
- لا صامت أصلي مسقط، ولا زوج موجب صادر؛ التشابه مع الأعضاء الأربعة لا يرفع العضو بلا حقه في النقض.
- حكم طبقة الجذر: OPEN-CANDIDATE. حكم طبقة النواة: OPEN-CANDIDATE.
- الجسر الدلالي الصريح: الفضيلة من جنس الجودة، لكن صحة الجسر وحدها لا تعوض غياب مصدر العضو ولا ترخص توريث حكم بطاقة أخرى.
- المصفاة الاتجاهية: لا حكم قرض أو إرث من غياب التأثيل.
- الحكم محفوظ: OPEN-CANDIDATE في الطبقتين؛ لا سطر نسخ لأن الحكمين لم يتغيرا.

<!-- HEBREW-REORDERED:HOLLOW-TOV-008:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-hollow-tov-008"
    for member_id, layers in CHANGES.items():
        row = indexed[member_id]
        for layer, (outcome, issued, basis, selected) in layers.items():
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
                if selected is None:
                    target.pop("selected", None)
                else:
                    target["selected"] = dict(selected)
        row["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
