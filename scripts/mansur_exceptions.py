# -*- coding: utf-8 -*-
"""استثناءاتُ الرواسي في مادّةِ منصور (2026-08-13، بأمرِ المؤلّف)

**أمرُ المؤلّفِ بنصِّه:** «استخرِجْ قائمةَ الاستثناءات: الحروفُ ل و ر ن م ب ك ت ق
تبقى على حالها 94 إلى 98 بالمئة. أخرِجْ لي المواضعَ التي تحرّكت فيها، الاثنَينِ
إلى الستّةِ بالمئة. **هذه أوّلُ ما يستحقُّ النظر، لأنّ فيها ما لا تُفسّرُه القاعدةُ
العامّة. النُدرةُ إشارةٌ لا خطأ**».

**ولماذا هي أثمنُ من الكثرة:** الحرفُ الذي يبقى نفسَه في 99.6% لا يُعلِّمُنا شيئًا
حينَ يبقى، فبقاؤُه هو القاعدة. أمّا حينَ يتحرَّكُ في أربعةٍ من ألفٍ فهناك سببٌ:
إمّا لهجةٌ، وإمّا خطأُ نسخٍ قديم، وإمّا صفُّ إبدالٍ حقيقيٌّ نادرٌ لم نُدوِّنْه،
وإمّا ضوضاءُ محاذاة. **والأربعةُ أبوابٌ يستحقُّ كلٌّ منها أن يُفتَحَ ويُقرَأ.**

**والمخرَجُ يعرضُ الموضعَ لا العددَ وحدَه:** الآيةُ وسِفرُها وصفحتُها، والكلمةُ في
السطرَينِ، والترجمةُ المعتمدةُ من السطرِ الثالث. فمن أرادَ أن يحكمَ قرأَ السياقَ.

الاستعمال:
    python scripts/mansur_exceptions.py
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
OUT = ROOT / "data" / "mansur-exceptions.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "mansur-exceptions.md"

# الرواسي التي سمّاها المؤلّف، وثباتُها في مصفوفتِنا المقيسة
ANCHORS = "لورنمبكتق"
DIAC = dict.fromkeys(range(0x064B, 0x0653))


def bare(s: str) -> str:
    return unicodedata.normalize("NFC", s).translate(DIAC).replace("ـ", "")


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    verses = json.loads(TRILINEAR.read_text(encoding="utf-8"))

    rows: list[dict] = []
    per_pair = collections.Counter()
    for v in verses:
        sk = bare(str(v.get("skeleton") or "")).split()
        rd = bare(str(v.get("reading") or "")).split()
        if not sk or len(sk) != len(rd):
            continue
        gl = str(v.get("gloss") or "")
        for a, b in zip(sk, rd):
            for tag, i1, i2, j1, j2 in difflib.SequenceMatcher(
                    None, a, b, autojunk=False).get_opcodes():
                if tag != "replace" or (i2 - i1) != (j2 - j1):
                    continue
                for c, d in zip(a[i1:i2], b[j1:j2]):
                    if c not in ANCHORS or c == d:
                        continue
                    per_pair[(c, d)] += 1
                    rows.append({
                        "from": c, "to": d,
                        "book": v.get("book", ""), "verse": v.get("verse", ""),
                        "page": v.get("page"),
                        "skeleton_word": a, "reading_word": b,
                        "gloss": gl[:120],
                    })

    rows.sort(key=lambda r: (per_pair[(r["from"], r["to"])], r["from"], r["to"]))
    OUT.write_text(json.dumps({
        "generated_by": "scripts/mansur_exceptions.py",
        "layer": "استكشاف",
        "order": "النُدرةُ إشارةٌ لا خطأ",
        "anchors": ANCHORS,
        "total": len(rows),
        "pairs": {f"{a}>{b}": n for (a, b), n in per_pair.most_common()},
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    lines = [
        "# اسْتِثناءاتُ الرَّواسي في مادّةِ منصور",
        "",
        "**الطَّبَقة:** استِكشاف. **مَواضِعُ تُعرَضُ لا أحكامٌ تُقَرَّر.**",
        "",
        "أمرُ المُؤَلِّف: «الحُروفُ `ل و ر ن م ب ك ت ق` تَبقى على حالِها 94 إلى 98%.",
        "أخرِجْ لي المَواضِعَ التي تَحَرَّكَت فيها. **هذه أوّلُ ما يَستَحِقُّ النَّظَر،",
        "لأنّ فيها ما لا تُفَسِّرُه القاعِدةُ العامّة. النُّدرةُ إشارةٌ لا خَطَأ**».",
        "",
        "والحَرفُ الذي يَبقى نَفسَه في 99.6% لا يُعَلِّمُنا شَيئًا حينَ يَبقى، فبَقاؤُه هو",
        "القاعِدة. أمّا حينَ يَتَحَرَّكُ في أربَعةٍ من ألفٍ فهُناكَ سَبَب: **لَهجةٌ، أو خَطَأُ",
        "نَسخٍ قَديم، أو صَفُّ إبدالٍ حَقيقِيٌّ نادِرٌ لم نُدَوِّنْه، أو ضَوضاءُ مُحاذاة.**",
        "وكُلٌّ منها بابٌ يَستَحِقُّ أن يُفتَحَ ويُقرَأ.",
        "",
        f"**المَواضِعُ المَرصودة: {len(rows)}.**",
        "",
        "## الإبدالاتُ بتَكرارِها، والأندَرُ أوّلًا",
        "",
        "| الإبدال | مَرّات |",
        "|---|---:|",
    ]
    for (a, b), n in sorted(per_pair.items(), key=lambda kv: kv[1]):
        lines.append(f"| `{a}` ← `{b}` | {n} |")
    lines += [
        "",
        "## المَواضِعُ نَفسُها، الأندَرُ أوّلًا",
        "",
        "| الإبدال | السِّفر | الآية | الرَّسم | القِراءة | التَّرجَمةُ المُعتَمَدة |",
        "|---|---|---|---|---|---|",
    ]
    for r in rows[:400]:
        lines.append(f"| `{r['from']}` ← `{r['to']}` | {r['book']} | {r['verse']} | "
                     f"`{r['skeleton_word']}` | **{r['reading_word']}** | {r['gloss'][:70]} |")
    if len(rows) > 400:
        lines.append(f"\n*وبَقِيَّتُها في `data/mansur-exceptions.json`، وعَدَدُها {len(rows) - 400}.*")
    lines += ["", "---", "",
              "*English abstract.* The letters that hold their value in ninety-four to ninety-nine",
              "per cent of positions teach nothing when they hold; holding is the rule. Where they",
              "move, in a handful of places per thousand, there is a reason: a dialect form, an old",
              "copying slip, a genuine rare correspondence we have not recorded, or alignment noise.",
              "Each is a door worth opening, so this sheet lists the positions themselves with book,",
              "verse and the received translation, rarest pair first, rather than counts alone."]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    print(f"مواضعُ استثناءِ الرواسي: {len(rows)}\n")
    print(f"{'الإبدال':12}{'مرّات'}")
    for (a, b), n in sorted(per_pair.items(), key=lambda kv: kv[1]):
        print(f"  {a} ← {b:8}{n}")
    print(f"\nكُتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
