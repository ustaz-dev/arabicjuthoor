# -*- coding: utf-8 -*-
"""المسحُ الصوتيُّ الشامل: قابِلْ أوّلًا ثمّ انظُرْ في المعنى (2026-08-06)

**العطبُ الذي يُصلِحُه، بنصِّ المؤلّف:** «ابدأْ بمقابلةِ الكلماتِ التي قد تكونُ نفسَها
صوتيًّا، ثمّ انظُرْ هل في معانيها صلة».

وطريقةُ المشروعِ كلُّها كانت عكسَ ذلك: كلمةٌ من طابورٍ نحنُ رتّبناه، ثمّ توليدُ
مرشّحينَ لها، ثمّ فحص. **ولم يُجرَ يومًا مسحٌ شاملٌ يسألُ: أيُّ كلماتِ الفرعِ لها جذرٌ
عربيٌّ بالهيكلِ نفسِه؟** فبقيَ البديهيُّ مختبئًا خلفَ ترتيبِ الطابور.

**الطريقة:** لكلِّ كلمةٍ في ذخيرةِ الفرع، يُجرَّدُ هيكلُها الصامتيُّ، وتُفتَحُ مروحتُها
العربيّةُ كاملةً (فالعربيّةُ حفِظَت ما دمجَه الفرع)، ويُبحَثُ عن كلِّ مرشّحٍ **موجودٍ
فعلًا في معاجمِ العربيّة**. ثمّ يُقاسُ تداخلُ المعنى بينَ الطرفَين.

**ويُخرِجُ ثلاثَ طبقات:**
  1. **مطابقةُ صوتٍ ومعنًى معًا:** الهيكلُ يوافقُ والمعنى يتقاطع. أثمنُها.
  2. **مطابقةُ صوتٍ بلا تقاطعِ معنًى:** تحتاجُ نظرَ إنسانٍ، فقد يكونُ المدارُ بعيدًا.
  3. **بلا مرشّحٍ موجود:** تُسجَّلُ عددًا فقط.

**ولا يُصدِرُ حكمًا.** يُخرِجُ طابورَ نظرٍ مرتَّبًا بقوّةِ الإشارة.

الاستعمال:
    python scripts/bulk_phonetic_sweep.py --lang aramaic
    python scripts/bulk_phonetic_sweep.py --lang hebrew --min-overlap 1
"""
from __future__ import annotations

import argparse
import collections
import glob
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402
import fan_any_script as FA  # noqa: E402
from readable import say  # noqa: E402

# اسمُ الذخيرة -> الخطُّ الذي تُقرأُ به مروحتُها. لا يُترَكُ للكشفِ التلقائيّ
# لأنّ كلمةً مصريّةً مثل jb لا تحملُ حرفًا يميّزُ خطَّها.
SCRIPT_OF = {
    "aramaic": "north", "hebrew": "north", "coptic": "coptic",
    "egyptian": "egyptian", "akkadian": "akkadian",
    "ancient_greek": "greek",
    # الفروعُ البعيدةُ التي لم تُمسَحْ قطُّ، وفيها تسكنُ النواةُ إن صحَّتِ الدعوى
    "latin": "latin", "old_irish": "latin", "welsh": "latin",
    "gothic": "gothic", "old_norse": "germanic",
    "english_old": "germanic", "english_middle": "germanic",
}

OUT_DIR = ROOT / "04-cross-linguistic" / "exploration"

# كلماتٌ إنجليزيّةٌ لا تحملُ معنًى مميّزًا فلا تُحسَبُ في التقاطع. والطفيليّاتُ
# النحويّةُ (verb, trans, lemma) كانت أكثرَ ما يلتقي فيُظَنُّ تقاطعَ معنًى وليسَ به.
STOP = {
    "a", "an", "the", "to", "of", "or", "and", "in", "on", "at", "for", "with",
    "be", "is", "are", "was", "were", "it", "its", "that", "this", "as", "by",
    "from", "one", "any", "some", "used", "esp", "especially", "person", "thing",
    "something", "someone", "make", "made", "form", "kind", "sort", "type",
    "meaning", "unknown", "uncertain", "trans", "intrans", "transitive",
    "intransitive", "verb", "noun", "adj", "adjective", "adverb", "pronoun",
    "particle", "lemma", "plural", "singular", "masculine", "feminine", "dual",
    "construct", "state", "sense", "senses", "see", "also", "var", "variant",
    "spelling", "alternative", "obsolete", "archaic", "rare", "figuratively",
    "literally", "kaikki", "glosses", "gloss", "dictionary", "entry", "line",
    "part", "place", "name", "word", "words", "written", "wrote",
}
WORD = re.compile(r"[a-z]+")

