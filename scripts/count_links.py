# -*- coding: utf-8 -*-
"""العدّادُ الواحدُ للصلات (2026-08-01)

**المشكلةُ التي يحلُّها:** في ملفّاتِ القراءةِ ستّةُ أشكالٍ من العناوينِ وستّةُ أسماءٍ
لحقلِ الحكم، فكانت كلُّ أداةٍ تُخرِجُ رقمًا مختلفًا: عدّادُ الموقعِ لا يرى ما ليسَ
تحتَ `### بطاقة` ولا ما ليسَ في `- الحكم`، فيسقطُ منه 640 حكمًا في الآراميّةِ و384
في العبريّة. ومحضرُ 2026-08-01 يسجّلُ فجوةَ مصالحةٍ في الإنجليزيّةِ والإيرلنديّةِ
لهذا السببِ عينِه.

**القاعدة:** هذا الملفُّ هو التعريفُ الوحيدُ للصلة. من أرادَ رقمًا فليأخذْه منه.

**ويُخرِجُ رقمَين لا رقمًا واحدًا، وهما لا يُخلَطان:**
  البطاقات  عددُ الأحكامِ الصادرة.
  الدعاوى   عددُ الأسرِ المتمايزةِ التي صدرَ فيها حكم. وهو الرقمُ الأصدقُ، لأنّ
            الأسرةَ الواحدةَ قد تحملُ ستَّ بطاقاتٍ فتُعَدُّ ستَّ صلاتٍ وهي دعوى واحدة.

الاستعمال:  python scripts/count_links.py [--json out.json] [--claims]
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

_DIAC = dict.fromkeys(range(0x064B, 0x0653))
_DIAC[0x0640] = None


def bare(t: str) -> str:
    return unicodedata.normalize("NFC", t).translate(_DIAC)


CARD_SPLIT = re.compile(r"^#{3,4}\s+", re.M)

# كلُّ أسماءِ حقولِ الحكمِ الموجودةِ فعلًا في الملفّات، لا المرغوبةِ منها
VERDICT_FIELDS = re.compile(
    r"^-\s*(?:"
    r"الحكم(?:\s*\([^)]*\))?"          # الحكم / الحكم (استكشاف)
    r"|الحسم"
    r"|حكم طبقة النواة"
    r"|حكم طبقة الجذر"
    r"|نتيجة طبقة النواة"
    r"|النتيجة"
    r")\s*[:：]\s*(.+)$",
    re.M,
)

FAMILY = re.compile(r"([a-z-]+:family:[0-9a-f]{8,})")
MEMBER = re.compile(
    r"(kaikki_[a-z_]+:\d+:[^\s`،؛,]+"
    r"|kellia_coptic_lexicon:C\d+"
    r"|aed-v1\.0:\d+)"
)
# بعضُ الملفّاتِ لا تحملُ معرّفَ أسرةٍ ولا عضوٍ، بل الكلمةَ في العنوانِ وحدَها،
# مثل `### بطاقة: alāku «يذهب»` و`### بطاقة: port «place»`. فتُتَّخذُ الكلمةُ مفتاحًا.
HEADWORD = re.compile(r"^[^:]{0,30}:\s*`?([^`«»\"'،؛,\n]{1,40}?)`?\s*[«\"']")

DEGREES = ("ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE")
CANCELLED = ("غير صادر", "ناسخ", "منسوخ", "غير صادرة")


def layer(degree: str) -> str:
    if "ROOT" in degree:
        return "root"
    if "NUCLEUS" in degree:
        return "nucleus"
    return "floor"


def is_template(head: str) -> bool:
    """القالبُ الفارغُ منسوخٌ في رأسِ كلِّ ملفِّ قراءةٍ وعنوانُه بأقواسٍ زاويّة،
    مثل `بطاقة: <الكلمة بالرومنة> «<معناها الموجز>»`، وفيه سطرُ حكمٍ نموذجيٌّ
    ليس حكمًا صادرًا. وخمسةُ قوالبَ كهذه كانت تُعَدُّ صلاتٍ قبلَ هذا الحارس."""
    return "<" in head


def scan_card(block: str) -> set[str]:
    """كلُّ الدرجاتِ الصادرةِ في بطاقةٍ واحدة، من أيِّ حقلٍ كان، بلا تكرار."""
    if is_template(block.split("\n", 1)[0]):
        return set()
    out = set()
    for v in VERDICT_FIELDS.findall(block):
        if any(c in v for c in CANCELLED):
            continue
        for d in DEGREES:
            if d in v:
                out.add(d)
                break
    return out


def scan_path(path: pathlib.Path):
    """اقرأ حقول العد فقط من غير إبقاء أجساد البطاقات الكبيرة في الذاكرة."""
    head: str | None = None
    degrees: set[str] = set()
    family: str | None = None
    member: str | None = None
    template = False
    with path.open(encoding="utf-8") as handle:
        for raw_line in handle:
            line = bare(raw_line.rstrip("\r\n"))
            heading = re.match(r"^#{3,4}\s+(.+)$", line)
            if heading:
                if head is not None:
                    key_match = HEADWORD.match(head)
                    yield head, degrees, family or member or (
                        key_match.group(1).strip() if key_match else None
                    )
                head = heading.group(1)
                degrees = set()
                family_match = FAMILY.search(head)
                member_match = MEMBER.search(head)
                family = family_match.group(1).strip() if family_match else None
                member = member_match.group(1).strip() if member_match else None
                template = is_template(head)
                continue
            if head is None or template:
                continue
            if family is None:
                match = FAMILY.search(line)
                if match:
                    family = match.group(1).strip()
            if member is None:
                match = MEMBER.search(line)
                if match:
                    member = match.group(1).strip()
            verdict = VERDICT_FIELDS.match(line)
            if not verdict:
                continue
            value = verdict.group(1)
            if any(cancelled in value for cancelled in CANCELLED):
                continue
            for degree in DEGREES:
                if degree in value:
                    degrees.add(degree)
                    break
    if head is not None:
        key_match = HEADWORD.match(head)
        yield head, degrees, family or member or (
            key_match.group(1).strip() if key_match else None
        )


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--json", help="اكتب الحصيلة إلى ملف JSON")
    ap.add_argument("--claims", action="store_true", help="اطبع عمود الدعاوى موسَّعًا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    per = collections.defaultdict(lambda: collections.Counter())
    fams = collections.defaultdict(lambda: collections.defaultdict(set))
    headings = collections.Counter()
    unkeyed = collections.Counter()
    total_cards = 0

    for path in sorted(READINGS.glob("*.md")):
        lang = path.stem
        # طبقةُ §8 المعمّاةُ تحقُّقٌ مقيسٌ قيدَ التنفيذِ، لا تدخلُ العدَّ المنشورَ
        # حتّى يحكمَ المؤلّفُ بعدَ كشفِ المفتاح (التسجيلُ المسبقُ 2026-08-17)
        if lang.startswith("s8-"):
            continue
        for head, degrees, key in scan_path(path):
            total_cards += 1
            if not degrees:
                continue
            headings[head.split(":", 1)[0].strip()[:34]] += 1
            if key is None:
                unkeyed[lang] += 1
            for d in degrees:
                lay = layer(d)
                per[lang][lay] += 1
                per[lang][d] += 1
                if key:
                    fams[lang][lay].add(key)

    root = sum(c["root"] for c in per.values())
    nuc = sum(c["nucleus"] for c in per.values())
    floor = sum(c["floor"] for c in per.values())
    croot = sum(len(f["root"]) for f in fams.values())
    cnuc = sum(len(f["nucleus"]) for f in fams.values())

    print(f"ملفّاتُ القراءة: {len(list(READINGS.glob('*.md')))}   البطاقاتُ الممسوحة: {total_cards:,}\n")
    print(f"{'اللسان':22} {'جذر':>6} {'نواة':>6} {'أرضيّة':>7} | {'دعاوى جذر':>10} {'دعاوى نواة':>11}")
    print("-" * 74)
    for lang, c in sorted(per.items(), key=lambda kv: -(kv[1]["root"] + kv[1]["nucleus"])):
        if not (c["root"] + c["nucleus"] + c["floor"]):
            continue
        print(f"{lang:22} {c['root']:6} {c['nucleus']:6} {c['floor']:7} | "
              f"{len(fams[lang]['root']):10} {len(fams[lang]['nucleus']):11}")
    print("-" * 74)
    print(f"{'المجموع':22} {root:6} {nuc:6} {floor:7} | {croot:10} {cnuc:11}")
    print(f"\nالبطاقات: {root + nuc + floor:,} حكمًا صادرًا")
    print(f"الدعاوى:  {croot + cnuc:,} أسرةً متمايزةً حُكِمَ فيها")
    if root + nuc:
        print(f"معامل التكرار: {(root + nuc) / max(croot + cnuc, 1):.2f} بطاقةً لكلِّ دعوى")
    if sum(unkeyed.values()):
        print(f"\nبطاقاتٌ بلا معرّفٍ يُميّزُها فلم تدخلِ الدعاوى: {sum(unkeyed.values())}"
              f"  ({', '.join(f'{k}={v}' for k, v in unkeyed.most_common(6))})")

    if args.claims:
        print("\nأشكالُ العناوينِ التي تحملُ أحكامًا (وكلُّها معدودةٌ هنا):")
        for h, n in headings.most_common(12):
            print(f"   {h:36} {n:6}")

    if args.json:
        payload = {
            "generated_from": "scripts/count_links.py",
            "cards_scanned": total_cards,
            "cards": {"root": root, "nucleus": nuc, "floor": floor},
            "claims": {"root": croot, "nucleus": cnuc},
            "by_language": {
                lang: {
                    "cards": {k: v for k, v in c.items()},
                    "claims": {lay: len(s) for lay, s in fams[lang].items()},
                }
                for lang, c in per.items()
            },
            "heading_forms": dict(headings),
        }
        pathlib.Path(args.json).write_text(
            json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"\nكُتبت الحصيلة: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
