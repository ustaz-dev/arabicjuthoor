# -*- coding: utf-8 -*-
"""بوّابةُ انضباطِ النواة (2026-08-01)

تكشفُ آليًّا العيوبَ التي أسقطَت 84% من عيّنةِ المراجعةِ المضادّة، ولا تحكمُ على
لسانٍ ولا تمنعُ صلةً، بل تسمّي البطاقةَ وعيبَها ليُعادَ فيها النظر.

العيوبُ المكشوفة:
  D1  تخطّي موضعٍ صامتٍ في اختيارِ زوجِ النواة (الموضعان 1 و3، أو 2 و4) بلا تعليل.
  D2  نواةٌ عربيّةٌ واحدةٌ تُعارُ لمعانٍ متباعدةٍ عبرَ الألسن (تشتُّتُ النواة).
  D3  معجمٌ مسمًّى بلا نصٍّ منقول، أو اسمٌ مبهمٌ لا يعيّنُ كتابًا.
  D4  إرثٌ محكومٌ به معَ اشتقاقٍ يذكرُ مانحًا (from / via / calque / ultimately).
  D5  حقلُ حكمٍ بلا وسمِ طبقةِ الحقيقة، فلا يُعرف أهو مقيس أم استكشاف.

الاستعمال:  python scripts/check_nucleus_discipline.py [--lang aramaic] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"

# ------------------------------------------------------------------ تطبيع

_DIACRITICS = dict.fromkeys(range(0x064B, 0x0653))
_DIACRITICS[0x0640] = None  # tatweel


def bare(text: str) -> str:
    """NFC ثمّ نزعُ الشكلِ والتطويل، فالحقولُ تُكتبُ مشكولةً وغيرَ مشكولة."""
    return unicodedata.normalize("NFC", text).translate(_DIACRITICS)


# ------------------------------------------------------------------ أنماط

CARD_SPLIT = re.compile(r"^###\s+", re.M)

CANON_VERDICT = "- الحكم (استكشاف):"
CANON_NUC_FIELD = "- حكم طبقة النواة:"

FIELD = lambda name: re.compile(r"^-\s*" + name + r"\s*[:：]\s*(.+)$", re.M)

RX_VERDICT = FIELD(r"الحكم(?:\s*\([^)]*\))?")
RX_NUC_LAYER = FIELD(r"حكم طبقة النواة")
RX_ROOT_LAYER = FIELD(r"حكم طبقة الجذر")
RX_SOUND = FIELD(r"مسار الصوت")
RX_OLDEST = FIELD(r"أقدم صورة مستعادة")
RX_SCREEN = FIELD(r"المصفاة")
RX_BRANCH_SENSE = FIELD(r"المعنى من قاموس الفرع")
RX_ARABIC_SCAN = FIELD(r"مسح (?:المعاني )?العربي[ةه]")

# النواةُ تُذكرُ هكذا: نواة `فر`  /  النواة `فم`
RX_NUCLEUS = re.compile(r"(?:ال)?نواة\s*[`«\"']([^`»\"'\n]{1,6})[`»\"']")

DEGREES = ("ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE")
CANCELLED = ("غير صادر", "ناسخ", "منسوخ")

# D1: مواضعُ الصوامتِ المأخوذة، مكتوبةً بالأرقامِ الغربيّةِ أو العربيّة
RX_POSITIONS = re.compile(r"الموضع(?:ين|ان|ي)?\s*([0-9٠-٩])\s*و\s*([0-9٠-٩])")

# D3: المعاجمُ المقبولةُ باسمٍ يعيّنُ كتابًا
ACCEPTED_LEXICA = (
    "لسان العرب", "تاج العروس", "تاج اللغة وصحاح العربية", "الصحاح",
    "القاموس المحيط", "مقاييس اللغة",
    "معجم مقاييس اللغة", "كتاب العين", "تهذيب اللغة", "المخصص", "أساس البلاغة",
    "جمهرة اللغة", "المحكم", "المفردات في غريب القرآن",
)
AMBIGUOUS_LEXICA = ("المحيط", "المفردات", "المعجم", "القاموس")
RX_QUOTE = re.compile(r"[«\"“]([^»\"”]{12,})[»\"”]")

# D4: عباراتُ المنحِ في الاشتقاق
DONOR_HINTS = (
    "borrowed from", "loanword", "loan from", "via ", "calque", "ultimately from",
    "from akkadian", "from aramaic", "from hebrew", "from syriac", "from phoenician",
    "from arabic", "from greek", "from latin", "from persian", "from egyptian",
)
INHERIT_OK = ("proto-", "inherited")


def norm_digits(ch: str) -> int:
    o = ord(ch)
    return o - 0x0660 if 0x0660 <= o <= 0x0669 else int(ch)


def issued_degree(block: str) -> str | None:
    """أعلى حكمٍ صادرٍ في البطاقة، من الحقلِ الرئيسِ أو حقلِ طبقةِ النواة."""
    for rx in (RX_VERDICT, RX_NUC_LAYER, RX_ROOT_LAYER):
        m = rx.search(block)
        if not m:
            continue
        v = m.group(1)
        if any(c in v for c in CANCELLED):
            continue
        for d in DEGREES:
            if d in v:
                return d
    return None


def check_card(lang: str, raw: str) -> list[dict]:
    """يُرجعُ قائمةَ عيوبٍ لبطاقةٍ واحدة."""
    block = bare(raw)
    head = block.split("\n", 1)[0].strip()[:110]
    degree = issued_degree(block)
    if degree is None:
        return []  # لا حكمَ صادرًا، فلا شيءَ يُدقَّق

    out = []
    add = lambda code, detail: out.append(
        {"lang": lang, "code": code, "heading": head, "degree": degree, "detail": detail}
    )

    # D5: وسمُ طبقةِ الحقيقة في حقل الحكم.  للعناوين التاريخية
    # أشكال قانونية متعددة يتولى scripts/count_links.py تعريف عدّها.
    if CANON_VERDICT not in block and "NUCLEUS" in degree and CANON_NUC_FIELD not in block:
        add("D5-FIELD", "حقل الحكم بغير الاسم الموحد")

    # D1: تخطّي موضع
    if "NUCLEUS" in degree:
        m = RX_SOUND.search(block)
        if m:
            pos = RX_POSITIONS.search(m.group(1))
            if pos:
                a, b = norm_digits(pos.group(1)), norm_digits(pos.group(2))
                if abs(b - a) > 1:
                    justified = any(
                        w in m.group(1) for w in ("زائدة", "من الوزن", "سابقة", "لاحقة", "علة", "أجوف", "مضعف")
                    )
                    if not justified:
                        add("D1-SKIP", f"أُخذ الموضعان {a} و{b} بلا تعليل لسقوط ما بينهما")

    # D3: المعاجم
    scan = RX_ARABIC_SCAN.search(block)
    scan_zone = block[scan.start():scan.start() + 1400] if scan else block
    named = [x for x in ACCEPTED_LEXICA if x in scan_zone]
    if "NUCLEUS" in degree or "ROOT" in degree:
        if len(named) < 2:
            amb = [x for x in AMBIGUOUS_LEXICA if x in scan_zone and not any(x in n for n in named)]
            add("D3-SOURCES", f"معاجم معيَّنة={len(named)}؛ أسماء مبهمة={amb or 'لا شيء'}")
        elif not RX_QUOTE.search(scan_zone):
            add("D3-NOQUOTE", "المعجمان مسمَّيان بلا نص منقول")

    # D4: اتجاه الانتقال
    old = RX_OLDEST.search(block)
    if old:
        low = old.group(1).lower()
        if any(h in low for h in DONOR_HINTS) and not any(k in low for k in INHERIT_OK):
            add("D4-DIRECTION", f"اشتقاق يذكر مانحًا: {old.group(1)[:70]}")

    return out


def nucleus_dispersion(cards_by_nucleus: dict) -> list[dict]:
    """D2: نواةٌ واحدةٌ تُعارُ لمعانٍ متباعدةٍ عبرَ الألسن."""
    out = []
    for nuc, rows in sorted(cards_by_nucleus.items(), key=lambda kv: -len(kv[1])):
        senses = {r["sense"].lower()[:40] for r in rows if r["sense"]}
        langs = {r["lang"] for r in rows}
        if len(rows) >= 6 and len(senses) >= 5 and len(langs) >= 2:
            out.append({
                "nucleus": nuc, "cards": len(rows), "languages": len(langs),
                "distinct_senses": len(senses),
                "sample": sorted(senses)[:6],
            })
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", action="append", help="اقصر الفحص على لسان (يتكرر)")
    ap.add_argument("--json", help="اكتب التقرير الكامل إلى ملف JSON")
    ap.add_argument("--max-show", type=int, default=4, help="أمثلة تُطبع لكل عيب")
    args = ap.parse_args()

    sys.stdout.reconfigure(encoding="utf-8")
    paths = sorted(READINGS.glob("*.md"))
    if args.lang:
        wanted = set(args.lang)
        paths = [p for p in paths if p.stem in wanted]
    if not paths:
        print("لا ملفات قراءة مطابقة.")
        return 2

    findings: list[dict] = []
    by_nucleus: dict[str, list] = collections.defaultdict(list)
    total_cards = 0

    for path in paths:
        lang = path.stem
        text = path.read_text(encoding="utf-8")
        for raw in CARD_SPLIT.split(text)[1:]:
            total_cards += 1
            findings.extend(check_card(lang, raw))
            block = bare(raw)
            deg = issued_degree(block)
            if deg and "NUCLEUS" in deg:
                mn = RX_NUCLEUS.search(block)
                ms = RX_BRANCH_SENSE.search(block)
                if mn:
                    by_nucleus[mn.group(1).strip()].append(
                        {"lang": lang, "sense": (ms.group(1) if ms else "")}
                    )

    dispersion = nucleus_dispersion(by_nucleus)

    counts = collections.Counter(f["code"] for f in findings)
    print(f"بطاقات مفحوصة: {total_cards:,} في {len(paths)} ملفًا")
    print(f"بطاقات ذات حكم صادر تحمل نواة مسماة: {sum(len(v) for v in by_nucleus.values()):,}"
          f" على {len(by_nucleus):,} نواة متمايزة\n")

    if not findings and not dispersion:
        print("RESULT: CLEAN")
        return 0

    print("العيوب المكشوفة:")
    for code, n in counts.most_common():
        print(f"   {code:16} {n:6}")
        for f in [x for x in findings if x["code"] == code][: args.max_show]:
            print(f"        [{f['lang']}] {f['heading'][:70]}")
            print(f"            {f['detail'][:110]}")

    if dispersion:
        print(f"\n   D2-DISPERSION    {len(dispersion):6}  (نواة واحدة لمعانٍ متباعدة)")
        for d in dispersion[: args.max_show * 2]:
            print(f"        `{d['nucleus']}`  بطاقات={d['cards']}  ألسن={d['languages']}"
                  f"  معانٍ متمايزة={d['distinct_senses']}")
            print(f"            {' | '.join(d['sample'])[:150]}")

    if args.json:
        pathlib.Path(args.json).write_text(
            json.dumps({"total_cards": total_cards, "findings": findings,
                        "dispersion": dispersion}, ensure_ascii=False, indent=1),
            encoding="utf-8")
        print(f"\nكُتب التقرير الكامل: {args.json}")

    print(f"\nRESULT: {len(findings) + len(dispersion)} finding(s)")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
