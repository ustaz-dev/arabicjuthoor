# -*- coding: utf-8 -*-
"""استخراجُ جدولِ التقابلاتِ من المادّةِ لا من الذاكرة (2026-08-06)

**السؤالُ الذي يُجيبُه:** سألَ المؤلّفُ أعِندَنا صفوفٌ ناقصةٌ غيرُ الرِجلِ الآراميّةِ
في SIB-07. والجوابُ لا يُخمَّن: يُستخرَجُ.

**الطريقة:** كلُّ كلمتَينِ في ذخيرتَينِ مختلفتَينِ لهما **المعنى نفسُه** بنصِّ معجمِهما
هما زوجٌ مرشَّح. تُجرَّدُ الكلمتانِ إلى صوامتِهما، فإن تساوى العددُ حوذيَ الصامتُ
بالصامتِ وسُجِّلَ كلُّ تقابل. **والتقابلُ الذي يتكرّرُ في عشراتِ الأزواجِ المستقلّةِ
يُثبِتُ نفسَه**، وهو المنهجُ المقارنُ الأصليّ: الانتظامُ يُستنبَطُ من التكرارِ ولا
يُفترَضُ قبلَه.

**وحدُّها:** هذا يُخرِجُ مرشَّحًا لا حكمًا. فتطابقُ المعنى في معجمَينِ إنجليزيَّينِ
قد يكونُ ترجمةً متساهلة، والصوامتُ المتساويةُ عددًا قد تكونُ صدفة. لكنّ الوزنَ
العدديَّ يفصلُ: ما ظهرَ مرّةً ضجيج، وما ظهرَ خمسينَ مرّةً بنية.

الاستعمال:  python scripts/derive_correspondences.py [--min 4] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import os
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "Resources"

# الصوائتُ وعلاماتُها في كلِّ خطّ، تُنزَعُ قبلَ المحاذاة
STRIP = {
    # العبريّة والآراميّة: النقطُ والتعليلُ والألفُ والياءُ والواوُ حينَ تكونُ أمَّ قراءة
    "hebrew": re.compile(r"[֑-ׇ׳״\s\-׳״]"),
    "aramaic": re.compile(r"[֑-ׇ׳״\s\-׳״]"),
}
# لواحقُ الحالةِ الآراميّةِ وأداةُ التعريفِ الملحقة
ARAMAIC_STATE = re.compile(r"א$")

# الحروفُ النهائيّةُ في الخطِّ العبريِّ والآراميِّ ليست صوامتَ أخرى بل صورةٌ
# موضعيّةٌ للحرفِ نفسِه. وتركُها يُنتِجُ تقابلاتٍ وهميّةً (נ~ן، מ~ם، כ~ך، פ~ף)
# تحتلُّ رأسَ الجدولِ وتُغرِقُ الإشارةَ الحقيقيّة.
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

# الفينيقيّةُ والبونيقيّةُ مكتوبتانِ في اللقطةِ بالأبجديّةِ الفينيقيّة. نطوي
# الرسمَ إلى نظيره الشماليِّ المربّع قبلَ المحاذاة، لا إلى العربيّة، لكي يبقى
# المستخرَج واصفًا لا حاكمًا ويصحَّ اختبارُ أزواج الغرب الساميّ الأخرى.
PHOENICIAN_TO_SQUARE = str.maketrans(
    "𐤀𐤁𐤂𐤃𐤄𐤅𐤆𐤇𐤈𐤉𐤊𐤋𐤌𐤍𐤎𐤏𐤐𐤑𐤒𐤓𐤔𐤕",
    "אבגדהוזחטיכלמנסעפצקרשת",
)
SQUARE_CONSONANTS = set("אבגדהוזחטיכלמנסעפצקרשת")

AKKADIAN_TO_SQUARE = {
    "ʾ": "א", "ʔ": "א", "b": "ב", "g": "ג", "d": "ד", "h": "ה",
    "w": "ו", "z": "ז", "ḫ": "ח", "ḥ": "ח", "ṭ": "ט", "y": "י",
    "k": "כ", "l": "ל", "m": "מ", "n": "נ", "s": "ס", "š": "ש",
    "ṣ": "צ", "p": "פ", "f": "פ", "q": "ק", "r": "ר", "t": "ת",
    "ṯ": "ת", "ḏ": "ד", "ʿ": "ע",
}
AKKADIAN_VOWELS = set("aeiouāēīōūâêîôû")
AKKADIAN_MIMATION = re.compile(r"[aiuāīūâîû]m$", re.IGNORECASE)

# حروفُ المدِّ التي تُحذَفُ من الهيكلِ الصامتيِّ حينَ لا تكونُ أصلًا. تُحذَفُ في
# الوسطِ والآخرِ فقط، لا في الأوّلِ حيثُ تكونُ همزةً أو أصلًا.
MATRES = "והי"


def skeleton(word: str, lang: str) -> str:
    w = unicodedata.normalize("NFC", word)
    if lang == "akkadian":
        w = AKKADIAN_MIMATION.sub("", w)
        folded = []
        for char in w.casefold():
            if char in AKKADIAN_VOWELS:
                continue
            mapped = AKKADIAN_TO_SQUARE.get(char)
            if mapped:
                folded.append(mapped)
        w = "".join(folded)
        w = re.sub(r"(.)\1+", r"\1", w)
    rx = STRIP.get(lang)
    if rx:
        w = rx.sub("", w)
    w = w.translate(FINALS)
    if lang in {"phn", "xpu"}:
        w = w.translate(PHOENICIAN_TO_SQUARE)
        w = "".join(char for char in w if char in SQUARE_CONSONANTS)
    if lang == "aramaic":
        w = ARAMAIC_STATE.sub("", w)
    if len(w) > 2 and lang in {"akkadian", "aramaic", "hebrew", "phn", "xpu"}:
        w = w[0] + "".join(c for c in w[1:] if c not in MATRES)
    return w


def load(lang: str) -> dict[str, list[str]]:
    """المعنى المطبَّع -> قائمةُ الكلمات."""
    by_gloss: dict[str, list[str]] = collections.defaultdict(list)
    for f in glob.glob(str(RESOURCES / lang / "*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                w = str(e.get("word") or "").strip()
                if not w:
                    continue
                for s in (e.get("senses") or [])[:3]:
                    for g in (s.get("glosses") or [])[:2]:
                        g = re.sub(r"\([^)]*\)", "", str(g)).strip().lower()
                        g = re.sub(r"^(to|a|an|the)\s+", "", g).strip()
                        if 2 < len(g) < 42:
                            by_gloss[g].append(w)
    return by_gloss


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=4, help="أدنى عدد شواهد يُطبع")
    ap.add_argument("--json", help="اكتب الحصيلة إلى ملف")
    ap.add_argument("--pair", default="aramaic:hebrew", help="لسانان مفصولان بنقطتين")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    a_lang, b_lang = args.pair.split(":")
    A, B = load(a_lang), load(b_lang)
    shared = set(A) & set(B)
    print(f"{a_lang}: {sum(len(v) for v in A.values()):,} صيغة على {len(A):,} معنًى")
    print(f"{b_lang}: {sum(len(v) for v in B.values()):,} صيغة على {len(B):,} معنًى")
    print(f"معانٍ مشتركة: {len(shared):,}\n")

    corr: dict[tuple[str, str], dict[tuple[str, str], set[str]]] = collections.defaultdict(
        lambda: collections.defaultdict(set)
    )
    examined_pairs: set[tuple[str, str]] = set()
    for g in sorted(shared):
        for wa in sorted(set(A[g])):
            sa = skeleton(wa, a_lang)
            for wb in sorted(set(B[g])):
                sb = skeleton(wb, b_lang)
                if not (2 <= len(sa) <= 4) or len(sa) != len(sb):
                    continue
                if sa == sb:
                    continue  # التطابقُ التامُّ لا يُعلِّمُنا شيئًا هنا
                diff = [(x, y) for x, y in zip(sa, sb) if x != y]
                if len(diff) != 1:
                    continue  # اختلافُ صامتٍ واحدٍ فقط: هذا هو موضعُ التعلُّم
                pair = (wa, wb)
                examined_pairs.add(pair)
                corr[diff[0]][pair].add(g)

    rows = sorted(
        ((key, len(pair_map)) for key, pair_map in corr.items()),
        key=lambda item: (-item[1], item[0]),
    )
    print(f"أزواجٌ مستقلة تختلفُ في صامتٍ واحدٍ فقط: {len(examined_pairs):,}\n")
    print(f"{a_lang[:3]:>4} ~ {b_lang[:3]:<4} {'شواهد':>7}   أمثلة")
    print("-" * 74)
    shown = 0
    for (x, y), n in rows:
        if n < args.min:
            continue
        shown += 1
        ex = []
        for (wa, wb), glosses in list(corr[(x, y)].items())[:3]:
            gloss = sorted(glosses)[0]
            ex.append(f"{gloss[:18]} [{wa} ~ {wb}]")
        print(f"{x:>4} ~ {y:<4} {n:>7}   {' | '.join(ex)}")
    print(f"\nتقابلات بلغت العتبة ({args.min} شواهد): {shown} من {len(rows)}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"pair": args.pair, "pairs_examined": len(examined_pairs),
             "correspondences": [
                 {
                     "a": x,
                     "b": y,
                     "witnesses": n,
                     "examples": [
                         {"a_word": wa, "b_word": wb, "glosses": sorted(glosses)}
                         for (wa, wb), glosses in list(corr[(x, y)].items())[:12]
                     ],
                 }
                 for (x, y), n in rows]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"كُتبت الحصيلة: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
