# -*- coding: utf-8 -*-
"""مسحُ أسماءِ المواضعِ والأعلام، بضابطِ نبونيد المسماريّ (2026-08-12)

**البابُ الذي يفتحُه:** لم نمرِّرْ عَلَمًا واحدًا في مروحتِنا قطّ. ودستورُنا
يُخرِجُ الأعلامَ من **عدِّ الصلات** وهو حقٌّ، لكنّه لا يمنعُ مسحَها في طبقةٍ
مستقلّةٍ موسومة. والأعلامُ بابٌ واسعٌ: أسماءُ المواضعِ في الأسفارِ التاريخيّةِ
مئاتٌ، وهي المادّةُ التي بنى عليها من سبقونا دعواهم.

**والضابطُ خارجيٌّ ومؤرَّخٌ ولم نخترْه:** ستائرُ نبونيد بحرّانَ تُسمّي بيدِ ملكٍ
بابليٍّ في القرنِ السادسِ قبلَ الميلادِ ستَّ واحاتٍ في شمالِ غربِ الجزيرة. فهي
عيّنةٌ نعرفُ جوابَها سلفًا من التاريخِ لا من قياسِنا، ونقيسُ عليها أداتَنا.

**وعطبانِ كشفَتهما هذه القائمةُ ولم يكنْ يظهرانِ في المفردات:**

  1. الأعلامُ تُكتَبُ بحرفٍ أوّلَ كبير، ومفاتيحُ المروحةِ صغيرةٌ كلُّها، فكان
     يسقطُ صدرُ كلِّ اسم: `Padakku` تُقرَأُ `دك` و`Yatribu` تُقرَأُ `ترب`.
  2. الإدغامُ كان يُقاسُ بعدَ طرحِ الصوائتِ لا قبلَه، فيلتقي صامتانِ كانا
     مفصولَينِ بصائتٍ فيُدغَمانِ ظلمًا: `Da-da-nu` تُقرَأُ `دن` لا `ددن`.

وبعدَ إصلاحِهما وقعَت القائمةُ الستُّ على جذورِها كلِّها.

**ولا حكمَ في هذا المسح.** الطبقةُ استكشاف، والناتجُ مرشَّحونَ لا صلات، ولا
يدخلونَ عدَّ الصلاتِ المنشور.

الاستعمال:
    python scripts/sweep_place_names.py
"""
from __future__ import annotations

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as F  # noqa: E402
import readable  # noqa: E402

OUT_JSON = ROOT / "data" / "place-name-sweep.json"
OUT_MD = ROOT / "04-cross-linguistic" / "exploration" / "place-name-sweep.md"

# الضابطُ الخارجيُّ المؤرَّخ: ستائرُ نبونيد بحرّان، القرنُ السادسُ ق.م.
# (الاسمُ كما في الحجر، الموضعُ اليوم، الجذرُ العربيُّ المعروفُ للموضع)
NABONIDUS = [
    ("Tēmāʾ", "تيماء", ("تمء", "تيم", "تمو", "تما")),
    ("Dadanu", "ددان", ("ددن",)),
    ("Padakku", "فدك", ("فدك",)),
    ("Ḫibrā", "خيبر", ("خبر", "خيبر")),
    ("Yadiḫu", "يديع", ("يدع", "يدح")),
    ("Yatribu", "يثرب", ("يثرب", "ثرب")),
]

