# -*- coding: utf-8 -*-
"""استخراجُ جدولِ التقابلاتِ من المادّةِ لا من الذاكرة (2026-08-06)

**السؤالُ الذي يُجيبُه:** سألَ المؤلّفُ أعِندَنا صفوفٌ ناقصةٌ غيرُ الرِجلِ الآراميّةِ
في SIB-07. والجوابُ لا يُخمَّن: يُستخرَجُ.

**الطريقة:** تحفظُ الأداةُ خطَّ الأساسِ القديمَ، وهو تطابقُ نصِّ المعنى بعدَ نزعِ
القوسِ والأداةِ الأولى. ثمّ توسّعُ الاسترجاعَ بثلاثةِ جسورٍ معلنة: تطابقُ المعنى
بعدَ إسقاطِ ما بعدَ الفاصلة، أو تطابقُ الكلمةِ الدلاليّةِ الأولى، أو اشتراكُ
كلمتَينِ دلاليّتَينِ على الأقلّ. تُجرَّدُ الكلمتانِ إلى صوامتِهما، فإن تساوى العددُ
حوذيَ الصامتُ بالصامتِ وسُجِّلَ كلُّ تقابل. ويظلُّ هذا استرجاعًا لا حكمًا.

**وحدُّها:** هذا يُخرِجُ مرشَّحًا لا حكمًا. فتطابقُ المعنى في معجمَينِ إنجليزيَّينِ
قد يكونُ ترجمةً متساهلة، والصوامتُ المتساويةُ عددًا قد تكونُ صدفة. لكنّ الوزنَ
العدديَّ يفصلُ: ما ظهرَ مرّةً ضجيج، وما ظهرَ خمسينَ مرّةً بنية.

الاستعمال:  python scripts/derive_correspondences.py [--min 4] [--json out.json]
"""
from __future__ import annotations

import argparse
import collections
import dataclasses
import glob
import json
import os
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
RESOURCES = ROOT / "Resources"
ARABIC_ROOTS = RESOURCES / "arabic_roots_hf" / "train-00000-of-00001.parquet"
ARABIC_ENGLISH_BOOK = "المعجم العربي الإنجليزي"

# الصوائتُ وعلاماتُها في كلِّ خطّ، تُنزَعُ قبلَ المحاذاة
STRIP = {
    # العبريّة والآراميّة: النقطُ والتعليلُ والألفُ والياءُ والواوُ حينَ تكونُ أمَّ قراءة
    "hebrew": re.compile(r"[֑-ׇ׳״\s\-׳״]"),
    "aramaic": re.compile(r"[֑-ׇ׳״\s\-׳״]"),
    "arabic": re.compile(r"[\u0640\u064b-\u065f\u0670\u06d6-\u06ed\s\-]"),
}
# لواحقُ الحالةِ الآراميّةِ وأداةُ التعريفِ الملحقة
ARAMAIC_STATE = re.compile(r"א$")

# الحروفُ النهائيّةُ في الخطِّ العبريِّ والآراميِّ ليست صوامتَ أخرى بل صورةٌ
# موضعيّةٌ للحرفِ نفسِه. وتركُها يُنتِجُ تقابلاتٍ وهميّةً (נ~ן، מ~ם، כ~ך، פ~ף)
# تحتلُّ رأسَ الجدولِ وتُغرِقُ الإشارةَ الحقيقيّة.
FINALS = str.maketrans("ךםןףץ", "כמנפצ")

# الفينيقيّةُ والبونيقيّةُ مكتوبتانِ في اللقطةِ بالأبجديّةِ الفينيقيّة. نطوي
# الرسمَ إلى نظيره الشماليِّ المربّع قبلَ المحاذاة، لا إلى العربيّة، لكي يبقى
# المستخرَج واصفًا لا حاكمًا ويصحَّ اختبارُ أزواج الغرب الساميّ الأخرى.
PHOENICIAN_TO_SQUARE = str.maketrans(
    "𐤀𐤁𐤂𐤃𐤄𐤅𐤆𐤇𐤈𐤉𐤊𐤋𐤌𐤍𐤎𐤏𐤐𐤑𐤒𐤓𐤔𐤕",
    "אבגדהוזחטיכלמנסעפצקרשת",
)
SQUARE_CONSONANTS = set("אבגדהוזחטיכלמנסעפצקרשת")

