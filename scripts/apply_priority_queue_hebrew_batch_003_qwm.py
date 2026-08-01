#!/usr/bin/env python3
"""Judge the explicit q-w-m priority row without inheriting from its parent."""

from __future__ import annotations

import json
import os
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
MEMBER = "kaikki_hebrew:3285:en-קום-he-verb-j6~RSR3H"
DATE = "2026-08-01"
EVIDENCE = "04-cross-linguistic/readings/hebrew.md#path2-priority-queue-hebrew-003-qwm"
MARKER = "<!-- PATH2-PRIORITY-QUEUE:HEBREW-003-QWM:BEGIN -->"


CARD = r'''

<!-- PATH2-PRIORITY-QUEUE:HEBREW-003-QWM:BEGIN -->

### بطاقة: `קום` qwm، العضو `kaikki_hebrew:3285:en-קום-he-verb-j6~RSR3H`
- أصل المرشح: طابور المسار 2، اقتراح ميليتاريف، `SEM 1178`؛ نص الحاشية المنقول في مصدر الطابور: «تحوُّلٌ ثانويٌّ لجذرٍ ثنائيِّ الصّامتِ إلى بنيةِ *CVwVC-».
- كلمة الفرع: `קום` kum، verb، «Bare infinitive (infinitive construct or gerund) of קם (kam)» [Kaikki Hebrew]. حُكم هذا العضو نفسه، ولم يرث حكم `קם`.
- جذر الفرع كاملًا بعد تعرية الصرف: `q-w-m` في صورة المصدر الأجوف؛ لا سابقة ولا لاحقة. الصامتان الأساسيان في تحليل ميليتاريف `q-m`، والواو توسعة ثانوية مصرح بها لا صامت جذر أسقط بالانتقاء.
- حكم طبقة الجذر: ROOT-TRACE؛ `q-w-m` ↔ `ق-و-م` كاملًا في فعل القيام.
- حكم طبقة النواة: NUCLEUS-TRACE؛ النواة `قم` «تجمع الشيء أو تضامه في كتلة قوية مع تسنم أو ارتفاع».
- مسح العربية: لسان العرب لابن منظور: «القيامُ: نقيض الجلوس، قام يَقُومُ قَوْماً وقِياماً وقَوْمة وقامةً»؛ تاج العروس لمرتضى الزبيدي: «قامَ الأمرُ قَوْمًا: اعتدل واستوى» و«قد يُعنى به ضدُّ القعود».
- مسار الصوت: أُخذ الموضعان `1 و3`؛ الواو في الموضع الثاني علة في بنية الأجوف `CVwVC`، وحاشية ميليتاريف تسميها تحولًا ثانويًا لجذر ثنائي الصامت. لا صامت أصلي ثالث محذوف.
- المدار الصريح: القيام انتقال الجسد إلى قوام مجتمع قوي مرتفع؛ فهذا يحقق مدار `قم` في التضام مع التسنم والارتفاع، لا مجرد اشتراك في لفظ «القيام».
- إشعاع الأسرة في الفرع: 1/4 لهذا المصدر وحده؛ `קם` له بطاقته المستقلة والصيغ الأخرى لا ترث. إشعاع العربية: حُصر في `قام` بمعنى نهض واعتدل.
- المصفاة الاتجاهية: المقابلة سامية موروثة، ولا مانح أو قرض في مصدر العضو أو المروحة.
- الحكم (استكشاف): ROOT-TRACE؛ وحكم النواة NUCLEUS-TRACE.
- سطر النسخ: السابق root=FORM-OF-ISOLATED وnucleus=FORM-OF-ISOLATED؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: فُتح العضو نفسه بدليل q-w-m الكامل، وشهادة صرفية صريحة بتوسعة الواو، ومدار نووي موثق.

<!-- PATH2-PRIORITY-QUEUE:HEBREW-003-QWM:END -->
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
    row = next((item for item in rows if item["member_id"] == MEMBER), None)
    if row is None:
        raise RuntimeError(f"coverage member missing: {MEMBER}")
    values = {
        "root": (
            "ROOT-TRACE",
            "الجذر q-w-m يقابل قوم كاملًا في فعل القيام؛ حُكم العضو نفسه لا حكم الأصل بالنيابة.",
            None,
        ),
        "nucleus": (
            "NUCLEUS-TRACE",
            "الواو توسعة CVwVC ثانوية بنص ميليتاريف، ومدار قم يحقق تضام القوام مع الارتفاع.",
            {
                "nucleus": "قم",
                "reading_ar": "تجمع الشيء أو تضامه في كتلة قوية مع تسنم أو ارتفاع",
                "status": "licensed",
                "positions": ["1-3"],
                "rule_ids": ["GLD-01"],
                "route_required": False,
                "arabic_root_witness": "قوم",
                "old_arabic_sources": ["لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي"],
                "omitted_branch_consonant": "w",
                "omission_basis": "Militarev SEM 1178: secondary CVwVC expansion of a biconsonantal consonantal root",
            },
        ),
    }
    for layer, (outcome, basis, selected) in values.items():
        target = row[f"{layer}_layer"]
        old = str(target.get("outcome"))
        if old != outcome:
            record = {
                "schema": "lane-a-judgment-supersession-v1",
                "date": DATE,
                "member_id": MEMBER,
                "layer": layer,
                "previous_outcome": old,
                "new_outcome": outcome,
                "reason": basis,
                "evidence": EVIDENCE,
            }
            history = row.setdefault("judgment_supersessions", [])
            if not any(item.get("layer") == layer and item.get("evidence") == EVIDENCE for item in history):
                history.append(record)
        target["outcome"] = outcome
        target["issued"] = True
        target["basis"] = basis
        if layer == "nucleus":
            target["selected"] = selected
    row["batch_number"] = "priority-queue-hebrew-003-qwm"
    atomic_write(COVERAGE, "\n".join(json.dumps(item, ensure_ascii=False) for item in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARD.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
