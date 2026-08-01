#!/usr/bin/env python3
"""Start the geminate-first Hebrew inventory after the hollow tranche."""

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
BATCH = "hebrew-geminate-first-010"
MARKER = "<!-- HEBREW-REORDERED:GEMINATE-FIRST-010:BEGIN -->"


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
        "omission_basis": "The third realization is gemination of the second consonant, not an independently omitted radical.",
    }


CHANGES = {
    "kaikki_hebrew:1834:en-דוב-he-noun-vJi7UOgJ": {
        "root": ("ROOT-TRACE", True, "المستعاد *dubb- يقابل دبّ كاملًا في اسم الحيوان؛ الواو الكتابية صائت لا صامت أصل.", None),
        "nucleus": ("NUCLEUS-ECHO", True, "d-b هما الصامتان المتميزان، ومشية الدب البطيئة تحقق مدار دب؛ خُفض إلى ECHO لأن مصدر التسمية يذكر علة بديلة هي الهمهمة.", selected("دب", "الثقل أو الضغط والحركة البطيئة، ويلزمها التخلف", "دبب", [])),
    },
    "kaikki_hebrew:11541:en-גרר-he-verb-JfR-Ge2t": {
        "root": ("ROOT-TRACE", True, "g-r-r يقابل ج-r-r كاملًا في الجر والسحب مع GUT-03.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "g-r هما الصامتان المتميزان والتضعيف ليس ثالثًا مستقلًا؛ جر الشيء امتداد لحركته بالسحب فيحقق مدار جر.", selected("جر", "الاسترسال والامتداد", "جرر", ["GUT-03"])),
    },
    "kaikki_hebrew:3977:en-דק-he-adj-Gg3CJ7Wq": {
        "root": ("ROOT-TRACE", True, "d-q الثنائي يقابل د-q-q المضعف في دقيق، ومعنى thin هو الرقة والدقة نفسها.", None),
        "nucleus": ("NUCLEUS-TRACE", True, "الصامتان d-q كاملان في الفرع؛ العربية تحقق التضعيف، ومعنى thin/fine يحقق الحدة والدقة في مدار دق.", selected("دق", "الصدم أو الضغط الشديد والحدة", "دقق", [])),
    },
}


CARDS = r'''

<!-- HEBREW-REORDERED:GEMINATE-FIRST-010:BEGIN -->

## الجرد العبري المعاد ترتيبه — المضعّف أولًا، الدفعة 010 (2026-08-01)

### بطاقة: `דוב` «bear»، العضو `kaikki_hebrew:1834:en-דוב-he-noun-vJi7UOgJ`
- أصل المرشح: الجرد العبري بالمضعّف بعد الأجوف؛ ليست البطاقة من صف خارجي بعينه.
- كلمة الفرع: `דוב` dov، noun، «bear» [Kaikki Hebrew]. مصدر العضو يعيد الاسم إلى `*dubb-` ويصرح بقرابته مع العربية `دُبّ`، ويذكر احتمال تسميته من مشيه البطيء اللين أو همهمته.
- جذر الفرع بصوامته كاملة بعد التحليل `d-b(b)`؛ الواو في الرسم حامل للصائت /o/، لا صامت جذر. الصامتان المتميزان `d-b` أُخذا كاملين، والتضعيف تكرار للصامت الثاني لا ثالث مستقل مسقط.
- حكم طبقة الجذر: ROOT-TRACE؛ `*dubb- ↔ د-b-b`. حكم طبقة النواة: NUCLEUS-ECHO؛ `دب` «الثقل أو الضغط والحركة البطيئة، ويلزمها التخلف».
- مسح العربية من مادة `دبب`: لسان العرب لابن منظور: «الدُّبُّ: معروف» و«دَبَّ يَدِبُّ دَبًّا ودَبِيباً: مَشَى على هِينَتِه»؛ تاج العروس لمرتضى الزبيدي: «الدُّبُّ: الحَيَوانُ المَعْرُوفُ» و«دَبَّ: مَشَى على هِينَتِه».
- الجسر الدلالي الصريح: الحيوان هو الدب نفسه في الطرفين، ومشيه على هينته يحقق الحركة البطيئة والثقل في مدار `دب`؛ لكنه ECHO لأن مصدر التسمية يذكر الهمهمة بديلًا.
- المصفاة الاتجاهية: لا مانح مسمى؛ لم يُنقل احتمال التسمية إلى يقين.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-ECHO.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-ECHO؛ السبب: أثبت المصدر أن الواو صائت في `*dubb-`، واكتملت مروحة الحيوان والحركة مع حفظ عدم يقين التعليل.

### بطاقة: `גרר` «to drag»، العضو `kaikki_hebrew:11541:en-גרר-he-verb-JfR-Ge2t`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ ويتقاطع مع المسار 2، اقتراح ميليتاريف `SEM 1061`: `grr גרר ↔ جرّ`، وحاشيته تعد التضعيف صورة لا أصلًا ثالثًا.
- كلمة الفرع: `גרר` garár، verb، «to drag» [Kaikki Hebrew]. جذر الفرع كاملًا `g-r(r)`؛ لا سابقة ولا لاحقة.
- الصامتان المتميزان `g-r` في الموضعين 1 و2؛ الراء الأخيرة تحقيق للتضعيف المصرح به، لا صامت مختلف أسقط بالانتقاء. المسار `GUT-03` يسوي `g ↔ ج`.
- حكم طبقة الجذر: ROOT-TRACE؛ `g-r-r ↔ ج-r-r`. حكم طبقة النواة: NUCLEUS-TRACE؛ `جر` «الاسترسال والامتداد».
- مسح العربية: لسان العرب لابن منظور: «جَرَّ الشيءَ يَجُرُّه جَرّاً: سَحَبَه»؛ تاج العروس لمرتضى الزبيدي: «جَرَّه يَجُرُّه جَرّاً: سَحَبَه».
- الجسر الدلالي الصريح: جر الشيء هو سحبه ممتدًا على الأرض أو في الحيز؛ فهو تحقق مباشر للاسترسال والامتداد، ومن مادة `جرر` نفسها.
- المصفاة الاتجاهية: لا مانح مسمى؛ موافقة ميليتاريف ليست الحكم، وحاشيته استُعملت في الصرف فقط.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق OPEN-CANDIDATE في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: اكتملت مروحة `جرر`، وثبت أن الثالث تضعيف لا صامت مستقل.

### بطاقة: `דק` «thin»، العضو `kaikki_hebrew:3977:en-דק-he-adj-Gg3CJ7Wq`
- أصل المرشح: الجرد العبري بالمضعّف أولًا؛ ليست البطاقة من صف خارجي بعينه، ومصدر العضو نفسه يقارن العربية `دَقِيق`.
- كلمة الفرع: `דק` dak، adj، «thin» [Kaikki Hebrew]. جذر الفرع كاملًا `d-q` بلا ثالث؛ العربية تحقق الأسرة في `د-q-q` المضعف و`دقيق`.
- الصامتان `d-q` أُخذا من الموضعين 1 و2، وهما كامل الفرع. لم يسقط صامت؛ التضعيف واقع في الشاهد العربي لا حذفًا من كلمة الفرع.
- حكم طبقة الجذر: ROOT-TRACE لأسرة `דק ↔ دقق/دقيق`. حكم طبقة النواة: NUCLEUS-TRACE؛ `دق` «الصدم أو الضغط الشديد والحدة».
- مسح العربية: لسان العرب لابن منظور: «الدَّقِيقُ: خلافُ الغَلِيظ» و«دَقَّ الشيءُ يَدِقُّ دِقَّةً: صار دَقِيقاً»؛ تاج العروس لمرتضى الزبيدي: «الدَّقِيقُ: ضِدُّ الغَلِيظ» و«دَقَّ: صار دَقِيقاً».
- الجسر الدلالي الصريح: thin هو الرقة وخلاف الغلظ، والدقة تنتهي إلى حدة وصغر في السماكة؛ فهذا يحقق وجه الحدة في مدار `دق` دون مادة أخرى.
- المصفاة الاتجاهية: لا مانح مسمى؛ حكم العضو من مقارنته المنشورة ومروحة `دقق`.
- الحكم (استكشاف): ROOT-TRACE وNUCLEUS-TRACE.
- سطر النسخ: السابق MORPHOLOGY-GAP في الطبقتين؛ الجديد ROOT-TRACE وNUCLEUS-TRACE؛ السبب: ثبت أن الفرع ثنائي كامل والعربية المضعفة تحمل الصورة والمعنى نفسيهما.

<!-- HEBREW-REORDERED:GEMINATE-FIRST-010:END -->
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

    evidence = "04-cross-linguistic/readings/hebrew.md#hebrew-reordered-geminate-first-010"
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
