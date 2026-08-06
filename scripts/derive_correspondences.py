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

# حروفُ المدِّ التي تُحذَفُ من الهيكلِ الصامتيِّ حينَ لا تكونُ أصلًا. تُحذَفُ في
# الوسطِ والآخرِ فقط، لا في الأوّلِ حيثُ تكونُ همزةً أو أصلًا.
MATRES = "והי"


def skeleton(word: str, lang: str) -> str:
    w = unicodedata.normalize("NFC", word)
    rx = STRIP.get(lang)
    if rx:
        w = rx.sub("", w)
    w = w.translate(FINALS)
    if lang == "aramaic":
        w = ARAMAIC_STATE.sub("", w)
    if len(w) > 2:
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

    corr: dict[tuple[str, str], collections.Counter] = collections.defaultdict(collections.Counter)
    pairs = 0
    for g in shared:
        for wa in set(A[g]):
            sa = skeleton(wa, a_lang)
            for wb in set(B[g]):
                sb = skeleton(wb, b_lang)
                if not (2 <= len(sa) <= 4) or len(sa) != len(sb):
                    continue
                if sa == sb:
                    continue  # التطابقُ التامُّ لا يُعلِّمُنا شيئًا هنا
                diff = [(x, y) for x, y in zip(sa, sb) if x != y]
                if len(diff) != 1:
                    continue  # اختلافُ صامتٍ واحدٍ فقط: هذا هو موضعُ التعلُّم
                pairs += 1
                corr[diff[0]][g] += 1

    rows = sorted(((k, len(v)) for k, v in corr.items()), key=lambda kv: -kv[1])
    print(f"أزواجٌ تختلفُ في صامتٍ واحدٍ فقط: {pairs:,}\n")
    print(f"{a_lang[:3]:>4} ~ {b_lang[:3]:<4} {'شواهد':>7}   أمثلة")
    print("-" * 74)
    shown = 0
    for (x, y), n in rows:
        if n < args.min:
            continue
        shown += 1
        ex = list(corr[(x, y)])[:3]
        print(f"{x:>4} ~ {y:<4} {n:>7}   {' | '.join(e[:20] for e in ex)}")
    print(f"\nتقابلات بلغت العتبة ({args.min} شواهد): {shown} من {len(rows)}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"pair": args.pair, "pairs_examined": pairs,
             "correspondences": [
                 {"a": x, "b": y, "witnesses": n, "glosses": list(corr[(x, y)])[:12]}
                 for (x, y), n in rows]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"كُتبت الحصيلة: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
