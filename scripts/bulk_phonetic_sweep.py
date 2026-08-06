# -*- coding: utf-8 -*-
"""المسحُ الصوتيُّ الشامل: قابِلْ أوّلًا ثمّ انظُرْ في المعنى (2026-08-06)

**العطبُ الذي يُصلِحُه، بنصِّ المؤلّف:** «ابدأْ بمقابلةِ الكلماتِ التي قد تكونُ نفسَها
صوتيًّا، ثمّ انظُرْ هل في معانيها صلة».

وطريقةُ المشروعِ كلُّها كانت عكسَ ذلك: كلمةٌ من طابورٍ نحنُ رتّبناه، ثمّ توليدُ
مرشّحينَ لها، ثمّ فحص. **ولم يُجرَ يومًا مسحٌ شاملٌ يسألُ: أيُّ كلماتِ الفرعِ لها جذرٌ
عربيٌّ بالهيكلِ نفسِه؟** فبقيَ البديهيُّ مختبئًا خلفَ ترتيبِ الطابور.

**الطريقة:** لكلِّ كلمةٍ في ذخيرةِ الفرع، يُجرَّدُ هيكلُها الصامتيُّ، وتُفتَحُ مروحتُها
العربيّةُ كاملةً (فالعربيّةُ حفِظَت ما دمجَه الفرع)، ويُبحَثُ عن كلِّ مرشّحٍ **موجودٍ
فعلًا في معاجمِ العربيّة**. ثمّ يُقاسُ تداخلُ المعنى بينَ الطرفَين.

**ويُخرِجُ ثلاثَ طبقات:**
  1. **مطابقةُ صوتٍ ومعنًى معًا:** الهيكلُ يوافقُ والمعنى يتقاطع. أثمنُها.
  2. **مطابقةُ صوتٍ بلا تقاطعِ معنًى:** تحتاجُ نظرَ إنسانٍ، فقد يكونُ المدارُ بعيدًا.
  3. **بلا مرشّحٍ موجود:** تُسجَّلُ عددًا فقط.

**ولا يُصدِرُ حكمًا.** يُخرِجُ طابورَ نظرٍ مرتَّبًا بقوّةِ الإشارة.

الاستعمال:
    python scripts/bulk_phonetic_sweep.py --lang aramaic
    python scripts/bulk_phonetic_sweep.py --lang hebrew --min-overlap 1
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402
from readable import say  # noqa: E402

OUT_DIR = ROOT / "04-cross-linguistic" / "exploration"

# كلماتٌ إنجليزيّةٌ لا تحملُ معنًى مميّزًا فلا تُحسَبُ في التقاطع
STOP = {
    "a", "an", "the", "to", "of", "or", "and", "in", "on", "at", "for", "with",
    "be", "is", "are", "was", "were", "it", "its", "that", "this", "as", "by",
    "from", "one", "any", "some", "used", "esp", "especially", "person", "thing",
    "something", "someone", "make", "made", "form", "kind", "sort", "type",
}
WORD = re.compile(r"[a-z]+")


def words_of(text: str) -> set[str]:
    return {w for w in WORD.findall(str(text).lower()) if len(w) > 2 and w not in STOP}


def load_branch(lang: str) -> list[dict]:
    rows = []
    for f in glob.glob(str(ROOT / "Resources" / lang / "*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                w = str(e.get("word") or "").strip()
                if not w:
                    continue
                glosses = [
                    str(g) for s in (e.get("senses") or [])[:4]
                    for g in (s.get("glosses") or [])[:2]
                ]
                if not glosses:
                    continue
                rows.append({"word": w, "glosses": glosses})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="aramaic")
    ap.add_argument("--min-overlap", type=int, default=1,
                    help="أدنى عدد كلمات معنى مشتركة لعدّ الصفّ مطابقًا في المعنى")
    ap.add_argument("--max-cands", type=int, default=12,
                    help="تجاهل الكلمات التي تفتح مروحة أوسع من هذا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("تحميلُ ذخيرةِ الجذورِ العربيّة...")
    ar = F.load_arabic_roots()
    ar_words = {r: words_of(" ".join(d for _, d in e[:3])) for r, e in ar.items()}
    print(f"جذورٌ عربيّةٌ: {len(ar):,}")

    rows = load_branch(args.lang)
    print(f"مداخلُ {args.lang}: {len(rows):,}\n")

    both, sound_only, none = [], [], 0
    for r in rows:
        sk = F.skeleton(r["word"])
        if not (2 <= len(sk) <= 4):
            continue
        cands = F.fan(sk)
        if not cands or len(cands) > args.max_cands:
            continue
        hits = [c for c in cands if c in ar]
        if not hits:
            none += 1
            continue
        branch_words = words_of(" ".join(r["glosses"]))
        scored = []
        for c in hits:
            shared = branch_words & ar_words.get(c, set())
            scored.append((c, len(shared), sorted(shared)[:4]))
        scored.sort(key=lambda x: -x[1])
        best = scored[0]
        row = {
            "branch": r["word"], "say": say(r["word"]), "skeleton": sk,
            "gloss": "; ".join(r["glosses"][:2])[:90],
            "candidates_found": [c for c, _, _ in scored],
            "best": best[0], "overlap": best[1], "shared": best[2],
        }
        (both if best[1] >= args.min_overlap else sound_only).append(row)

    both.sort(key=lambda r: -r["overlap"])
    print(f"مطابقةُ صوتٍ ومعنًى معًا: {len(both):,}")
    print(f"مطابقةُ صوتٍ بلا تقاطعِ معنًى: {len(sound_only):,}")
    print(f"بلا مرشّحٍ موجودٍ في المعاجم: {none:,}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"phonetic-sweep-{args.lang}"
    json.dump({"language": args.lang, "both": both, "sound_only": sound_only[:3000]},
              open(base.with_suffix(".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    lines = [
        f"# المسحُ الصوتيُّ الشامل: {args.lang}",
        "",
        "**الطبقة:** استكشاف. **لا حكمَ ولا عدَّ ولا نشر.**",
        "",
        "**الطريقة:** قُوبِلَ كلُّ مدخلٍ في الذخيرةِ بمروحتِه العربيّةِ كاملة، وأُبقيَ",
        "المرشَّحُ **الموجودُ فعلًا في المعاجم**، ثمّ قِيسَ تقاطعُ المعنى بينَ الطرفَين.",
        "**الصوتُ يُقابِلُ أوّلًا والمعنى يحكُمُ بعدَه**، وهذا عكسُ ما كنّا نفعل.",
        "",
        f"**مطابقةُ صوتٍ ومعنًى معًا: {len(both):,}** · مطابقةُ صوتٍ وحدَه: {len(sound_only):,}",
        "",
        "| كلمةُ الفرع | نطقُها | معناها | العربيّ | تقاطعُ المعنى | مرشّحاتٌ أخرى |",
        "|---|---|---|---|---|---|",
    ]
    for r in both[:600]:
        others = " · ".join(c for c in r["candidates_found"][1:6])
        lines.append(
            f"| `{r['branch']}` | {r['say']} | {r['gloss']} | **{r['best']}** | "
            f"{r['overlap']}: {' '.join(r['shared'])} | {others or '-'} |"
        )
    base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كُتب: {base.with_suffix('.md').relative_to(ROOT).as_posix()}")

    print("\nأقوى عشرين بتقاطعِ المعنى:")
    for r in both[:20]:
        print(f"   {r['branch']:10} {r['say'][:20]:22} {r['gloss'][:34]:36} "
              f"~ {r['best']:6} [{' '.join(r['shared'])}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