AKKADIAN_TO_SQUARE = {
    "ʾ": "א", "ʔ": "א", "b": "ב", "g": "ג", "d": "ד", "h": "ה",
    "w": "ו", "z": "ז", "ḫ": "ח", "ḥ": "ח", "ṭ": "ט", "y": "י",
    "k": "כ", "l": "ל", "m": "מ", "n": "נ", "s": "ס", "š": "ש",
    "ṣ": "צ", "p": "פ", "f": "פ", "q": "ק", "r": "ר", "t": "ת",
    "ṯ": "ת", "ḏ": "ד", "ʿ": "ע",
}
AKKADIAN_VOWELS = set("aeiouāēīōūâêîôû")
AKKADIAN_MIMATION = re.compile(r"[aiuāīūâîû]m$", re.IGNORECASE)

# حروفُ المدِّ التي تُحذَفُ من الهيكلِ الصامتيِّ حينَ لا تكونُ أصلًا. تُحذَفُ في
# الوسطِ والآخرِ فقط، لا في الأوّلِ حيثُ تكونُ همزةً أو أصلًا.
MATRES = "והי"

# هوياتُ المحاذاةِ العابرةِ للخطّ. الحروفُ العربيّةُ التي اندمجت في فرعِ الشمال
# تبقى متميزةً هنا، لكي يظهر خ~ח وغ~ע وث~ת ونحوُها في موضعِ الفرقِ بدلَ أن
# تُطوى النتيجةُ في الفرضِ السابقِ عليها.
ARABIC_ALIGN = {
    "ء": "א", "ا": "א", "ب": "ב", "ت": "ת", "ث": "θ", "ج": "ג",
    "ح": "ח", "خ": "x", "د": "ד", "ذ": "ð", "ر": "ר", "ز": "ז",
    "س": "ס", "ش": "ש", "ص": "צ", "ض": "D", "ط": "ט", "ظ": "Z",
    "ع": "ע", "غ": "G", "ف": "פ", "ق": "ק", "ك": "כ", "ل": "ל",
    "م": "מ", "ن": "נ", "ه": "ה", "و": "ו", "ي": "י",
}
ARABIC_LETTERS = set(ARABIC_ALIGN)
ARABIC_ROOT_FOLD = str.maketrans({
    "أ": "ء", "إ": "ء", "ؤ": "ء", "ئ": "ء", "آ": "ء", "ٱ": "ء", "ى": "ي",
})

TOKEN_RE = re.compile(r"[a-z]+(?:[-'][a-z]+)?", re.IGNORECASE)

# لا تدخلُ أدواتُ الصياغةِ المعجميّةِ في تقاطعِ المعنى. وإسقاطُها مهمٌّ خصوصًا
# لأنّ جميعَ صيغِ التصريفِ قد تبدأُ بعبارةٍ واحدةٍ وهي لا تحملُ معنى المدخل.
STOPWORDS = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "for", "from", "has", "have", "he", "her", "herself", "him", "himself",
    "in", "into", "is", "it", "itself", "its", "of", "on", "or", "she",
    "that", "the", "their", "them", "themselves", "they", "to", "was", "were",
    "which", "who", "with", "without", "someone", "something", "one", "person",
    "thing",
}
LEXICOGRAPHIC_NOISE = {
    "alternative", "comparative", "dative", "dual", "feminine", "form",
    "genitive", "imperative", "indicative", "inflection", "masculine",
    "nominative", "participle", "person", "plural", "preterite", "pronoun",
    "proper", "singular", "subjunctive", "superlative", "variant",
}
NOISE_PATTERNS = re.compile(
    r"\b(?:male|female) given name\b|\b(?:alternative|variant) form of\b|"
    r"\binflection of\b|\b(?:first|second|third)-person\b",
    re.IGNORECASE,
)


@dataclasses.dataclass(frozen=True)
class Sense:
    word: str
    legacy: str
    normalized: str
    tokens: tuple[str, ...]


@dataclasses.dataclass
class Lexicon:
    senses: list[Sense]
    legacy: dict[str, list[str]]


@dataclasses.dataclass
class Analysis:
    correspondences: dict[tuple[str, str], dict[tuple[str, str], set[str]]]
    examined_pairs: set[tuple[str, str]]
    sense_matches: int


