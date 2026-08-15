# -*- coding: utf-8 -*-
"""بناءُ معرضِ الصلاتِ للموقع (2026-08-06)

يقرأُ بطاقاتِ القراءةِ ويستخرجُ منها الصلاتِ الصادرةَ بتفصيلِها: كلمةُ الفرعِ ونطقُها
ومعناها، والعربيُّ المقابلُ ونصُّه المعجميّ، والطبقةُ التي وقعَت فيها الصلة.

**والطبقةُ هي محورُ العرض:** الجذرُ الثلاثيُّ طورٌ متأخّرٌ يبقى حيثُ قرُبَ الفرع،
والنواةُ الثنائيّةُ طورٌ أقدمُ فهي وحدَها ما يبقى حينَ يبعُد. فتوزّعُ الطبقتَينِ على
الألسنِ هو الدعوى نفسُها معروضةً بالأرقام.

**والاستخراجُ يقرأُ العنوانَ أوّلًا لا الحقول**، لأنّ عنوانَ البطاقةِ عندَ المؤلّفِ
يجمعُ الكلمةَ ومعناها ونظيرَها في سطرٍ واحدٍ نظيف: `بطاقة: seofon «seven»`، بينَما
حقلُ «الكلمةُ في الفرع» يحملُ معه الرمزَ الصوتيَّ والقسمَ والمعرّفَ المركَّب.

المخرَج: data/links-showcase.json يقرؤُه links.html
"""
from __future__ import annotations

import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
from readable import say  # noqa: E402
import count_links as C  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "links-showcase.json"

ARABIC = re.compile(r"[ء-ي]")
LATIN = re.compile(r"[A-Za-zĀ-ſǍ-ǰḀ-ỿ]")

FIELD = lambda n: re.compile(r"^-\s*" + n + r"[^\n]*?[:：]\s*(.+)$", re.M)
RX_WORD = FIELD(r"(?:الكلمةُ? في الفرع|العضو)")
RX_SENSE = FIELD(r"المعنى من قاموس الفرع")
RX_ARABIC = FIELD(r"(?:المقابلُ? من اللسان|النظيرُ? العربيّ)")
RX_SCAN = FIELD(r"مسح (?:المعاني )?العربي[ةه]")

# `بطاقة: seofon «seven»`  و  `بطاقة: κιέλλη «ضياء» ↔ كلل، WEEK-DAY1`
RX_HEAD = re.compile(r"^[^:\n]{0,34}:\s*[`*]?(.+?)[`*]?\s*[«\"“]([^»\"”]{1,120})[»\"”]")
# بطاقةُ الأسرة: `بطاقة: `hebrew:family:38483…`، פשר، الرتبة 216`
RX_HEAD_FAM = re.compile(r"^[^:\n]{0,34}:\s*`[a-z-]+:family:[0-9a-f]+`\s*،\s*([^،\n]{1,26})")
# حقلُها: `أسرة `structural` مرساتها פשר، وفيها 2 عضو: פשר `pésher`، noun، «…»`
RX_ANCHOR = re.compile(r"مرساتها\s+([^\s،؛]{1,26})")
RX_QUOTE_AR = re.compile(r"[«“]\s*([^»”]{10,190})\s*[»”]")
RX_LEX = re.compile(
    r"(لسان العرب|تاج العروس|الصحاح|القاموس المحيط|مقاييس اللغة|كتاب العين|العين"
    r"|تهذيب اللغة|المخصص|أساس البلاغة|جمهرة اللغة|المحكم|العباب|النهاية|الجيم)")

# ما يتصدَّرُ حقلَ المقابلِ فيُلبِسُه ثوبَ جذرٍ وليسَ بجذر
LEAD = re.compile(
    r"^(?:ال)?(?:نواة|جذر|وجه|مادة|كلمة|أصل|بناء|صيغة|فعل|اسم|لفظ|مروحة|سلسلة"
    r"|قراءة|بطاقة|حقل|طبقة|درجة|مقابل|نظير|في|من|عند|هو|هي|و)\s+")
NOT_ROOT = {
    "نواة", "النواة", "جذر", "الجذر", "وجه", "الوجه", "مادة", "المادة", "كلمة",
    "الكلمة", "اللسان", "العربية", "العربيّة", "لا", "نعم", "مباشر", "صلة", "أثر",
    "صدى", "حكم", "الحكم", "درجة", "طبقة", "مطابق", "غير", "مورد", "ليس", "قريب",
    "بعيد", "شاهد", "معنى", "المعنى", "هذا", "هذه", "ذلك", "التي", "الذي", "كما",
}
RX_ROOTISH = re.compile(r"^[ء-ي]{2}(?:[\s\-ـ]?[ء-ي]){0,3}$")

