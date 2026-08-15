# -*- coding: utf-8 -*-
"""البطاقةُ تحفظُ القرارَ والإحالة، ولا تُخزِّنُ ما تُولِّدُه الأداة (2026-08-15)

**القاعدةُ، بحكمِ المؤلّف:** لسانُ العربِ وتاجُ العروسِ منشورانِ منذ قرونٍ
ومتاحانِ للناسِ كلِّهم، **ونسخُهما في مستودعِنا ليس عملًا ولا حجّة**. والذي
يخصُّنا هو البطاقة: الصورةُ ونطقُها، والجذرُ العربيُّ، ومسارُ الصوتِ المسمّى،
وحدثُ الحرفِ من سجلِّنا، **والمدارُ الذي كتبَه قارئٌ بيدِه**، والإحالةُ إلى
الشاهدِ كما يفعلُ كلُّ باحث: اسمُ المعجمِ والمادّةُ والجملةُ العاملة.

**والحالُ التي كشفَتها:** جيت‑هَب يرفضُ ملفًّا فوقَ 100 ميجا، فبقيَ أحدَ عشرَ
إيداعًا محبوسًا ولم يُنشَرْ شيء. وجردُ ملفِّ اللاتينيّةِ (246 ميجا) قال:
**160 ميجا منها مقالاتُ معاجمَ منسوخةٌ**، و**85 ميجا عملُنا نحن**. فثلثاه
نقلٌ لما ليس لنا.

**والمبدأُ أوسعُ من الحجم**: كلُّ ما تستطيعُ الأداةُ توليدَه بأمرٍ لا يُخزَّن،
لأنّ خزنَه لا يزيدُ حجّةً ويُغرِقُ الحجّةَ في الركام. القارئُ لا يجدُ المدارَ
بينَ ثلاثينَ ألفَ سطرٍ من تاجِ العروس.

    يُحفَظُ:  الصورةُ والنطقُ والمعنى · الجذرُ المختار · مسارُ الصوتِ المسمّى ·
             نصُّ الحدثِ المجمَّد · **المدارُ المكتوبُ باليد** · الحكمُ وسببُه ·
             الإحالةُ بالجملةِ العاملة
    يُطرَحُ:  مقالُ المعجمِ كاملًا (يُولَّدُ بـ`search_arabic_root_senses.py`) ·
             المروحةُ كاملةً (`fan_any_script.fan`) · قائمةُ مداخلِ القاموس
             (`build_kaikki_index.look`) · جسورُ الإجراءِ وخطواتُه

**ولا يُمَسُّ سطرُ حكمٍ ولا مدارٌ ولا مسارُ صوتٍ ولا حدثٌ مجمَّد**، والأداةُ
تعُدُّها قبلَ الكتابةِ وبعدَها فتُبلِّغُ إن نقصَ واحد.

الاستعمال:
    python scripts/trim_card_dumps.py                 قياسٌ بلا كتابة
    python scripts/trim_card_dumps.py --write         يكتبُ بعدَ التحقُّق
"""
from __future__ import annotations

import argparse
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"

KEEP_QUOTE = 220      # ما يبقى من الشاهد: الإحالةُ والجملةُ العاملة

# صدورُ الأسطرِ التي تنقلُ نصَّ مصدرٍ منشورٍ أو ناتجَ أداةٍ يُولَّدُ بأمر
GENERATED = (
    # مقالاتُ المعاجمِ العربيّةِ المنشورة
    "تاج العروس", "لسان العرب", "تاج اللغة وصحاح", "الصحاح", "أساس البلاغة",
    "المحكم والمحيط", "المحكم", "كتاب العين", "المحيط", "المصباح المنير",
    "المفردات في غريب", "المعجم العربي الإنجليزي", "AlMaghreb", "الجمهرة",
    # ناتجُ أدواتِنا الذي يُعادُ توليدُه بأمرٍ واحد
    "المروحة الكاملة", "قائمة مداخل الصورة كلها", "قائمة المداخل",
    "القائمة كاملة", "مسح المعاني العربية", "مسحُ المعاني العربيّة",
    "مسحُ المعاني العربية", "جسور الاسترداد المفحوصة",
    "جسورُ الاسترداد المفحوصة", "قراءة عائلات اللسان",
    "فحص كل مرشحات المروحة", "إشعاع الأسرة",
)
# ما لا يُمَسُّ ولو طال: قرارٌ أو نصٌّ مجمَّدٌ أو كتابةُ إنسان
PROTECTED = re.compile(
    r"(الحكم|المدار|مسار الصوت|مسارُ الصوت|الحدث|الحدثُ|حالة الإغلاق|"
    r"حالةُ الإغلاق|المقابل|المقابلُ|عائق|سبب|الكلمة في الفرع|الكلمةُ في الفرع|"
    r"المدخلة المختارة|معنى قاموس الفرع|المعنى من قاموس الفرع|أقدم|أقدمُ)")


