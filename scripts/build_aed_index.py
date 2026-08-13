# -*- coding: utf-8 -*-
"""فهرسُ قاموسِ المصريّةِ القديمةِ AED، ليُصبِحَ للرِّجلِ الثالثةِ قاموسُ فرعٍ حقيقيّ (2026-08-14)

**العطبُ الذي يُنهيه.** الميثاقُ يشترطُ في الرِّجلِ الثالثةِ **معنى قاموسِ الفرعِ**
بلا رتوش، وكانت المساراتُ تأخذُ المعنى من **عمودِ خشيمٍ المقارِن**، وهو ليس
قاموسًا بل حزمةُ احتمالاتٍ يجمعُها المؤلّفُ ليُقارِن:

    mire   ←  «صحراء؛ ماء؛ ساحل»
    f-d    ←  «قطر أو بلاد؛ أربعة أو مدينة»
    bine   ←  «نخلة؛ بلح؛ أصابع؛ موز»

ولا يُكتَبُ مدارٌ أمينٌ إلى حدثِ حرفٍ من معنًى هو ثلاثةُ معانٍ غيرِ متّصلة. ولذلك
خرجَت دفعةُ 150 صفًّا بـ**147 مفتوحةً سببُها الوحيدُ «لا مدارَ يدويٌّ مقنع»**،
وليست العلّةُ في تشدُّدِ الكاتبِ بل في أنّ المادّةَ لا تحتملُ مدارًا.

**والقاموسُ عندَنا منذُ 2026-07-17 ولم تقرأْه أداةٌ واحدة**: `Resources/egyptian/`
فيه AED (Simon D. Schweitzer) بـ35,174 مدخلًا، لكلِّ مدخلٍ ترجمةٌ إنجليزيّةٌ
وألمانيّةٌ وقسمٌ نحويٌّ وإحالةٌ إلى Wb، ومعها شواهدُ منصوصةٌ من النصوص.

**والمفتاحُ هيكلٌ لا رسم.** كتبُ خشيمٍ تنقلُ عن بدج (`tch` و`kh` و`ā`)، وAED
يكتبُ بالرسمِ العلميِّ (`ḏ` و`ḫ` و`ꜥ`)، فلا يلتقيانِ حرفًا بحرف. فيُفهرَسُ كلُّ
مدخلٍ **بهيكلِه الصامتيِّ كما تحسبُه `fan_any_script.skeleton`**، وبه يلتقي
الرسمانِ على أرضٍ واحدةٍ من غيرِ أن نخترعَ مقابلةً.

الاستعمال:
    python scripts/build_aed_index.py                 يبني data/aed-egyptian-lexicon.json
    python scripts/build_aed_index.py --look bnt mwt  يستعلمُ عن صورةٍ أو أكثر
"""
from __future__ import annotations

import argparse
import html
import json
import pathlib
import re
import sys
import zipfile
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as FAN  # noqa: E402

AED_ZIP = ROOT / "Resources" / "egyptian" / "aed-v1.0.zip"
OUT = ROOT / "data" / "aed-egyptian-lexicon.json"

TITLE = re.compile(r'<h1 class="main_title">(.*?)</h1>', re.S)
FIELD = re.compile(
    r'<div class="tooltip">(?:&#x2022;)?\s*(.*?)\s*'
    r'<span class="tooltiptext">(.*?)</span>', re.S)
KEEP = ("english translation", "german translation", "part of speech",
        "lemma id", "bibliographical information")
SHORT = {"english translation": "en", "german translation": "de",
         "part of speech": "pos", "lemma id": "id",
         "bibliographical information": "ref"}


def clean(raw: str) -> str:
    return re.sub(r"\s+", " ", html.unescape(re.sub(r"<[^>]+>", "", raw))).strip()


