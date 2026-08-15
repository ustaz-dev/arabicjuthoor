# -*- coding: utf-8 -*-
"""فهرسُ القاموسِ القبطيِّ الجامع، ليكونَ للقبطيّةِ قاموسُ فرعٍ كما صارَ للمصريّة (2026-08-14)

**العلّةُ نفسُها التي عولِجَت في المصريّة**: الميثاقُ يشترطُ في الرِّجلِ الثالثةِ
معنى **قاموسِ الفرع**، وكانت القبطيّةُ تأخذُ معناها من أعمدةِ خشيمٍ ومقّارٍ
المقارِنة. والقاموسُ في المستودعِ منذُ 2026-06-02 ولم تقرأْه أداةٌ واحدة.

`Resources/coptic/Comprehensive_Coptic_Lexicon.xml`: 11,284 مدخلًا من أكاديميّةِ
برلين وبراندنبورغ، لكلِّ مدخلٍ صورتُه بالخطِّ القبطيِّ ولهجتُها (صعيديّةٌ وبحيريّةٌ
وأخميميّةٌ وغيرُها)، وقسمُه النحويُّ، وترجمتُه بالإنجليزيّةِ والألمانيّةِ
والفرنسيّة، وإحالتُه إلى كرم (CD) وغيرِه.

**والجسرُ رسمٌ لا حدس.** بطاقاتُنا القبطيّةُ منقولةٌ بحرفٍ لاتينيٍّ والقاموسُ
بالخطِّ القبطيّ، فيُنقَلُ الخطُّ القبطيُّ إلى اللاتينيِّ بجدولٍ **مطّردٍ معروفٍ
عند أهلِ الشأن** (ⲑ ← th، ϣ ← š، ϫ ← j …)، ثمّ يُحسَبُ الهيكلُ بالأداةِ نفسِها
التي تُفهرِسُ AED، فيلتقي الرسمانِ من غيرِ مقابلةٍ مخترَعة.

**وفائدةٌ ثانيةٌ مقصودةٌ**: عنوانُ القاموسِ نفسُه «شاملًا الدخيلَ من اليونانيّةِ
القديمة»، فهو يُسمّي الدخيلَ اليونانيَّ بالاسم. وذلك يخدمُ طابورَ القرضِ المعادَ
فتحُه: من كان دخيلًا يونانيًّا في القبطيّةِ **لا يُغلَقُ به بابُنا** لأنّ سؤالَنا
عن أصلِ المادّةِ لا عن آخرِ ناقل، لكنّه يُكتَبُ في البطاقةِ صراحةً.

الاستعمال:
    python scripts/build_coptic_index.py                يبني data/coptic-lexicon.json
    python scripts/build_coptic_index.py --look nout    يستعلمُ عن صورة
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import xml.etree.ElementTree as ET
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import build_aed_index as AED  # noqa: E402

SRC = ROOT / "Resources" / "coptic" / "Comprehensive_Coptic_Lexicon.xml"
OUT = ROOT / "data" / "coptic-lexicon.json"
TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"

# نقلُ الخطِّ القبطيِّ إلى اللاتينيِّ بالجدولِ المطّردِ المعروف
COPTIC_TO_LATIN = {
    "ⲁ": "a", "ⲃ": "b", "ⲅ": "g", "ⲇ": "d", "ⲉ": "e", "ⲍ": "z", "ⲏ": "e",
    "ⲑ": "th", "ⲓ": "i", "ⲕ": "k", "ⲗ": "l", "ⲙ": "m", "ⲛ": "n", "ⲝ": "ks",
    "ⲟ": "o", "ⲡ": "p", "ⲣ": "r", "ⲥ": "s", "ⲧ": "t", "ⲩ": "u", "ⲫ": "ph",
    "ⲭ": "kh", "ⲯ": "ps", "ⲱ": "o", "ϣ": "sh", "ϥ": "f", "ϧ": "kh",
    "ϩ": "h", "ϫ": "j", "ϭ": "c", "ϯ": "ti", "ⳉ": "kh",
}
DIALECT = {"S": "صعيديّة", "B": "بحيريّة", "A": "أخميميّة", "L": "ليكوبوليّة",
           "F": "فيّوميّة", "M": "أوسط مصر", "P": "بروتوصعيديّة", "V": "فيّوميّة"}


def latinize(coptic: str) -> str:
    return "".join(COPTIC_TO_LATIN.get(ch, "") for ch in coptic)


def text_of(el) -> str:
    return re.sub(r"\s+", " ", "".join(el.itertext())).strip()


def build() -> dict:
    if not SRC.exists():
        sys.exit(f"لا قاموسَ في {SRC}")
    tree = ET.parse(SRC)
    entries: list[dict] = []
    for entry in tree.iter(f"{TEI}entry"):
        forms, dialects = [], []
        for form in entry.iter(f"{TEI}form"):
            for orth in form.iter(f"{TEI}orth"):
                t = text_of(orth).strip("-= ")
                if t and t not in forms:
                    forms.append(t)
            for usg in form.iter(f"{TEI}usg"):
                d = text_of(usg)
                if d and d not in dialects:
                    dialects.append(d)
        if not forms:
            continue
        senses, pos = [], []
        for q in entry.iter(f"{TEI}quote"):
            if q.get("{http://www.w3.org/XML/1998/namespace}lang") == "en":
                t = text_of(q)
                if t and t not in senses:
                    senses.append(t)
        for p in entry.iter(f"{TEI}pos"):
            t = text_of(p)
            if t and t not in pos:
                pos.append(t)
        bibl = next((text_of(b) for b in entry.iter(f"{TEI}bibl") if text_of(b)), "")
        etymology = "؛ ".join(
            dict.fromkeys(
                text_of(etym)
                for etym in entry.findall(f"{TEI}etym")
                if text_of(etym)
            )
        )
        if not senses:
            continue
        entries.append({
            "id": entry.get(XML_ID, ""),
            "entry_type": entry.get("type", ""),
            "forms": forms[:6],
            "coptic": forms[0],
            "latin": latinize(forms[0]),
            "en": "؛ ".join(senses[:4]),
            "pos": "، ".join(pos[:2]),
            "dialects": [DIALECT.get(d, d) for d in dialects[:4]],
            "ref": bibl[:70],
            "etymology": etymology,
        })

    by_exact: dict[str, list[int]] = defaultdict(list)
    by_skeleton: dict[str, list[int]] = defaultdict(list)
    by_folded: dict[str, list[int]] = defaultdict(list)
    for i, e in enumerate(entries):
        for form in e["forms"]:
            lat = latinize(form)
            if not lat:
                continue
            exact = lat.casefold()
            if i not in by_exact[exact]:
                by_exact[exact].append(i)
            k = AED.skeleton_key(lat)
            if 1 <= len(k) <= 6 and i not in by_skeleton[k]:
                by_skeleton[k].append(i)
            f = AED.folded_key(lat)
            if 1 <= len(f) <= 6 and i not in by_folded[f]:
                by_folded[f].append(i)

    return {
        "source": ("Comprehensive Coptic Lexicon v1.2, Berlin-Brandenburgische "
                   "Akademie der Wissenschaften (Resources/coptic/)"),
        "note": ("الخطُّ القبطيُّ منقولٌ إلى اللاتينيِّ بجدولٍ مطّرد، ثمّ الهيكلُ "
                 "بأداةِ المروحةِ نفسِها. والمطويُّ مفتاحُ بحثٍ لا دعوى صوت."),
        "entries": entries,
        "by_exact": {k: v for k, v in sorted(by_exact.items())},
        "by_skeleton": {k: v for k, v in sorted(by_skeleton.items())},
        "by_folded": {k: v for k, v in sorted(by_folded.items())},
    }


_CACHE: dict | None = None


def lexicon() -> dict:
    global _CACHE
    if _CACHE is None:
        _CACHE = json.loads(OUT.read_text(encoding="utf-8"))
    return _CACHE


def look(form: str, limit: int | None = None) -> tuple[list[dict], str]:
    """مداخلُ القاموسِ القبطيِّ الموافقةُ للصورة، ومعها وسمُ الطريق.

    **ولا تُؤخَذُ الأولى وحدَها**، للعلّةِ نفسِها المكتوبةِ في `build_aed_index`.
    ولذلك الأصلُ أن تُرَدَّ المداخلُ **كلُّها** ويقصُرَها الطالبُ إن شاء.
    """
    lex = lexicon()

    def clipped(values: list[dict]) -> list[dict]:
        return values if limit is None else values[:limit]

    query = latinize(form) or form
    if not AED.skeleton_key(query):
        idx = lex.get("by_exact", {}).get(query.casefold(), [])
        if idx:
            return clipped([lex["entries"][i] for i in idx]), "رسمٌ مطابق بلا هيكل صامتي"
    idx = lex["by_skeleton"].get(AED.skeleton_key(query), [])
    if idx:
        return clipped([lex["entries"][i] for i in idx]), "هيكلٌ مطابق"
    idx = lex["by_folded"].get(AED.folded_key(query), [])
    if idx:
        return clipped([lex["entries"][i] for i in idx]), "هيكلٌ مطويٌّ (فرقُ رسم)"
    idx = lex.get("by_exact", {}).get(query.casefold(), [])
    if idx:
        return clipped([lex["entries"][i] for i in idx]), "رسمٌ مطابق بعد تعذر الهيكل"
    return [], "لا مدخل"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--look", nargs="+", metavar="FORM")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.look:
        for form in args.look:
            hits, how = look(form)
            query = latinize(form) or form
            print(f"\n{form}  (هيكل {AED.skeleton_key(query)})  {len(hits)} مدخلًا، {how}:")
            for e in hits[:12]:
                print(f"  {e['coptic']:14} {e['latin']:12} {e['pos'][:14]:16} {e['en'][:60]}")
        return 0

    payload = build()
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"CLEAN: القاموسُ القبطيُّ {len(payload['entries']):,} مدخلًا بترجمةٍ "
          f"إنجليزيّة، و{len(payload['by_skeleton']):,} هيكلًا متمايزًا [{OUT.name}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
