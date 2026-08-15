# -*- coding: utf-8 -*-
"""الحدثُ المجمَّدُ لكلِّ مرشَّحٍ عربيٍّ، بالنزولِ الذي نصَّ عليه القانون (2026-08-14)

**العطبُ الذي يُنهيه.** كانت كلُّ أداةٍ تسألُ سؤالًا واحدًا: هل الجذرُ الثلاثيُّ
مذكورٌ في `computational/data/layer_2_results_v2.jsonl`؟ فإن لم يكنْ كتبَت
«لا حدثَ مجمَّدَ للمرشَّح؛ لذلك لا حكمَ موجب» وأغلقَت البطاقة. وذلك الملفُّ
يحملُ 2,285 جذرًا وهو **مخرَجُ محرِّكٍ داخليٍّ لم يكتملْ**، لا أداةً مجمَّدة.

والكلفةُ مقيسة: من 30,998 مرشَّحًا مصريًّا **23.2% وحدَها** كان لها حدثٌ
بهذا السؤال، فسقطَ 77% منها قبلَ أن يُنظَرَ في صوتِها أو معناها. ومسارُ
المصريّةِ كتبَ 738 بطاقةً في يومٍ واحدٍ وخرجَ منها **صفرُ صلة**.

**والقانونُ يقولُ غيرَ ذلك نصًّا**، في موضعَينِ بتوقيعِ المؤلّف:

- التعديل 2 (2026-07-07): «مسارُ الجذرِ الكاملِ أوّلًا ... (قراءاتُ الـ2,285
  وعائلاتُ اللسان). **وعندَ غيابِه يُنزَلُ إلى مسارِ النواةِ كما كان**.»
  فغيابُ الجذرِ عن الـ2,285 يُنزِلُ في السلَّمِ ولا يُسكِتُ الحكم.
- حكمُ المؤلّف (2026-07-12) في التعديل 3: «ليست القراءاتُ فاسدةً؛ **سجلُّ
  الوجوهِ ناقص**. قاعدةٌ تُسقطُ ثلاثةَ أرباعِ القانونِ ... **مقصٌّ في اللحمِ
  لا في الزوائد**.» وهي الحالُ نفسُها هنا حرفًا بحرف: ثلاثةُ أرباعٍ تسقطُ
  لنقصٍ في سجلِّنا لا لعيبٍ في المادّة.

**والدرجاتُ أربعٌ، ولا نصَّ فيها مؤلَّفٌ من عندِنا**؛ كلُّ حرفٍ يُنقَلُ كما هو
من ملفٍّ مجمَّدٍ ويُسمّى مصدرُه في البطاقة:

    1 جذر    الجذرُ في الـ2,285              `jabal_axial`
    2 نواة   المرشَّحُ ثنائيٌّ مسجَّل          `jabal_lexicon_reading_ar`
    3 نزول   نواتُه مسجَّلةٌ وثالثُه في المحكمة   الاثنانِ معًا (التعديل 2)
    4 محاكم  حروفُه كلُّها في المحاكمِ الـ29    `gesture_event_ar`

والدرجةُ **لا تُغيِّرُ رتبةَ السلَّم**، فالرتبةُ تُحدِّدُها الأرجلُ الثلاثُ وحدَها
كما في القسم 7. وإنّما تُكتَبُ في البطاقةِ ليملكَ المؤلّفُ نقضَ درجةٍ بكلمة.

**والأجوفُ يُعامَلُ بالتعديل 1**: نواتُه صامتاه القويّان (موت ← م-ت)، فلا
يُطلَبُ له `مو` في السجلّ. وهذا نصٌّ موقَّعٌ أيضًا لا اجتهاد.
"""
from __future__ import annotations

import json
import pathlib
import unicodedata
from dataclasses import dataclass
from functools import cache

ROOT = pathlib.Path(__file__).resolve().parent.parent
LAYER2 = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
CORE_LEVELS = ROOT / "data" / "juthoor-core-levels.json"
REGISTRY = ROOT / "data" / "juthoor-canonical-registry.json"

WEAK = "واي"


def nfc(s: str) -> str:
    return unicodedata.normalize("NFC", str(s or "")).strip()


@cache
def root_events() -> dict[str, str]:
    """الجذورُ الـ2,285 وحدثُها المحوريُّ كما كتبَه جبل."""
    out: dict[str, str] = {}
    for line in LAYER2.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        row = json.loads(line)
        root, event = nfc(row.get("tri_root")), nfc(row.get("jabal_axial"))
        if root and event:
            out[root] = event
    return out


@cache
def nucleus_events() -> dict[str, str]:
    payload = json.loads(CORE_LEVELS.read_text(encoding="utf-8"))
    return {
        nfc(row["nucleus"]): nfc(row["jabal_lexicon_reading_ar"])
        for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]
        if row.get("jabal_lexicon_reading_ar")
    }


@cache
def courts() -> dict[str, str]:
    """محاكمُ الحروفِ الـ29: حدثُ النطقِ الكاملُ لكلِّ حرف، `registry-freeze-v1.0`."""
    payload = json.loads(REGISTRY.read_text(encoding="utf-8"))
    return {
        nfc(row["letter"]): nfc(row["gesture_event_ar"])
        for row in payload["letters"]
        if row.get("gesture_event_ar")
    }