def skeleton_key(translit: str) -> str:
    """هيكلُ الصورةِ الصامتيُّ بالأداةِ نفسِها التي تُولِّدُ المروحة."""
    w = re.sub(r"[.,()\[\]{}=|/\\~*?!:;\"'0-9\s-]", "", translit)
    return "".join(FAN.skeleton(w, "egyptian"))


# **الطيُّ مفتاحُ بحثٍ لا دعوى صوت.** رسمُ بدج الذي تنقلُ عنه كتبُ خشيمٍ يكتبُ
# `ntr` حيثُ يكتبُ الرسمُ العلميُّ `nṯr`، فلا يلتقيانِ في الهيكلِ الدقيقِ ويضيعُ
# أشهرُ كلماتِ اللسان. فيُفهرَسُ المدخلُ بمفتاحَين: هيكلِه كما هو، وهيكلٍ مطويٍّ
# تسقطُ فيه فروقُ النقطِ والحواشي. **والبحثُ بالدقيقِ أوّلًا**، ولا يُنزَلُ إلى
# المطويِّ إلّا عندَ خلوِّ الأوّل، ويُكتَبُ في البطاقةِ أيُّهما أصابَ مع رسمِ
# المدخلِ كما هو في القاموس، فيرى القارئُ `nṯr` بإزاءِ `ntr` ويحكمُ بنفسِه.
#
# **والطيُّ يجري على الوحداتِ لا على الحروف**، لأنّ بدج يكتبُ المزدوجَ حرفَين
# (`kh` و`tch` و`sh`) والرسمَ العلميَّ حرفًا واحدًا (`ḫ` و`ḏ` و`š`)، ولو طُوِيَ
# حرفًا بحرفٍ لبقيَ `ankh` لا يلقى `ꜥnḫ` أبدًا.
FOLD_UNIT = {
    "ṯ": "t", "ṱ": "t", "ṭ": "t", "th": "t", "t": "t",
    "ḏ": "d", "ḍ": "d", "tch": "d", "d": "d",
    "ḫ": "h", "ẖ": "h", "ḥ": "h", "kh": "h", "h": "h",
    "š": "s", "ś": "s", "ṣ": "s", "sh": "s", "s": "s", "z": "s",
    "ꜣ": "ʾ", "ꜥ": "ʾ", "ʿ": "ʾ", "ʔ": "ʾ", "ā": "ʾ",
    "ḳ": "q", "q": "q", "j": "i", "i": "i", "y": "i",
    "p": "p", "f": "f", "b": "b", "m": "m", "n": "n",
    "r": "r", "l": "r", "k": "k", "g": "g", "w": "w",
}


def folded_key(translit: str) -> str:
    """مفتاحٌ خشنٌ تلتقي عليه رسومُ المدارسِ المختلفة. **مفتاحُ بحثٍ لا دعوى صوت.**"""
    w = re.sub(r"[.,()\[\]{}=|/\\~*?!:;\"'0-9\s-]", "", translit)
    units = FAN.skeleton(w, "egyptian")
    folded = "".join(FOLD_UNIT.get(u, u) for u in units)
    return folded.lstrip("ʾ") or folded      # بدج يُسقِطُ الهمزَ الصدريَّ كثيرًا


def parse(text: str) -> dict | None:
    m = TITLE.search(text)
    if not m:
        return None
    translit = clean(m.group(1))
    if not translit:
        return None
    entry: dict = {"translit": translit}
    for value, label in FIELD.findall(text):
        label = clean(label)
        if label in KEEP and SHORT[label] not in entry:
            entry[SHORT[label]] = clean(value)
    return entry if entry.get("en") or entry.get("de") else None