def skeleton(word: str, lang: str) -> str:
    w = unicodedata.normalize("NFC", word)
    if lang == "akkadian":
        w = AKKADIAN_MIMATION.sub("", w)
        folded = []
        for char in w.casefold():
            if char in AKKADIAN_VOWELS:
                continue
            mapped = AKKADIAN_TO_SQUARE.get(char)
            if mapped:
                folded.append(mapped)
        w = "".join(folded)
        w = re.sub(r"(.)\1+", r"\1", w)
    rx = STRIP.get(lang)
    if rx:
        w = rx.sub("", w)
    w = w.translate(FINALS)
    if lang in {"phn", "xpu"}:
        w = w.translate(PHOENICIAN_TO_SQUARE)
        w = "".join(char for char in w if char in SQUARE_CONSONANTS)
    if lang == "aramaic":
        w = ARAMAIC_STATE.sub("", w)
    if lang == "arabic":
        w = w.translate(ARABIC_ROOT_FOLD)
        w = "".join(char for char in w if char in ARABIC_LETTERS)
    if len(w) > 2 and lang in {"akkadian", "aramaic", "hebrew", "phn", "xpu"}:
        w = w[0] + "".join(c for c in w[1:] if c not in MATRES)
    return w


def aligned_skeleton(word: str, lang: str) -> tuple[str, str]:
    raw = skeleton(word, lang)
    if lang == "arabic":
        return raw, "".join(ARABIC_ALIGN.get(char, char) for char in raw)
    return raw, raw


def legacy_gloss(value: object) -> str:
    """التطبيعُ القديمُ بحرفِه لكي يبقى رقمُ ما قبلَ التوسيعِ قابلًا للإعادة."""
    gloss = re.sub(r"\([^)]*\)", "", str(value)).strip().lower()
    return re.sub(r"^(to|a|an|the)\s+", "", gloss).strip()


def expanded_gloss(value: object) -> str:
    """أسقطِ الحاشيةَ بينَ قوسينِ وكلَّ ما بعدَ الفاصلةِ ثمّ الأدواتِ المتتابعة."""
    gloss = unicodedata.normalize("NFC", str(value)).casefold()
    gloss = re.sub(r"\([^)]*\)", "", gloss)
    gloss = gloss.split(",", 1)[0]
    gloss = re.sub(r"\s+", " ", gloss).strip(" .;:")
    while True:
        reduced = re.sub(r"^(?:to|a|an|the)\s+", "", gloss).strip()
        if reduced == gloss:
            return gloss
        gloss = reduced


def semantic_tokens(gloss: str) -> tuple[str, ...]:
    if NOISE_PATTERNS.search(gloss):
        return ()
    tokens = []
    for token in TOKEN_RE.findall(gloss):
        token = token.casefold()
        if token in STOPWORDS or token in LEXICOGRAPHIC_NOISE:
            continue
        if token not in tokens:
            tokens.append(token)
    return tuple(tokens)


LANE_ANCHOR = re.compile(
    r"\b(?:He|She|It|They|A|An|The|To|One who|One that|Name of|Act of)\b",
)


def normalize_arabic_root(value: object) -> str:
    root = unicodedata.normalize("NFC", str(value or ""))
    root = STRIP["arabic"].sub("", root).translate(ARABIC_ROOT_FOLD)
    return "".join(char for char in root if char in ARABIC_LETTERS)


def lane_glosses(value: object) -> list[str]:
    """استخرج أوائلَ العباراتِ التعريفيّةِ الإنجليزيّةِ من مقالةِ Lane الطويلة."""
    text = unicodedata.normalize("NFC", str(value or ""))
    text = re.sub(r"\([^)]*\)|\[[^]]*\]", " ", text)
    text = re.sub(r"[ء-ي\u064b-\u065f\u0670]+", " ", text)
    text = re.sub(r"\bb\d+\s*:", ".", text, flags=re.IGNORECASE)
    output: list[str] = []
    seen: set[str] = set()
    for segment in re.split(r"[.;]", text):
        match = LANE_ANCHOR.search(segment)
        if match is None:
            continue
        gloss = expanded_gloss(segment[match.start():])
        tokens = semantic_tokens(gloss)
        if not tokens or len(gloss) < 3 or len(gloss) > 180:
            continue
        if gloss not in seen:
            seen.add(gloss)
            output.append(gloss)
        if len(output) >= 4:
            break
    return output


