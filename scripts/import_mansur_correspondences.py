# -*- coding: utf-8 -*-
"""مصفوفةُ الإبدالِ المقيسةُ من «التراثِ المأثور» (2026-08-13، بأمرِ المؤلّف)

**ما هذه المادّة:** الدكتور **محمّد مصطفى منصور** أعادَ قراءةَ العهدِ القديمِ
بثمانيةٍ وعشرينَ حرفًا على أنّه نصٌّ عربيٌّ بلهجةٍ قديمة، ثمرةَ ثمانٍ وثلاثينَ
سنة. والمؤلّفُ لقيَه وأتى بمادّتِه: **10,399 آيةً بثلاثةِ سطور**، سطرُ الرسمِ
الحرفيِّ وسطرُ القراءةِ وسطرُ الترجمةِ المعتمدة.

**ولماذا تدخلُ مشروعَنا:** شبكةُ الإبدالاتِ عندَنا 62 صفًّا لكلٍّ شاهدُه المسمّى،
**وليس لصفٍّ منها وزن**. فالمروحةُ تُخرِجُ مرشَّحيها بلا ترتيب، والمعنى وحدَه
يختار. وهذه المصفوفةُ تُعطي كلَّ إبدالٍ **تكرارَه المقيس**، فيصيرُ الاشتقاقُ
مرجَّحًا بعدد.

**والوزنُ ترتيبٌ لا بوّابة.** لا يُحذَفُ مرشَّحٌ لأنّ وزنَه خفيف، إنّما يتأخّرُ
في العرض. أمرُ المؤلّفِ القائم: «لا تدَعْني ولا تدَعْ نفسَك تُخرِّبُ طورَ
الاستكشافِ بقوانينَ حَذِرة».

**والمحاذاةُ على مستوى الكلمةِ لا السطر:** الملفُّ الثلاثيُّ يحفظُ حدودَ الكلماتِ
في السطرَين، فتُقابَلُ الكلمةُ بالكلمةِ ثمّ الحرفُ بالحرفِ بـ`SequenceMatcher`،
وهذا أدقُّ من محاذاةِ سطرٍ كامل. والآياتُ التي يختلفُ فيها عددُ الكلماتِ
بينَ السطرَينِ تُدوَّنُ ولا تُحاذى، فالمحاذاةُ الظنّيّةُ تصنعُ إبدالاتٍ لا وجودَ لها.

**والطبقة: استكشاف.** الأرقامُ تكراراتٌ في مادّةِ باحثٍ مسمًّى، لا أحكامًا ولا
نسبَ تحقُّقٍ منشورة.

الاستعمال:
    python scripts/import_mansur_correspondences.py
"""
from __future__ import annotations

import collections
import difflib
import json
import pathlib
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
SRC = pathlib.Path.home() / "AI Projects" / "jesus-truth-book" / "_sources"
TRILINEAR = SRC / "turath-trilinear.json"
OUT = ROOT / "data" / "mansur-correspondences.json"
SHEET = ROOT / "04-cross-linguistic" / "mansur-correspondence-matrix.md"

# الستّةُ التي لا يعرفُها الرسمُ ذو الاثنَينِ والعشرين وتُدخِلُها القراءة
SIX = "ثذخغضظ"
DIAC = dict.fromkeys(range(0x064B, 0x0653))