# طيُّ الرومنةِ العلميّةِ إلى حروفٍ تُقرَأُ بالعين
FOLD = {
    "ḫ": "kh", "ẖ": "kh", "ḥ": "h", "š": "sh", "ṯ": "th", "ṭ": "t", "ṣ": "s",
    "ḏ": "dh", "ḍ": "d", "ẓ": "z", "ġ": "gh", "ǧ": "j", "č": "ch", "ṇ": "n",
    "ꜣ": "ʾ", "ꜥ": "ʿ", "ð": "dh", "þ": "th", "ø": "o", "æ": "ae", "œ": "oe",
    "ē": "e", "ī": "i", "ō": "o", "ū": "u", "ā": "a", "ǖ": "u", "ê": "e",
    "â": "a", "î": "i", "û": "u", "ô": "o", "ü": "u", "ö": "o", "ä": "a",
}

NAMES = {
    "aramaic": ("الآراميّة", "Aramaic"), "hebrew": ("العبريّة", "Hebrew"),
    "coptic": ("القبطيّة", "Coptic"), "egyptian": ("المصريّة القديمة", "Ancient Egyptian"),
    "akkadian": ("الأكّاديّة", "Akkadian"), "ancient-greek": ("اليونانيّة القديمة", "Ancient Greek"),
    "old-latin": ("اللاتينيّة القديمة", "Old Latin"), "gothic": ("القوطيّة", "Gothic"),
    "old-norse": ("النُّرديّة القديمة", "Old Norse"), "old-english": ("الإنجليزيّة القديمة", "Old English"),
    "middle-english": ("الإنجليزيّة الوسطى", "Middle English"),
    "old-irish": ("الإيرلنديّة القديمة", "Old Irish"), "welsh": ("الويلزيّة", "Welsh"),
    "persian": ("الفارسيّة", "Persian"),
    "phoenician-punic-scout": ("الفينيقيّة", "Phoenician"), "punic": ("البونيّة", "Punic"),
}
# قربُ الفرعِ من العربيّة، لترتيبِ عرضِ التدرُّج
DISTANCE = {
    "aramaic": 1, "hebrew": 1, "akkadian": 1, "phoenician-punic-scout": 1, "punic": 1,
    "egyptian": 2, "coptic": 2,
    "ancient-greek": 3, "old-latin": 3, "persian": 3,
    "gothic": 4, "old-norse": 4, "old-english": 4, "middle-english": 4,
    "old-irish": 4, "welsh": 4,
}
WANT = 8


def clean(s: str) -> str:
    s = re.sub(r"\[[^\]]*\]", "", str(s))
    s = re.sub(r"\s+", " ", s)
    return unicodedata.normalize("NFC", s).strip(" .;،؛`*«»\"'")


def fold(s: str) -> str:
    return "".join(FOLD.get(c, FOLD.get(c.lower(), c)) for c in s)


def split_word(raw: str) -> tuple[str, str]:
    """يفصلُ صورةَ الخطِّ عن نطقِها. `ⲗⲁⲥ las` -> (ⲗⲁⲥ, las)"""
    raw = clean(raw).split("،")[0].split("؛")[0].split("/")[0].strip(" `*")
    raw = re.sub(r"^\S*(?:ال)?(?:أكادي|آرامي|عبري|قبطي|يوناني|مصري)\S*\s+", "", raw)
    raw = re.sub(r"\s*\((?:[^)]*)\)\s*$", "", raw).strip(" `*")
    toks = [t.strip(" `*,") for t in raw.split() if t.strip(" `*,")]
    if not toks:
        return "", ""
    native = [t for t in toks if not LATIN.search(t) and not ARABIC.search(t)]
    latin = [t for t in toks if LATIN.search(t)]
    if native and latin:
        return native[0], fold(latin[0])
    word = toks[0]
    if LATIN.search(word):                      # كلمةٌ مرقونةٌ أصلًا
        return word, (fold(word) if fold(word) != word else "")
    spoken = say(word)                          # خطٌّ غيرُ لاتينيّ: يُنطَقُ له
    spoken = fold(spoken.split("(")[0].strip()) if spoken != word else ""
    return word, spoken


def ok_root(root: str) -> bool:
    letters = re.sub(r"[^ء-ي]", "", root)
    if not (2 <= len(letters) <= 8) or root in NOT_ROOT or letters in NOT_ROOT:
        return False
    return not (letters.startswith("ال") and len(letters) < 4)


