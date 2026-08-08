# -*- coding: utf-8 -*-
"""جسرُ المعنى بينَ الإنجليزيّةِ والعربيّة (2026-08-07)

**العطبُ الذي يُصلِحُه:** المسحُ الصوتيُّ كانَ يقيسُ تقاطعَ المعنى بمقابلةِ شرحِ
الفرعِ **الإنجليزيِّ** بنصِّ المعجمِ العربيِّ **العربيّ**، وهما لا يلتقيان في حرف.
فما كانَ يلتقي إلّا كلماتٌ طفيليّةٌ مثل meaning وverb وtrans، فامتلأَ طابورُ
«صوتٌ ومعنًى» بما لا معنى فيه، وبقيَ الصيدُ الحقيقيُّ في طابورِ «صوتٌ وحدَه».

**الحلُّ من موردٍ عندَنا أصلًا:** معجمُ ويكاموس الإنجليزيُّ يحملُ في كلِّ مدخلٍ
جدولَ ترجماتِه، وفيه العربيّةُ بلفظِها ومعناها. فمنه يُبنى جسرٌ مباشر:

    كلمةٌ إنجليزيّةٌ ← كلمةٌ عربيّةٌ ← جذرُها

**وردُّ الكلمةِ إلى جذرِها** يُجرَّبُ على مراتب: الصورةُ المجرَّدةُ نفسُها، ثمّ بعدَ
نزعِ أل والتاءِ والزوائدِ المشهورة، ثمّ بأخذِ ثلاثةِ أصولٍ على ترتيبِها من الصورة.
وكلُّ ما لا يُردُّ بيقينٍ يُترَكُ بصورتِه ولا يُخمَّنُ له جذر.

الاستعمال:
    python scripts/build_en_ar_bridge.py            بناءٌ كامل
    python scripts/build_en_ar_bridge.py --check    فحصُ حداثةِ المخرَج
"""
from __future__ import annotations

import argparse
import collections
import itertools
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402

SRC = ROOT / "Resources" / "english_modern" / "kaikki.org-dictionary-English.jsonl"
SRC_AR = ROOT / "Resources" / "arabic_kaikki" / "kaikki.org-dictionary-Arabic.jsonl"
OUT = ROOT / "data" / "en-ar-bridge.json"
READINGS = ROOT / "04-cross-linguistic" / "readings"

# «Arabic terms belonging to the root ح ل ل»: المعجمُ العربيُّ يُصرِّحُ بجذرِ كلِّ
# كلمةٍ في تصنيفاتِها، وهذا إسنادٌ من المصدرِ لا اجتهادٌ من رادِّنا، فيُقدَّمُ عليه.
RX_ROOT_CAT = re.compile(r"belonging to the root\s+([ء-ي](?:\s+[ء-ي]){1,4})")

# شرحٌ يصفُ الصرفَ لا المعنى: «active participle of», «accusative of». لو أُخِذَ
# لأدخلَ كلماتِ النحوِ في معاني الجذرِ فأفسدَ كلَّ مقابلةٍ بعدَه.
RX_MORPH_GLOSS = re.compile(
    r"^\s*(?:active|passive|verbal|present|past|future|nominative|accusative|"
    r"genitive|dative|construct|definite|indefinite|masculine|feminine|dual|"
    r"plural|singular|first-person|second-person|third-person|elative|"
    r"comparative|superlative|diminutive|augmentative|imperative|jussive|"
    r"subjunctive|inflected|inflection|alternative|obsolete|archaic|dialectal|"
    r"colloquial|romanization|transliteration|abbreviation|misspelling|"
    r"participle|noun|verb|adjective|adverb|form|dual|nisba|feminine)"
    r"[^.]{0,70}of", re.I)

_DIAC = dict.fromkeys(range(0x064B, 0x0653))
_DIAC[0x0640] = None
SHADDA = "ّ"

WEAK = set("اوىي")
PREFIX = ("است", "مست", "ال", "مت", "من", "مو", "مي", "ما", "م", "ت", "ي", "ن", "ا", "أ", "إ")
SUFFIX = ("ات", "ون", "ين", "ان", "ية", "ة", "ه", "ى", "ي", "ا", "و", "ن")