BRIDGE = ROOT / "data" / "en-ar-bridge.json"

# **مدخلٌ ليسَ كلمةً في اللسان.** بابانِ يُفسدانِ الطابورَ إن تُركا:
# 1. أعلامٌ حديثةٌ وأسماءُ بلدانٍ ينقلُها العربُ اليومَ بحروفِها، فتتطابقُ الكلمةُ
#    مع نفسِها لا مع أصلٍ: Nepal ~ نبل، Serbia ~ صرب، film ~ فلم.
# 2. صيغٌ صرفيّةٌ لا مداخلَ معجميّة: «first-person singular present of…».
INFLECTION = re.compile(
    r"^\s*(?:alternative|obsolete|archaic|dialectal|misspelling|inflection|"
    r"nominative|genitive|dative|accusative|vocative|instrumental|ablative|"
    # الصيغُ تُكتَبُ أحيانًا مشتركةً بشَرطة: «second/third-person singular ... of»
    r"(?:first|second|third)(?:[/-](?:first|second|third))*[- ]person|"
    r"past|present|future|singular|"
    r"plural|dual|comparative|superlative|definite|indefinite|feminine|"
    r"masculine|neuter|strong|weak|verbal noun|participle|imperative|"
    r"subjunctive|construct|emphatic|soft mutation|nasal mutation|aspirate|"
    r"diminutive|augmentative|synonym|abbreviation|initialism|acronym|"
    r"clipping|contraction|romanization|transliteration|medieval and early)"
    r"[^.]{0,90}\bof\b", re.I)
PROPER = re.compile(
    r"\b(?:given name|surname|male name|female name|a country|a city|a town|"
    r"capital (?:city )?of|a village|a river in|a province|a region|a state in|"
    r"a county|an island|Biblical|apostle|a district|a commune|a municipality|"
    r"a language spoken|a people|ISO |a letter of|a month of)\b", re.I)


ROMAN_FOLD = str.maketrans({"c": "k", "q": "k", "y": "i", "j": "i", "v": "f",
                            "þ": "t", "ð": "d", "w": "u"})


def latin_skeleton(s: str) -> str:
    s = unicodedata.normalize("NFD", str(s).lower())
    s = "".join(c for c in s if not unicodedata.combining(c))
    s = s.replace("ph", "f").replace("x", "ks").translate(ROMAN_FOLD)
    s = re.sub(r"[^a-z]", "", s)
    s = "".join(c for c in s if c not in "aeiou")
    return re.sub(r"(.)\1+", r"\1", s)


def looks_modern_loan(branch: str, shared: list[str]) -> bool:
    """الويلزيّةُ أخذَت film وmink من الإنجليزيّة، والعربيّةُ أخذَتهما منها أيضًا،
    فيلتقي الطرفانِ في كلمةٍ حديثةٍ لا في أصلٍ قديم. وعلامتُها أنّ هيكلَ كلمةِ
    الفرعِ هو هيكلُ الكلمةِ الإنجليزيّةِ نفسِها."""
    b = latin_skeleton(branch)
    return bool(b) and any(latin_skeleton(w) == b for w in shared)


def entry_is_lexical(word: str, glosses: list[str]) -> bool:
    g = " ".join(glosses)
    if INFLECTION.match(g) or PROPER.search(g):
        return False
    if " " in word.strip() or "-" in word.strip():
        return False
    # العلَمُ في الخطِّ اللاتينيِّ يُكتَبُ بحرفٍ كبير، وهو أوضحُ علامةٍ عليه
    first = word.strip()[:1]
    return not (first.isascii() and first.isupper())


def words_of(text: str) -> set[str]:
    return {w for w in WORD.findall(str(text).lower()) if len(w) > 2 and w not in STOP}