def arabic_root(field: str, block: str) -> str:
    """النظيرُ العربيُّ كما كتبَه صاحبُ البطاقة. المحصورُ بين علامتَينِ أوثقُ،
    مثل `باء الجر `بـ` في وجه الإلصاق` فالمقصودُ فيها ما بينَ العلامتَين."""
    txt = clean(field)
    for m in re.finditer(r"[`«\"]\s*([ء-يـ]{1,7}(?:[\s\-ـ][ء-ي]){0,3})\s*[`»\"]", txt):
        root = re.sub(r"\s+", " ", m.group(1)).strip(" ـ") or m.group(1).strip()
        if ok_root(root):
            return root
    for _ in range(4):
        new = LEAD.sub("", txt)
        if new == txt:
            break
        txt = new
    cand = txt.split("«")[0].split("[")[0].strip(" .،؛:")
    # إمّا كلمةٌ واحدة، وإمّا نواةٌ مكتوبةٌ حروفًا مفرَّقةً مثل `س-ب`. ولا يُخلَطُ
    # البابانِ وإلّا التقطَ حرفَ جرٍّ تالٍ فصارَ `كلل ف`.
    m = (re.match(r"^([ء-ي](?:[\-ـ\s][ء-ي]){1,3})(?![ء-ي])", cand)
         or re.match(r"^([ء-ي]{2,8})(?![ء-ي])", cand))
    if m:
        root = re.sub(r"\s+", " ", m.group(1)).strip()
        if ok_root(root):
            return root
    return ""


def lexicon_quote(block: str) -> tuple[str, str]:
    """نصٌّ عربيٌّ منقولٌ من معجم، ولا يُنسَبُ إلى معجمٍ إلّا إن كان اسمُه ملاصقًا
    للنصِّ فعلًا. فالنسبةُ إلى أوّلِ اسمٍ في البطاقةِ تنسبُ إلى غيرِ قائل."""
    sc = RX_SCAN.search(block)
    zones = ([block[sc.start():sc.start() + 1800]] if sc else []) + [block]
    for zone in zones:
        for q in RX_QUOTE_AR.finditer(zone):
            text = clean(q.group(1))
            if len(ARABIC.findall(text)) < 6 or LATIN.search(text):
                continue
            before = zone[max(0, q.start() - 170):q.start()]
            lex = list(RX_LEX.finditer(before)) or list(
                RX_LEX.finditer(zone[q.end():q.end() + 90]))
            return text[:170], (lex[-1].group(1) if lex else "")
    return "", ""


SOURCEY = re.compile(r"السطر|اللقطة|المعرّ?ف|المصدر|kaikki|Kaikki|TLA|CAD|CD ", re.I)


def branch_sense(head_gloss: str, field: str) -> str:
    """معنى الكلمةِ كما في قاموسِ فرعِها. عنوانُ البطاقةِ أنظفُ من الحقلِ لأنّ
    الحقلَ يحملُ معه اسمَ اللقطةِ ورقمَ السطرِ ومعرّفَ العضو."""
    for raw in (head_gloss, field):
        if not raw:
            continue
        # يُبحَثُ عن المحصورِ بين علامتَينِ **قبل** التنظيف، لأنّ التنظيفَ يقشِطُ
        # علامةَ الإغلاقِ من الطرفِ فيُخفيها عن البحث
        s = re.sub(r"\s+", " ", re.sub(r"\[[^\]]*\]", "", str(raw))).strip()
        s = re.sub(r"^[^:：]{0,26}[:：]\s*", "", s) if SOURCEY.match(s) else s
        # حقلُ الأسرةِ يسبقُ معناها بمرساتِها وقسمِها: `פשר `pésher`، noun، «…»`
        inner = re.search(r"[«“]([^»”]{2,120})[»”]", s)
        s = clean(inner.group(1) if inner else s)
        s = s.split("»")[0].split("”")[0].split("[")[0]
        s = s.strip(" `*«»\"'.،؛:")
        if s and not SOURCEY.search(s) and len(s) > 1:
            return s[:78]
    return ""


