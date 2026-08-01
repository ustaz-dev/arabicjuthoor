#!/usr/bin/env python3
"""Read three common Hebrew hollow roots before descending to nuclei."""

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
BATCH = "hebrew-hollow-full-roots-009"
MARKER = "<!-- HEBREW-REORDERED:HOLLOW-FULL-ROOTS-009:BEGIN -->"


CHANGES = {
    "kaikki_hebrew:1000:en-עין-he-noun-hJ~EkWC-": {
        "root": ("ROOT-TRACE", True, "עין وعيْن الماء تطابقان ʕ-y-n كاملًا في النبع والعين الجارية."),
        "nucleus": ("OPEN-CANDIDATE", False, "الياء أصل في *ʕayn-؛ لا تسقط إلى عن، ومدار عن المجمد لا يسمي النبع."),
    },
    "kaikki_hebrew:370:en-בית-he-noun-1uIShmIa": {
        "root": ("ROOT-TRACE", True, "בית وبيت تطابقان b-y-t كاملًا في المسكن."),
        "nucleus": ("OPEN-CANDIDATE", False, "الياء أصل في *bayt-؛ لا تسقط إلى بت، ومدار القطع والانفصال لا يحمل البيت."),
    },
    "kaikki_hebrew:1574:en-דין-he-noun-Cuqm2RNC": {
        "root": ("ROOT-TRACE", True, "דין ودين تطابقان d-y-n كاملًا في الحكم والقضاء والجزاء الملزم."),
        "nucleus": ("OPEN-CANDIDATE", False, "الياء أصل في الجذر؛ لا تسقط إلى دن، ومدار الاندساس والثبات لا يحمل الحكم أو القانون."),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:HOLLOW-FULL-ROOTS-009:BEGIN -->

## الجرد العبري المعاد ترتيبه — الأجوف ذو الجذر الكامل (2026-08-01)

### بطاقة: `עין` «spring, fountain»، العضو `kaikki_hebrew:1000:en-עין-he-noun-hJ~EkWC-`
- أصل المرشح: الجرد العبري بالأجوف أولًا؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `עין` áyin، noun، «spring, fountain» [Kaikki Hebrew]. مصدر العضو يعيدها إلى `*ʕayn-`.
- جذر الفرع بصوامته كاملة `ʕ-y-n`؛ لا سابقة ولا لاحقة. أي زوج `ʕ-n` يأخذ الموضعين 1 و3 ويسقط الياء الأصلية في الموضع 2، وهذا ممنوع.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʕ-y-n ↔ ع-y-n`. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `عن`.
- مسح العربية: لسان العرب لابن منظور: «العَيْنُ: يَنْبُوعُ الماءِ الذي يَنْبُعُ من الأَرض ويَجْري»؛ تاج العروس لمرتضى الزبيدي: «العَيْنُ: يَنْبُوعُ الماءِ الذي يَنْبُعُ من الأَرْض ويَجْرِي».
- الجسر الدلالي الصريح: الينبوع الخارج من الأرض والجاري بالماء هو معنى `עין` المنشور نفسه؛ الصورة والمعنى من `عين` كاملة.
- المصفاة الاتجاهية: لا مانح مسمى؛ الأصل السامي المنشور لا يحول الأجوف إلى نواة.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: اكتملت مروحة `عين`، وحُفظت الياء الأصلية بدل إسقاطها.

### بطاقة: `בית` «house»، العضو `kaikki_hebrew:370:en-בית-he-noun-1uIShmIa`
- أصل المرشح: الجرد العبري بالأجوف أولًا؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `בית` báyit، noun، «house» [Kaikki Hebrew]. مصدر العضو يعيدها إلى `*bayt-` ويصرح بقرابتها مع العربية `بَيْت`.
- جذر الفرع كاملًا `b-y-t`؛ لا زيادة صرفية. اختيار `b-t` من الموضعين 1 و3 يسقط الياء الأصلية في الموضع 2، فلا يصدر.
- حكم طبقة الجذر: ROOT-TRACE؛ `b-y-t ↔ ب-y-t`. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `بت`.
- مسح العربية: كتاب العين للخليل بن أحمد: «البَيْتُ سَقْفُكَ الذي تَبيتُ فيه»؛ تاج اللغة وصحاح العربية للجوهري: «البَيْتُ معروفٌ، والجمع أَبْياتٌ وبُيوتٌ».
- الجسر الدلالي الصريح: المسكن المسقوف الذي يبيت فيه الإنسان هو house في الفرع؛ التطابق للمادة `بيت` كلها.
- المصفاة الاتجاهية: لا مانح مسمى؛ المقابلة موروثة، ومدار `بت` في القطع والانفصال لا يحمل المسكن.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: اكتملت مروحة `بيت`، وبقيت الياء صامتًا أصليًا.

### بطاقة: `דין` «judgement; law»، العضو `kaikki_hebrew:1574:en-דין-he-noun-Cuqm2RNC`
- أصل المرشح: الجرد العبري بالأجوف أولًا؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `דין` din، noun، «judgement; law» [Kaikki Hebrew]. مصدر العضو يصرح بقرابته مع العربية `دِين`.
- جذر الفرع كاملًا `d-y-n`؛ لا زيادة صرفية. اختيار `d-n` من الموضعين 1 و3 يسقط الياء الأصلية، فلا يصدر.
- حكم طبقة الجذر: ROOT-TRACE؛ `d-y-n ↔ د-y-n`. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `دن`.
- مسح العربية: لسان العرب لابن منظور: «الدِّينُ: الجزاءُ والمكافأَةُ» و«الدَّيَّانُ: القاضي»؛ تاج العروس لمرتضى الزبيدي: «الدِّينُ: الجَزاءُ» و«الدَّيَّانُ: القاضِي».
- الجسر الدلالي الصريح: الحكم والقانون في الفرع يلتقيان العربية في القضاء والجزاء الملزم؛ الصورة والمعنى من `دين` نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ لم يؤخذ معنى من `حكم` وصورة من `دين`، بل الشاهدان داخل مادة `دين`.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: عُزل اسم الحكم عن صوره الأخرى، وقُرئ الجذر الأجوف كاملًا مع حفظ الياء.

<!-- HEBREW-REORDERED:HOLLOW-FULL-ROOTS-009:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-hollow-full-roots-009"
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