def load_bridge() -> dict[str, set[str]]:
    """**جسرُ المعنى.** كان هذا الموضعُ يقابِلُ شرحًا إنجليزيًّا بنصٍّ عربيٍّ فلا
    يلتقيان، فامتلأَ طابورُ «صوتٌ ومعنًى» بالطفيليّاتِ وضاعَ الصيدُ في طابورِ
    «صوتٌ وحدَه». والجسرُ يُعطي كلَّ جذرٍ عربيٍّ معانِيَه الإنجليزيّةَ من جدولِ
    ترجماتِ ويكاموس ومن بطاقاتِ المشروعِ نفسِها، فيصيرُ الطرفانِ بلسانٍ واحد."""
    if not BRIDGE.exists():
        print("   تنبيه: جسرُ المعنى غيرُ مبنيّ، فالمعنى لا يُقاس.")
        print("   ابنِه بـ python scripts/build_en_ar_bridge.py")
        return {}
    d = json.loads(BRIDGE.read_text(encoding="utf-8"))
    head = {r: {w for w in g if w not in STOP} for r, g in d.get("root_head", {}).items()}
    gloss = {r: {w for w in g if w not in STOP} for r, g in d.get("root_gloss", {}).items()}
    return head, gloss


# الذخائرُ التي ليست jsonl، ولها قارئاتٌ في خطِّ الاسترداد أصلًا
SPECIAL = {
    "coptic": ("Comprehensive_Coptic_Lexicon.xml", "iter_coptic_tei"),
    "egyptian": ("aed-v1.0.zip", "iter_aed_html_zip"),
}


def load_special(lang: str) -> list[dict]:
    """القبطيّةُ XML والمصريّةُ zip، فتُقرآنِ بقارئِ خطِّ الاسترداد لا بقارئي."""
    name, reader = SPECIAL[lang]
    from recovery_pipeline import sources as S

    it = getattr(S, reader)
    rows = []
    for e in it(ROOT / "Resources" / lang / name, lang):
        w = str(getattr(e, "headword", "") or getattr(e, "form", "") or "").strip()
        g = str(getattr(e, "gloss", "") or "").strip()
        if w and g:
            rows.append({"word": w, "glosses": [g]})
    return rows


