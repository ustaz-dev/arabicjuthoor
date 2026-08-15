# -*- coding: utf-8 -*-
"""تقريرُ التغطية: كم في القاموس، كم عولِج، كم رُبِط، كم بقي (2026-08-16)

**سؤالُ المؤلّفِ الذي يجيبُ عنه:** «كم كلمةً عالجْنا في كلِّ لسانٍ وكم وجدْنا
مربوطًا، حتّى أفهمَ كم بقيَ للمعالجةِ والدرس».

**الوحدةُ واحدةٌ في كلِّ الأعمدة**: مفتاحُ البطاقةِ كما يعرّفُه العدّادُ القانونيُّ
`count_links.scan_path` (أسرةٌ أو عضوٌ مسمًّى أو كلمةُ العنوان)، فالمعالَجُ
والمربوطُ يُعَدّانِ بالمقياسِ نفسِه ولا يظهرُ عدّادانِ متخالفان. وسكّانُ القاموسِ
عددُ فهرسِ الفرعِ الكاملِ، وذكرُه جائزٌ (أعدادُ الفهارسِ الكاملةِ سكّانُ كتالوج،
لا قائمةً خاصّةً معدودة).

الأعمدة:
    السكّان     مداخلُ فهرسِ قاموسِ الفرعِ المبنيِّ عندَنا (باسمِ مصدرِه)
    عولِج       مفاتيحُ متمايزةٌ ظهرَت في بطاقاتِ ملفِّ القراءة (بحكمٍ أو بغيرِه)
    رُبِط       المفاتيحُ المتمايزةُ التي صدرَ فيها حكمٌ (أيُّ درجةٍ من السلَّم)
    مرشَّحاتُ المسح   صوتٌ+معنًى وصوتٌ فقط من لوحةِ المسحِ المباشر، تنتظرُ قارئًا
    بطاقاتُ مسحٍ بلا حكم   بطاقاتٌ مكتوبةٌ في مجلّداتِ المسحِ الفرعيّةِ لم يُحكَمْ فيها
    الباقي      السكّانُ ناقصَ المعالَجِ حيثُ الفهرسُ هو مصدرُ المعالجةِ نفسُه

**طبقةُ استكشاف**: الأرقامُ أعدادُ فهارسَ ومعدَّلاتُ تقدُّمٍ، لا دعوى نتيجةٍ.

الاستعمال:
    python scripts/build_coverage_report.py            يطبعُ ويكتبُ JSON
    python scripts/build_coverage_report.py --check    يفحصُ طزاجةَ المكتوب
"""
from __future__ import annotations

import argparse
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as C  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
LEXICONS = ROOT / "data" / "branch-lexicons"
OUT = ROOT / "data" / "coverage-report.json"

# ملفُّ القراءةِ ← فهرسُ سكّانِه. والغائبُ عن هذا الجدولِ سكّانُه غيرُ مفهرَسينَ
# آليًّا عندَنا (كالفينيقيّةِ من ألواحِ Cooke 1903) فيُتركُ عمودُه فارغًا بصدق.
POPULATION = {
    "aramaic": ("aramaic", "Kaikki Aramaic"),
    "hebrew": ("hebrew", "Kaikki Hebrew"),
    "akkadian": ("akkadian", "Kaikki Akkadian"),
    "old-latin": ("latin", "Kaikki Latin"),
    "ancient-greek": ("ancient-greek", "Kaikki Ancient Greek"),
    "gothic": ("gothic", "Kaikki Gothic"),
    "old-norse": ("old-norse", "Kaikki Old Norse"),
    "old-english": ("old-english", "Kaikki Old English"),
    "middle-english": ("middle-english", "Kaikki Middle English"),
    "old-irish": ("old-irish", "Kaikki Old Irish"),
    "welsh": ("welsh", "Kaikki Welsh"),
    "persian": ("persian", "Kaikki Persian"),
}
SPECIAL = {
    "egyptian": (ROOT / "data" / "aed-egyptian-lexicon.json", "AED v1.0"),
    "coptic": (ROOT / "data" / "coptic-lexicon.json", "CCL v1.2"),
}
# الأكّاديّةُ عولجَت من CAD وخشيم فوقَ فهرسِ kaikki الصغير، فباقيها لا يُحسَبُ
# من الفهرسِ وحدَه ويُذكَرُ ذلك في الحاشية.
PARTIAL_INDEX = {"akkadian"}

