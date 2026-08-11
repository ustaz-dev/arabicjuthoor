# -*- coding: utf-8 -*-
"""حصادُ معاجمِ خشيم المقارِنة (2026-08-10، بأمرِ المؤلّف)

**مَن هو:** الليبيُّ **علي فهمي خشيم**، وكتبُه عناوينُها بنفسِها دعوانا:
«الأكّاديّةُ عربيّة» و«القبطيّةُ عربيّة» و«اللاتينيّةُ عربيّة» و«البرهانُ على
عروبةِ اللغةِ المصريّةِ القديمة» و«الوحدةُ والتنوّعُ في اللهجاتِ العروبيّةِ
القديمة». **وهي ألسنُنا بعينِها**: الأكّاديّةُ والقبطيّةُ والمصريّةُ واللاتينيّة.

**وبنيةُ كتبِه معجميّةٌ لا مقاليّة**، وهذا ما يجعلُها تُحصَدُ آليًّا:

    شمت : قدر، مصير. (من «شم»)
    ع : سمي. سمّى: عيّن، أي قرّر قدره ومصيره، خصّص.

    شزب : لبن.
    ع : شخب. الشّخب: ما خرج من الضرع من اللبن إذا احتُلب.

فالسطرُ الأوّلُ الكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ ومعناها، والسطرُ الذي يبدأُ
بـ`ع :` فيه **الجذرُ العربيُّ ونصُّ معجمِه**. والعلامةُ `ع` مرساةٌ ثابتةٌ في
الكتابِ كلِّه.

**وعقبتانِ في الاستخراجِ عولِجَتا:**

1. **النصُّ يخرجُ بترتيبٍ بصريٍّ معكوس** لأنّ ملفَّ المسحِ لا يحملُ ترتيبًا
   منطقيًّا: تخرجُ «والعبريين» هكذا «نييربعلاو». فتُقلَبُ حروفُ كلِّ كلمةٍ
   ويُقلَبُ ترتيبُ الكلماتِ في السطر.
2. **المسحُ الضوئيُّ عربيٌّ فقط**، فالحروفُ اللاتينيّةُ في كتابِ اللاتينيّةِ
   سقطَت كلَّها (صفرُ حرفٍ لاتينيٍّ في 234 صفحة). فيُحصَدُ ما كتبَه هو بالعربيّة،
   ويبقى نصُّ الكلمةِ الأجنبيّةِ بالحرفِ الأصليِّ نقصًا مسمًّى يُسَدُّ بمسحٍ ثانٍ.

**ولا حكمَ هنا على زوج.** أمرُ المؤلّف: «استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ
أقصى ما يمكنُ من الصلات».

الاستعمال:
    python scripts/harvest_khashim.py
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
STORE = pathlib.Path.home() / "AI Projects" / "Resources" / "prior-art"
OUT = ROOT / "data" / "khashim-pairs.json"
SHEET = ROOT / "04-cross-linguistic" / "exploration" / "khashim-harvest.md"

BOOKS = {
    "khashim-akkadian": ("الأكّاديّة", "akkadian"),
    "khashim-coptic": ("القبطيّة", "coptic"),
    "khashim-latin": ("اللاتينيّة", "old-latin"),
    "khashim-dialects": ("اللهجاتُ العروبيّةُ القديمة", "semitic"),
}

AR = re.compile(r"[؀-ۿ]")
# **مرساتانِ لا واحدة**: في «الأكّاديّةُ عربيّة» يكتبُ `ع :` مختصرًا، وفي
# «اللاتينيّةُ عربيّة» يكتبُ `في العربية :` كاملةً ويُخرِجُها المسحُ ناقصةَ
# الصدرِ هكذا `د العربية :` و`بد العربية :`. فمن طلبَ العينَ المفردةَ وحدَها
# خرجَ من كتابِ اللاتينيّةِ بصفر.
RX_AR_LINE = re.compile(r"^\s*(?:ع|[ء-ي]{0,3}\s*العربية)\s*[:：]\s*(.+)$")
# الجذرُ أوّلُ كلمةٍ عربيّةٍ في السطر، وقد يليها شرحُها
RX_ROOT = re.compile(r"^([ء-ي]{2,6})\b")
# الكلمةُ الأجنبيّةُ ومعناها: `شمت : قدر، مصير`
RX_ENTRY = re.compile(r"^\s*([ء-ي][ء-يـ\s]{0,14}?)\s*[:：]\s*(.{2,90})$")
NOISE = ("انظر", "المرجع", "الصفحة", "الفصل", "الباب", "المصدر", "الهامش")


def unmirror(line: str) -> str:
    """يُعادُ السطرُ إلى ترتيبِه المنطقيّ. المسحُ يخرجُه بترتيبِ العينِ لا العقل."""
    if not AR.search(line):
        return line
    return " ".join(w[::-1] for w in line.split()[::-1])


def clean(s: str) -> str:
    s = unicodedata.normalize("NFC", s)
    s = re.sub(r"[ـ‌‏‫‬]", "", s)   # تطويلٌ وعلاماتُ اتّجاه
    s = re.sub(r"[«»\"'‘’]", "", s)
    return re.sub(r"\s+", " ", s).strip(" .,؛:،")


def mine(path: pathlib.Path, tongue_ar: str, tongue_key: str) -> list[dict]:
    import fitz                                             # noqa: PLC0415
    doc = fitz.open(path)
    lines: list[str] = []
    for page in doc:
        lines.extend(unmirror(x) for x in page.get_text().splitlines())

    pairs, seen = [], set()
    for i, line in enumerate(lines):
        m = RX_AR_LINE.match(line)
        if not m:
            continue
        ar_side = clean(m.group(1))
        rm = RX_ROOT.match(ar_side)
        if not rm:
            continue
        root = rm.group(1)
        gloss_ar = clean(ar_side[rm.end():])

        # المدخلُ الأجنبيُّ في السطورِ الثلاثةِ التي قبلَه، وأقربُها أولى
        foreign = foreign_sense = ""
        for back in range(1, 4):
            if i - back < 0:
                break
            prev = clean(lines[i - back])
            if not prev or RX_AR_LINE.match(lines[i - back]):
                continue
            em = RX_ENTRY.match(prev)
            if em and not any(n in prev for n in NOISE):
                foreign, foreign_sense = clean(em.group(1)), clean(em.group(2))
                break
        if not foreign:
            # **كتابُ اللاتينيّةِ لا يُخرِجُ رأسَ المدخل** لأنّ حرفَه لاتينيٌّ وقد
            # سقطَ في المسح، فيُؤخَذُ أقربُ سطرٍ عربيٍّ ذي معنًى بوصفِه شرحَ
            # المدخل. والزوجُ يُحفَظُ بنقصٍ مسمًّى لا يُطرَحُ لأجلِه.
            for back in range(1, 4):
                if i - back < 0:
                    break
                prev = clean(lines[i - back])
                if len(prev) >= 4 and AR.search(prev) and not RX_AR_LINE.match(lines[i - back]):
                    foreign_sense = prev[:90]
                    foreign = "(سقطَ حرفُه في المسح)"
                    break
        if not foreign or len(root) < 2:
            continue
        key = (foreign if "سقط" not in foreign else foreign_sense, root)
        if key in seen:
            continue
        seen.add(key)
        pairs.append({
            "tongue_ar": tongue_ar, "tongue": tongue_key,
            "foreign": foreign, "foreign_sense": foreign_sense,
            "arabic_root": root, "arabic_gloss": gloss_ar[:160],
            "source": path.stem,
        })
    return pairs


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    if not STORE.exists():
        print(f"لا ذخيرةَ في {STORE}")
        return 1

    rows: list[dict] = []
    print(f"{'الكتاب':24}{'أزواج':>8}")
    for stem, (ar, key) in BOOKS.items():
        p = STORE / f"{stem}.pdf"
        if not p.exists():
            print(f"  {stem:24}{'غائب':>8}")
            continue
        got = mine(p, ar, key)
        rows.extend(got)
        print(f"  {stem:24}{len(got):>8}")

    OUT.write_text(json.dumps({
        "generated_by": "scripts/harvest_khashim.py",
        "layer": "استكشاف",
        "author": "علي فهمي خشيم",
        "order": "استعملْ أعمالَه، لا تحكمْ عليها، واحصدْ أقصى ما يمكنُ من الصلات",
        "note": ("أزواجٌ اقترحَها خشيم في معاجمِه المقارِنة. **مرشَّحاتٌ لا أحكام.** "
                 "والكلمةُ الأجنبيّةُ بحروفٍ عربيّةٍ كما كتبَها هو، لأنّ المسحَ الضوئيَّ "
                 "عربيٌّ فقط فسقطَ الحرفُ الأصليُّ، وهو نقصٌ مسمًّى يُسَدُّ بمسحٍ ثانٍ."),
        "pairs": len(rows),
        "rows": rows,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    by_tongue: dict[str, int] = {}
    for r in rows:
        by_tongue[r["tongue_ar"]] = by_tongue.get(r["tongue_ar"], 0) + 1
    lines = [
        "# حَصادُ مَعاجِمِ خَشيم المُقارِنة",
        "",
        "**الطَّبَقة:** استِكشاف. **مُرَشَّحاتٌ لا أحكام.**",
        "",
        "علي فهمي خشيم، وكُتُبُه: «الأكّادِيّةُ عَرَبِيّة» و«القِبطِيّةُ عَرَبِيّة»",
        "و«اللّاتينِيّةُ عَرَبِيّة» و«الوَحدةُ والتَّنَوُّعُ في اللَّهَجاتِ العَروبِيّةِ القَديمة».",
        "وبِنيةُ كُتُبِه مُعجَمِيّةٌ، فالسَّطرُ الأوّلُ الكَلِمةُ الأجنَبِيّةُ ومَعناها،",
        "ويَليه سَطرٌ يَبدَأُ بـ`ع :` فيه الجَذرُ العَرَبِيُّ ونَصُّ مُعجَمِه.",
        "",
        "**الكَلِمةُ الأجنَبِيّةُ هنا بحُروفٍ عَرَبِيّةٍ كما كَتَبَها هو**، لأنّ المَسحَ",
        "الضَّوئِيَّ للكُتُبِ عَرَبِيٌّ فقط فسَقَطَ الحَرفُ الأصلِيّ. وهذا نَقصٌ مُسَمًّى.",
        "",
        f"**العَدَد: {len(rows)} زَوجًا.**  " + " · ".join(f"{k}: {v}" for k, v in by_tongue.items()),
        "",
        "| اللِّسان | الكَلِمةُ عندَه | مَعناها | الجَذرُ العَرَبِيّ | نَصُّه |",
        "|---|---|---|---|---|",
    ]
    for r in rows:
        lines.append(f"| {r['tongue_ar']} | `{r['foreign']}` | {r['foreign_sense'][:44]} | "
                     f"**{r['arabic_root']}** | {r['arabic_gloss'][:70]} |")
    lines += ["", "---", "",
              "*English abstract.* Pairs harvested from Ali Fahmi Khashim's comparative",
              "dictionaries, whose titles state the thesis directly: Akkadian is Arabic, Coptic is",
              "Arabic, Latin is Arabic. His entries are lexicographic, so each foreign headword and",
              "its sense is followed by a line marked with the Arabic letter ain giving the Arabic",
              "root and its lexical text. These are candidates, not verdicts. The foreign words",
              "appear in Arabic transcription because the available scans were OCRed for Arabic",
              "only and dropped every Latin character; that is a named gap, not a choice."]
    SHEET.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nالمجموع: {len(rows)} زوجًا")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {SHEET.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