def load_branch(lang: str) -> list[dict]:
    if lang in SPECIAL:
        try:
            return load_special(lang)
        except Exception as exc:  # noqa: BLE001
            print(f"   تعذّرت قراءةُ {lang} بقارئِها الخاصّ: {exc}")
            return []
    rows = []
    for f in glob.glob(str(ROOT / "Resources" / lang / "*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                w = str(e.get("word") or "").strip()
                if not w:
                    continue
                glosses = [
                    str(g) for s in (e.get("senses") or [])[:4]
                    for g in (s.get("glosses") or [])[:2]
                ]
                if not glosses:
                    continue
                rows.append({"word": w, "glosses": glosses})
    return rows


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="aramaic")
    ap.add_argument("--min-overlap", type=int, default=1,
                    help="أدنى عدد كلمات معنى مشتركة لعدّ الصفّ مطابقًا في المعنى")
    ap.add_argument("--max-cands", type=int, default=12,
                    help="تجاهل الكلمات التي تفتح مروحة أوسع من هذا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("تحميلُ ذخيرةِ الجذورِ العربيّة...")
    ar = F.load_arabic_roots()
    print(f"جذورٌ عربيّةٌ: {len(ar):,}")
    head, gloss = load_bridge()
    print(f"جسرُ المعنى: {len(head):,} جذرًا بمعانيها الإنجليزيّة\n")

    rows = load_branch(args.lang)
    print(f"مداخلُ {args.lang}: {len(rows):,}\n")

    both, sound_only, none, skipped = [], [], 0, 0
    script = SCRIPT_OF.get(args.lang, "north")
    for r in rows:
        if not entry_is_lexical(r["word"], r["glosses"]):
            skipped += 1
            continue
        sk = "".join(FA.skeleton(r["word"], script))
        if not (2 <= len(sk) <= 4):
            continue
        cands = FA.fan(r["word"], script)
        if not cands or len(cands) > args.max_cands:
            continue
        hits = [c for c in cands if c in ar]
        if not hits:
            none += 1
            continue
        branch_words = words_of(" ".join(r["glosses"]))
        scored = []
        for c in hits:
            # الشهادةُ المباشرةُ تُعَدُّ ثلاثًا والقرينةُ واحدة، فلا يعلو ما حولَ
            # المعنى على ما هو المعنى
            direct = branch_words & head.get(c, set())
            near = (branch_words & gloss.get(c, set())) - direct
            score = 3 * len(direct) + len(near)
            scored.append((c, score, sorted(direct)[:4] or sorted(near)[:3], bool(direct)))
        scored.sort(key=lambda x: (-x[1], len(x[0])))
        best = scored[0]
        row = {
            "branch": r["word"], "say": say(r["word"]), "skeleton": sk,
            "gloss": "; ".join(r["glosses"][:2])[:90],
            "candidates_found": [c for c, _, _, _ in scored],
            "best": best[0], "overlap": best[1], "shared": best[2],
            "direct": best[3], "depth": len(sk),
            "loan_suspect": looks_modern_loan(r["word"], best[2]),
        }
        (both if best[1] >= args.min_overlap else sound_only).append(row)

    # الشهادةُ المباشرةُ أوّلًا، ثمّ قوّةُ التقاطع، ثمّ الهيكلُ الثلاثيُّ قبلَ الثنائيِّ
    # لأنّ الثلاثيَّ أضيقُ فاحتمالُ الصدفةِ فيه أقلّ
    both.sort(key=lambda r: (r["loan_suspect"], not r["direct"], -r["overlap"], -r["depth"]))
    direct = sum(1 for r in both if r["direct"] and not r["loan_suspect"])
    loans = sum(1 for r in both if r["loan_suspect"])
    print(f"مطابقةُ صوتٍ ومعنًى معًا: {len(both):,}  (بشهادةٍ مباشرةٍ نظيفة: {direct:,}"
          f"، ومشتبَهٌ فيه قرضًا حديثًا: {loans:,})")
    print(f"مطابقةُ صوتٍ بلا تقاطعِ معنًى: {len(sound_only):,}")
    print(f"بلا مرشّحٍ موجودٍ في المعاجم: {none:,}\n")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"phonetic-sweep-{args.lang}"
    json.dump({"language": args.lang, "both": both, "sound_only": sound_only[:3000]},
              open(base.with_suffix(".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    lines = [
        f"# المسحُ الصوتيُّ الشامل: {args.lang}",
        "",
        "**الطبقة:** استكشاف. **لا حكمَ ولا عدَّ ولا نشر.**",
        "",
        "**الطريقة:** قُوبِلَ كلُّ مدخلٍ في الذخيرةِ بمروحتِه العربيّةِ كاملة، وأُبقيَ",
        "المرشَّحُ **الموجودُ فعلًا في المعاجم**، ثمّ قِيسَ تقاطعُ المعنى بينَ الطرفَين.",
        "**الصوتُ يُقابِلُ أوّلًا والمعنى يحكُمُ بعدَه**، وهذا عكسُ ما كنّا نفعل.",
        "",
        f"**مطابقةُ صوتٍ ومعنًى معًا: {len(both):,}**، منها **{direct:,}** بشهادةٍ",
        f"مباشرةٍ من جسرِ المعنى · مطابقةُ صوتٍ وحدَه: {len(sound_only):,}",
        "",
        "| كلمةُ الفرع | نطقُها | معناها | العربيّ | تقاطعُ المعنى | مرشّحاتٌ أخرى |",
        "|---|---|---|---|---|---|",
    ]
    for r in both[:600]:
        others = " · ".join(c for c in r["candidates_found"][1:6])
        lines.append(
            f"| `{r['branch']}` | {r['say']} | {r['gloss']} | **{r['best']}** | "
            f"{'قرضٌ حديثٌ؟' if r['loan_suspect'] else 'مباشر' if r['direct'] else 'قرينة'} {r['overlap']}: "
            f"{' '.join(r['shared'])} | {others or '-'} |"
        )
    base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كُتب: {base.with_suffix('.md').relative_to(ROOT).as_posix()}")

    print("\nأقوى عشرين بتقاطعِ المعنى:")
    for r in both[:20]:
        print(f"   {r['branch']:10} {r['say'][:20]:22} {r['gloss'][:34]:36} "
              f"~ {r['best']:6} [{' '.join(r['shared'])}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