def load_arabic_roots() -> Lexicon:
    """حوّل ذخيرةَ الجذورِ المختلفةِ الصيغةِ إلى أزواجِ (جذر، معنى)."""
    try:
        import pyarrow.parquet as pq
    except ImportError as exc:
        raise RuntimeError("يلزم pyarrow لقراءة Resources/arabic_roots_hf") from exc

    table = pq.read_table(ARABIC_ROOTS, columns=["root", "definition", "book_name"])
    senses: list[Sense] = []
    by_legacy: dict[str, list[str]] = collections.defaultdict(list)
    seen: set[tuple[str, str]] = set()
    for row in table.to_pylist():
        if str(row.get("book_name") or "") != ARABIC_ENGLISH_BOOK:
            continue
        root = normalize_arabic_root(row.get("root"))
        if not 2 <= len(root) <= 4:
            continue
        for gloss in lane_glosses(row.get("definition")):
            key = (root, gloss)
            if key in seen:
                continue
            seen.add(key)
            tokens = semantic_tokens(gloss)
            senses.append(Sense(root, gloss, gloss, tokens))
            by_legacy[gloss].append(root)
    if not senses:
        raise RuntimeError("لم يستخرج محمّل العربية أي زوج (جذر، معنى)")
    return Lexicon(senses=senses, legacy=dict(by_legacy))


