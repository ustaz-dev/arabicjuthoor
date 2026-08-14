# -*- coding: utf-8 -*-
"""فهارسُ قواميسِ الفروعِ من ذخيرةِ kaikki، لتكونَ الرِّجلُ الثالثةُ من قاموسٍ لا من عمود (2026-08-14)

**لماذا الآن.** لمّا فُهرِسَ قاموسُ المصريّةِ AED وأُعيدَ به حصادُ دفعتَين، تغيّرَ
الحسابُ في الاتّجاهَينِ معًا:

    4 + 5   بطاقاتٍ تحوّلَت من مفتوحٍ إلى موجبٍ لمّا صارَ لها معنًى مفرَد
    11 + 1  بطاقةً موجبةً **نُسِخَت** لأنّ القاموسَ لا يُسنِدُ المعنى الذي قامَ
            عليه مدارُها السابق

فاثنتا عشرةَ صلةً كانت معدودةً وليس لمعناها سندٌ من قاموسِ فرعِها. وليس ذلك
تشدُّدًا جديدًا: الميثاقُ يشترطُ **معنى قاموسِ الفرع** منذُ أوّلِ يوم، وإنّما
كانت الأداةُ تقرأُ من عمودِ باحثٍ سابقٍ مكانَه.

**والخطرُ الحاضرُ أنّ مسارَينِ يحصدانِ الآنَ اللاتينيّةَ والويلزيّةَ والفارسيّةَ
واليونانيّةَ بلا قاموسِ فرعٍ البتّة**، وهي الألسنُ التي فيها 12,000 بطاقةٍ من
الطابورِ المهمَل. فإن مضَت بلا قاموسٍ أنتجَت الصنفَ نفسَه من الموجبِ الذي يُنسَخُ
غدًا. والذخيرةُ عندَنا لكلِّ لسانٍ نعملُ فيه، ولم تُقرَأْ.

**والرومنةُ تُحفَظُ عمدًا.** مداخلُ kaikki تحملُ صورةَ النطقِ بالحرفِ اللاتينيِّ
(`כְּתַב` ← `kəṯaḇ`)، والمؤلّفُ يحلُّ البطاقةَ بقراءتِها جهرًا، فالخطُّ العبريُّ
أو الآراميُّ وحدَه يُخفي عنه الكلمة. فتدخلُ الرومنةُ في الفهرسِ لتُطبَعَ في كلِّ
بطاقةٍ وفي كلِّ ورقةِ أذُن.

**وصورُ التصريفِ تُطرَح**: مدخلٌ معناهُ «inflection of ...» ليس معنًى بل إحالة،
ولو أُدخِلَ لأغرقَ الفهرسَ بضجيجٍ يُوهِمُ الغنى.

الاستعمال:
    python scripts/build_kaikki_index.py --lang latin welsh persian
    python scripts/build_kaikki_index.py --all
    python scripts/build_kaikki_index.py --look latin rex regis
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata
from collections import defaultdict

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as FAN  # noqa: E402

RES = ROOT / "Resources"
OUTDIR = ROOT / "data" / "branch-lexicons"

# اللسانُ عندَنا: مجلّدُ الذخيرةِ، وخطُّ المروحةِ الذي يُحسَبُ به الهيكل
LANGS: dict[str, tuple[str, str]] = {
    "latin": ("latin", "latin"),
    "welsh": ("welsh", "latin"),
    "persian": ("persian", "latin"),
    "ancient-greek": ("ancient_greek", "greek"),
    "aramaic": ("aramaic", "north"),
    "hebrew": ("hebrew", "north"),
    "gothic": ("gothic", "gothic"),
    "old-norse": ("old_norse", "germanic"),
    "old-irish": ("old_irish", "latin"),
    "old-english": ("english_old", "germanic"),
    "middle-english": ("english_middle", "germanic"),
    "akkadian": ("akkadian", "akkadian"),
}
SKIP_GLOSS = re.compile(r"^(inflection of|plural of|genitive of|alternative "
                        r"(form|spelling) of|obsolete (form|spelling) of|"
                        r"misspelling of|romanization of)\b", re.I)


def source_file(folder: str) -> pathlib.Path | None:
    d = RES / folder
    if not d.is_dir():
        return None
    hits = sorted(d.glob("kaikki.org-dictionary-*.jsonl"))
    return hits[0] if hits else None


def romanization(row: dict) -> str:
    for form in row.get("forms") or []:
        if "romanization" in (form.get("tags") or []):
            return str(form.get("form") or "").strip()
    return ""


def glosses_of(row: dict) -> list[str]:
    out: list[str] = []
    for sense in row.get("senses") or []:
        if "form-of" in (sense.get("tags") or []):
            continue
        for g in sense.get("glosses") or []:
            g = re.sub(r"\s+", " ", str(g)).strip()
            if g and not SKIP_GLOSS.match(g) and g not in out:
                out.append(g)
        if len(out) >= 3:
            break
    return out[:3]


def build(lang: str) -> dict:
    folder, script = LANGS[lang]
    src = source_file(folder)
    if not src:
        return {}
    entries: list[dict] = []
    with src.open(encoding="utf-8") as fh:
        for line in fh:
            if not line.strip():
                continue
            try:
                row = json.loads(line)
            except json.JSONDecodeError:
                continue
            gl = glosses_of(row)
            if not gl:
                continue
            word = str(row.get("word") or "").strip()
            if not word or len(word) > 40:
                continue
            entries.append({
                "word": word,
                "read": romanization(row),
                "pos": str(row.get("pos") or "")[:16],
                "en": "؛ ".join(gl),
                "etym": re.sub(r"\s+", " ", str(row.get("etymology_text") or ""))[:180],
            })

    by_word: dict[str, list[int]] = defaultdict(list)
    by_read: dict[str, list[int]] = defaultdict(list)
    by_skeleton: dict[str, list[int]] = defaultdict(list)
    for i, e in enumerate(entries):
        by_word[e["word"].lower()].append(i)
        if e["read"]:
            by_read[folded_read(e["read"])].append(i)
        for form in (e["word"], e["read"]):
            if not form:
                continue
            try:
                key = "".join(FAN.skeleton(form, script))
            except Exception:
                continue
            if 2 <= len(key) <= 5 and i not in by_skeleton[key]:
                by_skeleton[key].append(i)

    return {
        "language": lang,
        "source": f"kaikki.org via Resources/{folder}/{src.name}",
        "script": script,
        "note": ("صورُ التصريفِ والإحالاتِ مطروحة. والرومنةُ محفوظةٌ لتُطبَعَ "
                 "في البطاقةِ، فالمؤلّفُ يحلُّ البطاقةَ بقراءتِها جهرًا."),
        "entries": entries,
        "by_word": {k: v for k, v in sorted(by_word.items())},
        "by_read": {k: v for k, v in sorted(by_read.items())},
        "by_skeleton": {k: v for k, v in sorted(by_skeleton.items())},
    }


_CACHE: dict[str, dict] = {}
_READ_SKELETON_CACHE: dict[str, dict[str, list[int]]] = {}


def folded_read(value: str) -> str:
    """Comparison key for a stored romanization.

    Kaikki keeps accents in readings (``síkera``), while the harvested source
    often prints the same reading without them (``sikera``).  Folding only the
    romanization preserves the dictionary headword and merely makes that
    already-stored reading searchable.
    """
    return "".join(
        ch for ch in unicodedata.normalize("NFKD", value.strip().casefold())
        if not unicodedata.combining(ch)
    )


def lexicon(lang: str) -> dict:
    if lang not in _CACHE:
        path = OUTDIR / f"{lang}.json"
        _CACHE[lang] = json.loads(path.read_text(encoding="utf-8")) if path.exists() else {}
    return _CACHE[lang]


def read_skeleton_index(lang: str, lex: dict) -> dict[str, list[int]]:
    """Index stored Latin-script readings once per loaded lexicon."""
    if lang not in _READ_SKELETON_CACHE:
        by_skeleton: dict[str, list[int]] = defaultdict(list)
        for i, entry in enumerate(lex["entries"]):
            read = entry.get("read") or ""
            if not read:
                continue
            try:
                key = "".join(FAN.skeleton(read, "latin"))
            except Exception:
                continue
            if key:
                by_skeleton[key].append(i)
        _READ_SKELETON_CACHE[lang] = dict(by_skeleton)
    return _READ_SKELETON_CACHE[lang]


def look(lang: str, form: str, limit: int | None = None) -> tuple[list[dict], str]:
    """مداخلُ قاموسِ الفرعِ الموافقةُ للصورة، ومعها وسمُ الطريق.

    **الصورةُ بنصِّها أوّلًا**، فإن لم تُصَبْ فبالهيكل. ولا تُؤخَذُ الأولى وحدَها.
    """
    lex = lexicon(lang)
    if not lex:
        return [], "لا فهرسَ لهذا اللسان"

    def clipped(v: list[dict]) -> list[dict]:
        return v if limit is None else v[:limit]

    idx = lex["by_word"].get(form.strip().lower(), [])
    if idx:
        return clipped([lex["entries"][i] for i in idx]), "الصورةُ بنصِّها"

    # The romanization is part of the branch dictionary and must be searchable.
    # Prefer the built `by_read` table; fall back to a scan for payloads built
    # before that table existed, so an older file still answers instead of
    # silently requiring a rebuild. The scan is O(entries) per miss, and a miss
    # is the common case, so it must stay the fallback and never the path.
    read_key = folded_read(form)
    reads = lex.get("by_read")
    if reads is None:                     # ملفٌّ بُنِيَ قبلَ وجودِ الجدول
        read_hits = [e for e in lex["entries"]
                     if e.get("read") and folded_read(e["read"]) == read_key]
    else:
        read_hits = [lex["entries"][i] for i in reads.get(read_key, [])]
    if read_hits:
        return clipped(read_hits), "الصورةُ بنصِّها"
    try:
        key = "".join(FAN.skeleton(form, lex["script"]))
    except Exception:
        key = ""
    idx = lex["by_skeleton"].get(key, []) if key else []
    if idx:
        return clipped([lex["entries"][i] for i in idx]), "هيكلٌ مطابق"

    # Greek and northern-script lexicons store their readings in Latin script.
    # Search that reading with the Latin skeleton when the source gives a
    # romanized form; this is a search path, not a sound claim.
    try:
        latin_key = "".join(FAN.skeleton(form, "latin"))
    except Exception:
        latin_key = ""
    if latin_key:
        idx = read_skeleton_index(lang, lex).get(latin_key, [])
        if idx:
            return clipped([lex["entries"][i] for i in idx]), "هيكلٌ مطابق"
    return [], "لا مدخل"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", nargs="+", choices=sorted(LANGS))
    ap.add_argument("--all", action="store_true")
    ap.add_argument("--look", nargs="+", metavar="LANG FORM")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.look:
        lang, *forms = args.look
        for form in forms:
            hits, how = look(lang, form)
            print(f"\n{form}  ({lang})  {len(hits)} مدخلًا، {how}:")
            for e in hits[:8]:
                read = f" /{e['read']}/" if e["read"] else ""
                print(f"  {e['word']}{read}  [{e['pos']}]  {e['en'][:70]}")
                if e["etym"]:
                    print(f"      اشتقاقًا: {e['etym'][:80]}")
        return 0

    OUTDIR.mkdir(parents=True, exist_ok=True)
    todo = sorted(LANGS) if args.all else (args.lang or [])
    if not todo:
        return print("لا لسانَ مطلوب. استعملْ --lang أو --all") or 1
    for lang in todo:
        payload = build(lang)
        if not payload:
            print(f" !! {lang}: لا ذخيرةَ في Resources")
            continue
        (OUTDIR / f"{lang}.json").write_text(
            json.dumps(payload, ensure_ascii=False), encoding="utf-8")
        reads = sum(1 for e in payload["entries"] if e["read"])
        print(f"    {lang:16} {len(payload['entries']):>7,} مدخلًا، "
              f"{reads:>6,} برومنة، {len(payload['by_skeleton']):>6,} هيكلًا")
    print("CLEAN: فهارسُ قواميسِ الفروع")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
