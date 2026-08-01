#!/usr/bin/env python3
"""Start the reordered Hebrew inventory with three explicit hollow stems."""

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
BATCH = "hebrew-hollow-first-007"
MARKER = "<!-- HEBREW-REORDERED:HOLLOW-FIRST-007:BEGIN -->"


CHANGES = {
    "kaikki_hebrew:8195:en-נם-he-verb-RNXsstRu": {
        "root": ("ROOT-TRACE", True, "نָם هو انعكاس الفعل الأجوف n-w-m ويقابل ن-و-م في النوم مباشرة."),
        "nucleus": ("OPEN-CANDIDATE", False, "النواة نم في الفهرس تعني الانتشار اللطيف من الباطن، لا النوم؛ ولا يستعاض عن فشل المدار بالتطابق المعجمي لنوم."),
    },
    "kaikki_hebrew:3513:en-קול-he-noun-cRBjQzvm": {
        "root": ("ROOT-ECHO", True, "q-w-l يقابل قول كاملًا، والصوت هو التحقيق المسموع للقول؛ مصدر العضو نفسه يقول related لا cognate مباشرًا."),
        "nucleus": ("OPEN-CANDIDATE", False, "اختيار q-l يسقط الواو الأصلية، ومدار قل في الرفع لا يدل على الصوت أو القول."),
    },
    "kaikki_hebrew:3268:en-עוף-he-noun-deLfqPu0": {
        "root": ("ROOT-TRACE", True, "ʕ-w-p يقابل ع-و-ف كاملًا في اسم الطائر مع p/f المرخص، وشاهد عوف العربي يسمي الديك والطير."),
        "nucleus": ("OPEN-CANDIDATE", False, "اختيار ʕ-p من الموضعين 1 و3 يسقط الواو الأصلية، ومدار عف المجمد لا يدل على الطير."),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:HOLLOW-FIRST-007:BEGIN -->

## الجرد العبري المعاد ترتيبه — الأجوف أولًا، الدفعة 007 (2026-08-01)

### بطاقة: `נם`، العضو `kaikki_hebrew:8195:en-נם-he-verb-RNXsstRu`
- أصل المرشح: جرد العبريّة المعاد ترتيبه بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح ميليتاريف `SEM 1218` وكلاين 1987 في مادة `ישׁן`: `nwm נום ↔ نام`.
- كلمة الفرع: `נם` nám، verb، «to slumber» [Kaikki Hebrew]. مصدر العضو يقارنه صراحة بالآرامية `נָם` والعربية `نَامَ`.
- جذر الفرع بصوامته كاملة بعد استعادة الأجوف: `n-w-m`؛ الواو عين الفعل في المقارنة `نوم`، لا سابقة ولا لاحقة.
- الزوج الذي حكمت به البطاقة القديمة `n-m` من الموضعين الجذريين 1 و3؛ الواو في الموضع 2 أصل في الجذر الأجوف. وحتى مع اقتراح الثنائية الخارجي لا تصدر النواة إذا أخفق مدارها.
- حكم طبقة الجذر: ROOT-TRACE؛ `n-w-m ↔ ن-w-m`. حكم طبقة النواة: OPEN-CANDIDATE؛ أُبطلت `نم`.
- مسح العربية: لسان العرب لابن منظور: «النوم: معروف» و«نام ينام نوماً ونياماً»؛ تاج العروس لمرتضى الزبيدي: «النوم معروف» و«النعاس».
- الجسر الدلالي الصريح: السبات أو النعاس في الفرع هو النوم نفسه في العربية؛ هذا جسر `نوم` الكامل. أما `نم` «انتشار من باطن الشيء إلى ظاهره مع لطف» فلا يصل الطرفين.
- المصفاة الاتجاهية: لا مانح مسمى؛ اقتراح ميليتاريف وكلاين نَسَب للمرشح لا بدل من اختبار المدار.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق root=OPEN-CANDIDATE وnucleus=NUCLEUS-TRACE (`نم`)؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: استُعيد الجذر الأجوف الكامل، ونقض اختلاف المدار الحكم النووي القديم.

### بطاقة: `קול`، العضو `kaikki_hebrew:3513:en-קול-he-noun-cRBjQzvm`
- أصل المرشح: جرد العبريّة المعاد ترتيبه بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح ميليتاريف `SEM 594`: `qōl קול ↔ قول`.
- كلمة الفرع: `קול` kol، noun، «voice; statement, opinion, or order» [Kaikki Hebrew]. مصدر العضو يسمي صلته بالعربية `قَوْل` ويستعيد الهيكل `q-w-l`.
- جذر الفرع كاملًا `q-w-l`؛ لا زيادة صرفية. الزوج الخارجي `q-l` من الموضعين 1 و3 يسقط الواو في الموضع 2، ولا حاشية جازمة كتلك التي في `קום` تسميها توسعة ثانوية.
- حكم طبقة الجذر: ROOT-ECHO؛ الصورة كاملة، لكن المصدر يقول `related to Arabic qawl` والانزياح من القول إلى الصوت يحتاج حفظ درجة الصدى. حكم طبقة النواة: OPEN-CANDIDATE.
- مسح العربية: لسان العرب لابن منظور: «القَوْلُ: الكلامُ على الترتيب»؛ تاج العروس لمرتضى الزبيدي: «القَوْلُ: الكلامُ» و«كلُّ لفظٍ قال به اللسان».
- الجسر الدلالي الصريح: الصوت هو الوعاء المسموع الذي يخرج به القول، ومنه انتقال الاسم من حدث الكلام إلى صوته أو أمره؛ هذا جسر واحد محدد لا جمع لمعانٍ متباعدة.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة ميليتاريف ليست حكمًا، وصيغة مصدر العضو تمنع رفع ECHO إلى TRACE.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد ROOT-ECHO وOPEN-CANDIDATE؛ السبب: الهيكل `q-w-l` منشور كاملًا، ثم رُفض إسقاط الواو ومدار `قل` المخالف.

### بطاقة: `עוף`، العضو `kaikki_hebrew:3268:en-עוף-he-noun-deLfqPu0`
- أصل المرشح: جرد العبريّة المعاد ترتيبه بالأجوف أولًا؛ ويتقاطع مع المسار 2، اقتراح ميليتاريف `SEM 2347`: `ʕōp עוף ↔ عوف`، مع تنبيهه إلى أن المقابل العربي مهمل شبه تمام في الأدبيات.
- كلمة الفرع: `עוף` of، noun، «bird» [Kaikki Hebrew]. مصدر العضو يقارن الجعزية `ʿof`؛ وصف المسار الثاني يضيف العربية `عوف`.
- جذر الفرع كاملًا `ʕ-w-p`؛ لا زيادة صرفية. المقابل العربي الكامل `ʕ-w-f` يحفظ الواو، و`p/f` على `LAB-02`.
- الزوج المقترح `ʕ-p` من الموضعين 1 و3؛ الواو في الموضع 2 أصل في المقابلة الكاملة، فلا تسقط ما دام `عوف` متاحًا.
- حكم طبقة الجذر: ROOT-TRACE؛ `ʕ-w-p ↔ ع-w-f` في الطائر. حكم طبقة النواة: OPEN-CANDIDATE؛ لا تصدر `عف`.
- مسح العربية: لسان العرب لابن منظور: «العَوْفُ: الدِّيكُ» و«العَوْفُ: طائر»؛ تاج العروس لمرتضى الزبيدي: «العَوْفُ: الدِّيكُ» و«وقيل: طائرٌ».
- الجسر الدلالي الصريح: الديك طائر، ولفظ `عوف` العربي يسمي طائرًا من الجنس الذي تسميه العبرية اسمًا عامًا؛ صلة الخاص بالعام واضحة ومحصورة.
- المصفاة الاتجاهية: لا مانح مسمى؛ ندرة المقابل في الأدبيات ليست دليلًا مستقلًا، لذلك اكتملت المروحة العربية قبل الحكم.
- الحكم (استكشاف): ROOT-TRACE؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد ROOT-TRACE وOPEN-CANDIDATE؛ السبب: فُتح المقابل الكامل `عوف` بدل إسقاط الواو إلى نواة ذات مدار مخالف.

<!-- HEBREW-REORDERED:HOLLOW-FIRST-007:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-hollow-first-007"
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