NAMES = {
    "aramaic": "الآراميّة", "hebrew": "العبريّة", "akkadian": "الأكّاديّة",
    "phoenician-punic-scout": "الفينيقيّة", "punic": "البونيّة",
    "egyptian": "المصريّة القديمة", "coptic": "القبطيّة",
    "ancient-greek": "اليونانيّة القديمة", "old-latin": "اللاتينيّة القديمة",
    "persian": "الفارسيّة", "gothic": "القوطيّة", "old-norse": "النُّرديّة القديمة",
    "old-english": "الإنجليزيّة القديمة", "middle-english": "الإنجليزيّة الوسطى",
    "old-irish": "الإيرلنديّة القديمة", "welsh": "الويلزيّة",
}
# مفاتيحُ لوحةِ المسحِ تخالفُ أسماءَ ملفّاتِ القراءة: شرطاتٌ سفليّةٌ وترتيبٌ
# معكوسٌ (`english_middle` مقابلَ `middle-english`). تُطبَّعُ الشرطةُ أوّلًا
# ثمّ يُسأَلُ الجدول، وبغيرِ هذا ضاعَ من الجدولِ 893 مرشَّحَ صوتٍ+معنًى.
SWEEP_ALIAS = {"latin": "old-latin", "greek": "ancient-greek",
               "norse": "old-norse", "irish": "old-irish",
               "english-middle": "middle-english",
               "english-old": "old-english"}


def sweep_key(raw: str) -> str:
    key = raw.strip().lower().replace("_", "-").replace(" ", "-")
    return SWEEP_ALIAS.get(key, key)


def population(lang: str) -> tuple[int | None, str]:
    if lang in SPECIAL:
        path, src = SPECIAL[lang]
        if path.exists():
            return len(json.load(path.open(encoding="utf-8"))["entries"]), src
        return None, src
    if lang in POPULATION:
        stem, src = POPULATION[lang]
        path = LEXICONS / f"{stem}.json"
        if path.exists():
            return len(json.load(path.open(encoding="utf-8"))["entries"]), src
        return None, src
    return None, ""


def scan_readings() -> dict[str, dict]:
    """المعالَجُ والمربوطُ بوحدةِ العدّادِ القانونيِّ نفسِها، في مرورٍ واحد."""
    out: dict[str, dict] = {}
    for path in sorted(READINGS.glob("*.md")):
        lang = path.stem
        treated: set[str] = set()
        linked: set[str] = set()
        cards = verdict_cards = keyless = keyless_linked = 0
        for head, degrees, key in C.scan_path(path):
            if "<" in head:                     # قالبُ رأسِ الملفّ
                continue
            cards += 1
            if degrees:
                verdict_cards += 1
            if key:
                treated.add(key)
                if degrees:
                    linked.add(key)
            else:
                keyless += 1
                if degrees:
                    keyless_linked += 1
        out[lang] = {
            "cards": cards,
            "verdict_cards": verdict_cards,
            "treated_distinct": len(treated) + keyless,
            "linked_distinct": len(linked) + keyless_linked,
            "keyless": keyless,
        }
    return out


def scan_sweep_folders() -> dict[str, int]:
    """بطاقاتُ المسحِ في المجلّداتِ الفرعيّةِ: مكتوبةٌ ولا حكمَ فيها بعد."""
    out: dict[str, int] = {}
    for path in READINGS.rglob("*.md"):
        if path.parent == READINGS:
            continue
        stem = path.stem                        # batch-013-old-irish
        lang = stem.split("-", 2)[-1] if stem.startswith("batch-") else stem
        lang = sweep_key(lang)
        n = sum(1 for line in path.open(encoding="utf-8", errors="replace")
                if line.startswith("### "))
        out[lang] = out.get(lang, 0) + n
    return out


def sweep_board() -> dict[str, dict]:
    path = ROOT / "data" / "sweep-board.json"
    if not path.exists():
        return {}
    board = json.load(path.open(encoding="utf-8"))
    out = {}
    for t in board.get("tongues", []):
        key = sweep_key(t["key"])
        out[key] = {"both": t.get("both", 0), "sound_only": t.get("sound_only", 0)}
    return out


def screening_events() -> dict[str, int]:
    """أحداثُ الفحصِ الخامِّ من `coverage-summary.json`، **بوحدةِ الحدثِ لا
    العضوِ المتمايز**: العضوُ يُفحَصُ في جولاتٍ متكرّرةٍ فيُعَدُّ في كلِّ مرّة
    (اللاتينيّةُ 864 ألفَ حدثٍ لفهرسِ 48 ألفَ مدخلة). فلا يدخلُ حسابَ الباقي،
    ويُعرَضُ سياقًا باسمِه الصحيح."""
    path = ROOT / "data" / "coverage-summary.json"
    if not path.exists():
        return {}
    d = json.load(path.open(encoding="utf-8"))
    return {sweep_key(k): v.get("members_examined", 0)
            for k, v in d.get("by_language", {}).items()}


