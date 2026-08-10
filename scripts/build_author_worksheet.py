# -*- coding: utf-8 -*-
"""ورقةُ عملِ المؤلّف: المفهومُ الواحدُ عبرَ الألسنِ كلِّها (2026-08-09، بأمرِه)

**أمرُ المؤلّف:** «أعطِني أمثلةً ممّا رفضتَه أو لم تجدْ له صلة، من ألسنٍ كثيرة،
ومعها النطق، لعلّي أرى ما لا تراه. أنت تُفوِّتُ أشياءَ بيّنةً جدًّا».

**وهو محقٌّ، والعطبُ في العرضِ لا في المادّة.** حينَ عُرِضَت `pater` وحدَها بقيَت
الأداةُ ترتّبُ فوقَها `بتر` و`بطر`، **ولو عُرِضَ الصفُّ كاملًا لقفزَت `فطر` إلى
العينِ في لحظة**:

    pater · patḗr · fæder · faðir · fader · athair   ←   كلُّها *ph₂tḗr

فالعرضُ الصحيحُ ليس قائمةً لكلِّ لسانٍ على حِدَة، بل **المفهومُ الواحدُ في سطرٍ
واحدٍ عبرَ الفروعِ كلِّها**، ومعه المرشَّحاتُ العربيّةُ الموجودةُ فعلًا في المعاجم.

**وتُرشَّحُ المفاهيمُ الأساسيّةُ وحدَها** (الجسدُ والقرابةُ والطبيعةُ وأفعالُ
الحياةِ والعدد)، لأنّها أقلُّ ما تقترضُه الألسنُ وأكثرُ ما توارثُه، وهي مَعينُ
المقارنةِ في كلِّ مدرسةٍ تاريخيّة.

**وما يُعرَضُ هنا لم يصدُرْ فيه حكمٌ بعد.** ورقةُ نظرٍ للمؤلّف، لا طابورَ أحكام.

المخرَج: data/author-worksheet.json و05-audits/…-worksheet.md
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
import count_links as C  # noqa: E402
from readable import say  # noqa: E402

SWEEPS = ROOT / "04-cross-linguistic" / "exploration"
READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "author-worksheet.json"
SHEET = ROOT / "05-audits" / "2026-08-09-author-worksheet-core-concepts.md"

NAMES = {
    "latin": "اللاتينيّة", "ancient_greek": "اليونانيّة القديمة",
    "english_old": "الإنجليزيّة القديمة", "english_middle": "الإنجليزيّة الوسطى",
    "old_norse": "النُّرديّة القديمة", "old_irish": "الإيرلنديّة القديمة",
    "gothic": "القوطيّة", "welsh": "الويلزيّة", "persian": "الفارسيّة",
    "hebrew": "العبريّة", "aramaic": "الآراميّة", "akkadian": "الأكّاديّة",
    "coptic": "القبطيّة", "egyptian": "المصريّة القديمة",
}

# **المفرداتُ الأساسيّة.** كلُّ مفهومٍ ومعه ألفاظُه الإنجليزيّةُ كما تردُ في شروحِ
# المعاجم، ليُلتقَطَ من الشرحِ لا من ترجمةٍ نصنعُها نحن.
CONCEPTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "father": ("الأب", ("father", "male parent")),
    "mother": ("الأمّ", ("mother", "female parent")),
    "brother": ("الأخ", ("brother",)),
    "sister": ("الأخت", ("sister",)),
    "son": ("الابن", ("son",)),
    "daughter": ("البنت", ("daughter",)),
    "man": ("الرجل", ("man", "male", "husband")),
    "woman": ("المرأة", ("woman", "wife", "female")),
    "name": ("الاسم", ("name",)),
    "eye": ("العين", ("eye",)),
    "ear": ("الأذن", ("ear",)),
    "mouth": ("الفم", ("mouth",)),
    "tooth": ("السنّ", ("tooth", "teeth")),
    "tongue": ("اللسان", ("tongue",)),
    "hand": ("اليد", ("hand",)),
    "foot": ("القدم", ("foot", "feet")),
    "head": ("الرأس", ("head", "skull")),
    "heart": ("القلب", ("heart",)),
    "blood": ("الدم", ("blood",)),
    "bone": ("العظم", ("bone",)),
    "skin": ("الجلد", ("skin", "hide")),
    "hair": ("الشعر", ("hair",)),
    "horn": ("القرن", ("horn", "antler")),
    "water": ("الماء", ("water",)),
    "fire": ("النار", ("fire", "flame")),
    "sun": ("الشمس", ("sun",)),
    "moon": ("القمر", ("moon",)),
    "star": ("النجم", ("star",)),
    "sky": ("السماء", ("sky", "heaven")),
    "earth": ("الأرض", ("earth", "ground", "soil", "land")),
    "stone": ("الحجر", ("stone", "rock")),
    "mountain": ("الجبل", ("mountain",)),
    "sea": ("البحر", ("sea", "ocean")),
    "river": ("النهر", ("river", "stream")),
    "wind": ("الريح", ("wind",)),
    "rain": ("المطر", ("rain",)),
    "night": ("الليل", ("night",)),
    "day": ("النهار", ("day", "daytime")),
    "year": ("السنة", ("year",)),
    "tree": ("الشجر", ("tree",)),
    "seed": ("البذر", ("seed", "grain")),
    "leaf": ("الورق", ("leaf",)),
    "root": ("الجذر", ("root of a plant", "root")),
    "salt": ("الملح", ("salt",)),
    "milk": ("اللبن", ("milk",)),
    "bread": ("الخبز", ("bread", "loaf")),
    "house": ("البيت", ("house", "dwelling", "home")),
    "door": ("الباب", ("door", "gate")),
    "road": ("الطريق", ("road", "path", "way")),
    "fish": ("السمك", ("fish",)),
    "bird": ("الطير", ("bird",)),
    "dog": ("الكلب", ("dog",)),
    "cow": ("البقر", ("cow", "ox", "cattle")),
    "sheep": ("الغنم", ("sheep", "ewe", "ram")),
    "snake": ("الحيّة", ("snake", "serpent")),
    "eat": ("الأكل", ("to eat", "eat")),
    "drink": ("الشرب", ("to drink", "drink")),
    "see": ("الرؤية", ("to see", "see", "look")),
    "hear": ("السمع", ("to hear", "hear", "listen")),
    "know": ("المعرفة", ("to know", "know")),
    "die": ("الموت", ("to die", "death", "die")),
    "kill": ("القتل", ("to kill", "kill", "slay")),
    "give": ("العطاء", ("to give", "give")),
    "take": ("الأخذ", ("to take", "take", "seize", "grasp")),
    "come": ("المجيء", ("to come", "come", "arrive")),
    "go": ("الذهاب", ("to go", "go", "walk")),
    "stand": ("القيام", ("to stand", "stand", "rise")),
    "sit": ("القعود", ("to sit", "sit")),
    "sleep": ("النوم", ("to sleep", "sleep")),
    "say": ("القول", ("to say", "say", "speak", "tell")),
    "cut": ("القطع", ("to cut", "cut", "sever")),
    "split": ("الشقّ", ("to split", "split", "cleave", "break open")),
    "bind": ("الربط", ("to bind", "bind", "tie")),
    "burn": ("الحرق", ("to burn", "burn")),
    "wash": ("الغسل", ("to wash", "wash")),
    "one": ("الواحد", ("one",)),
    "two": ("الاثنان", ("two",)),
    "three": ("الثلاثة", ("three",)),
    "seven": ("السبعة", ("seven",)),
    "ten": ("العشرة", ("ten",)),
    "hundred": ("المئة", ("hundred",)),
    "new": ("الجديد", ("new",)),
    "old": ("القديم", ("old", "aged", "ancient")),
    "big": ("الكبير", ("big", "large", "great")),
    "small": ("الصغير", ("small", "little")),
    "long": ("الطويل", ("long",)),
    "good": ("الحسن", ("good",)),
    "black": ("الأسود", ("black",)),
    "white": ("الأبيض", ("white",)),
    "red": ("الأحمر", ("red",)),
    "green": ("الأخضر", ("green",)),
    "full": ("الملء", ("full",)),
    "cold": ("البرد", ("cold",)),
    "warm": ("الحرّ", ("warm", "hot")),
    "king": ("الملك", ("king", "ruler")),
    "god": ("الإله", ("god", "deity")),
    "heart_mind": ("العقل", ("mind", "wit", "understanding")),
}


def concept_of(gloss: str) -> str | None:
    """أوّلُ مفهومٍ أساسيٍّ يذكرُه شرحُ الكلمة. تُطلَبُ الكلمةُ مستقلّةً لا جزءًا
    من كلمةٍ أخرى، فلا يلتقطُ `earth` من `earthenware`."""
    g = " " + re.sub(r"[^a-z ]", " ", str(gloss).lower()) + " "
    for key, (_, terms) in CONCEPTS.items():
        for t in terms:
            if f" {t} " in g:
                return key
    return None


def carded_words() -> set[str]:
    """ما صدرَ فيه حكمٌ بالفعل، فلا يُعرَضُ على المؤلّفِ مرّةً ثانية."""
    out: set[str] = set()
    for path in READINGS.glob("*.md"):
        text = C.bare(path.read_text(encoding="utf-8"))
        for raw in C.CARD_SPLIT.split(text)[1:]:
            if C.scan_card(raw):
                out.add(raw.split("\n", 1)[0].strip().lower()[:80])
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--max-per-cell", type=int, default=2)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    carded = carded_words()
    # مفهوم -> لسان -> صفوف
    grid: dict[str, dict[str, list[dict]]] = collections.defaultdict(
        lambda: collections.defaultdict(list))
    seen: set[tuple[str, str, str]] = set()

    for f in sorted(glob.glob(str(SWEEPS / "*sweep-*.json"))):
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        # بعضُ المخرَجاتِ القديمةِ قائمةٌ لا قاموس، فتُتَجاوَزُ بلا ضجيج
        if not isinstance(d, dict):
            continue
        lang = d.get("language") or pathlib.Path(f).stem.split("-")[-1]
        if lang not in NAMES:
            continue
        ancestor_pass = "ancestor" in pathlib.Path(f).stem
        for bucket in ("both", "sound_only"):
            for r in d.get(bucket, []):
                key = concept_of(r.get("gloss", ""))
                if not key:
                    continue
                word = str(r.get("branch", "")).strip()
                if not word or (lang, key, word) in seen:
                    continue
                if any(word.lower() in c for c in carded):
                    continue
                seen.add((lang, key, word))
                cands = [c for c in r.get("candidates_found", []) if c]
                # **النطقُ يُحسَبُ هنا ولا يُؤخَذُ من المسح**، فمسحُ الصورةِ
                # المستعادةِ لا يخزّنُه، فكانت اليونانيّةُ والويلزيّةُ تخرجانِ
                # بخطِّهما بلا لفظٍ يُقرَأ، وذلك يحجبُ الكلمةَ عن المؤلّف.
                spoken = (r.get("say") or "").split("(")[0].strip()
                if not spoken or spoken == word:
                    spoken = say(word).split("(")[0].strip()
                grid[key][lang].append({
                    "word": word,
                    "say": spoken if spoken != word else "",
                    "gloss": str(r.get("gloss", ""))[:70],
                    "ancestor": r.get("ancestor", ""),
                    "candidates": cands[:10],
                    "from_ancestor": ancestor_pass,
                    "judged": bucket == "both",
                })

    # **المرشَّحُ الذي يظهرُ في كلِّ مفهومٍ لا يدلُّ على شيء.** المروحاتُ واسعةٌ
    # فيتقاطعُ فيها الغثُّ، والمفيدُ ما **تركّزَ في مفهومٍ واحدٍ واقترحَته فروعٌ
    # كثيرة**. فيُحسَبُ لكلِّ مرشَّحٍ في كم مفهومٍ ظهر، ثمّ يُرجَّحُ بعددِ الفروعِ
    # مقسومًا على انتشارِه في المفاهيم.
    spread = collections.Counter()
    for key, langs in grid.items():
        seen_here = set()
        for items in langs.values():
            for it in items:
                seen_here.update(it["candidates"])
        spread.update(seen_here)

    rows = []
    for key, (ar_name, _) in CONCEPTS.items():
        langs = grid.get(key, {})
        if len(langs) < 2:          # مفهومٌ في لسانٍ واحدٍ لا يُري صفًّا
            continue
        cells = {}
        by_branch = collections.defaultdict(set)
        for lang, items in langs.items():
            items.sort(key=lambda x: (not x["from_ancestor"], -len(x["candidates"])))
            cells[lang] = items[:args.max_per_cell]
            for it in cells[lang]:
                for c in it["candidates"]:
                    by_branch[c].add(lang)
        scored = []
        for cand, branches in by_branch.items():
            if len(branches) < 2:
                continue
            focus = len(branches) / spread.get(cand, 1)   # تركُّزٌ لا انتشار
            scored.append((focus, len(branches), cand))
        scored.sort(reverse=True)
        rows.append({
            "concept": key, "concept_ar": ar_name,
            "languages": len(langs),
            "cells": cells,
            "shared_candidates": [
                f"{c} ({n})" for _, n, c in scored[:8]
            ],
            "top_focus": [c for _, _, c in scored[:4]],
        })
    # الصفُّ الذي يجتمعُ فيه مرشَّحٌ عندَ فروعٍ كثيرةٍ وهو غيرُ منتشرٍ أولى بالنظر
    rows.sort(key=lambda r: (-(len(r["top_focus"]) and r["languages"]), r["concept"]))

    OUT.write_text(json.dumps({
        "generated_by": "scripts/build_author_worksheet.py",
        "note": "ورقةُ نظرٍ للمؤلّف. لا حكمَ فيها ولا عدَّ منشور.",
        "concepts": len(rows), "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# ورقةُ عمل: المفهومُ الواحدُ عبرَ الألسن، 2026-08-09",
        "",
        "**الطبقة:** استكشاف. **ورقةُ نظرٍ لا طابورَ أحكام، ولم يصدُرْ في شيءٍ منها حكم.**",
        "",
        "بأمرِ المؤلّف. وسببُ هذا الشكلِ أنّ الأداةَ حينَ عرضَت `pater` وحدَها رتّبَت",
        "فوقَها `بتر` و`بطر`، ولو عُرِضَ الصفُّ كاملًا لقفزَت `فطر` إلى العينِ في لحظة.",
        "",
        "**كيف تُقرَأ:** في كلِّ صفٍّ مفهومٌ واحد، وتحتَه ما تقولُه الفروعُ فيه بنطقِه،",
        "ثمّ **المرشَّحاتُ العربيّةُ الموجودةُ فعلًا في المعاجم** التي فتحَتها المروحة.",
        "والمشترَكُ منها بينَ فرعَينِ فأكثرَ مذكورٌ في آخرِ كلِّ صفٍّ لأنّه أثمنُها.",
        "",
        f"**المفاهيم: {len(rows)}.** مرتَّبةٌ بعددِ الفروعِ التي شهدَت فيها.",
        "",
    ]
    for r in rows:
        lines.append(f"## {r['concept_ar']} · {r['concept']}   ({r['languages']} فروع)")
        lines.append("")
        lines.append("| الفرع | الكلمة | نطقُها | معناها | المرشَّحاتُ العربيّةُ في المعاجم |")
        lines.append("|---|---|---|---|---|")
        for lang, items in r["cells"].items():
            for it in items:
                anc = f" ← \\*{it['ancestor']}" if it["ancestor"] else ""
                lines.append(
                    f"| {NAMES[lang]} | `{it['word']}`{anc} | {it['say']} | "
                    f"{it['gloss']} | {' · '.join(it['candidates']) or '-'} |")
        if r["shared_candidates"]:
            lines.append("")
            lines.append(f"**المشترَكُ بينَ فرعَينِ فأكثر:** {' · '.join(r['shared_candidates'])}")
        lines.append("")
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"مفاهيمُ فيها فرعانِ فأكثر: {len(rows)}")
    print(f"{'المفهوم':22}{'فروع':>6}  أقوى المشترَك")
    for r in rows[:26]:
        print(f"  {r['concept_ar']:20}{r['languages']:>5}  {' · '.join(r['shared_candidates'][:7])}")
    print(f"\nكُتب: {SHEET.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