def load(lang: str) -> Lexicon:
    """حمّل مداخلَ Kaikki مع خطِّ الأساسِ ومفاتيحِ الاسترجاعِ الموسّع."""
    if lang == "arabic":
        return load_arabic_roots()
    senses: list[Sense] = []
    by_legacy: dict[str, list[str]] = collections.defaultdict(list)
    for f in glob.glob(str(RESOURCES / lang / "*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                w = str(e.get("word") or "").strip()
                if not w:
                    continue
                for s in (e.get("senses") or [])[:3]:
                    for g in (s.get("glosses") or [])[:2]:
                        old = legacy_gloss(g)
                        if not 2 < len(old) < 42:
                            continue
                        normalized = expanded_gloss(g)
                        tokens = semantic_tokens(normalized)
                        senses.append(Sense(w, old, normalized, tokens))
                        by_legacy[old].append(w)
    return Lexicon(senses=senses, legacy=dict(by_legacy))


def accepted_pair(wa: str, wb: str, a_lang: str, b_lang: str) -> tuple[str, str] | None:
    raw_a, sa = aligned_skeleton(wa, a_lang)
    raw_b, sb = aligned_skeleton(wb, b_lang)
    if not (2 <= len(sa) <= 4) or len(sa) != len(sb) or sa == sb:
        return None
    positions = [index for index, (x, y) in enumerate(zip(sa, sb)) if x != y]
    if len(positions) != 1:
        return None
    index = positions[0]
    return raw_a[index], raw_b[index]


def record_pair(
    analysis: Analysis,
    wa: str,
    wb: str,
    evidence: str,
    a_lang: str,
    b_lang: str,
) -> None:
    diff = accepted_pair(wa, wb, a_lang, b_lang)
    if diff is None:
        return
    pair = (wa, wb)
    analysis.examined_pairs.add(pair)
    analysis.correspondences[diff][pair].add(evidence)


def legacy_analysis(A: Lexicon, B: Lexicon, a_lang: str, b_lang: str) -> Analysis:
    corr = collections.defaultdict(lambda: collections.defaultdict(set))
    result = Analysis(corr, set(), 0)
    shared = set(A.legacy) & set(B.legacy)
    for gloss in sorted(shared):
        for wa in sorted(set(A.legacy[gloss])):
            for wb in sorted(set(B.legacy[gloss])):
                result.sense_matches += 1
                record_pair(result, wa, wb, gloss, a_lang, b_lang)
    return result


def expanded_analysis(A: Lexicon, B: Lexicon, a_lang: str, b_lang: str) -> Analysis:
    """استرجاعٌ مفهرس: تطابقٌ مطبّع أو كلمةٌ أولى أو تقاطعُ كلمتَين."""
    exact: dict[str, list[int]] = collections.defaultdict(list)
    first: dict[str, list[int]] = collections.defaultdict(list)
    token_index: dict[str, list[int]] = collections.defaultdict(list)
    for index, sense in enumerate(B.senses):
        if sense.normalized:
            exact[sense.normalized].append(index)
        if sense.tokens:
            first[sense.tokens[0]].append(index)
            for token in sense.tokens:
                token_index[token].append(index)

    corr = collections.defaultdict(lambda: collections.defaultdict(set))
    result = Analysis(corr, set(), 0)
    seen_sense_pairs: set[tuple[int, int]] = set()
    for a_index, left in enumerate(A.senses):
        candidates = set(exact.get(left.normalized, ()))
        if left.tokens:
            candidates.update(first.get(left.tokens[0], ()))
            overlap_counts: collections.Counter[int] = collections.Counter()
            for token in left.tokens:
                overlap_counts.update(token_index.get(token, ()))
            candidates.update(index for index, count in overlap_counts.items() if count >= 2)

        for b_index in candidates:
            if (a_index, b_index) in seen_sense_pairs:
                continue
            right = B.senses[b_index]
            common = sorted(set(left.tokens) & set(right.tokens))
            exact_match = bool(left.normalized and left.normalized == right.normalized)
            first_match = bool(left.tokens and right.tokens and left.tokens[0] == right.tokens[0])
            if not (exact_match or first_match or len(common) >= 2):
                continue
            seen_sense_pairs.add((a_index, b_index))
            result.sense_matches += 1
            if exact_match:
                evidence = f"exact: {left.normalized}"
            elif len(common) >= 2:
                evidence = "shared: " + " ".join(common[:4])
            else:
                evidence = f"first: {left.tokens[0]}"
            record_pair(result, left.word, right.word, evidence, a_lang, b_lang)
    return result


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--min", type=int, default=4, help="أدنى عدد شواهد يُطبع")
    ap.add_argument("--json", help="اكتب الحصيلة إلى ملف")
    ap.add_argument("--pair", default="aramaic:hebrew", help="لسانان مفصولان بنقطتين")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    a_lang, b_lang = args.pair.split(":")
    A, B = load(a_lang), load(b_lang)
    baseline = legacy_analysis(A, B, a_lang, b_lang)
    expanded = expanded_analysis(A, B, a_lang, b_lang)
    shared = set(A.legacy) & set(B.legacy)
    print(f"{a_lang}: {len(A.senses):,} صيغة-معنى على {len(A.legacy):,} معنًى قديمًا")
    print(f"{b_lang}: {len(B.senses):,} صيغة-معنى على {len(B.legacy):,} معنًى قديمًا")
    print(f"معانٍ مشتركة بالتطابق القديم: {len(shared):,}")
    print(f"قبل التوسيع، أزواجٌ صالحة تختلفُ في صامتٍ واحدٍ: {len(baseline.examined_pairs):,}")
    print(f"بعد التوسيع، أزواجٌ صالحة تختلفُ في صامتٍ واحدٍ: {len(expanded.examined_pairs):,}")
    print(f"الزيادة الصافية: {len(expanded.examined_pairs - baseline.examined_pairs):,}\n")

    corr = expanded.correspondences
    examined_pairs = expanded.examined_pairs

    rows = sorted(
        ((key, len(pair_map)) for key, pair_map in corr.items()),
        key=lambda item: (-item[1], item[0]),
    )
    print(f"أزواجٌ مستقلة تختلفُ في صامتٍ واحدٍ فقط: {len(examined_pairs):,}\n")
    print(f"{a_lang[:3]:>4} ~ {b_lang[:3]:<4} {'شواهد':>7}   أمثلة")
    print("-" * 74)
    shown = 0
    for (x, y), n in rows:
        if n < args.min:
            continue
        shown += 1
        ex = []
        for (wa, wb), glosses in list(corr[(x, y)].items())[:3]:
            gloss = sorted(glosses)[0]
            ex.append(f"{gloss[:18]} [{wa} ~ {wb}]")
        print(f"{x:>4} ~ {y:<4} {n:>7}   {' | '.join(ex)}")
    print(f"\nتقابلات بلغت العتبة ({args.min} شواهد): {shown} من {len(rows)}")

    if args.json:
        pathlib.Path(args.json).write_text(json.dumps(
            {"pair": args.pair,
             "matching": {
                 "before": "legacy exact normalized English gloss",
                 "after": "comma-trimmed exact or first semantic keyword or >=2 shared semantic tokens",
             },
             "before": {
                 "shared_exact_glosses": len(shared),
                 "sense_matches": baseline.sense_matches,
                 "pairs_examined": len(baseline.examined_pairs),
             },
             "after": {
                 "sense_matches": expanded.sense_matches,
                 "pairs_examined": len(examined_pairs),
                 "new_pairs": len(expanded.examined_pairs - baseline.examined_pairs),
             },
             "pairs_examined": len(examined_pairs),
             "correspondences": [
                 {
                     "a": x,
                     "b": y,
                     "witnesses": n,
                     "examples": [
                         {"a_word": wa, "b_word": wb, "glosses": sorted(glosses)}
                         for (wa, wb), glosses in list(corr[(x, y)].items())[:12]
                     ],
                 }
                 for (x, y), n in rows]},
            ensure_ascii=False, indent=1), encoding="utf-8")
        print(f"كُتبت الحصيلة: {args.json}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