WORD = re.compile(r"[a-z]+")
# كلماتُ الشروحِ الطفيليّةُ التي لا تدلُّ على معنًى فلا تُحسَبُ تقاطعًا
NOISE = {
    "meaning", "unknown", "uncertain", "trans", "intrans", "verb", "noun", "adj",
    "adjective", "adverb", "pronoun", "particle", "lemma", "form", "plural",
    "singular", "masculine", "feminine", "dual", "construct", "state", "sense",
    "used", "usually", "esp", "especially", "etc", "see", "also", "var",
    "variant", "spelling", "alternative", "obsolete", "archaic", "rare",
    "figuratively", "literally", "transitive", "intransitive", "the", "and",
    "of", "to", "in", "on", "at", "for", "with", "from", "that", "this", "it",
    "its", "as", "by", "or", "be", "is", "are", "was", "were", "a", "an", "one",
    "any", "some", "person", "thing", "something", "someone", "make", "made",
    "kind", "sort", "type", "part", "place", "name",
    # أسماءُ المواردِ والألسنِ تتسرّبُ من حقولِ البطاقاتِ فتُشبِهُ معنًى وليست منه
    "kaikki", "glosses", "gloss", "dictionary", "entry", "line", "snapshot",
    "source", "lemma", "wiktionary", "crum", "kellia", "cad", "tla", "aed",
    "arabic", "hebrew", "aramaic", "coptic", "egyptian", "akkadian", "gothic",
    "greek", "latin", "norse", "irish", "welsh", "english", "persian",
    "punic", "phoenician", "semitic", "proto", "reconstructed", "attested",
    "define", "definition", "having", "been", "because", "certain", "various",
    "senses",
    # مصطلحاتُ النحوِ والصرف: تصفُ صيغةَ الكلمةِ لا معناها، وهي أكثرُ ما يتسرّبُ
    # من معجمٍ يشرحُ كلَّ صيغةٍ مشتقّةٍ بمدخلٍ مستقلّ
    "accusative", "nominative", "genitive", "dative", "vocative", "active",
    "passive", "participle", "verbal", "elative", "nisba", "construct",
    "imperfective", "perfective", "jussive", "subjunctive", "imperative",
    "indicative", "inflected", "conjugation", "declension", "pausal",
    "indefinite", "definite", "colloquial", "romanized", "romanization",
}


def bare(s: str) -> str:
    s = unicodedata.normalize("NFC", str(s))
    out = []
    for ch in s:
        if ch == SHADDA and out:
            out.append(out[-1])       # الشدّةُ حرفٌ مضاعَفٌ لا حركة
            continue
        out.append(ch)
    s = "".join(out).translate(_DIAC)
    return re.sub(r"[^ء-ي]", "", s)


def root_of(word: str, roots: set[str], strict: bool = True) -> str:
    """يردُّ الصورةَ إلى جذرِها إن أمكنَ بيقينٍ، وإلّا فارغ.

    و`strict` يمنعُ آخرَ المراتب، وهي أخذُ ثلاثةِ أصولٍ على ترتيبِها من الصورة.
    تلكَ المرتبةُ ردَّت `سكايب` (Skype) إلى `سكب` فأدخلَت skype في معاني
    الصبِّ والسكب، وهي بابُ خطأٍ مفتوحٌ على كلِّ علَمٍ منقول."""
    w = bare(word)
    if not w:
        return ""
    if w in roots:
        return w
    for pre in PREFIX:
        if w.startswith(pre) and len(w) - len(pre) >= 2:
            core = w[len(pre):]
            if core in roots:
                return core
            for suf in SUFFIX:
                if core.endswith(suf) and len(core) - len(suf) >= 2:
                    if core[:-len(suf)] in roots:
                        return core[:-len(suf)]
    for suf in SUFFIX:
        if w.endswith(suf) and len(w) - len(suf) >= 2:
            if w[:-len(suf)] in roots:
                return w[:-len(suf)]
    # آخرُ المراتب: ثلاثةُ أصولٍ على ترتيبِها، ولا تُقبَلُ إلّا إن كانت الزيادةُ
    # حرفَينِ فأقلَّ وكانَ المحذوفُ كلُّه من حروفِ الزيادةِ والعلّة
    if not strict and 3 <= len(w) <= 6:
        for combo in itertools.combinations(range(len(w)), 3):
            cand = "".join(w[i] for i in combo)
            if cand not in roots:
                continue
            dropped = [w[i] for i in range(len(w)) if i not in combo]
            if len(dropped) <= 2 and all(c in WEAK or c in "متنسءأإ" for c in dropped):
                return cand
    return ""


def words_of(text: str) -> set[str]:
    return {w for w in WORD.findall(str(text).lower()) if len(w) > 2 and w not in NOISE}


