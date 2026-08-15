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
import re
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


# **سؤالُ المؤلّفِ الذي فرضَ هذا الفصلَ (2026-08-16):** «26 من 6,810 في
# اليونانيّةِ معناهُ منهجٌ خاطئ». والقياسُ كشفَ أنّ 6,810 كان يخلطُ المسجَّلَ
# بالمقروء: 5,665 من حقولِ حكمِ اليونانيّةِ نصُّها «غيرُ صادر» أي جردٌ لم
# يُقرَأْ بعدُ، و362 بطاقةً أُغلِقَت «مصدرٌ ساميٌّ مسمًّى» وهي وصلٌ إيجابيٌّ
# لا يعدُّه السلَّم. فالنسبةُ الصادقةُ تُحسَبُ من المقروءِ حتّى قرار.
OPEN_VALUE = re.compile(
    r"غير صادر|OPEN-|TWO-LAYER-OPEN|مرشحون مرخصون|لا مرشح|لم يصدر|قيد "
    r"|TOOL-GAP|LAW-GAP|MORPHOLOGY-GAP|SOURCE-GAP")
SEMITIC_CLOSE = re.compile(r"SEMITIC-SOURCE")
RANK = {"open": 0, "closed": 1, "semitic": 2, "linked": 3}


def classify(values: list[str]) -> str:
    """حالُ البطاقةِ من حقولِ حكمِها: سلَّمٌ، فمصدرٌ ساميٌّ، فمُغلَقٌ مسمًّى،
    فمفتوح. والحقلُ الفارغُ أو المفتوحُ لا يجعلُ البطاقةَ مقروءة."""
    named = semitic = False
    for v in values:
        if any(d in v for d in C.DEGREES):
            return "linked"
        if not v.strip(" *`.؛:") or OPEN_VALUE.search(v):
            continue
        named = True
        if SEMITIC_CLOSE.search(v):
            semitic = True
    return "semitic" if semitic else "closed" if named else "open"