def bare(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(DIAC).replace("ـ", "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not TRILINEAR.exists():
        print(f"لا مادّةَ في {TRILINEAR}")
        return 1

    verses = json.loads(TRILINEAR.read_text(encoding="utf-8"))
    sub = collections.Counter()      # (حرفُ الرسم، حرفُ القراءة)
    kept = collections.Counter()     # الحرفُ بقيَ نفسَه
    added = collections.Counter()    # حرفٌ في القراءةِ بلا أصلٍ في الرسم
    dropped = collections.Counter()  # حرفٌ في الرسمِ سقطَ من القراءة
    aligned = skipped = 0
    six_skeleton = six_reading = 0

    for v in verses:
        sk = bare(str(v.get("skeleton") or "")).split()
        rd = bare(str(v.get("reading") or "")).split()
        six_skeleton += sum(c in SIX for c in "".join(sk))
        six_reading += sum(c in SIX for c in "".join(rd))
        # **لا تُحاذى آيةٌ يختلفُ فيها عددُ الكلمات**، فالمحاذاةُ الظنّيّةُ
        # تصنعُ إبدالاتٍ لا وجودَ لها وتُفسِدُ المصفوفةَ كلَّها
        if not sk or len(sk) != len(rd):
            skipped += 1
            continue
        aligned += 1
        for a, b in zip(sk, rd):
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                    None, a, b, autojunk=False).get_opcodes():
                if tag == "equal":
                    for c in a[i1:i2]:
                        kept[c] += 1
                elif tag == "replace":
                    # الاستبدالُ حرفًا بحرفٍ حينَ تساوى الطرفان، وإلّا فزيادةٌ وحذف
                    if i2 - i1 == j2 - j1:
                        for c, d in zip(a[i1:i2], b[j1:j2]):
                            sub[(c, d)] += 1
                    else:
                        for c in a[i1:i2]:
                            dropped[c] += 1
                        for c in b[j1:j2]:
                            added[c] += 1
                elif tag == "delete":
                    for c in a[i1:i2]:
                        dropped[c] += 1
                elif tag == "insert":
                    for c in b[j1:j2]:
                        added[c] += 1

    # ثباتُ كلِّ حرفٍ ومروحتُه المرجَّحة
    letters = sorted({c for c, _ in sub} | set(kept), key=lambda c: -kept[c])
    table = {}
    for c in letters:
        moves = {d: n for (a, d), n in sub.items() if a == c}
        total = kept[c] + sum(moves.values())
        if total < 20:
            continue
        table[c] = {
            "kept": kept[c],
            "moved": sum(moves.values()),
            "stability": round(100 * kept[c] / total, 1),
            "becomes": dict(sorted(moves.items(), key=lambda kv: -kv[1])),
            "dropped": dropped[c],
        }

    payload = {
        "generated_by": "scripts/import_mansur_correspondences.py",
        "layer": "استكشاف",
        "source": ("محمّد مصطفى منصور، «التراثُ المأثور»؛ محاذاةُ سطرِ الرسمِ على "
                   "سطرِ القراءةِ كلمةً بكلمةٍ ثمّ حرفًا بحرف"),
        "note": ("تكراراتٌ لا أحكام. والوزنُ يُرتِّبُ المروحةَ ولا يُغلِقُ بابًا، "
                 "فلا يُحذَفُ مرشَّحٌ لخفّةِ وزنِه."),
        "verses_total": len(verses),
        "verses_aligned": aligned,
        "verses_skipped_word_count": skipped,
        "six_sounds_in_skeleton": six_skeleton,
        "six_sounds_in_reading": six_reading,
        "letters": table,
        "top_substitutions": [
            {"from": a, "to": b, "count": n}
            for (a, b), n in sub.most_common(80)
        ],
        "added_in_reading": dict(added.most_common(24)),
        "dropped_from_skeleton": dict(dropped.most_common(24)),
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8", newline="\n")

    ratio = (six_reading / six_skeleton) if six_skeleton else 0
    print(f"آياتٌ في المادّة: {len(verses):,}   حوذيَ منها: {aligned:,}   "
          f"تُرِكَ لاختلافِ عددِ الكلمات: {skipped:,}")
    print(f"الأصواتُ الستّةُ في الرسم: {six_skeleton:,}   وفي القراءة: {six_reading:,}"
          f"   النسبة: 1 إلى {ratio:,.0f}")
    print(f"\n{'الحرف':8}{'يبقى':>8}{'يُبدَل':>8}{'الثبات':>8}   أكثرُ ما يصيرُ إليه")
    for c, r in sorted(table.items(), key=lambda kv: kv[1]["stability"]):
        top = "، ".join(f"{d}:{n}" for d, n in list(r["becomes"].items())[:5])
        print(f"{c:8}{r['kept']:>8}{r['moved']:>8}{r['stability']:>7}%   {top}")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
