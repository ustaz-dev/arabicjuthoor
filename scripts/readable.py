# -*- coding: utf-8 -*-
"""نطقٌ يُقرَأُ لكلِّ خطٍّ غيرِ عربيّ (2026-08-06، بأمرِ المؤلّف)

**العطبُ الذي يُصلِحُه:** كُتِبَت للمؤلّفِ كلماتٌ بخطوطٍ لا يقرؤُها ورموزٍ صوتيّةٍ
دوليّةٍ لا تُنطَقُ في الذهن، فحُجِبَتِ الكلمةُ عنه. كتبتُ `/laʕiːsˈtaː/` فسألَ: أهذه
«Lah-ees-tah»؟ ولمّا قرأَها هو بنفسِه رأى فيها `لحس` في لحظة، وكنّا رددناها.

**القاعدة:** كلُّ كلمةٍ بخطٍّ غيرِ عربيٍّ تُكتَبُ ومعها **نطقُها بحروفٍ تُقرَأ**،
وبالعربيّةِ حيثُ أمكن. والرمزُ الدوليُّ يُزادُ للدقّةِ ولا يُكتفى به.

الاستعمال في السكربتات:
    from readable import say
    print(f"{word} ({say(word, 'hebrew')})")
"""
from __future__ import annotations

import re
import unicodedata

# ------------------------------------------------------------------ الشمالُ الساميّ
# الحرفُ الشماليُّ -> (نطقٌ لاتينيٌّ يُقرَأ، حرفٌ عربيٌّ يُقرَّبُ به)
NORTH = {
    "א": ("ʾ", "أ"), "ב": ("b", "ب"), "ג": ("g", "ج"), "ד": ("d", "د"),
    "ה": ("h", "هـ"), "ו": ("w", "و"), "ז": ("z", "ز"), "ח": ("ḥ", "ح"),
    "ט": ("ṭ", "ط"), "י": ("y", "ي"), "כ": ("k", "ك"), "ך": ("k", "ك"),
    "ל": ("l", "ل"), "מ": ("m", "م"), "ם": ("m", "م"), "נ": ("n", "ن"),
    "ן": ("n", "ن"), "ס": ("s", "س"), "ע": ("ʿ", "ع"), "פ": ("p/f", "ف"),
    "ף": ("p/f", "ف"), "צ": ("ṣ", "ص"), "ץ": ("ṣ", "ص"), "ק": ("q", "ق"),
    "ר": ("r", "ر"), "ש": ("š", "ش"), "ת": ("t", "ت"),
}

# حركاتُ النقطِ العبريّة، لتقريبِ النطقِ لا لضبطِه
NIQQUD = {
    "ְ": "ə", "ֱ": "e", "ֲ": "a", "ֳ": "o",
    "ִ": "i", "ֵ": "e", "ֶ": "e", "ַ": "a",
    "ָ": "ā", "ֹ": "o", "ֻ": "u", "ּ": "",
}

# ------------------------------------------------------------------ اليونانيّة
GREEK = {
    "α": "a", "β": "b", "γ": "g", "δ": "d", "ε": "e", "ζ": "z", "η": "ē",
    "θ": "th", "ι": "i", "κ": "k", "λ": "l", "μ": "m", "ν": "n", "ξ": "ks",
    "ο": "o", "π": "p", "ρ": "r", "σ": "s", "ς": "s", "τ": "t", "υ": "u",
    "φ": "ph", "χ": "kh", "ψ": "ps", "ω": "ō",
}
GREEK_AR = {
    "α": "ا", "β": "ب", "γ": "غ", "δ": "د", "ε": "إ", "ζ": "ز", "η": "ي",
    "θ": "ث", "ι": "ي", "κ": "ك", "λ": "ل", "μ": "م", "ν": "ن", "ξ": "كس",
    "ο": "و", "π": "ب", "ρ": "ر", "σ": "س", "ς": "س", "τ": "ت", "υ": "و",
    "φ": "ف", "χ": "خ", "ψ": "بس", "ω": "و",
}

# ------------------------------------------------------------------ القبطيّة
COPTIC = {
    "ⲁ": "a", "ⲃ": "b", "ⲅ": "g", "ⲇ": "d", "ⲉ": "e", "ⲍ": "z", "ⲏ": "ē",
    "ⲑ": "th", "ⲓ": "i", "ⲕ": "k", "ⲗ": "l", "ⲙ": "m", "ⲛ": "n", "ⲝ": "ks",
    "ⲟ": "o", "ⲡ": "p", "ⲣ": "r", "ⲥ": "s", "ⲧ": "t", "ⲩ": "u", "ⲫ": "ph",
    "ⲭ": "kh", "ⲯ": "ps", "ⲱ": "ō", "ϣ": "š", "ϥ": "f", "ϧ": "ḫ",
    "ϩ": "h", "ϫ": "j", "ϭ": "č", "ϯ": "ti",
}

PHOENICIAN = dict(zip(
    "𐤀𐤁𐤂𐤃𐤄𐤅𐤆𐤇𐤈𐤉𐤊𐤋𐤌𐤍𐤎𐤏𐤐𐤑𐤒𐤓𐤔𐤕",
    ["ʾ", "b", "g", "d", "h", "w", "z", "ḥ", "ṭ", "y", "k", "l",
     "m", "n", "s", "ʿ", "p", "ṣ", "q", "r", "š", "t"],
))


def _script_of(text: str) -> str:
    for ch in text:
        o = ord(ch)
        if 0x0590 <= o <= 0x05FF:
            return "north"
        if 0x0370 <= o <= 0x03FF or 0x1F00 <= o <= 0x1FFF:
            return "greek"
        if 0x2C80 <= o <= 0x2CFF or 0x03E2 <= o <= 0x03EF:
            return "coptic"
        if 0x10900 <= o <= 0x1091F:
            return "phoenician"
    return "latin"


def say(word: str, script: str | None = None, with_arabic: bool = True) -> str:
    """نطقٌ يُقرَأ. مثال: say('תישא') -> 'tysh-ʾa  (تيشا)'"""
    w = unicodedata.normalize("NFC", str(word))
    script = script or _script_of(w)

    if script in {"north", "hebrew", "aramaic"}:
        lat, ar = [], []
        for ch in w:
            if ch in NIQQUD:
                lat.append(NIQQUD[ch])
                continue
            if ch in NORTH:
                a, b = NORTH[ch]
                lat.append(a)
                ar.append(b)
        out = "".join(lat)
        return f"{out}  ({''.join(ar)})" if with_arabic and ar else out

    if script == "greek":
        base = unicodedata.normalize("NFD", w.lower())
        base = "".join(c for c in base if not unicodedata.combining(c))
        lat = "".join(GREEK.get(c, c) for c in base)
        ar = "".join(GREEK_AR.get(c, "") for c in base)
        return f"{lat}  ({ar})" if with_arabic and ar else lat

    if script == "coptic":
        lat = "".join(COPTIC.get(c, c) for c in w.lower())
        return lat

    if script == "phoenician":
        return "".join(PHOENICIAN.get(c, c) for c in w)

    return w


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    tests = sys.argv[1:] or ["תישא", "ראשא", "עינא", "לעיסתא", "עסקתא",
                             "א־ר־ץ", "κέρας", "βδάλλω", "ⲙⲟⲟⲩ", "𐤌𐤋𐤊"]
    for t in tests:
        print(f"   {t:14} {say(t)}")
