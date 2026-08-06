# -*- coding: utf-8 -*-
"""مروحةُ المرشَّحاتِ العربيّةِ لكلِّ خطّ، لا للخطِّ المربَّعِ وحدَه (2026-08-06)

**العطبُ الذي يُصلِحُه:** `fan_northern_word.py` يمحو كلَّ حرفٍ ليس عبريًّا مربّعًا،
فأخرجَ المسحُ الشاملُ صفرًا في القبطيّةِ والمصريّةِ والأكديّة، **وهي أبعدُ الفروعِ
وأثمنُها لدعوى المؤلّف**، إذ فيها تسكنُ النواةُ الثنائيّةُ إن صحَّت الدعوى.

**المبدأُ واحدٌ في كلِّ خطّ:** الفرعُ دمجَ ما فرّقَته العربيّة، فالحرفُ الواحدُ في
الفرعِ بابٌ على عدّةِ أصواتٍ عربيّة، والمعنى هو الذي يختارُ بعدَ أن يفتحَ الصوتُ الباب.

**وصوائتُ الفرعِ تُطرَحُ كلُّها** لأنّ المقارنةَ على الهيكلِ الصامتيّ. والمصريّةُ
تُكتَبُ بلا صوائتَ أصلًا، وهذا في مصلحتِنا لا ضدَّنا.
"""
from __future__ import annotations

import itertools
import re
import unicodedata

# ------------------------------------------------------------------ القبطيّة
# حروفُها اليونانيّةُ الأصلِ ومعها سبعةٌ ديموطيّةٌ أصيلةٌ هي أنقى ما فيها
COPTIC_FAN: dict[str, tuple[str, ...]] = {
    "ⲃ": ("ب",), "ⲅ": ("ج", "غ", "ق"), "ⲇ": ("د", "ض", "ذ"),
    "ⲍ": ("ز", "ذ"), "ⲑ": ("ث", "ط", "ت"), "ⲕ": ("ك", "ق"),
    "ⲗ": ("ل",), "ⲙ": ("م",), "ⲛ": ("ن",), "ⲡ": ("ب", "ف"),
    "ⲣ": ("ر",), "ⲥ": ("س", "ص", "ش", "ز"), "ⲧ": ("ت", "ط", "د"),
    "ⲫ": ("ف",), "ⲭ": ("خ",), "ϣ": ("ش", "س"), "ϥ": ("ف", "ب"),
    "ϧ": ("خ", "ح"), "ϩ": ("ه", "ح", "خ"), "ϫ": ("ج", "ز", "ض"),
    "ϭ": ("ج", "ق", "ك"), "ϯ": ("ت",), "ⲝ": ("ك",), "ⲯ": ("ب",),
}
COPTIC_VOWELS = set("ⲁⲉⲏⲓⲟⲩⲱⲐ")

# ------------------------------------------------------------------ المصريّة
# الرومنةُ المصريّةُ القياسيّة. الألفُ المصريّةُ ꜣ والعينُ ꜥ أوسعُ الأبواب.
EGYPTIAN_FAN: dict[str, tuple[str, ...]] = {
    "ꜣ": ("ء", "ا", "ل", "ر"), "ꜥ": ("ع", "ض", "غ"),
    "j": ("ي", "ء"), "i": ("ي", "ء"), "y": ("ي",), "w": ("و",),
    "b": ("ب",), "p": ("ب", "ف"), "f": ("ف",), "m": ("م",), "n": ("ن",),
    "r": ("ر", "ل"), "h": ("ه",), "ḥ": ("ح",), "ḫ": ("خ",), "ẖ": ("خ", "ح"),
    "z": ("ز", "س"), "s": ("س", "ش", "ص"), "š": ("ش", "س"),
    "q": ("ق",), "ḳ": ("ق",), "k": ("ك",), "g": ("ج", "ق", "غ"),
    "t": ("ت", "ط"), "ṯ": ("ث", "ت", "ط"), "d": ("د", "ض"),
    "ḏ": ("ذ", "ز", "ض", "ج"),
}

# ------------------------------------------------------------------ الأكديّة
AKKADIAN_FAN: dict[str, tuple[str, ...]] = {
    "ʾ": ("ء",), "ʔ": ("ء",), "ʿ": ("ع", "غ"),
    "b": ("ب",), "p": ("ف", "ب"), "m": ("م",), "n": ("ن",),
    "l": ("ل",), "r": ("ر",), "w": ("و",), "y": ("ي",), "j": ("ي", "ج"),
    "d": ("د", "ذ", "ض"), "t": ("ت", "ث"), "ṭ": ("ط", "ظ"),
    "z": ("ز", "ذ"), "s": ("س",), "ṣ": ("ص", "ض", "ظ"),
    "š": ("ش", "س", "ث"), "g": ("ج", "غ"), "k": ("ك",), "q": ("ق",),
    "ḫ": ("خ", "ح", "ه", "ع", "غ"), "ḥ": ("ح",), "h": ("ه",),
}
AKKADIAN_VOWELS = set("aeiouāēīōūâêîôû")
AKKADIAN_MIMATION = re.compile(r"[aiuāīū]m$", re.I)