@dataclass(frozen=True)
class Ev:
    """حدثٌ منقولٌ حرفيًّا من ملفٍّ مجمَّد، ومعه اسمُ مصدرِه ودرجتُه."""

    text: str
    source: str
    tier: int
    tier_ar: str
    note: str

    def line(self) -> str:
        """سطرُ البطاقةِ الجاهزُ كما يُطبَع."""
        return (f"- الحدثُ من السجلِّ المجمَّدِ كما هو (درجة {self.tier}، "
                f"{self.tier_ar}): «{self.text}» [{self.source}]"
                + (f". {self.note}" if self.note else ""))


def nucleus_of(candidate: str) -> str:
    """نواةُ المرشَّحِ بنصِّ التعديل 1: الأجوفُ صامتاه القويّان، وغيرُه أوّلاه."""
    c = nfc(candidate)
    if len(c) == 3 and c[1] in WEAK and c[0] not in WEAK and c[2] not in WEAK:
        return c[0] + c[2]
    return c[:2]


def all_tiers(candidate: str) -> list[Ev]:
    """كلُّ الأحداثِ المتاحةِ للمرشَّح، بالدرجاتِ من الأعلى إلى الأدنى.

    **العطبُ الذي تُنهيه هذه الدالّة، وقد أوقفَ مسارًا كاملًا (2026-08-15).**
    كانت `resolve` شلّالًا يردُّ أعلى درجةٍ متاحةٍ **ويُخفي ما دونَها**، فظنَّ
    الضابطُ أنّ بطاقةً صادرةً انقلبَ حكمُها وهي لم تنقلب:

        `tinniō` «to ring, jingle» ↔ `طن`: بطاقتُها صادرةٌ FLOOR-TRACE،
        ورِجلُ حدثِها قائمةٌ على **محكمتَي الحرفَينِ منفردَين** (ط «ضغطٌ باتّساعٍ
        واستغلاظ» ون «امتدادٌ لطيفٌ في الباطن»)، ومدارُها «محاكاةُ الرنين».
        وردَّتِ الأداةُ حدثَ النواةِ المسجَّلِ «التكتّلُ واللزوم» لأنّه أعلى
        درجةً، وهو لا يمتُّ إلى الرنينِ بصلة. فبدا الحكمُ منقوضًا وليس كذلك.

    **والدرجةُ الأعلى ليست الأصوبَ دائمًا.** المحاكاةُ الصوتيّةُ خاصّةً يقومُ
    حدثُها على الحروفِ أنفسِها لا على قراءةِ نواةٍ مركَّبة. فالبطاقةُ تُعلِنُ
    الدرجةَ التي تقومُ عليها، والأداةُ تعرضُ **ما توفَّرَ كلَّه** ولا تختارُ
    عنها. والاختيارُ يُكتَبُ باليدِ في المدارِ كسائرِ الأرجل.
    """
    c = nfc(candidate)
    if len(c) < 2:
        return []
    R, N, C = root_events(), nucleus_events(), courts()
    out: list[Ev] = []

    if len(c) == 3 and c in R:
        out.append(Ev(R[c], "computational/data/layer_2_results_v2.jsonl", 1,
                      "جذرٌ في الـ2,285", ""))

    if len(c) == 2 and c in N:
        out.append(Ev(N[c], "data/juthoor-core-levels.json", 2,
                      "نواةٌ مسجَّلة", ""))

    nuc = nucleus_of(c)
    third = "".join(x for x in c if x not in nuc) or c[-1]
    if len(c) >= 3 and nuc in N and third[0] in C:
        out.append(Ev(
            f"{N[nuc]}؛ والحرفُ الثالثُ «{third[0]}» حدثُه: {C[third[0]]}",
            "data/juthoor-core-levels.json + data/juthoor-canonical-registry.json",
            3, "نزولٌ إلى النواة",
            f"نواةُ «{c}» هي «{nuc}»"
            + ("، وهي صامتاه القويّانِ لأنّه أجوفُ (التعديل 1)"
               if nucleus_of(c) != c[:2] else "")))

    if all(x in C for x in c):
        out.append(Ev(
            "؛ ".join(f"«{x}»: {C[x]}" for x in c),
            "data/juthoor-canonical-registry.json", 4, "محاكمُ الحروف",
            "حدثُ النطقِ لكلِّ حرفٍ كما في السجلِّ المجمَّد، والتأليفُ يُكتَبُ "
            "باليدِ في المدار"))

    return out


def resolve(candidate: str, tier: int | None = None) -> Ev | None:
    """حدثٌ واحدٌ للمرشَّح: أعلى الدرجاتِ المتاحةِ، أو درجةٌ بعينِها إن طُلِبَت.

    **ولا يُحكَمُ بغيابِ درجةٍ على البطاقة**: من أرادَ درجةً بعينِها فليطلبْها،
    ومن أرادَ الجردَ كلَّه فـ`all_tiers`. والبطاقةُ التي تُعلِنُ درجتَها تُفحَصُ
    بها هي، لا بأعلى ما وجدَته الأداة.
    """
    evs = all_tiers(candidate)
    if tier is not None:
        return next((e for e in evs if e.tier == tier), None)
    return evs[0] if evs else None


def coverage(candidates: list[str]) -> dict[str, int]:
    """جردُ الدرجاتِ لقائمةِ مرشَّحين، للمحاضرِ لا للحكم."""
    out = {1: 0, 2: 0, 3: 0, 4: 0, 0: 0}
    for c in candidates:
        ev = resolve(c)
        out[ev.tier if ev else 0] += 1
    return {str(k): v for k, v in out.items()}


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    for word in (sys.argv[1:] or ["بتر", "شيث", "قول", "دبب", "زقم"]):
        ev = resolve(word)
        print(f"\n{word}: " + (ev.line() if ev else "لا حدثَ (حرفٌ خارجَ المحاكم)"))
