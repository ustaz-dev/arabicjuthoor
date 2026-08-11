# -*- coding: utf-8 -*-
"""ورقةُ ألغازِ المؤلّف: ما فتحَته علامةُ الإعرابِ ولم يقرأْه أحد (2026-08-10)

**الحاجة:** أصلحَ مسحُ السلفِ قراءةَ علامةِ الإعرابِ فظهرَ نحوُ 386 زوجًا كانت
محجوبةً بحرفٍ ليس من الكلمة. والآلةُ تختارُ من المروحةِ بأعلى تقاطعٍ في المعنى،
وهو مقياسٌ يُصيبُ ويُخطئ: `flock ~ فرق` يستقيمُ للقارئ، و`saddle ~ صدر` لا
يستقيم. **والفرقُ بينَهما لا تدركُه الآلةُ لأنّها تزنُ ولا تقرأ.**

**ولذلك لا تُعرَضُ الورقةُ حكمًا يُصدَّقُ أو يُكذَّب، بل مروحةً يُختارُ منها.**
في كلِّ صفٍّ: الكلمةُ ونطقُها، والصورةُ المستعادةُ ونطقُها، ومعناها المنشور،
واختيارُ الآلة، **وكلُّ ما أجازَته المروحةُ من جذورٍ عربيّة**. فيشطبُ المؤلّفُ
اختيارَ الآلةِ ويسمّي غيرَه من المروحةِ، أو يكتبُ جذرًا من عندِه.

**والقانونُ الحاكمُ في العرض:** لا خطَّ أجنبيَّ بلا نطقٍ مقروء. فالخطُّ العبريُّ
والقوطيُّ واليونانيُّ يُخفي الكلمةَ عمّن يحلُّها بالسماع، والمؤلّفُ يقرأُها
جهرًا. وقد ضاعَ سؤالٌ كاملٌ مرّةً لأنّه عُرِضَ بخطٍّ عارٍ.

**الترتيبُ يقدِّمُ ما يحتاجُ العين:** الشاهدُ غيرُ المباشرِ أوّلًا (المعنى بقرينةٍ
لا بترجمةٍ مباشرة)، ثمّ الأضعفُ تقاطعًا، ثمّ الأوسعُ مروحةً. فأوّلُ الورقةِ هو
موضعُ الخطأ المرجَّح، وآخرُها ما تكادُ الآلةُ تصيبُه وحدَها.

الاستعمال:
    python scripts/build_riddle_sheet.py                 كلُّ ما فتحَه البديل
    python scripts/build_riddle_sheet.py --limit 60      أوّلَ ستّينَ لغزًا
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import readable  # noqa: E402

SWEEPS = ROOT / "04-cross-linguistic" / "exploration"
OUT_MD = ROOT / "04-cross-linguistic" / "exploration" / "riddle-sheet-case-endings.md"
OUT_JSON = ROOT / "data" / "riddle-sheet-case-endings.json"

LANGS = [
    ("latin", "اللَّاتِينِيّة"), ("ancient_greek", "اليُونانِيّةُ القَديمة"),
    ("english_old", "الإنجليزِيّةُ القَديمة"), ("english_middle", "الإنجليزِيّةُ الوُسطى"),
    ("old_norse", "النُّردِيّةُ القَديمة"), ("gothic", "القوطِيّة"),
    ("old_irish", "الإيرلَندِيّةُ القَديمة"), ("welsh", "الويلزِيّة"),
    ("persian", "الفارِسِيّة"), ("hebrew", "العِبرِيّة"),
    ("aramaic", "الآرامِيّة"), ("akkadian", "الأكّادِيّة"),
]


def say(form: str) -> str:
    """نطقُ الكلمةِ الحيّة: الخطُّ العبريُّ والقوطيُّ واليونانيُّ يُرَدُّ إلى حروفٍ
    تُقرَأ، واللاتينيُّ يُقرَأُ كما هو."""
    s = (readable.say(form) or "").strip()
    return s if s and s != form else form


def read_old(form: str) -> str:
    """نطقُ الصورةِ المستعادة. **ولا يُكتفى بردِّ الرمزِ كما هو**، فقد كُتِبَ مرّةً
    `*h₂eḱrós` وبجانبِها «النطق: h₂eḱrós» وهذا تكرارٌ لا نطق، والحنجريّةُ
    والرقمُ السفليُّ اصطلاحُ كتابةٍ لا صوتٌ يُسمَع."""
    lat = readable.pie(form)
    return lat if lat else form


def rows_of(lang: str) -> list[dict]:
    p = SWEEPS / f"ancestor-sweep-{lang}.json"
    if not p.exists():
        return []
    d = json.loads(p.read_text(encoding="utf-8"))
    out = []
    for r in d.get("both", []):
        if "بإسقاط" not in str(r.get("skeleton_source", "")):
            continue
        out.append(r)
    # ما يحتاجُ العينَ أوّلًا: القرينةُ قبلَ المباشر، ثمّ الأضعفُ تقاطعًا
    out.sort(key=lambda r: (bool(r.get("direct")), r.get("overlap", 0),
                            -len(r.get("candidates_found") or [])))
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=0, help="أقصى عددِ ألغازٍ لكلِّ لسان")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    payload, lines, total = [], [], 0
    lines += [
        "# وَرَقَةُ الألغاز: ما فَتَحَتْهُ عَلامَةُ الإعرابِ ولم يَقرأْهُ أحَد",
        "",
        "**التاريخ:** 2026-08-10. **الطَّبَقة:** استِكشاف. **هذه مَروَحةٌ يُختارُ منها، لا حُكمٌ يُصدَّق.**",
        "",
        "كانَ المَسحُ يُقابِلُ الصُّورةَ المُستَعادةَ بحَرفٍ ليسَ من الكَلِمة، وهو عَلامةُ الإعرابِ",
        "في آخِرِها. فلمّا فُتِحَ الهَيكَلُ البَديلُ ظَهَرَت هذه الأزواجُ ولم تُقرَأْ بَعد.",
        "",
        "**والآلةُ تَختارُ من المَروَحةِ بأعلى تَقاطُعٍ في المَعنى، وهو مِقياسٌ يُصيبُ ويُخطِئ.**",
        "فـ`flock` بإزاءِ **فرق** يَستَقيمُ للقارِئ، و`saddle` بإزاءِ **صدر** لا يَستَقيم،",
        "والآلةُ لا تُفَرِّقُ بينَهُما لأنّها تَزِنُ ولا تَقرَأ.",
        "",
        "**كَيفَ تُحَلُّ:** اقرَأِ النُّطقَ جَهرًا، ثُمَّ انظُرِ المَعنى المَنشور، ثُمَّ اختَرْ من",
        "**عَمودِ المَروَحة** ما تَسمَعُه. إن كانَ اختِيارُ الآلةِ صَوابًا فاترُكْه، وإن كانَ",
        "غَيرُه أنظَفَ فاكتُبْه، وإن لم يَكُنْ في المَروَحةِ فاكتُبْ ما عِندَك ونَبحَثُ عن صَفِّه.",
        "",
        "**والتَّرتيبُ يُقَدِّمُ ما يَحتاجُ العَين:** الشّاهِدُ بقَرينةٍ أوّلًا، ثُمَّ الأضعَفُ تَقاطُعًا.",
        "فأوّلُ كُلِّ جَدوَلٍ مَوضِعُ الخَطَأِ المُرَجَّح.",
        "",
    ]

    for key, ar in LANGS:
        rs = rows_of(key)
        if not rs:
            continue
        if args.limit:
            rs = rs[:args.limit]
        total += len(rs)
        lines += [
            f"## {ar}  ({len(rs)} لُغزًا)",
            "",
            "| # | الكَلِمةُ ونُطقُها | الصُّورةُ المُستَعادةُ ونُطقُها | ما أُسقِطَ | مَعناها المَنشور | اختِيارُ الآلة | المَروَحةُ كُلُّها | شاهِدُها |",
            "|---:|---|---|---|---|---|---|---|",
        ]
        for i, r in enumerate(rs, 1):
            br, an = r.get("branch", ""), r.get("ancestor", "")
            cf = r.get("comparison_form", "")
            dropped = str(r.get("skeleton_source", "")).replace("بإسقاطِ علامةِ الإعرابِ ", "")
            fan = [c for c in (r.get("candidates_found") or []) if c != r.get("best")]
            gloss = (r.get("gloss") or "").replace("|", "،").strip()[:88]
            witness = ("مُباشِر" if r.get("direct") else "قَرينة") + f" {r.get('overlap', 0)}"
            lines.append(
                f"| {i} | `{br}` · **{say(br)}** | `*{an}` · **{read_old(an)}** "
                f"(المُقابَل **{read_old(cf)}**) | `{dropped}` | {gloss} | "
                f"**{r.get('best','')}** | "
                f"{'، '.join(fan[:11]) if fan else 'لا بَديلَ فيها'} | {witness} |"
            )
            payload.append({
                "language": key, "branch": br, "branch_say": say(br),
                "ancestor": an, "ancestor_say": read_old(an),
                "comparison_form": cf, "comparison_say": read_old(cf),
                "dropped": dropped, "gloss": r.get("gloss", ""),
                "machine_pick": r.get("best", ""), "fan": r.get("candidates_found") or [],
                "direct": bool(r.get("direct")), "overlap": r.get("overlap", 0),
                "author_pick": None,
            })
        lines.append("")

    lines += [
        "---",
        "",
        "*English abstract.* The case-ending fix in the ancestor sweep exposed pairs that had been",
        "compared against a skeleton containing a letter that is not part of the word. This sheet",
        "lists every one of them for the author to read. Each row carries a readable pronunciation for",
        "every foreign form, the published gloss, the machine's pick, and the full Arabic candidate fan",
        "so that the author selects rather than merely confirms. Rows are ordered so that the weakest",
        "semantic evidence comes first, which is where the machine is most likely to have chosen wrong.",
        "These are open exploratory candidates, not verdicts.",
    ]

    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    OUT_JSON.write_text(json.dumps({
        "generated_by": "scripts/build_riddle_sheet.py",
        "layer": "استكشاف",
        "note": "مروحةٌ يُختارُ منها لا حكمٌ يُصدَّق؛ كلُّ صورةٍ أجنبيّةٍ معها نطقُها",
        "riddles": len(payload), "rows": payload,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    print(f"ألغازٌ مكتوبة: {total}")
    print(f"كُتب: {OUT_MD.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {OUT_JSON.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