def from_cards() -> dict[str, set[str]]:
    """طبقةٌ ثانيةٌ من الجسر: كلُّ صلةٍ صادرةٍ في بطاقاتِنا تحملُ جذرًا عربيًّا
    ومعنًى إنجليزيًّا من قاموسِ الفرع، وهي شهادةٌ مباشرةٌ جمعَها المشروعُ بنفسِه."""
    import count_links as C

    rx_sense = re.compile(r"^-\s*المعنى من قاموس الفرع[^\n]*?[:：]\s*(.+)$", re.M)
    rx_ar = re.compile(r"^-\s*(?:المقابلُ? من اللسان|النظيرُ? العربيّ)[^\n]*?[:：]\s*(.+)$", re.M)
    out: dict[str, set[str]] = collections.defaultdict(set)
    for path in sorted(READINGS.glob("*.md")):
        text = C.bare(path.read_text(encoding="utf-8"))
        for raw in C.CARD_SPLIT.split(text)[1:]:
            if not C.scan_card(raw):
                continue
            ms, ma = rx_sense.search(raw), rx_ar.search(raw)
            if not (ms and ma):
                continue
            m = re.search(r"([ء-ي]{2,6})", re.sub(r"\[[^\]]*\]", "", ma.group(1)))
            if not m:
                continue
            gloss = words_of(re.sub(r"\[[^\]]*\]", "", ms.group(1)))
            if gloss:
                out[bare(m.group(1))] |= gloss
    return out


