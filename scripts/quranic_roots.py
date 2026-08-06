# -*- coding: utf-8 -*-
"""جردُ الجذورِ القرآنيّةِ ومصفاةُ الأصالة (2026-08-06، بقرارِ المؤلّف)

**القاعدةُ النافذةُ بنصِّ المؤلّف:** «كلُّ كلمةٍ وردَت في القرآنِ فهي عربيّةٌ محضةٌ
لا مقترَضة». فالجذرُ المشهودُ في القرآنِ لا يُحكَمُ عليه بالاقتراضِ من فرعٍ آخرَ
مهما قالَ المعجمُ الأجنبيّ، وإذا وُجِدَ شبَهٌ بينَه وبينَ صورةٍ في فرعٍ **فالاتّجاهُ
من العربيّةِ إلى الفرعِ أو من الأصلِ المشتركِ إلى كليهما، لا من الفرعِ إلى العربيّة**.

**العطبُ الذي أوجبَها:** رُدَّت بطاقةُ `תגרא` الآراميّةِ بحجّةِ أنّ «التاجر» العربيّةَ
مقترَضةٌ من الآراميّةِ عن الأكديّةِ tamkāru. والجذرُ **تجر** قرآنيٌّ مشهود: «فما رَبِحَت
تِجارَتُهم» و«تِجارةً عن تَراضٍ» و«هل أدُلُّكم على تِجارةٍ». **فالحكمُ بالاقتراضِ ساقطٌ
بالقاعدة**، ويُعادُ النظرُ في البطاقةِ على أنّها إمّا إرثٌ مشتركٌ وإمّا خروجٌ من العربيّة.

الاستعمال:
    python scripts/quranic_roots.py --build          يبني الجرد
    python scripts/quranic_roots.py تجر عشق لحس      يسأل عن جذور
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
MORPH = ROOT / "Resources" / "qac_morphology" / "quran-morphology.txt"
OUT = ROOT / "data" / "quranic-roots.json"

_DIAC = dict.fromkeys(range(0x064B, 0x0653))
_DIAC[0x0640] = None

# صرفُ القرآنِ يكتبُ الجذرَ برومنةِ Buckwalter في الحقلِ FEATURES هكذا: ROOT:tjr
BW = {
    "'": "ء", "|": "آ", ">": "أ", "&": "ؤ", "<": "إ", "}": "ئ", "A": "ا",
    "b": "ب", "p": "ة", "t": "ت", "v": "ث", "j": "ج", "H": "ح", "x": "خ",
    "d": "د", "*": "ذ", "r": "ر", "z": "ز", "s": "س", "$": "ش", "S": "ص",
    "D": "ض", "T": "ط", "Z": "ظ", "E": "ع", "g": "غ", "f": "ف", "q": "ق",
    "k": "ك", "l": "ل", "m": "م", "n": "ن", "h": "ه", "w": "و", "y": "ي",
    "Y": "ى",
}
RX_ROOT = re.compile(r"ROOT:([^|\s]+)")


def bw_to_arabic(s: str) -> str:
    return "".join(BW.get(c, c) for c in s)


def bare(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(_DIAC)


def build() -> dict:
    if not MORPH.is_file():
        raise SystemExit(f"لا يوجد ملفُّ الصرفِ القرآنيّ: {MORPH}")
    roots: dict[str, int] = {}
    for line in MORPH.read_text(encoding="utf-8", errors="replace").splitlines():
        m = RX_ROOT.search(line)
        if not m:
            continue
        r = bw_to_arabic(m.group(1))
        roots[r] = roots.get(r, 0) + 1
    payload = {
        "source": str(MORPH.relative_to(ROOT).as_posix()),
        "rule": (
            "كلُّ جذرٍ في هذا الجردِ عربيٌّ محضٌ بقرارِ المؤلّفِ 2026-08-06، "
            "فلا يُحكَمُ عليه بالاقتراضِ من فرعٍ آخر."
        ),
        "roots": len(roots),
        "by_root": dict(sorted(roots.items(), key=lambda kv: -kv[1])),
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    return payload


def load() -> dict:
    if not OUT.is_file():
        return build()
    return json.loads(OUT.read_text(encoding="utf-8"))


def is_quranic(root: str) -> bool:
    return bare(root) in {bare(k) for k in load()["by_root"]}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--build", action="store_true")
    ap.add_argument("roots", nargs="*")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    data = build() if args.build else load()
    print(f"جذورٌ قرآنيّةٌ في الجرد: {data['roots']:,}   المصدر: {data['source']}")
    if not args.roots:
        top = list(data["by_root"].items())[:12]
        print("\nأكثرُها ورودًا:")
        for r, n in top:
            print(f"   {r:8} {n:5}")
        return 0

    print()
    index = {bare(k): v for k, v in data["by_root"].items()}
    for r in args.roots:
        n = index.get(bare(r))
        if n:
            print(f"   {r:8} قرآنيّ، {n} موضعًا  ==> عربيٌّ محضٌ، لا يُحكَمُ عليه بالاقتراض")
        else:
            print(f"   {r:8} ليس في جردِ القرآن")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