def build() -> dict:
    if not AED_ZIP.exists():
        sys.exit(f"لا قاموسَ في {AED_ZIP}")
    entries: list[dict] = []
    with zipfile.ZipFile(AED_ZIP) as z:
        for name in z.namelist():
            if not name.endswith(".html") or name.endswith("index.html"):
                continue
            entry = parse(z.read(name).decode("utf-8", "replace"))
            if entry:
                entries.append(entry)

    by_skeleton: dict[str, list[int]] = defaultdict(list)
    by_folded: dict[str, list[int]] = defaultdict(list)
    for i, entry in enumerate(entries):
        key = skeleton_key(entry["translit"])
        if 1 <= len(key) <= 6:
            by_skeleton[key].append(i)
            by_folded[folded_key(entry["translit"])].append(i)

    return {
        "source": "AED, Simon D. Schweitzer (Resources/egyptian/aed-v1.0.zip)",
        "note": ("المفتاحُ هيكلٌ صامتيٌّ محسوبٌ بـ`fan_any_script.skeleton` "
                 "ليلتقيَ رسمُ بدج بالرسمِ العلميِّ من غيرِ مقابلةٍ مخترَعة. "
                 "والمطويُّ مفتاحُ بحثٍ احتياطيٌّ لا دعوى صوت."),
        "entries": entries,
        "by_skeleton": {k: v for k, v in sorted(by_skeleton.items())},
        "by_folded": {k: v for k, v in sorted(by_folded.items())},
    }


_CACHE: dict | None = None


def lexicon() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(OUT.read_text(encoding="utf-8"))
    return _CACHE


def look(form: str, limit: int = 6) -> tuple[list[dict], str]:
    """مداخلُ القاموسِ الموافقةُ للصورة، ومعها وسمُ الطريقِ الذي أصابَ بها.

    **الدقيقُ أوّلًا والمطويُّ احتياطًا**، ويُكتَبُ الوسمُ في البطاقةِ دائمًا.

    **ولا تُؤخَذُ المدخلةُ الأولى وحدَها أبدًا.** الهيكلُ يُسقِطُ صوائتَ الصورةِ،
    فتتصادمُ الأعلامُ بأسماءِ الأجناس: `Amentet` تلقى `mnt.t` «الديوريت»
    و`Ast` تلقى `s.t` «أداةَ تجريد»، وكلاهما غلط. فالقائمةُ **تُعرَضُ كلُّها**
    في البطاقةِ ويختارُ كاتبُ المدارِ ما يوافقُ سياقَ الصفِّ في كتابِه.
    وتُقدَّمُ مداخلُ `entity_name` حينَ تكونُ الصورةُ عَلَمًا (صدرُها كبير)،
    فذلك وسمُ القاموسِ نفسِه للأعلامِ لا حدسٌ منّا.
    """
    lex = lexicon()
    proper = form[:1].isupper()

    def order(hits: list[dict]) -> list[dict]:
        return sorted(hits, key=lambda e: (
            not ("entity_name" in (e.get("pos") or "")) if proper
            else ("entity_name" in (e.get("pos") or ""))))

    idx = lex["by_skeleton"].get(skeleton_key(form), [])
    if idx:
        return order([lex["entries"][i] for i in idx])[:limit], "هيكلٌ مطابق"
    idx = lex.get("by_folded", {}).get(folded_key(form), [])
    if idx:
        return (order([lex["entries"][i] for i in idx])[:limit],
                "هيكلٌ مطويٌّ (فرقُ نقطٍ في الرسم)")
    return [], "لا مدخل"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", nargs="+", metavar="FORM")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.look:
        for form in args.look:
            hits, how = look(form)
            print(f"\n{form}  (هيكل {skeleton_key(form)})  {len(hits)} مدخلًا، {how}:")
            for e in hits:
                print(f"  {e['translit']:18} {e.get('pos','')[:12]:14} "
                      f"{(e.get('en') or e.get('de') or '')[:74]}")
        return 0

    payload = build()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    n, k = len(payload["entries"]), len(payload["by_skeleton"])
    with_en = sum(1 for e in payload["entries"] if e.get("en"))
    print(f"CLEAN: فهرسُ AED {n:,} مدخلًا، منها {with_en:,} بترجمةٍ إنجليزيّة، "
          f"و{k:,} هيكلًا متمايزًا [{OUT.name}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