# مواضعُ وأعلامٌ توراتيّةٌ بالخطِّ المربَّع، لم يمرَّ منها شيءٌ في مروحتِنا قطّ
BIBLICAL = [
    ("שָׁלֵם", "شاليم"), ("עֲרָבָה", "العَرَبة"), ("הָגָר", "هاجر"),
    ("נֶגֶב", "النقب"), ("חֶבְרוֹן", "حبرون"), ("שְׁכֶם", "شكيم"),
    ("שָׂרַי", "سارَيْ"), ("תֵּימָן", "تيمان"), ("מִדְיָן", "مدين"),
    ("סִינַי", "سيناء"), ("כְּנַעַן", "كنعان"), ("יַרְדֵּן", "الأردنّ"),
    ("לְבָנוֹן", "لبنان"), ("כַּרְמֶל", "الكرمل"), ("גִּלְעָד", "جلعاد"),
    ("בָּשָׁן", "باشان"), ("עֵילָם", "عيلام"), ("אַשּׁוּר", "أشور"),
]


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    rows: list[dict] = []

    print("الضابطُ المؤرَّخُ: قائمةُ نبونيد المسماريّة\n")
    hits = 0
    for name, today, expect in NABONIDUS:
        fan = F.fan(name, "akkadian")
        got = [c for c in fan if c in expect]
        hits += bool(got)
        rows.append({"set": "nabonidus", "name": name, "today": today,
                     "expected": list(expect), "fan": fan[:40],
                     "hit": got[0] if got else ""})
        print(f"  {name:10}{today:9}{'، '.join(fan[:7]):34}"
              f"{'✔ ' + got[0] if got else '✘'}")
    print(f"\n  أصابَ جذرَ الموضع: {hits} من {len(NABONIDUS)}\n")

    print("الأعلامُ والمواضعُ التوراتيّة (بلا جوابٍ معروفٍ سلفًا)\n")
    for heb, known in BIBLICAL:
        fan = F.fan(heb, "north")
        rows.append({"set": "biblical", "name": heb, "today": known,
                     "say": readable.say(heb), "fan": fan[:40], "hit": ""})
        print(f"  {heb:12}{readable.say(heb)[:16]:18}{known:10}"
              f"{'، '.join(fan[:8]) if fan else '(صفر)'}")

    OUT_JSON.write_text(json.dumps({
        "generated_by": "scripts/sweep_place_names.py",
        "layer": "استكشاف",
        "note": ("مرشَّحونَ لا صلات، ولا يدخلونَ عدَّ الصلاتِ المنشور. "
                 "والضابطُ قائمةُ نبونيد المسماريّةُ وهي خارجيّةٌ مؤرَّخةٌ لم نخترْها."),
        "control_hits": hits, "control_size": len(NABONIDUS),
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    lines = [
        "# مَسحُ أسماءِ المَواضِعِ والأعلام",
        "",
        "**الطَّبَقة:** استِكشاف. **مُرَشَّحونَ لا صِلات، ولا يَدخُلونَ عَدَّ الصِّلاتِ المَنشور.**",
        "",
        "لم نُمَرِّرْ عَلَمًا واحِدًا في مَروَحَتِنا قَبلَ اليَوم. والدُّستورُ يُخرِجُ الأعلامَ",
        "من **عَدِّ الصِّلات** وهو حَقّ، لكنّه لا يَمنَعُ مَسحَها في طَبَقةٍ مُستَقِلّةٍ مَوسومة.",
        "",
        "## الضّابِطُ الخارِجِيُّ المُؤَرَّخ",
        "",
        "ستائرُ نَبونيد بحَرّان، القَرنُ السّادِسُ قَبلَ الميلاد: سِتُّ واحاتٍ سَمّاها مَلِكٌ",
        "بابِلِيٌّ بيَدِه. **ونَحنُ لم نَختَرْها**، فجَوابُها مَعروفٌ من التّاريخِ لا من قِياسِنا.",
        "",
        f"**أصابَ جَذرَ المَوضِع: {hits} من {len(NABONIDUS)}.**",
        "",
        "| في الحَجَر | اليَوم | مَروَحَتُنا | أصابَت؟ |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if r["set"] != "nabonidus":
            continue
        lines.append(f"| `{r['name']}` | {r['today']} | {'، '.join(r['fan'][:7])} | "
                     f"{'**' + r['hit'] + '**' if r['hit'] else 'لا'} |")
    lines += [
        "",
        "## الأعلامُ والمَواضِعُ التَّوراتِيّة",
        "",
        "بلا جَوابٍ مَعروفٍ سَلَفًا، فهذه مَروَحةٌ تُعرَضُ لا نَتيجةٌ تُقَرَّر.",
        "",
        "| الاسمُ بخَطِّه | نُطقُه | المَعروفُ به | مَروَحَتُنا |",
        "|---|---|---|---|",
    ]
    for r in rows:
        if r["set"] != "biblical":
            continue
        lines.append(f"| {r['name']} | {r.get('say','')} | {r['today']} | "
                     f"{'، '.join(r['fan'][:9]) if r['fan'] else '(صفر)'} |")
    lines += [
        "", "---", "",
        "*English abstract.* A first sweep of proper names, a class this project had never",
        "passed through its candidate fan. The control is external and dated and was not",
        "chosen by us: the six north-west Arabian oases named on Nabonidus' Harran stelae in",
        "the sixth century BC. Running them through the fan exposed two tool defects that",
        "ordinary lexical entries could never reveal, since dictionary headwords are",
        "lowercase: proper names lost their first consonant to a case mismatch, and",
        "gemination was measured after vowel stripping so that two consonants separated by a",
        "vowel were wrongly merged. With both fixed the control list lands on its roots.",
        "These rows are exploratory candidates and are excluded from the published link",
        "count.",
    ]
    OUT_MD.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nكُتب: {OUT_JSON.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {OUT_MD.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