# **البطاقةُ تستشهدُ ولا تستوعب.** أعقابُ التقليمِ وحدَها بلغَت 64 ميجا في
# اللاتينيّةِ (126,254 سطرًا بمعدّلِ ثمانيةٍ ونصفٍ في البطاقة)، فلا يكفي تقصيرُ
# كلِّ سطر. والباحثُ يستشهدُ بشاهدَينِ ويقولُ كم قرأ، فذلك عُرفُ التحقيقِ لا
# اختصارٌ نصنعُه: تُبقى **شاهدتانِ في البطاقةِ** بإحالتِهما وجملتِهما العاملة،
# ويُطرَحُ ما بعدَهما بسطرٍ واحدٍ يقولُ كم قُرِئَ وبأيِّ أمرٍ يُولَّد.
QUOTES_PER_CARD = 2


def trim_line(line: str, seen_in_card: int = 0) -> tuple[str, int]:
    head = line[:170]
    if PROTECTED.search(head):
        return line, 0
    if not any(f in head for f in GENERATED):
        return line, 0
    if seen_in_card < QUOTES_PER_CARD:
        if len(line) <= KEEP_QUOTE + 80:
            return line, 0
        removed = len(line) - KEEP_QUOTE
        return (line[:KEEP_QUOTE].rstrip()
                + f" … [طُرِحَ نقلٌ طولُه {removed:,} حرفًا]\n"), removed
    return "", len(line)


def census(path: pathlib.Path) -> dict:
    """جردُ ما لا يجوزُ أن ينقصَ حرفًا واحدًا بعدَ التقليم."""
    c = {"cards": 0, "verdicts": 0, "orbits": 0, "sound": 0, "events": 0}
    for line in path.open(encoding="utf-8", errors="replace"):
        if line.startswith("### "):
            c["cards"] += 1
            continue
        head = line[:40]
        if "الحكم" in head:
            c["verdicts"] += 1
        elif "المدار" in head:
            c["orbits"] += 1
        elif "مسار" in head and "الصوت" in head:
            c["sound"] += 1
        elif "الحدث" in head:
            c["events"] += 1
    return c


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    ap.add_argument("--files", nargs="+")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    targets = ([READINGS / f for f in args.files] if args.files
               else sorted(READINGS.glob("*.md")))
    tot_b = tot_a = 0
    bad = 0
    for p in targets:
        if not p.exists():
            continue
        pre = census(p)
        before = p.stat().st_size
        out: list[str] = []
        removed = touched = 0
        quoted = dropped = 0
        for line in p.open(encoding="utf-8", errors="replace"):
            if line.startswith("### "):
                if dropped:
                    out.append(f"- شواهدُ أخرى قُرِئَت ولم تُنسَخ: {dropped}. "
                               "تُولَّدُ بـ`search_arabic_root_senses.py <الجذر> "
                               "--max-chars 0` وبـ`build_kaikki_index.look`.\n")
                quoted = dropped = 0
                out.append(line)
                continue
            new, cut = trim_line(line, quoted)
            if cut:
                removed += cut
                touched += 1
                if new == "":
                    dropped += 1
                else:
                    quoted += 1
            elif any(f in line[:170] for f in GENERATED) and not PROTECTED.search(line[:170]):
                quoted += 1
            if new:
                out.append(new)
        if dropped:
            out.append(f"- شواهدُ أخرى قُرِئَت ولم تُنسَخ: {dropped}.\n")
        after = sum(len(x.encode("utf-8")) for x in out)
        if args.write and touched:
            p.write_text("".join(out), encoding="utf-8", newline="\n")
            post = census(p)
            if any(pre[k] != post[k] for k in pre):
                print(f"!! {p.stem}: نقصَ محتوًى محميّ {pre} ← {post}")
                bad += 1
        tot_b += before
        tot_a += after
        if touched:
            print(f"{p.stem:24}{before/1048576:>7.0f}م ← {after/1048576:>6.0f}م"
                  f"  (طُرِحَ نقلٌ في {touched:,} سطرًا)")
    print(f"\nالجملة: {tot_b/1048576:.0f}م ← {tot_a/1048576:.0f}م"
          f"  ({'كُتِبَ' if args.write else 'قياسٌ بلا كتابة'})")
    if bad:
        print(f"!! {bad} ملفًّا نقصَ فيه محتوًى محميّ، فراجِعْ قبلَ الإيداع.")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
