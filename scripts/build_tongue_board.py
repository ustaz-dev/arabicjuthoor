# -*- coding: utf-8 -*-
"""لوحةُ الألسن: ما ردَّه كلُّ لسانٍ فُتِحَ له ملفُّ قراءة (2026-08-10)

**لماذا هذه اللوحةُ وعندَنا شريطُ التدرُّجِ في الصدرِ أصلًا؟** لأنّ الشريطَ يجيبُ
عن سؤالِ «**أيّ طبقةٍ** ردَّها الفرع»، وهو سؤالُ الدعوى. واللوحةُ تجيبُ عن سؤالٍ
آخرَ يسبقُه في ذهنِ القارئ: «**وهل ردَّ شيئًا أصلًا؟**». والجوابُ المقيسُ اليومَ
أنّ **كلَّ لسانٍ فُتِحَ له ملفٌّ ردَّ صلات، بلا استثناءٍ واحد**، وهذا لا يظهرُ في
شريطٍ يعرضُ من له صلاتٌ ويسكتُ عمّن لا صلاتِ له.

**والمقياسُ الثالثُ الذي تضيفُه:** عددُ **الجذورِ العربيّةِ المتمايزةِ** التي بلغَها
اللسان. فمئةُ صلةٍ تنتهي كلُّها إلى عشرةِ جذورٍ ليست كمئةٍ تنتهي إلى ثمانين، وعددُ
الصلاتِ وحدَه لا يفرِّقُ بينَهما.

**والعدُّ من `count_links.py` حرفًا بحرف** (الدالّةُ `scan_card` نفسُها والقالبُ
نفسُه والملغى نفسُه)، فلا يكونُ في الموقعِ عدّادانِ يختلفان.

**والتأريخُ في بطاقاتِ الألسنِ تقريبيٌّ متعارَفٌ عليه، وليس من قياسِنا**، وهو
مكتوبٌ في اللوحةِ بهذا الوصفِ صراحةً، لأنّ طبقاتِ الحقيقةِ تُوسَمُ ولا تُخلَط.

الاستعمال:
    python scripts/build_tongue_board.py
    python scripts/build_tongue_board.py --check     يفشلُ إن باتَتِ اللوحة
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as C  # noqa: E402
import build_links_showcase as S  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "tongue-board.json"

# التأريخُ عمودُ تعريفٍ للقارئِ لا عمودُ دليل: أقدمُ ما شاعَ من شهادةِ اللسانِ
# مكتوبةً، بالتقريبِ المتعارَفِ عليه في كتبِ التاريخِ اللغويّ.
META = {
    "aramaic":       ("الآرامِيّة", "Aramaic", "القَرنُ العاشِرُ ق.م", "10th c. BC", "آرامِيّة", "Aramaic script"),
    "hebrew":        ("العِبرِيّة", "Hebrew", "القَرنُ العاشِرُ ق.م", "10th c. BC", "عِبرِيّة", "Hebrew script"),
    "akkadian":      ("الأكّادِيّة", "Akkadian", "الألفُ الثّالِثةُ ق.م", "3rd millennium BC", "مِسمارِيّة", "cuneiform"),
    "phoenician-punic-scout": ("الفينيقِيّة", "Phoenician", "القَرنُ الحادي عَشَرَ ق.م", "11th c. BC", "فينيقِيّة", "Phoenician script"),
    "punic":         ("البونِيّة", "Punic", "القَرنُ التّاسِعُ ق.م", "9th c. BC", "بونِيّة", "Punic script"),
    "egyptian":      ("المِصرِيّةُ القَديمة", "Ancient Egyptian", "الألفُ الرّابِعةُ ق.م", "4th millennium BC", "هيروغليفِيّة", "hieroglyphs"),
    "coptic":        ("القِبطِيّة", "Coptic", "القَرنُ الثّالِثُ للميلاد", "3rd c. AD", "قِبطِيّة", "Coptic script"),
    "old-latin":     ("اللّاتينِيّةُ القَديمة", "Old Latin", "القَرنُ السّادِسُ ق.م", "6th c. BC", "لاتينِيّة", "Latin script"),
    "ancient-greek": ("اليونانِيّةُ القَديمة", "Ancient Greek", "القَرنُ الثّامِنُ ق.م", "8th c. BC", "يونانِيّة", "Greek script"),
    "persian":       ("الفارِسِيّة", "Persian", "القَرنُ التّاسِعُ للميلاد", "9th c. AD", "عَرَبِيّةٌ مُوَسَّعة", "Perso-Arabic"),
    "gothic":        ("القوطِيّة", "Gothic", "القَرنُ الرّابِعُ للميلاد", "4th c. AD", "قوطِيّةُ أُلفيلا", "Ulfilas alphabet"),
    "old-irish":     ("الإيرلَندِيّةُ القَديمة", "Old Irish", "القَرنُ السّادِسُ للميلاد", "6th c. AD", "أوغامِيّةٌ ثُمَّ لاتينِيّة", "Ogham then Latin"),
    "old-english":   ("الإنجليزِيّةُ القَديمة", "Old English", "القَرنُ السّابِعُ للميلاد", "7th c. AD", "رونِيّةٌ ثُمَّ لاتينِيّة", "runes then Latin"),
    "old-norse":     ("النُّردِيّةُ القَديمة", "Old Norse", "القَرنُ الثّامِنُ للميلاد", "8th c. AD", "رونِيّة", "runes"),
    "welsh":         ("الويلزِيّة", "Welsh", "القَرنُ التّاسِعُ للميلاد", "9th c. AD", "لاتينِيّة", "Latin script"),
    "middle-english": ("الإنجليزِيّةُ الوُسطى", "Middle English", "القَرنُ الثّاني عَشَرَ للميلاد", "12th c. AD", "لاتينِيّة", "Latin script"),
}

FAMILIES = [
    ("semitic", "الأخَواتُ السّامِيّةُ القَريبة", "The near Semitic sisters",
     "أقرَبُ ما إلى العَرَبِيّة، فتَرُدُّ الجَذرَ الثُّلاثِيَّ نَفسَه",
     "The nearest kin, so they return the triliteral root itself",
     lambda d: d == 1),
    ("egyptian", "الفَرعُ المِصرِيُّ، انشَقَّ أبكَر", "The Egyptian branch, split deeper",
     "انشَقَّ قَبلَ أن يَستَقِرَّ الجَذرُ الثُّلاثِيّ، فيَرُدُّ النَّواةَ",
     "Split before the triliteral root settled, so it returns the nucleus",
     lambda d: d == 2),
    ("distant", "الفُروعُ البَعيدة", "The distant branches",
     "أبعَدُ الفُروعِ نَسَبًا، وفيها اللّاتينِيَّةُ واليونانِيَّةُ والجِرمانِيّةُ والسِّلتِيَّةُ والفارِسِيّة",
     "The farthest branches: Latin, Greek, Germanic, Celtic and Persian",
     lambda d: d >= 3),
]


def iter_cards(path):
    """بطاقاتُ الملفِّ واحدةً واحدةً، بمخرَجٍ مطابقٍ لـ`CARD_SPLIT.split(...)[1:]`.

    **العلّةُ ذاكرةٌ لا سرعة.** ملفّاتُ القراءةِ 380 ميجا، وكان البانِي يُبقي
    ثلاثَ نسخٍ من الملفِّ الواحدِ في آنٍ: النصَّ الخامَّ، ونسخةَ `bare` بعدَ
    التطبيعِ ونزعِ الشكل، ثمّ قائمةَ `split` بكلِّ بطاقاتِه. فبلغَ البانِي
    **1.2 جيجا** في ذروتِه، وهو يعملُ في كلِّ إيداع. والذاكرةُ الحرّةُ على
    الجهازِ 1.2 جيجا من 15.4، فصارَ هذا البانِي وحدَه سقفَ التوازي.

    والمولِّدُ يُبقي نسخةَ `bare` وبطاقةً واحدةً فقط، ويُحرِّرُ النصَّ الخامَّ
    فورَ التطبيع. **والمخرَجُ لم يتغيّرْ حرفًا**، وذلك مُتحقَّقٌ منه بمقابلةِ
    `data/tongue-board.json` قبلَ التعديلِ وبعدَه.
    """
    # طبّع سطرًا واحدًا في كل مرة. صيغة المخرَج مطابقةٌ للمقسّم القديم:
    # تبدأ البطاقة بما بعد بادئة العنوان ``### `` وتنتهي قبل العنوان التالي.
    block: list[str] | None = None
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = C.bare(raw_line)
            marker = C.CARD_SPLIT.match(line)
            if marker:
                if block is not None:
                    yield "".join(block)
                block = [line[marker.end():]]
            elif block is not None:
                block.append(line)
    if block is not None:
        yield "".join(block)


def gather() -> dict:
    per = collections.defaultdict(collections.Counter)
    roots = collections.defaultdict(set)
    words = collections.defaultdict(set)

    for path in sorted(READINGS.glob("*.md")):
        lang = path.stem
        # طبقةُ §8 المعمّاةُ تحقُّقٌ مقيسٌ قيدَ التنفيذِ، لا تدخلُ العدَّ المنشورَ
        # حتّى يحكمَ المؤلّفُ بعدَ كشفِ المفتاح (التسجيلُ المسبقُ 2026-08-17)
        if lang.startswith("s8-"):
            continue
        if lang not in META:
            continue
        for block in iter_cards(path):
            degrees = C.scan_card(block)
            if not degrees:
                continue
            for d in degrees:
                per[lang][C.layer(d)] += 1
            ma = S.RX_ARABIC.search(block)
            r = S.arabic_root(ma.group(1) if ma else "", block)
            if r:
                roots[lang].add(r)
            m = (C.FAMILY.search(block) or C.MEMBER.search(block)
                 or C.HEADWORD.match(block.split("\n", 1)[0]))
            if m:
                words[lang].add(m.group(1).strip())
    return per, roots, words


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    per, roots, words = gather()
    dist = S.DISTANCE

    tongues = []
    for key, c in per.items():
        ar, en, era_ar, era_en, scr_ar, scr_en = META[key]
        r, n, f = c["root"], c["nucleus"], c["floor"]
        total = r + n + f
        share = round(100 * n / (r + n), 1) if (r + n) else 0.0
        # **يُجيبُ عندَ...**: وصفٌ للقارئِ مُشتَقٌّ من الرقمِ لا مضافٌ إليه
        if share >= 60:
            ans_ar, ans_en, ans = "يُجيبُ عندَ النَّواة", "answers at the nucleus", "nucleus"
        elif share <= 40:
            ans_ar, ans_en, ans = "يُجيبُ عندَ الجَذر", "answers at the root", "root"
        else:
            ans_ar, ans_en, ans = "يُجيبُ عندَ الطَّبَقَتَين", "answers at both layers", "both"
        tongues.append({
            "key": key, "ar": ar, "en": en,
            "era_ar": era_ar, "era_en": era_en, "script_ar": scr_ar, "script_en": scr_en,
            "distance": dist.get(key, 3),
            "links": total, "root": r, "nucleus": n, "floor": f,
            "nucleus_share": share,
            "arabic_roots": len(roots[key]), "branch_words": len(words[key]),
            "answers": ans, "answers_ar": ans_ar, "answers_en": ans_en,
        })
    tongues.sort(key=lambda t: (-t["links"], t["key"]))

    fams = []
    for fkey, far, fen, nar, nen, test in FAMILIES:
        mem = [t for t in tongues if test(t["distance"])]
        if not mem:
            continue
        R = sum(t["root"] for t in mem)
        N = sum(t["nucleus"] for t in mem)
        fams.append({
            "key": fkey, "ar": far, "en": fen, "note_ar": nar, "note_en": nen,
            "links": sum(t["links"] for t in mem),
            "nucleus_share": round(100 * N / (R + N), 1) if (R + N) else 0.0,
            # الجذورُ المتمايزةُ في الأسرةِ **اتّحادُ مجموعاتِها لا جمعُ أعدادِها**،
            # فاللسانانِ الشقيقانِ يبلغانِ الجذرَ الواحدَ فيُعَدُّ مرّتَينِ لو جُمِع
            "arabic_roots": len(set().union(*(roots[t["key"]] for t in mem))),
            "tongues": mem,
        })

    payload = {
        "generated_by": "scripts/build_tongue_board.py",
        "layer": "استكشاف",
        "note": ("العدُّ من count_links.py وهو التعريفُ الوحيدُ للصلةِ في المشروع. "
                 "والتأريخُ في بطاقاتِ الألسنِ تقريبيٌّ متعارَفٌ عليه وليس من قياسِنا."),
        "opened": len(tongues),
        "answered": sum(1 for t in tongues if t["links"] > 0),
        "totals": {
            "links": sum(t["links"] for t in tongues),
            "arabic_roots": len(set().union(*roots.values())) if roots else 0,
            "branch_words": sum(t["branch_words"] for t in tongues),
        },
        "families": fams,
        "tongues": tongues,
    }

    text = json.dumps(payload, ensure_ascii=False, indent=1)
    if args.check:
        old = OUT.read_text(encoding="utf-8") if OUT.exists() else ""
        if old.strip() != text.strip():
            print("FAIL: لوحةُ الألسنِ باتَت؛ أعِدْ build_tongue_board.py وأودِعِ الناتج")
            return 1
        print(f"CLEAN: لوحةُ الألسنِ حاضرة، {payload['answered']} من "
              f"{payload['opened']} لسانًا ردَّ صلات")
        return 0

    OUT.write_text(text, encoding="utf-8", newline="\n")
    print(f"{'اللسان':24}{'صلة':>7}{'جذرًا':>8}{'كلمة':>8}{'نواة%':>8}")
    for t in tongues:
        print(f"  {t['key']:24}{t['links']:>7}{t['arabic_roots']:>8}"
              f"{t['branch_words']:>8}{t['nucleus_share']:>8}")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}  ({payload['answered']} من "
          f"{payload['opened']} لسانًا ردَّ صلات، والمجموع {payload['totals']['links']:,} صلة)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
