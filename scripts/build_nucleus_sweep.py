# -*- coding: utf-8 -*-
"""المسحُ النوويُّ: وحدةُ المسحِ النواةُ الثنائيّةُ لا الجذر (2026-08-19)

**المرحلةُ ج من خطّةِ 2026-08-18، وهي بابُ توسعةٍ لا بابُ احتياط.** دستورُ
المشروعِ نفسُه يقول: الجذرُ الثلاثيُّ طورٌ متأخّرٌ يبقى حيثُ قرُبَ الفرعُ،
والنواةُ الثنائيّةُ أقدمُ فهي ما يبقى حينَ يبعُد. ومسحُنا الجاري وحدتُه
الجذرُ الكاملُ، فطبقةُ النواةِ تفوتُه **بالبناءِ** في الفروعِ البعيدةِ التي
هي موطنُها المتوقَّع. هذا المسحُ يفتحُ تلك الطبقة:

    كلمةُ الفرعِ ← لبُّها الصامتُ ← أزواجُه الثنائيّةُ عبرَ مراوحِ الحروفِ
    ← ما وقعَ منها في ديوانِ النوى الـ455 ← غربالُ المعنى بطريقَين

**وطريقا المعنى يُسجَّلانِ باسمَيهما ولا يُخلَطان:**
1. `bridge`: تقاطعُ كلماتِ شرحِ الفرعِ بكلماتِ النواةِ الإنجليزيّةِ من جسرِ
   ويكاموس (`data/en-ar-bridge.json`، root_head).
2. `event`: تقاطعُها بكلماتِ قراءةِ النواةِ المركَّبةِ الإنجليزيّةِ من ديوانِ
   النوى نفسِه حيثُ وُجِدَت، فالنظريّةُ (الحدثُ هو المعنى) هي الغربال.

**طبقةُ استكشافٍ محضة**: حوضُ مرشَّحينَ للقارئِ، لا حكمَ ولا عدَّ ولا نشرَ
رقمٍ منه. ولا سقوفَ صامتة: يُكتَبُ الحوضُ كلُّه بمجاميعِه.

الاستعمال:
    python scripts/build_nucleus_sweep.py --lang gothic
    python scripts/build_nucleus_sweep.py --lang old_irish --probe
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as F  # noqa: E402

OUT_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICONS = ROOT / "data" / "branch-lexicons"

STOP = {
    "the", "a", "an", "of", "to", "or", "and", "in", "on", "for", "with",
    "by", "at", "as", "is", "be", "was", "are", "it", "its", "one", "who",
    "that", "which", "used", "form", "type", "kind", "any", "some", "etc",
    "especially", "usually", "often", "made", "making", "person", "thing",
    "something", "someone", "act", "state", "quality", "manner", "way",
}


def words_of(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", str(text).lower())
            if len(w) > 2 and w not in STOP}


def load_nuclei() -> dict[str, dict]:
    lv = json.load((ROOT / "data" / "juthoor-core-levels.json")
                   .open(encoding="utf-8"))["levels"]["level_2_binary_nuclei"]
    out = {}
    for e in lv["nuclei"]:
        en = words_of(" ".join(str(e.get(k, "")) for k in
                               ("composed_reading_en",)))
        out[e["nucleus"]] = {
            "reading_ar": e.get("jabal_lexicon_reading_ar")
                          or e.get("composed_reading_ar", ""),
            "event_en": en,
        }
    return out


def load_bridge() -> dict[str, set[str]]:
    b = json.load((ROOT / "data" / "en-ar-bridge.json").open(encoding="utf-8"))
    return {root: set(toks) for root, toks in b["root_head"].items()
            if len(re.sub(r"[^ء-ي]", "", root)) == 2}


def candidate_nuclei(word: str, script: str, table: dict) -> dict[str, str]:
    """أزواجُ النواةِ المرشَّحةُ من هياكلِ الكلمةِ كلِّها، بوسمِ مصدرِ كلٍّ."""
    sk_variants: list[tuple[list[str], str]] = []
    base = F.skeleton(word, script)
    if base:
        sk_variants.append((base, "كما وردَت"))
    if script in {"latin", "germanic"}:
        sk_variants += F.oe_skeletons(word, script)
        sk_variants += F.latin_stem_skeletons(word, script)
    out: dict[str, str] = {}
    for sk, label in sk_variants:
        cons = [c for c in sk]
        pairs = []
        if len(cons) == 2:
            pairs.append((cons[0], cons[1], "الهيكلُ نفسُه"))
        for i in range(len(cons) - 1):
            pairs.append((cons[i], cons[i + 1], f"الزوجُ المتجاورُ {i+1}"))
        if len(cons) >= 3:
            pairs.append((cons[0], cons[-1], "الطرفانِ (قاعدةُ خانةِ المدّ)"))
        for a, b, why in pairs:
            for ar1 in table.get(a, ()):
                for ar2 in table.get(b, ()):
                    nuc = ar1 + ar2
                    if nuc not in out:
                        out[nuc] = f"{label}؛ {why}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--probe", action="store_true",
                    help="اطبع عيّنةً ولا تكتبْ ملفًّا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    nuclei = load_nuclei()
    bridge = load_bridge()
    lex = json.load((LEXICONS / f"{args.lang}.json").open(encoding="utf-8"))
    script = "latin"
    table = F.FANS[script]

    both, sound_only = [], []
    for e in lex["entries"]:
        word, gloss = e.get("word", ""), e.get("en", "")
        if not word or not gloss:
            continue
        # القوطيّةُ وأخواتُها بخطِّها الأصليِّ في `word` ورومنتُها في `read`،
        # والهيكلُ اللاتينيُّ يعودُ من الخطِّ الأصليِّ فارغًا فيموتُ المسحُ صفرًا
        text = word if F.skeleton(word, script) else e.get("read", "")
        if not text:
            continue
        cands = candidate_nuclei(text, script, table)
        hits = {n: how for n, how in cands.items() if n in nuclei}
        if not hits:
            continue
        gtoks = words_of(gloss)
        best = None
        for n, how in hits.items():
            via = []
            shared_b = gtoks & bridge.get(n, set())
            shared_e = gtoks & nuclei[n]["event_en"]
            if shared_b:
                via.append(("bridge", sorted(shared_b)[:4]))
            if shared_e:
                via.append(("event", sorted(shared_e)[:4]))
            if via and (best is None or len(via) > len(best[2])):
                best = (n, how, via)
        row = {
            "branch": word, "read": e.get("read", ""), "gloss": gloss[:120],
            "nuclei_found": sorted(hits),
        }
        if best:
            n, how, via = best
            row.update({
                "best_nucleus": n, "how": how,
                "reading_ar": nuclei[n]["reading_ar"][:100],
                "via": [{"path": p, "shared": s} for p, s in via],
            })
            both.append(row)
        else:
            sound_only.append(row)

    print(f"{args.lang}: نواةٌ بصوتٍ ومعنًى: {len(both):,} · "
          f"نواةٌ بصوتٍ فقط: {len(sound_only):,}")
    if args.probe:
        for r in both[:10]:
            via = "؛ ".join(f"{v['path']}:{','.join(v['shared'][:3])}"
                            for v in r["via"])
            print(f"  {r['branch']:14} «{r['gloss'][:34]:34}» ~ "
                  f"{r['best_nucleus']} ({r['reading_ar'][:30]}) [{via}]")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"nucleus-sweep-{args.lang}.json"
    out.write_text(json.dumps({
        "language": args.lang,
        "layer": "استكشاف؛ حوضُ مرشَّحي نواةٍ للقارئ، لا حكمَ ولا عدّ",
        "note": "وحدةُ المسحِ النواةُ الثنائيّة؛ طريقا المعنى bridge/event "
                "موسومانِ ولا يُخلَطان؛ لا سقوفَ صامتة",
        "both_total": len(both), "sound_only_total": len(sound_only),
        "both": both, "sound_only": sound_only,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"كُتب: {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