def iter_cards(path: pathlib.Path):
    """مرّر بطاقةً مطبّعةً واحدةً، ولا تحمل ملف القراءة الكبير كله في الذاكرة."""
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


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    langs: dict[str, dict] = {}

    for path in sorted(READINGS.glob("*.md")):
        lang = path.stem
        if lang not in NAMES:
            continue
        entry = langs.setdefault(lang, {
            "key": lang, "ar": NAMES[lang][0], "en": NAMES[lang][1],
            "distance": DISTANCE.get(lang, 3),
            "root": 0, "nucleus": 0, "floor": 0, "pool": [], "examples": [],
        })
        for block in iter_cards(path):
            degrees = C.scan_card(block)
            if not degrees:
                continue
            # يُعَدُّ كما يعدُّ `count_links.py` بالضبط: كلُّ درجةٍ صادرةٍ تُحسَبُ
            # في طبقتِها، فالبطاقةُ الواحدةُ قد تحملُ درجتَينِ وهي صلتان. وإلّا
            # اختلفَ رقمُ الصفحةِ عن الرقمِ القانونيِّ وصارَ في المشروعِ عدّادان.
            for d in degrees:
                entry[C.layer(d)] += 1
            layer = "nucleus" if any("NUCLEUS" in d for d in degrees) else "root"

            head = block.split("\n", 1)[0]
            mh = RX_HEAD.match(head)
            mw, ms = RX_WORD.search(block), RX_SENSE.search(block)
            field = mw.group(1) if mw else ""
            # ثلاثةُ أشكالٍ للعنوانِ في الملفّات، وأنظفُها أوّلًا
            anchor = RX_ANCHOR.search(field) or RX_HEAD_FAM.match(head)
            raw_word = (anchor.group(1) if anchor
                        else mh.group(1) if mh else field)
            word, spoken = split_word(raw_word)
            if not word or len(word) > 26:
                continue
            if not spoken and not LATIN.search(word):
                # نطقُ الأسرةِ مكتوبٌ بعدَ مرساتِها بين علامتَين
                mt = re.search(re.escape(word) + r"\s*`([^`]{1,18})`", block)
                if mt and LATIN.search(mt.group(1)):
                    spoken = fold(mt.group(1))
            sense = branch_sense(mh.group(2) if mh else "", ms.group(1) if ms else "")
            if not sense:
                continue
            ma = RX_ARABIC.search(block)
            root = arabic_root(ma.group(1) if ma else "", block)
            if not root:
                continue
            quote, lex = lexicon_quote(block)
            entry["pool"].append({
                "word": word, "say": spoken, "sense": sense, "arabic": root,
                "quote": quote, "lexicon": lex, "layer": layer,
                "degree": sorted(degrees)[0],
                "rank": (2 if quote and lex else 1 if quote else 0),
            })

    rows = [e for e in langs.values() if e["root"] + e["nucleus"] > 0]
    for e in rows:
        tot = e["root"] + e["nucleus"]
        e["total"] = tot
        e["nucleus_share"] = round(100 * e["nucleus"] / tot, 1) if tot else 0.0
        seen, picked = set(), []
        # الأثمنُ أوّلًا: ما حملَ نصًّا معجميًّا مسمًّى. ثمّ تُوازَنُ الطبقتان.
        for want_layer in ("nucleus", "root", None):
            for x in sorted(e["pool"], key=lambda x: -x["rank"]):
                if len(picked) >= WANT:
                    break
                if want_layer and x["layer"] != want_layer:
                    continue
                key = (x["word"], x["arabic"])
                if key in seen:
                    continue
                if want_layer and sum(1 for p in picked if p["layer"] == want_layer) >= WANT // 2:
                    continue
                seen.add(key)
                picked.append(x)
        for x in picked:
            x.pop("rank", None)
        e["examples"] = picked
        e.pop("pool", None)
    rows.sort(key=lambda e: (e["distance"], -e["total"]))

    payload = {
        "generated_by": "scripts/build_links_showcase.py",
        "note": "طبقةُ استكشاف. الأرقامُ من scripts/count_links.py وهو التعريفُ الوحيدُ للصلة.",
        "totals": {
            "root": sum(e["root"] for e in rows),
            "nucleus": sum(e["nucleus"] for e in rows),
            "languages": len(rows),
        },
        "languages": rows,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"ألسنٌ فيها صلات: {len(rows)}")
    print(f"{'اللسان':22}{'جذر':>6}{'نواة':>6}{'حصّةُ النواة':>13}{'أمثلة':>7}{'بنصّ معجم':>11}")
    for e in rows:
        q = sum(1 for x in e["examples"] if x["quote"])
        print(f"{e['ar']:22}{e['root']:>6}{e['nucleus']:>6}"
              f"{e['nucleus_share']:>12.0f}%{len(e['examples']):>7}{q:>11}")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
