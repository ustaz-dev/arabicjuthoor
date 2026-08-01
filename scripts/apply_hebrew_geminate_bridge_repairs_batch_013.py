#!/usr/bin/env python3
"""Revoke manufactured nucleus bridges while preserving supported full roots."""

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
BATCH = "hebrew-geminate-bridge-repairs-013"
MARKER = "<!-- HEBREW-REORDERED:GEMINATE-BRIDGE-REPAIRS-013:BEGIN -->"


CHANGES = {
    "kaikki_hebrew:3515:en-זמם-he-verb-SuZFn5pM": {
        "root": ("ROOT-ECHO", True, "جذر الفرع الكامل z-m-m يقابل زمم في حس القصد؛ الصلة معجمية مخصوصة لا تعميم نووي.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت نواة زم: التخطيط والقصد لا يحققان القراءة المجمدة «ضم الكثير باكتناز»، والجسر القديم جمع أفكار متخيل غير منقول.", None),
    },
    "kaikki_hebrew:16169:en-סרר-he-verb-3x-0qwxX": {
        "root": ("ROOT-ECHO", True, "تحقيق الفرع s-r-r الثانوي يقابل صرر في حس الإصرار والعزم؛ الصلة مخصوصة بالحس لا بمدار الضغط.", None),
        "nucleus": ("OPEN-CANDIDATE", False, "نُقضت نواة صر: العناد والإصرار شاهد للجذر الكامل، أما تصوير الإرادة كتضام يمنع الانتشار فجسر مصنوع لا نص معجميًا.", None),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:GEMINATE-BRIDGE-REPAIRS-013:BEGIN -->

## الجرد العبري المعاد ترتيبه — نقض جسور مصنوعة في المضعّف، الدفعة 013 (2026-08-01)

### بطاقة: `זמם` «to plan, intend»، العضو `kaikki_hebrew:3515:en-זמם-he-verb-SuZFn5pM`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ المقارنة العربية فردية من المسار الأول، لا صفًّا من طابور المسار 2.
- كلمة الفرع: `זמם` zamám، verb، «to plan, intend» [Kaikki Hebrew].
- جذر الفرع بصوامته كاملة بعد تعرية الصرف `z-m-m`؛ لا زوائد. الصامتان المتميزان `z-m` في الموضعين 1 و2؛ الميم الثالثة تضعيف الثانية، لا أصل مختلف مسقط.
- حكم طبقة الجذر: ROOT-ECHO؛ `z-m-m ↔ ز-m-m` في حس القصد. حكم طبقة النواة: OPEN-CANDIDATE؛ لا موجب صادر.
- مسح العربيّة: لسان العرب لابن منظور: «أَمْرُ بني فلان زَمَمٌ أَي هيَّن لم يجاوز القَدْرَ ... وقيل أَي قَصْدٌ»؛ تاج العروس لمرتضى الزبيدي: «أَمرُ بني فلان زَمَمٌ ... وقيل: أَي قَصْد».
- مسار الصوت: الجذر الكامل متطابق؛ فحص النواة تناول الصامتين في الموضعين 1 و2، والثالث تضعيف، فلا إسقاط صامت.
- الجسر الدلالي الصريح للجذر: plan/intend هو قصد الفعل، والعربية تحفظ `زمم` في حس القصد؛ لذلك يبقى صدى الجذر الكامل. أمّا القراءة المجمدة للنواة `زم` فهي «ضم الكثير باكتناز»، ولا يقول المعجمان إن التخطيط جمعٌ مكتنز.
- المصفاة الاتجاهية: لا مانح مسمى؛ ولأن مصدر العضو لا يصرح بالمقابل العربي بقي حكم الجذر ECHO لا TRACE.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق NUCLEUS-ECHO بـ`زم`؛ الجديد OPEN-CANDIDATE؛ السبب: الجسر القديم من التخطيط إلى «ضم الكثير» مصنوع. حكم ROOT-ECHO باقٍ على شاهد القصد المخصوص.

### بطاقة: `סרר` «to be stubborn, disobedient»، العضو `kaikki_hebrew:16169:en-סרר-he-verb-3x-0qwxX`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `סרר` sarár، verb، «to be stubborn, disobedient» [Kaikki Hebrew]. مصدر العضو يرد الفعل إلى قاعدة ثنائية `s-r` «turn aside» ويعد الراء الأخيرة تضعيفًا ثانويًا.
- جذر الفرع بعد التحليل التاريخي كاملًا `s-r`، وتحقيقه السطحي `s-r-r`؛ الصامتان في الموضعين 1 و2 هما القاعدة كلها، والراء في 3 تضعيف ثانوي لا أصل ثالث مسقط.
- حكم طبقة الجذر: ROOT-ECHO؛ التحقيق `s-r-r` يقابل `ص-r-r` في الإصرار والعزم. حكم طبقة النواة: OPEN-CANDIDATE؛ لا موجب صادر.
- مسح العربيّة: لسان العرب لابن منظور: «وأَصَرَّ على الأَمر: عَزَم» و«أَصَرَّ على الذنب لم يُقْلِع عنه»؛ تاج العروس لمرتضى الزبيدي: «أَصَرَّ على الأَمر: عَزَم».
- مسار الصوت: فُحص الصامتان في الموضعين 1 و2 من القاعدة الثنائية، والموضع 3 تضعيف للثاني؛ لم يُسقط صامت أصلي.
- الجسر الدلالي الصريح للجذر: stubborn هو الثبات على العصيان وعدم الإقلاع، والعربية تقول أصر على الذنب فلم يقلع؛ فهذا صدى معجمي للجذر الكامل المضعّف. أمّا القراءة المجمدة للنواة `صر` فهي «التضام الشديد الذي يمنع الانتشار»، ولا يثبت النص أن الإرادة جسم متضام.
- المصفاة الاتجاهية: لا مانح مسمى؛ الصلة العربية مستقلة لكنها ليست مقارنة صريحة في مصدر العضو، فبقيت ECHO.
- الحكم (استكشاف): ROOT-ECHO؛ النواة OPEN-CANDIDATE.
- سطر النسخ: السابق NUCLEUS-ECHO بـ`صر`؛ الجديد OPEN-CANDIDATE؛ السبب: الجسر القديم «انغلاق الإرادة كتضام» استعارة مصنوعة. حكم ROOT-ECHO باقٍ على شاهد الإصرار وعدم الإقلاع.

<!-- HEBREW-REORDERED:GEMINATE-BRIDGE-REPAIRS-013:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-geminate-bridge-repairs-013"
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
                target.pop("selected", None)
        row["batch_number"] = BATCH

    atomic_write(COVERAGE, "\n".join(json.dumps(row, ensure_ascii=False) for row in rows) + "\n")
    text = READING.read_text(encoding="utf-8")
    if MARKER not in text:
        atomic_write(READING, text.rstrip() + "\n" + CARDS.lstrip("\n"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
