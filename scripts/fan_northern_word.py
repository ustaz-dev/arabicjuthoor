# -*- coding: utf-8 -*-
"""مروحةُ المرشَّحاتِ العربيّة: افتحْ كلَّ الاحتمالاتِ ثمّ دعِ المعنى يختار.

**المبدأُ الذي أوجبَها، بنصِّ المؤلّف:** «العربيّةُ فيها أصواتٌ أكثر، ولا يمكنُ أن
ننفيَ أنّ ع الشماليّةَ تكونُ أحيانًا ح لا ع وحدَها. وسّعِ الاحتمالات».

**والواقعُ اللسانيُّ وراءَه:** الشمالُ دمجَ ما فرّقَته العربيّة. فصادُ العبريّةِ `צ`
مجمعُ ثلاثةِ أصواتٍ أمٍّ تُعطي في العربيّةِ ص وض وظ، وشينُها `ש` مجمعُ ثلاثةٍ تُعطي
ش وس وث، وعينُها `ע` مجمعُ ما يُعطي ع وغ وض. فالكلمةُ الشماليّةُ الثلاثيّةُ قد يكونُ
لها ستّةٌ وثلاثونَ مرشَّحًا عربيًّا.

**والعطبُ الذي تُصلِحُه:** كنّا نأخذُ مرشَّحًا واحدًا لكلِّ حرفٍ ونبني عليه الحكم، فإذا
أخطأنا الاختيارَ سقطَت الصلةُ الصحيحة. مثالُه `לעס` «مضغ»: أخذنا العينَ عينًا فبلغنا
`لعس` (سوادُ الشفة) ورددنا البطاقة، ولو فتحنا المروحةَ لبلغنا `لحس` «اللَحْسُ باللسان»
وهو المعنى بعينِه. ومثلُه `עסק` «انشغل»: أخذنا `عسر` ولو فتحناها لبلغنا `عشق`.

**وهذه أداةُ توليدٍ لا أداةُ حكم.** تُخرِجُ كلَّ جذرٍ عربيٍّ **موجودٍ فعلًا في المعاجم**
يوافقُ هيكلَ الكلمةِ الشماليّة، ومعه معناه، **ثمّ يختارُ الباحثُ بالمعنى لا بالصوت**.

الاستعمال:
    python scripts/fan_northern_word.py לעס
    python scripts/fan_northern_word.py עסק --gloss "occupied, engaged"
    python scripts/fan_northern_word.py --file words.txt
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "Resources"

# ------------------------------------------------------------------ المروحة
#
# لكلِّ حرفٍ شماليٍّ كلُّ ما يُقابِلُه في العربيّة، مرتَّبًا بالأشهرِ أوّلًا.
# السندُ انعكاساتُ الأصواتِ الساميّةِ الأمِّ: ما دمجَه الشمالُ فرّقَته العربيّة.
FAN: dict[str, tuple[str, ...]] = {
    "א": ("ء", "ا"),
    "ב": ("ب",),
    "ג": ("ج",),
    "ד": ("د", "ذ"),                 # *d و*ḏ
    "ה": ("ه",),
    "ו": ("و",),
    "ז": ("ز", "ذ"),                 # *z و*ḏ في العبريّة
    "ח": ("ح", "خ"),                 # *ḥ و*ḫ
    "ט": ("ط", "ظ"),                 # *ṭ و*ṯ̣
    "י": ("ي", "و"),                 # الواوُ الأولى تصيرُ ياءً في العبريّة
    "כ": ("ك",),
    "ל": ("ل",),
    "מ": ("م",),
    "נ": ("ن",),
    "ס": ("س", "ش"),                 # *s و*ś في الآراميّة
    "ע": ("ع", "غ", "ض", "ح"),       # *ʕ و*ġ و*ḍ، والحاءُ باحتمالِ المؤلّف
    "פ": ("ف", "ب"),
    "צ": ("ص", "ض", "ظ", "ز"),       # *ṣ و*ḍ و*ṯ̣
    "ק": ("ق", "ك"),
    "ר": ("ر",),
    "ש": ("ش", "س", "ث"),            # *š و*ś و*ṯ
    "ת": ("ت", "ث"),                 # *t و*ṯ
}

FINALS = str.maketrans("ךםןףץ", "כמנפצ")
_DIAC = dict.fromkeys(range(0x0591, 0x05C8))
STRIP_AFFIX = (
    ("א", "suffix"),   # لاحقةُ الحالةِ الآراميّةِ المعرَّفة
    ("תא", "suffix"),  # لاحقةُ الاسمِ الآراميّةِ المؤنّثةِ المعرَّفة
    ("ה", "suffix"),   # تاءُ التأنيثِ العبريّة
)
MATRES = "והי"


def skeleton(word: str) -> str:
    w = unicodedata.normalize("NFC", word).translate(_DIAC).translate(FINALS)
    w = re.sub(r"[^א-ת]", "", w)
    for suf, _ in STRIP_AFFIX:
        if len(w) > len(suf) + 1 and w.endswith(suf):
            w = w[: -len(suf)]
            break
    return w


_AR_DIAC = dict.fromkeys(range(0x064B, 0x0653))
_AR_DIAC[0x0640] = None


def bare_ar(s: str) -> str:
    return unicodedata.normalize("NFC", str(s)).translate(_AR_DIAC).strip()


def load_arabic_roots() -> dict[str, list[tuple[str, str]]]:
    """جذرٌ عربيٌّ مجرَّد -> [(المعجم، التعريف)]. من ذخيرةِ الجذورِ المحلّيّة.

    الذخيرةُ ملفُّ parquet فيه 56,606 مادّةً من عشرةِ معاجم، أعمدتُه
    root و definition و book_name و url.
    """
    import pandas as pd

    roots: dict[str, list[tuple[str, str]]] = {}
    for path in sorted(RESOURCES.glob("arabic_roots_*/**/*.parquet")):
        df = pd.read_parquet(path)
        cols = set(df.columns)
        if "definition" not in cols:
            # ذخيرةُ الجذورِ بلا تعريفات: تُستعمَلُ لإثباتِ وجودِ الجذرِ وحدَه
            for r in df["root"]:
                key = bare_ar(r)
                if key:
                    roots.setdefault(key, [])
            continue
        book = df["book_name"] if "book_name" in cols else ["" for _ in range(len(df))]
        for r, d, b in zip(df["root"], df["definition"], book):
            key = bare_ar(r)
            if not key:
                continue
            roots.setdefault(key, []).append((str(b), bare_ar(d)[:200]))
    return roots


def fan(word: str, limit: int = 400) -> list[str]:
    sk = skeleton(word)
    if not (2 <= len(sk) <= 4):
        return []
    options = [FAN.get(c, (c,)) for c in sk]
    total = 1
    for o in options:
        total *= len(o)
    out = []
    for combo in itertools.islice(itertools.product(*options), limit):
        out.append("".join(combo))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("words", nargs="*")
    ap.add_argument("--file", help="ملفّ فيه كلمة في كلّ سطر")
    ap.add_argument("--gloss", default="", help="معنى الكلمة الشماليّة، يُطبع للمقارنة")
    ap.add_argument("--all", action="store_true", help="اعرض المرشّحات غير الموجودة أيضًا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    words = list(args.words)
    if args.file:
        words += [l.strip() for l in open(args.file, encoding="utf-8") if l.strip()]
    if not words:
        ap.error("لا كلمات")

    print("تحميلُ ذخيرةِ الجذورِ العربيّة...")
    roots = load_arabic_roots()
    print(f"جذورٌ عربيّةٌ متاحةٌ للمطابقة: {len(roots):,}\n")

    for w in words:
        sk = skeleton(w)
        cands = fan(w)
        hits = [(c, roots[c]) for c in cands if c in roots]
        print(f"═══ {w}   الهيكل: {sk}   مرشّحات: {len(cands)}"
              + (f"   [{args.gloss}]" if args.gloss else ""))
        if not hits:
            print("   لا جذرَ عربيًّا موجودًا يوافقُ الهيكل\n")
            continue
        print(f"   موجودٌ فعلًا في المعاجم: {len(hits)}\n")
        for c, entries in hits:
            book, definition = entries[0]
            print(f"   {c}   [{book[:34]}]")
            print(f"        {definition[:130]}")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