def scan_readings() -> dict[str, dict]:
    """يفصلُ المسجَّلَ عن المقروءِ حتّى قرار، بوحدةِ مفتاحِ العدّادِ القانونيّ.

    المفتاحُ (أسرةٌ أو عضوٌ أو كلمةُ عنوانٍ، كما في `count_links.scan_path`)
    يُصنَّفُ بأقوى حالٍ رُئيَت له في بطاقاتِه كلِّها، والبطاقاتُ بلا مفتاحٍ
    تُعَدُّ أفرادًا."""
    heading = re.compile(r"^#{3,4}\s+(.+)$")
    out: dict[str, dict] = {}
    for path in sorted(READINGS.glob("*.md")):
        best: dict[str, int] = {}
        keyless = {"open": 0, "closed": 0, "semitic": 0, "linked": 0}
        cards = verdict_cards = 0
        head: str | None = None
        key: str | None = None
        hw_key: str | None = None
        values: list[str] = []

        def close_card() -> None:
            # كلمةُ العنوانِ احتياطٌ أخيرٌ كما في `scan_path` بالضبط: معرّفُ
            # الأسرةِ أو العضوِ من المتنِ يتقدَّمُ عليها ولو جاءَ متأخّرًا،
            # وإقفالُها مبكّرًا خفَّضَ عدَّ المصريّةِ 679 مفتاحًا عن العدّاد.
            nonlocal verdict_cards
            if head is None or "<" in head:
                return
            state = classify(values)
            if state == "linked":
                verdict_cards += 1
            k = key or hw_key
            if k:
                best[k] = max(best.get(k, 0), RANK[state])
            else:
                keyless[state] += 1

        for raw in path.open(encoding="utf-8", errors="replace"):
            line = C.bare(raw.rstrip("\r\n"))
            m = heading.match(line)
            if m:
                close_card()
                head = m.group(1)
                if "<" not in head:
                    cards += 1
                values = []
                fam = C.FAMILY.search(head)
                mem = C.MEMBER.search(head)
                key = (fam.group(1).strip() if fam
                       else mem.group(1).strip() if mem else None)
                hw = C.HEADWORD.match(head)
                hw_key = hw.group(1).strip() if hw else None
                continue
            if head is None:
                continue
            if key is None:
                fam = C.FAMILY.search(line)
                mem = C.MEMBER.search(line)
                if fam:
                    key = fam.group(1).strip()
                elif mem:
                    key = mem.group(1).strip()
            v = C.VERDICT_FIELDS.match(line)
            if v and not any(c in v.group(1) for c in C.CANCELLED):
                values.append(v.group(1))
        close_card()

        counts = dict(keyless)
        names = {r: n for n, r in RANK.items()}
        for state_rank in best.values():
            counts[names[state_rank]] += 1
        concluded = counts["linked"] + counts["semitic"] + counts["closed"]
        out[path.stem] = {
            "cards": cards,
            "verdict_cards": verdict_cards,
            "treated_distinct": sum(counts.values()),
            "registered_open": counts["open"],
            "concluded": concluded,
            "linked_distinct": counts["linked"],
            "semitic_source": counts["semitic"],
            "closed_other": counts["closed"],
            "keyless": sum(keyless.values()),
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
            "registered_open": r["registered_open"],
            "concluded": r["concluded"],
            "linked_distinct": r["linked_distinct"],
            "semitic_source": r["semitic_source"],
            "closed_other": r["closed_other"],
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
                "يُصنَّفُ بأقوى حالٍ رُئيَت له",
        "note": "السكّانُ أعدادُ فهارسِ الفروعِ الكاملةِ بأسماءِ مصادرِها. "
                "المسجَّلُ جردٌ لم يُقرَأْ بعدُ ولا يدخلُ في مقامِ نسبةِ الربط؛ "
                "النسبةُ = المربوطُ من المقروءِ حتّى قرار. "
                "الباقي = السكّانُ ناقصَ كلِّ ما مُسَّ (مسجَّلًا ومقروءًا).",
        "rows": rows,
        "totals": {
            "population": sum(x["population"] or 0 for x in rows),
            "treated_distinct": sum(x["treated_distinct"] for x in rows),
            "registered_open": sum(x["registered_open"] for x in rows),
            "concluded": sum(x["concluded"] for x in rows),
            "linked_distinct": sum(x["linked_distinct"] for x in rows),
            "semitic_source": sum(x["semitic_source"] for x in rows),
            "closed_other": sum(x["closed_other"] for x in rows),
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
    hdr = (f"{'اللسان':20}{'السكّان':>9}{'سُجِّل':>8}{'قُرِئ':>7}{'رُبِط':>7}"
           f"{'ساميّ':>7}{'أُغلِق':>7}{'نسبة':>6}{'ص+م':>7}{'الباقي':>9}")
    print(hdr)
    print("-" * 96)
    for x in payload["rows"]:
        pop = f"{x['population']:,}" if x["population"] is not None else "-"
        rem = f"{x['remaining']:,}" if x["remaining"] is not None else "-"
        rate = (f"{100 * x['linked_distinct'] / x['concluded']:.0f}%"
                if x["concluded"] else "-")
        mark = "*" if x["partial_index"] else " "
        print(f"{x['ar']:20}{pop:>9}{x['registered_open']:>8,}"
              f"{x['concluded']:>7,}{x['linked_distinct']:>7,}"
              f"{x['semitic_source']:>7,}{x['closed_other']:>7,}{rate:>6}"
              f"{x['sweep_both']:>7,}{rem:>8}{mark}")
    t = payload["totals"]
    print("-" * 96)
    print(f"{'الجملة':20}{t['population']:>9,}{t['registered_open']:>8,}"
          f"{t['concluded']:>7,}{t['linked_distinct']:>7,}"
          f"{t['semitic_source']:>7,}{t['closed_other']:>7,}{'':>6}"
          f"{t['sweep_both']:>7,}")
    print("\nالنسبةُ = المربوطُ سلَّميًّا من المقروءِ حتّى قرار (لا من المسجَّل)."
          "\nساميّ = أُغلِقَ «مصدرٌ ساميٌّ مسمًّى» وهو وصلٌ بالمجالِ الساميِّ خارجَ السلَّم."
          "\nأُغلِقَ = إغلاقاتٌ مسمّاةٌ أخرى (قرضٌ من طرفٍ ثالث، خارجُ النطاق، إحالةُ صيغة…)."
          "\n* فهرسُ kaikki جزئيٌّ لهذا اللسانِ والمعالجةُ من مصادرَ أوسعَ منه "
          "(CAD وخشيم)، فباقيه لا يُقرأُ من هذا العمود.")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