# ------------------------------------------------------------------ اليونانيّة
GREEK_FAN: dict[str, tuple[str, ...]] = {
    "β": ("ب",), "γ": ("ج", "غ", "ق"), "δ": ("د", "ض", "ذ"),
    "ζ": ("ز", "ذ", "ج"), "θ": ("ث", "ط", "ت"), "κ": ("ك", "ق"),
    "λ": ("ل",), "μ": ("م",), "ν": ("ن",), "π": ("ب", "ف"),
    "ρ": ("ر",), "σ": ("س", "ص", "ش", "ز"), "ς": ("س", "ص", "ش", "ز"),
    "τ": ("ت", "ط", "د"), "φ": ("ف", "ب"), "χ": ("خ", "ح", "ك"),
    "ψ": ("ب",), "ξ": ("ك",),
}
GREEK_VOWELS = set("αειηουω")

_DIAC_HEB = dict.fromkeys(range(0x0591, 0x05C8))
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

NORTH_FAN: dict[str, tuple[str, ...]] = {
    "א": ("ء", "ا"), "ב": ("ب",), "ג": ("ج",), "ד": ("د", "ذ"),
    "ה": ("ه",), "ו": ("و",), "ז": ("ز", "ذ"), "ח": ("ح", "خ"),
    "ט": ("ط", "ظ"), "י": ("ي", "و"), "כ": ("ك",), "ל": ("ل",),
    "מ": ("م",), "נ": ("ن",), "ס": ("س", "ش"),
    "ע": ("ع", "غ", "ض", "ح"), "פ": ("ف", "ب"),
    "צ": ("ص", "ض", "ظ", "ز"), "ק": ("ق", "ك"), "ר": ("ر",),
    "ש": ("ش", "س", "ث"), "ת": ("ت", "ث"),
}


def detect(text: str) -> str:
    for ch in text:
        o = ord(ch)
        if 0x0590 <= o <= 0x05FF:
            return "north"
        if 0x2C80 <= o <= 0x2CFF or 0x03E2 <= o <= 0x03EF:
            return "coptic"
        if 0x0370 <= o <= 0x03FF or 0x1F00 <= o <= 0x1FFF:
            return "greek"
    if any(c in text for c in "ꜣꜥẖṯḏḳ"):
        return "egyptian"
    return "akkadian"


def skeleton(word: str, script: str | None = None) -> list[str]:
    """الهيكلُ الصامتيُّ كقائمةِ حروفٍ يُبنى عليها التوليد."""
    w = unicodedata.normalize("NFC", str(word)).strip()
    script = script or detect(w)

    if script == "north":
        w = w.translate(_DIAC_HEB).translate(FINALS)
        w = re.sub(r"[^א-ת]", "", w)
        if len(w) > 2 and w.endswith("א"):
            w = w[:-1]
        if len(w) > 2:
            w = w[0] + "".join(c for c in w[1:] if c not in "והי")
        return list(w)

    if script == "coptic":
        w = w.lower()
        return [c for c in w if c in COPTIC_FAN and c not in COPTIC_VOWELS]

    if script == "greek":
        base = unicodedata.normalize("NFD", w.lower())
        base = "".join(c for c in base if not unicodedata.combining(c))
        return [c for c in base if c in GREEK_FAN and c not in GREEK_VOWELS]

    if script == "egyptian":
        out, i = [], 0
        keys = sorted(EGYPTIAN_FAN, key=len, reverse=True)
        while i < len(w):
            for k in keys:
                if w[i:i + len(k)] == k:
                    out.append(k)
                    i += len(k)
                    break
            else:
                i += 1
        return out

    # الأكديّة: تُنزَعُ ميمةُ التنوينِ والصوائت
    w = AKKADIAN_MIMATION.sub("", w)
    out = []
    for c in w:
        if c in AKKADIAN_VOWELS:
            continue
        if c in AKKADIAN_FAN:
            out.append(c)
    # الإدغامُ في الرومنةِ لا يُضاعِفُ الصامت
    return [c for i, c in enumerate(out) if i == 0 or c != out[i - 1]]


FANS = {
    "north": NORTH_FAN, "coptic": COPTIC_FAN, "greek": GREEK_FAN,
    "egyptian": EGYPTIAN_FAN, "akkadian": AKKADIAN_FAN,
}


def fan(word: str, script: str | None = None, limit: int = 400) -> list[str]:
    script = script or detect(word)
    sk = skeleton(word, script)
    if not (2 <= len(sk) <= 4):
        return []
    table = FANS[script]
    options = [table.get(c, ()) for c in sk]
    if any(not o for o in options):
        return []
    return ["".join(c) for c in itertools.islice(itertools.product(*options), limit)]


if __name__ == "__main__":
    import sys

    sys.stdout.reconfigure(encoding="utf-8")
    for w in sys.argv[1:] or ["ⲙⲟⲟⲩ", "ⲣⲱⲙⲉ", "jb", "mw", "ꜥꜣ", "kalbum", "עינא", "κέρας"]:
        s = detect(w)
        print(f"   {w:12} [{s:9}] هيكل={''.join(skeleton(w, s)):8} مرشّحات={len(fan(w, s))}")