def build() -> dict:
    readings = scan_readings()
    folders = scan_sweep_folders()
    board = sweep_board()
    events = screening_events()
    rows = []
    langs = [l for l in readings if l in NAMES]
    for lang in langs:
        r = readings[lang]
        pop, src = population(lang)
        remaining = None
        if pop is not None:
            remaining = max(pop - r["treated_distinct"], 0)
        rows.append({
            "key": lang,
            "ar": NAMES[lang],
            "population": pop,
            "population_source": src,
            "partial_index": lang in PARTIAL_INDEX,
            "cards": r["cards"],
            "treated_distinct": r["treated_distinct"],
            "linked_distinct": r["linked_distinct"],
            "verdict_cards": r["verdict_cards"],
            "sweep_both": board.get(lang, {}).get("both", 0),
            "sweep_sound_only": board.get(lang, {}).get("sound_only", 0),
            "sweep_cards_unjudged": folders.get(lang, 0),
            "screening_events": events.get(lang),
            "remaining": remaining,
        })
    rows.sort(key=lambda x: -(x["linked_distinct"]))
    return {
        "generated_by": "scripts/build_coverage_report.py",
        "layer": "استكشاف",
        "unit": "مفتاحُ البطاقةِ كما يعرّفُه count_links.scan_path؛ "
                "المعالَجُ والمربوطُ بوحدةٍ واحدة",
        "note": "السكّانُ أعدادُ فهارسِ الفروعِ الكاملةِ بأسماءِ مصادرِها. "
                "الباقي = السكّانُ ناقصَ المعالَجِ المتمايز.",
        "rows": rows,
        "totals": {
            "population": sum(x["population"] or 0 for x in rows),
            "treated_distinct": sum(x["treated_distinct"] for x in rows),
            "linked_distinct": sum(x["linked_distinct"] for x in rows),
            "sweep_both": sum(x["sweep_both"] for x in rows),
            "sweep_sound_only": sum(x["sweep_sound_only"] for x in rows),
            "sweep_cards_unjudged": sum(x["sweep_cards_unjudged"] for x in rows),
        },
    }


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    payload = build()
    if args.check:
        if not OUT.exists():
            print(f"STALE: {OUT.name} غيرُ موجود")
            return 1
        old = json.load(OUT.open(encoding="utf-8"))
        if old.get("rows") != payload["rows"]:
            print(f"STALE: {OUT.name} لا يطابقُ بياناتِ المستودع")
            return 1
        print("CURRENT")
        return 0

    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8", newline="\n")
    hdr = (f"{'اللسان':20}{'السكّان':>9}{'عولِج':>8}{'رُبِط':>7}"
           f"{'نسبة':>6}{'مسح ص+م':>9}{'صوت فقط':>9}{'بلا حكم':>9}{'الباقي':>9}")
    print(hdr)
    print("-" * 88)
    for x in payload["rows"]:
        pop = f"{x['population']:,}" if x["population"] is not None else "-"
        rem = f"{x['remaining']:,}" if x["remaining"] is not None else "-"
        rate = (f"{100 * x['linked_distinct'] / x['treated_distinct']:.0f}%"
                if x["treated_distinct"] else "-")
        mark = "*" if x["partial_index"] else " "
        print(f"{x['ar']:20}{pop:>9}{x['treated_distinct']:>8,}"
              f"{x['linked_distinct']:>7,}{rate:>6}{x['sweep_both']:>9,}"
              f"{x['sweep_sound_only']:>9,}{x['sweep_cards_unjudged']:>9,}"
              f"{rem:>8}{mark}")
    t = payload["totals"]
    print("-" * 88)
    print(f"{'الجملة':20}{t['population']:>9,}{t['treated_distinct']:>8,}"
          f"{t['linked_distinct']:>7,}{'':>6}{t['sweep_both']:>9,}"
          f"{t['sweep_sound_only']:>9,}{t['sweep_cards_unjudged']:>9,}")
    print("\n* فهرسُ kaikki جزئيٌّ لهذا اللسانِ والمعالجةُ من مصادرَ أوسعَ منه "
          "(CAD وخشيم)، فباقيه لا يُقرأُ من هذا العمود.")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
