# -*- coding: utf-8 -*-
"""ورقةُ أذُنِ المؤلّفِ الأكّاديّة (2026-08-11)

**لماذا هذه الورقةُ بالذات:** حصادُ خشيمٍ الأكّاديُّ 588 زوجًا، ومروحتُنا الآليّةُ
لا تبلغُ مرشَّحَه إلّا في 9% منها، لأنّ الرجلَ يصلُ بالمعنى والقلبِ والإبدالِ
أكثرَ ممّا يصلُ بالحرفِ الواحد. **فهذه مادّةُ عينٍ لا مادّةُ آلة.**

**وميزتُها الفريدة:** خشيمٌ كتبَ الكلمةَ الأكّاديّةَ **بحروفٍ عربيّةٍ أصلًا**،
فالمؤلّفُ يقرؤُها جهرًا بلا رومنةٍ ولا وسيط، وهو يحلُّ بالسماعِ ما لا تحلُّه
الآلةُ بالحساب (مثلَما رأى مطر في mater وفغر في פערא).

**الترتيبُ يُقدِّمُ ما يحتاجُ الأذُن:** ما لم تبلغْه مروحتُنا أوّلًا، فهو الموضعُ
الذي لا تُغني فيه الآلةُ عن المؤلّف. الطبقةُ: استكشاف، ولا حكمَ في الورقة.

الاستعمال:
    python scripts/build_akkadian_ear_sheet.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as F  # noqa: E402

OUT = ROOT / "04-cross-linguistic" / "exploration" / "akkadian-ear-sheet.md"


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    d = json.loads((ROOT / "data" / "khashim-pairs.json").read_text(encoding="utf-8"))
    rows = [r for r in d["rows"] if r["tongue"] == "akkadian" and r["foreign"]]

    hard, easy = [], []
    for r in rows:
        fn = F.fan(r["foreign"])
        (easy if r["arabic_root"] in fn else hard).append((r, fn))

    lines = [
        "# وَرَقَةُ الأُذُن: أكّادِيّةُ خَشيم، حَيثُ لا تُغني الآلةُ عن المُؤَلِّف",
        "",
        "**الطَّبَقة:** استِكشاف. **مَروَحةٌ يُختارُ منها، لا حُكم.**",
        "",
        "الكَلِمةُ الأكّادِيّةُ هنا **بحُروفٍ عَرَبِيّةٍ كما كَتَبَها خَشيمٌ نَفسُه**، فتُقرَأُ",
        "جَهرًا رَأسًا. ومَروَحَتُنا الآلِيّةُ لا تَبلُغُ مُرَشَّحَه إلّا في قَليلٍ منها، لأنّه",
        "يَصِلُ بالمَعنى والقَلبِ والإبدالِ أكثَرَ مِمّا يَصِلُ بالحَرف. **فهذِه مادّةُ أُذُنٍ:**",
        "اقرَأِ الكَلِمةَ والمَعنى، فإن سَمِعتَ جَذرًا عَرَبِيًّا فاكتُبْه، وافِقَ مُرَشَّحَ",
        "خَشيمٍ أم خالَفَه، كانَ في مَروَحَتِنا أم لم يَكُن.",
        "",
        f"## أوّلًا: ما لم تَبلُغْهُ مَروَحَتُنا ({len(hard)} زَوجًا)، وهو مَوضِعُ أُذُنِك",
        "",
        "| # | الكَلِمةُ الأكّادِيّة | مَعناها عِندَه | مُرَشَّحُ خَشيم | نَصُّهُ المُعجَمِيّ |",
        "|---:|---|---|---|---|",
    ]
    for i, (r, _) in enumerate(hard, 1):
        lines.append(
            f"| {i} | **{r['foreign']}** | {r['foreign_sense'][:70]} | "
            f"{r['arabic_root']} | {r['arabic_gloss'][:80]} |")
    lines += [
        "",
        f"## ثانِيًا: ما بَلَغَتْهُ المَروَحةُ أيضًا ({len(easy)} زَوجًا)، تَصديقٌ من طَريقَين",
        "",
        "| # | الكَلِمة | مَعناها | مُرَشَّحُ خَشيمٍ وهو في مَروَحَتِنا |",
        "|---:|---|---|---|",
    ]
    for i, (r, _) in enumerate(easy, 1):
        lines.append(f"| {i} | **{r['foreign']}** | {r['foreign_sense'][:70]} | {r['arabic_root']} |")
    lines += [
        "", "---", "",
        "*English abstract.* Khashim's Akkadian dictionary writes every Akkadian word in",
        "Arabic script, so the author can read it aloud directly. Our automatic fan reaches",
        "his Arabic candidate in only a small fraction of the 588 pairs, because he links",
        "through meaning, metathesis and substitution more than letter identity. This sheet",
        "therefore puts the unreached pairs first: they are ear-work, the part of the task",
        "where the machine cannot replace the author. Exploration layer; no verdicts here.",
    ]
    OUT.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}  (عينٌ: {len(hard)} · تصديق: {len(easy)})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