def from_arabic_dictionary(roots: set[str]) -> tuple[dict[str, set[str]], dict]:
    """**الاتّجاهُ المباشر:** مدخلٌ عربيٌّ ومعناه بالإنجليزيّة. وهو أوثقُ من جدولِ
    الترجماتِ لأنّه لا يمرُّ بكلمةٍ إنجليزيّةٍ وسيطة، وأوسعُ منه لأنّه يغطّي
    المعجمَ كلَّه لا ما اختارَ محرِّرٌ أن يُترجِمَه."""
    out: dict[str, set[str]] = collections.defaultdict(set)
    stats = {"entries": 0, "with_declared_root": 0, "resolved": 0, "unresolved": 0}
    if not SRC_AR.exists():
        return out, stats
    with open(SRC_AR, encoding="utf-8") as fh:
        for line in fh:
            try:
                e = json.loads(line)
            except Exception:
                continue
            word = str(e.get("word") or "")
            if not word or not re.search(r"[ء-ي]", word):
                continue
            stats["entries"] += 1
            # رومنةُ الكلمةِ نفسِها تُكتَبُ بحروفٍ لاتينيّةٍ فتُشبِهُ معنًى إنجليزيًّا
            # وليست منه: sakaba وbaraqa وallafa. تُجمَعُ لتُطرَح.
            roman = set()
            for f in e.get("forms") or []:
                if "romanization" in (f.get("tags") or []) or f.get("roman"):
                    roman |= words_of(f.get("form") or "") | words_of(f.get("roman") or "")
            for h in e.get("head_templates") or []:
                roman |= words_of(re.sub(r"[^A-Za-z ]", " ", str(h.get("expansion") or "")))
            for s in e.get("sounds") or []:
                roman |= words_of(s.get("romanization") or "")
            gloss = set()
            for s in e.get("senses") or []:
                for g in (s.get("glosses") or [])[:3]:
                    if RX_MORPH_GLOSS.match(str(g)):
                        continue          # شرحُ صرفٍ لا شرحُ معنى
                    # الرومنةُ تُكتَبُ بين قوسَينِ بعدَ الصورةِ العربيّة، فتُطرَحُ
                    # الأقواسُ كلُّها: المعنى في الجملةِ لا في القوس
                    gloss |= words_of(re.sub(r"\([^)]*\)", " ", str(g)))
            gloss -= roman
            if not gloss:
                continue
            cats = [c.get("name", "") if isinstance(c, dict) else str(c)
                    for c in (e.get("categories") or [])]
            cats += [c.get("name", "") if isinstance(c, dict) else str(c)
                     for s in (e.get("senses") or [])
                     for c in (s.get("categories") or [])]
            root = ""
            for c in cats:
                m = RX_ROOT_CAT.search(c)
                if m:
                    root = re.sub(r"\s+", "", m.group(1))
                    stats["with_declared_root"] += 1
                    break
            if not root:
                root = root_of(word, roots, strict=False)  # اجتهادُ الرادِّ عندَ غيابِ التصريح
            if root:
                out[root] |= gloss
                stats["resolved"] += 1
            else:
                stats["unresolved"] += 1
    return out, stats


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    ap.add_argument("--limit", type=int, default=0, help="اقرأ هذا العددَ من الأسطرِ فقط (للتجربة)")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.check:
        if not OUT.exists():
            print("MISSING: data/en-ar-bridge.json غير مبنيّ")
            return 1
        d = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"CLEAN: جسرُ المعنى {len(d['root_head']):,} جذرًا، "
              f"{d['stats']['pairs']:,} زوجًا من ويكاموس، "
              f"{d['stats']['from_cards']:,} من بطاقاتِنا")
        return 0

    if not SRC.exists():
        print(f"SKIPPED: الذخيرةُ خارجَ git ({SRC.relative_to(ROOT).as_posix()})")
        return 0

    print("تحميلُ جذورِ العربيّة...")
    roots = set(F.load_arabic_roots())
    print(f"جذورٌ: {len(roots):,}\n")

    # طبقتان لا واحدة: **الرأسُ** هو اللفظُ الإنجليزيُّ الذي تُرجِمَ بهذا الجذرِ
    # نفسِه فهو شهادةٌ مباشرة، و**الشرحُ** كلامٌ حولَه فهو قرينةٌ أضعف. وخلطُهما
    # يُغرِقُ الشهادةَ في الكلام.
    root_head: dict[str, set[str]] = collections.defaultdict(set)
    root_gloss: dict[str, set[str]] = collections.defaultdict(set)
    surface: dict[str, set[str]] = collections.defaultdict(set)
    pairs = unresolved = lines = 0

    print("مسحُ معجمِ ويكاموس الإنجليزيِّ بحثًا عن جداولِ الترجمة...")
    with open(SRC, encoding="utf-8") as fh:
        for line in fh:
            lines += 1
            if args.limit and lines > args.limit:
                break
            if '"code": "ar"' not in line and '"lang": "Arabic"' not in line:
                continue
            try:
                e = json.loads(line)
            except Exception:
                continue
            head = str(e.get("word") or "").lower()
            if not head or not WORD.fullmatch(head):
                continue
            # الترجماتُ تسكنُ طبقتَين: طبقةَ المدخلِ وطبقةَ كلِّ معنًى على حِدة،
            # وتسعةُ أعشارِها في الثانية. وشرحُ المعنى نفسِه أدقُّ من شرحِ المدخل.
            layers = [(e.get("translations") or [], "")]
            for sn in e.get("senses") or []:
                if sn.get("translations"):
                    layers.append((sn["translations"], " ".join(sn.get("glosses") or [])))
            for group, sense_gloss in layers:
                for t in group:
                    if t.get("code") != "ar":
                        continue
                    aw = str(t.get("word") or "").strip()
                    if not aw:
                        continue
                    pairs += 1
                    gloss = words_of(t.get("sense") or "") | words_of(sense_gloss)
                    r = root_of(aw, roots)
                    if r:
                        root_head[r].add(head)
                        root_gloss[r] |= gloss
                    else:
                        unresolved += 1
                        surface[bare(aw)] |= {head} | gloss
            if lines % 400_000 == 0:
                print(f"   {lines:,} سطرًا، {pairs:,} زوجًا، {len(root_gloss):,} جذرًا")

    print(f"\nمن ويكاموس: {pairs:,} زوجًا، رُدَّ منها إلى جذرٍ {pairs - unresolved:,}")

    ar_layer, ar_stats = from_arabic_dictionary(roots)
    for r, g in ar_layer.items():
        root_head[r] |= g      # مدخلٌ عربيٌّ ومعناه، وهو أوثقُ الطبقاتِ وأوسعُها
    if ar_stats["entries"]:
        print(f"من المعجمِ العربيّ: {ar_stats['entries']:,} مدخلًا، "
              f"بجذرٍ مصرَّحٍ في المصدر {ar_stats['with_declared_root']:,}، "
              f"رُدَّ إلى جذرٍ {ar_stats['resolved']:,}")
    else:
        print("المعجمُ العربيُّ غيرُ موجودٍ بعد، فطبقتُه لم تُبنَ")

    card_layer = from_cards()
    for r, g in card_layer.items():
        root_head[r] |= g      # معنى البطاقةِ من قاموسِ الفرعِ شهادةٌ مباشرةٌ أيضًا
    print(f"من بطاقاتِنا: {len(card_layer):,} جذرًا بمعانيها الإنجليزيّة")

    payload = {
        "generated_by": "scripts/build_en_ar_bridge.py",
        "note": "جسرُ معنًى بين الإنجليزيّةِ والعربيّة. طبقةُ أداةٍ لا حكم.",
        "stats": {
            "pairs": pairs, "resolved": pairs - unresolved,
            "from_cards": len(card_layer), "roots": len(root_head),
            "from_arabic_dictionary": ar_stats,
            "surface_only": len(surface),
        },
        "root_head": {r: sorted(g)[:80] for r, g in sorted(root_head.items()) if g},
        "root_gloss": {r: sorted(g)[:60] for r, g in sorted(root_gloss.items()) if g},
        "surface_gloss": {w: sorted(g)[:20] for w, g in sorted(surface.items()) if g},
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")
    print(f"\nجذورٌ بمعنًى إنجليزيّ: {len(root_gloss):,}")
    print(f"كُتب: {OUT.relative_to(ROOT).as_posix()}  ({OUT.stat().st_size // 1024:,} KB)")

    print("\nعيّنةٌ للتحقُّق:")
    for r in ("قرن", "عين", "بيت", "كلب", "شمس", "سكب", "غلف", "قطع", "برق"):
        if r in root_head:
            print(f"   {r:6} {', '.join(sorted(root_head[r])[:10])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
