# -*- coding: utf-8 -*-
"""المسحُ النوويُّ: وحدةُ المسحِ النواةُ الثنائيّةُ لا الجذر (2026-08-19)

**المرحلةُ ج من خطّةِ 2026-08-18، وهي بابُ توسعةٍ لا بابُ احتياط.** دستورُ
المشروعِ نفسُه يقول: الجذرُ الثلاثيُّ طورٌ متأخّرٌ يبقى حيثُ قرُبَ الفرعُ،
والنواةُ الثنائيّةُ أقدمُ فهي ما يبقى حينَ يبعُد. ومسحُنا الجاري وحدتُه
الجذرُ الكاملُ، فطبقةُ النواةِ تفوتُه **بالبناءِ** في الفروعِ البعيدةِ التي
هي موطنُها المتوقَّع. هذا المسحُ يفتحُ تلك الطبقة:

    كلمةُ الفرعِ ← لبُّها الصامتُ ← أزواجُه الثنائيّةُ عبرَ مراوحِ الحروفِ
    ← ما وقعَ منها في ديوانِ النوى الـ455 ← غربالُ المعنى بطريقَين

**وطريقا المعنى يُسجَّلانِ باسمَيهما ولا يُخلَطان:**
1. `bridge`: تقاطعُ كلماتِ شرحِ الفرعِ بكلماتِ النواةِ الإنجليزيّةِ من جسرِ
   ويكاموس (`data/en-ar-bridge.json`، root_head).
2. `event`: تقاطعُها بكلماتِ قراءةِ النواةِ المركَّبةِ الإنجليزيّةِ من ديوانِ
   النوى نفسِه حيثُ وُجِدَت، فالنظريّةُ (الحدثُ هو المعنى) هي الغربال.

**طبقةُ استكشافٍ محضة**: حوضُ مرشَّحينَ للقارئِ، لا حكمَ ولا عدَّ ولا نشرَ
رقمٍ منه. ولا سقوفَ صامتة: يُكتَبُ الحوضُ كلُّه بمجاميعِه.

الاستعمال:
    python scripts/build_nucleus_sweep.py --lang gothic
    python scripts/build_nucleus_sweep.py --lang old_irish --probe
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_any_script as F  # noqa: E402

OUT_DIR = ROOT / "04-cross-linguistic" / "exploration"
LEXICONS = ROOT / "data" / "branch-lexicons"

STOP = {
    "the", "a", "an", "of", "to", "or", "and", "in", "on", "for", "with",
    "from", "above", "below", "participle", "substantivized",
    "then", "clitic", "compound", "univerbation",
    "by", "at", "as", "is", "be", "was", "are", "it", "its", "one", "who",
    "that", "which", "used", "form", "type", "kind", "any", "some", "etc",
    "especially", "usually", "often", "made", "making", "person", "thing",
    "something", "someone", "act", "state", "quality", "manner", "way",
}


# **طبقةُ الأعلامِ تُعزَلُ ولا تُغرِبَل** (بعيّنةِ 2026-08-24): شرحُ العَلَمِ
# «a male given name» لا يحملُ معنًى للكلمةِ بل وصفًا لصنفِها، فتقاطعُ
# `given/male` تقاطعٌ فارغٌ يُدخِلُ عشراتِ الأعلامِ في حوضِ المعنى بلا معنى.
# والأعلامُ عندَنا طبقةٌ مستقلّةٌ بأمرِ الأوامرِ القائمةِ أصلًا.
RX_ONOMASTIC = re.compile(
    r"(given name|proper name|surname|a male name|a female name|"
    r"place name|toponym|patronymic|the name of)", re.I)


def words_of(text: str) -> set[str]:
    return {w for w in re.findall(r"[a-z]+", str(text).lower())
            if len(w) > 2 and w not in STOP}


def load_nuclei() -> dict[str, dict]:
    lv = json.load((ROOT / "data" / "juthoor-core-levels.json")
                   .open(encoding="utf-8"))["levels"]["level_2_binary_nuclei"]
    out = {}
    for e in lv["nuclei"]:
        en = words_of(" ".join(str(e.get(k, "")) for k in
                               ("composed_reading_en",)))
        out[e["nucleus"]] = {
            "reading_ar": e.get("jabal_lexicon_reading_ar")
                          or e.get("composed_reading_ar", ""),
            "event_en": en,
        }
    return out


def load_bridge() -> dict[str, set[str]]:
    b = json.load((ROOT / "data" / "en-ar-bridge.json").open(encoding="utf-8"))
    return {root: set(toks) for root, toks in b["root_head"].items()
            if len(re.sub(r"[^ء-ي]", "", root)) == 2}


def load_tri_roots() -> set[str]:
    """الجذورُ الثلاثيّةُ المشهودةُ في الجسرِ، لوسمِ «الجذرُ أوّلًا»."""
    b = json.load((ROOT / "data" / "en-ar-bridge.json").open(encoding="utf-8"))
    out = set()
    for root in b["root_head"]:
        bare = re.sub(r"[^\u0621-\u064a]", "", root)
        if len(bare) == 3:
            out.add(bare)
    return out


# **الجذعُ من تفكيكِ القاموسِ نفسِه لا من الحدس** (بمسبارِ المسارِ D في
# 2026-08-24): مدخلةُ ويكاموس تكتبُ تفكيكَها نصًّا `X + -suffix`، وفي القوطيّةِ
# وحدَها 1,884 مدخلةً من 3,711 تحملُه. وأوّلُ صفٍّ في المسبارِ كشفَ الثمنَ:
# `usbraidjan` هيكلُها `s-b-r-d-j-n`، فأخذَتِ الأداةُ طرفَيها `s-n` نواةً،
# والسينُ من سابقةِ `us-` والنونُ من لاحقةِ `-jan`، فكانت «نواةٌ» ليس فيها
# حرفٌ أصليٌّ واحد. وهو العطبُ التاسعُ بعينِه: الصرفُ يُحسَبُ أصلًا.
RX_DECOMP = re.compile(r"\(([a-zāēīōūþƕ\-]{2,})\)\s*\+\s*[^()]*\(-")
RX_PREFIXED = re.compile(r"\+\s*[^()]*\(([a-zāēīōūþƕ\-]{2,})\)")


# سوابقُ الجرمانيّةِ المطّردةُ، بحكمِ المؤلّفِ في gaainān (معايرةُ 2026-08-24):
# "no suffix or prefix... and without forms". تُنزَعُ نزعًا موسومًا كاللواحق.
# حرفا العلّةِ اللذانِ يُكتَبانِ في خانةِ المدِّ وسطَ الأجوفِ (qawama تُهيكَلُ
# q-w-m): بهما وحدَهما يجوزُ زوجُ الطرفَينِ، وما سواهما صامتٌ لا يُقفَزُ فوقَه
MADD_MIDDLE = {"w", "y"}

# الألسنُ التي نونُ مصدرِها صرفٌ محضٌ يُنزَعُ قبلَ حكمِ الجذرِ؛ أمّا
# الفارسيّةُ ونحوُها فنونُ آخرِها قد تكونُ أصلًا (saman) فلا تُحجَبُ صورتُها
GERMANIC_LANGS = {"gothic", "old_norse", "english_old", "english_middle"}

# علاماتُ النزعِ اليقينيِّ تُستمَدُّ من جدولِ اللواحقِ الموسومِ نفسِه
# (مسبارُ D الثاني عشر: النسخةُ اليدويّةُ الجزئيّةُ فاتَتها -on)، ومعها
# نزوعُ القاموسِ المسمّاةُ والسوابقُ فكلُّها صرفٌ منصوصٌ عليه
CERTAIN_SUFFIX_MARKS = tuple(
    why for end, why in F.OLD_ENGLISH_ENDINGS if end in F.CERTAIN_ENDINGS
) + ("بنزعِ اللاحقةِ المسمّاةِ",)
CERTAIN_PREFIX_MARKS = ("بنزعِ سابقتِه", "بنزعِ السابقةِ", "بنزعِ سابقةِ")


def strip_is_certain(label: str) -> bool:
    """هل آخرُ نزعٍ في هذه الصورةِ صرفٌ يقينيٌّ لا مطابقةٌ عارضة؟"""
    seg = label.split(" ثمّ ")[-1]
    return (any(m in seg for m in CERTAIN_SUFFIX_MARKS)
            or any(m in seg for m in CERTAIN_PREFIX_MARKS))

GERMANIC_PREFIXES = ("ufar", "faur", "mith", "and", "fra", "dis", "ga",
                     "us", "bi", "af", "at", "in", "un", "ur", "uf")


RX_PAREN = re.compile(r"\(([^()]{1,40})\)")
RX_ROMAN = re.compile(r"[A-Za-zÀ-ÿ\u0100-\u017f\u01dd\u0250-\u02af'-]+")


def _fold_roman(s: str) -> str:
    """طي علامات المد للمطابقة: -ān تطابق ذيل gaainan."""
    import unicodedata
    return "".join(c for c in unicodedata.normalize("NFD", s.lower())
                   if not unicodedata.combining(c))


def named_affixes(etym: str) -> tuple[list[str], list[str]]:
    """اللواصقُ التي يسمّيها نصُّ الاشتقاقِ في أيِّ صيغةٍ، ولو بلا علامةِ +:
    مدخلةُ fruma تكتبُ `Contains the comparative suffix -uma` نثرًا (عطبُ
    مسبارِ D السادسِ NUC-GOTHIC-00006). كلُّ قوسٍ رومنتُه تبدأُ بشرطةٍ
    لاحقةٌ مسمّاةٌ، وكلُّ قوسٍ تنتهي بها سابقةٌ مسمّاة."""
    pres, sufs = [], []
    if not etym:
        return pres, sufs
    for raw_tok in RX_PAREN.findall(etym):
        tok = raw_tok.split("/")[0].split(",")[0].strip().strip("*").strip()
        if not tok or not RX_ROMAN.fullmatch(tok):
            continue
        if tok.startswith("-") and len(tok) >= 2:
            sufs.append(tok.lstrip("-"))
        elif tok.endswith("-") and len(tok) >= 2:
            pres.append(tok.rstrip("-"))
    return pres, sufs


# ألفاظُ الصيغِ الصريحةُ وحدَها تجعلُ ما بعدَ of جذعًا؛ فالقرينُ الموازي
# (Doublet of) والنظيرُ (Cognate) ليسا تفكيكًا (مسبارُ D الخامسَ عشرَ:
# kintus أُقحِمَ فيها hund جذعًا من عبارةِ Doublet)
RX_FORMREF = re.compile(
    r"\b(?:forms?|participles?|plural|singular|genitive|dative|accusative"
    r"|nominative|vocative|diminutive|augmentative|inflections?"
    r"|conjugations?|declensions?|variants?|spellings?|romanizations?"
    r"|univerbations?|substantivi[sz]ed|comparatives?|superlatives?"
    r"|preterite|supine|gerund|infinitive|compounds?|roots?|stems?|bases?)"
    r"\s+of\s+[^()]*?\(([^()]{1,40})\)", re.I)


def decomp_parts(etym: str) -> tuple[list[str], bool]:
    """قطعُ تفكيكِ القاموسِ نصًّا: (الأجذاعُ، أوُجِدَ تفكيكٌ أصلًا).
    المعوَّلُ عليه الرومنةُ بينَ قوسَينِ حولَ علامةِ + كما تكتبُها المداخلُ
    فعلًا (مسبارُ المادّةِ 2026-08-25): السابقةُ تنتهي بشرطةٍ، واللاحقةُ
    تبدأُ بها، وما سواهما جذعٌ. والمحلّلُ القديمُ كانَ يمسكُ نمطَ
    `X + -suffix` وحدَه فيفوتُه `ga- + ains + -ān` الثلاثيُّ (عطبُ مسبارِ
    D الرابعِ في gaainān)."""
    if not etym:
        return [], False
    # صيغُ الإحالةِ تسمّي لمّتَها بينَ قوسَينِ بعدَ of (مسبارُ D التاسعُ
    # NUC-GOTHIC-00017: nasjands اسمُ فاعلِ nasjan فاللمّةُ جذعُها)
    ref_stems = []
    for raw_ref in RX_FORMREF.findall(etym):
        tok = raw_ref.split("/")[0].split(",")[0].strip().strip("*").strip()
        if (tok and RX_ROMAN.fullmatch(tok) and len(tok) >= 3
                and not tok.startswith("-") and not tok.endswith("-")):
            ref_stems.append(tok)
    if "+" not in etym:
        return ref_stems, bool(ref_stems)
    clause = next((s for s in re.split(r"[.;]", etym) if "+" in s), "")
    toks = []
    for raw_tok in RX_PAREN.findall(clause):
        # القوسُ قد يحملُ شرحًا بعدَ فاصلةٍ: `(ains, "one")` رومنتُها ains
        tok = raw_tok.split("/")[0].split(",")[0].strip().strip("*").strip()
        if tok and RX_ROMAN.fullmatch(tok):
            toks.append(tok)
    if not toks:
        return [], False
    stems = [tok for tok in toks
             if not tok.startswith("-") and not tok.endswith("-")
             and len(tok) >= 3]
    for r in ref_stems:
        if r not in stems:
            stems.append(r)
    return stems, True


def stem_from_etym(etym: str) -> str:
    """أوّلُ جذعٍ يسمّيه التفكيكُ (واجهةٌ قديمةٌ باقية، والقديمُ جزءٌ من الجديد)."""
    stems, _ = decomp_parts(etym)
    return stems[0] if stems else ""


def skeleton_variants(text: str, script: str,
                      etym: str = "") -> tuple[list[tuple[list[str], str, str]], bool]:
    """صورُ الهيكلِ الموسومةُ موحَّدةً للنوى والجذورِ معًا (مسبارُ D الرابع).
    الترتيبُ حكمٌ: جذعُ التفكيكِ أوّلًا فهو نصُّ القاموسِ، ثمّ نزعُ السابقةِ،
    ثمّ نزعُ اللواحقِ، والخامُ آخرًا كي لا يتصدّرَ المركَّبُ نسبةَ المرشَّح."""
    out: list[tuple[list[str], str, str]] = []
    stems, has_decomp = decomp_parts(etym)
    pres, sufs = named_affixes(etym)
    has_decomp = has_decomp or bool(pres) or bool(sufs)
    low_f = _fold_roman(text.strip())
    def _push_with_compose(rem: str, label: str, tier: str) -> None:
        """البقيّةُ بعدَ نزعٍ، ومعها صورُها منزوعةَ اللواحقِ التصريفيّةِ
        (مسبارُ D السابعُ NUC-GOTHIC-00008: afmaitan بعدَ af- بقيَت maitan
        بنونِ مصدرِها فوُسِمَت جذرًا من نونِ الصرف)."""
        sk = F.skeleton(rem, script)
        if sk:
            out.append((sk, label, tier))
        if script in {"latin", "germanic"}:
            for ssk, slab in F.oe_skeletons(rem, script):
                if ssk and ssk != sk:
                    out.append((ssk, f"{label} ثمّ {slab}", tier))
            # والسابقةُ الاصطلاحيّةُ تُنزَعُ من البقيّةِ أيضًا: usdaudōza
            # بعدَ نزعِ -ōza بقيَت usdaud فورثَت مروحةُ شدد سينَ us-
            # (مسبارُ D الثالثَ عشرَ NUC-GOTHIC-00046)
            for pre2 in GERMANIC_PREFIXES:
                pf2 = _fold_roman(pre2)
                if rem.startswith(pf2) and len(rem) - len(pf2) >= 2:
                    sk3 = F.skeleton(rem[len(pf2):], script)
                    if sk3 and sk3 != sk:
                        out.append((sk3,
                                    f"{label} ثمّ بنزعِ سابقةِ `{pre2}-`",
                                    tier))
                    break
            for suf2 in sufs:
                sf2 = _fold_roman(suf2)
                if rem.endswith(sf2) and len(rem) - len(sf2) >= 2:
                    sk4 = F.skeleton(rem[: len(rem) - len(sf2)], script)
                    if sk4 and sk4 != sk:
                        out.append(
                            (sk4,
                             f"{label} ثمّ بنزعِ اللاحقةِ المسمّاةِ `-{suf2}`",
                             tier))

    for suf in sufs:
        sf = _fold_roman(suf)
        if low_f.endswith(sf) and len(low_f) - len(sf) >= 2:
            _push_with_compose(low_f[: len(low_f) - len(sf)],
                               f"بنزعِ اللاحقةِ المسمّاةِ `-{suf}`", "named")
    for pre in pres:
        pf = _fold_roman(pre)
        if low_f.startswith(pf) and len(low_f) - len(pf) >= 2:
            _push_with_compose(low_f[len(pf):],
                               f"بنزعِ السابقةِ المسمّاةِ `{pre}-`", "named")
            # والنزعانِ معًا حيثُ سمّى النصُّ الطرفَين (مسبارُ D العاشرُ
            # NUC-GOTHIC-00018: gaskadweins لا تلدُ skadw إلّا بهما معًا)
            for suf in sufs:
                sf = _fold_roman(suf)
                if (low_f.endswith(sf)
                        and len(low_f) - len(pf) - len(sf) >= 2):
                    _push_with_compose(
                        low_f[len(pf): len(low_f) - len(sf)],
                        f"بنزعِ السابقةِ المسمّاةِ `{pre}-` ثمّ "
                        f"بنزعِ اللاحقةِ المسمّاةِ `-{suf}`",
                        "named")
    for st in stems:
        if _fold_roman(st) == low_f:
            continue
        sk = F.skeleton(st, script)
        if sk:
            out.append((sk, f"جذعُ القاموسِ `{st}`", "stem"))
        # والجذعُ نفسُه قد يحملُ لاحقةَ تصريفٍ (braidjan جذعُها braid)
        if script in {"latin", "germanic"}:
            for ssk, slab in F.oe_skeletons(st, script):
                if ssk and ssk != sk:
                    out.append((ssk, f"جذعُ القاموسِ `{st}` ثمّ {slab}", "stem"))
            low_st0 = _fold_roman(st)
            for suf2 in sufs:
                sf2 = _fold_roman(suf2)
                if low_st0.endswith(sf2) and len(low_st0) - len(sf2) >= 2:
                    sk4 = F.skeleton(low_st0[: len(low_st0) - len(sf2)],
                                     script)
                    if sk4 and sk4 != sk:
                        out.append(
                            (sk4,
                             f"جذعُ القاموسِ `{st}` ثمّ بنزعِ اللاحقةِ "
                             f"المسمّاةِ `-{suf2}`",
                             "stem"))
            # وقد يحملُ سابقةً مطّردةً فوقَ لاحقتِه (gaskadwjan جذعُها
            # skadw بنزعِ ga- ثمّ -jan؛ مسبارُ D العاشر)
            low_st = _fold_roman(st)
            for pre in GERMANIC_PREFIXES:
                if low_st.startswith(pre) and len(low_st) - len(pre) >= 3:
                    rem2 = low_st[len(pre):]
                    sk2 = F.skeleton(rem2, script)
                    base_lab = f"جذعُ القاموسِ `{st}` بنزعِ سابقتِه `{pre}-`"
                    if sk2:
                        out.append((sk2, base_lab, "stem"))
                    for ssk, slab in F.oe_skeletons(rem2, script):
                        if ssk and ssk != sk2:
                            out.append((ssk, f"{base_lab} ثمّ {slab}", "stem"))
                    break
    if script in {"latin", "germanic"}:
        # السطحُ يُطوى قبلَ النزعِ وإلّا بقيَت المدّةُ تمنعُ مطابقةَ اللاحقةِ
        # (ushulōn بقيَت hulōn فلم يولَدِ ابنُ -on الحاجبُ؛ مسبارُ D الثاني عشر)
        low = _fold_roman(text.strip())
        for pre in GERMANIC_PREFIXES:
            if low.startswith(pre) and len(low) - len(pre) >= 3:
                rem = low[len(pre):]
                sk = F.skeleton(rem, script)
                if sk:
                    out.append((sk, f"بنزعِ سابقةِ `{pre}-`", "prefix"))
                    for ssk, slab in F.oe_skeletons(rem, script):
                        if ssk and ssk != sk:
                            out.append((ssk,
                                        f"بنزعِ سابقةِ `{pre}-` ثمّ {slab}",
                                        "prefix"))
                    for suf2 in sufs:
                        sf2 = _fold_roman(suf2)
                        if rem.endswith(sf2) and len(rem) - len(sf2) >= 2:
                            sk4 = F.skeleton(rem[: len(rem) - len(sf2)],
                                             script)
                            if sk4 and sk4 != sk:
                                out.append(
                                    (sk4,
                                     f"بنزعِ سابقةِ `{pre}-` ثمّ بنزعِ "
                                     f"اللاحقةِ المسمّاةِ `-{suf2}`",
                                     "prefix"))
                break
        for sk, lab in F.oe_skeletons(text, script):
            out.append((sk, lab, "suffix"))
        for sk, lab in F.latin_stem_skeletons(text, script):
            out.append((sk, lab, "suffix"))
    base = F.skeleton(text, script)
    if base:
        out.append((base, "كما وردَت", "raw"))
    return out, has_decomp


def candidate_nuclei(word: str, script: str, table: dict,
                     etym: str = "") -> dict[str, str]:
    """أزواجُ النواةِ المرشَّحةُ من هياكلِ الكلمةِ كلِّها، بوسمِ مصدرِ كلٍّ."""
    sk_variants, _ = skeleton_variants(word, script, etym)
    out: dict[str, str] = {}
    for sk, label, _tier in sk_variants:
        cons = [c for c in sk]
        pairs = []
        if len(cons) == 2:
            pairs.append((cons[0], cons[1], "الهيكلُ نفسُه"))
        for i in range(len(cons) - 1):
            pairs.append((cons[i], cons[i + 1], f"الزوجُ المتجاورُ {i+1}"))
        # **الطرفانِ حيثُ الوسطُ خانةُ مدٍّ مكتوبةٌ حصرًا**: نصُّ التعديلِ 1
        # الأجوفُ C1+مدّ+C2، فالوسطُ حرفُ علّةٍ (w/y) لا صامتٌ قويّ. ومسبارُ
        # D الخامسُ (NUC-GOTHIC-00005) أمسكَ الأداةَ تأخذُ طرفَي g-q-m وكأنّ
        # القافَ خانةُ مدٍّ، فتصنعُ مرشَّحًا يقفزُ فوقَ صامتٍ أصليٍّ ظاهر.
        if len(cons) == 3 and cons[1] in MADD_MIDDLE:
            pairs.append((cons[0], cons[-1],
                          f"الطرفانِ (الوسطُ {cons[1]} خانةُ مدٍّ، قاعدةُ التعديل 1)"))
        for a, b, why in pairs:
            for ar1 in table.get(a, ()):
                for ar2 in table.get(b, ()):
                    nuc = ar1 + ar2
                    if nuc not in out:
                        out[nuc] = f"{label}؛ {why}"
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", required=True)
    ap.add_argument("--probe", action="store_true",
                    help="اطبع عيّنةً ولا تكتبْ ملفًّا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    nuclei = load_nuclei()
    bridge = load_bridge()
    tri_roots = load_tri_roots()
    # أسماءُ ملفّاتِ الفهارسِ بشرطةٍ عاديّةٍ (old-norse) وأسماءُ المسوحِ
    # بشرطةٍ سفليّةٍ (old_norse)، وخمسةُ ألسنٍ سقطَت بهذا الخلافِ أوّلَ تشغيل
    stem = args.lang.replace("_", "-")
    stem = {"ancient-greek": "ancient-greek", "english-middle": "middle-english",
            "english-old": "old-english"}.get(stem, stem)
    lex = json.load((LEXICONS / f"{stem}.json").open(encoding="utf-8"))
    script = "latin"
    table = F.FANS[script]

    both, sound_only = [], []
    for e in lex["entries"]:
        word, gloss = e.get("word", ""), e.get("en", "")
        if not word or not gloss:
            continue
        if RX_ONOMASTIC.search(gloss):
            continue
        # القوطيّةُ وأخواتُها بخطِّها الأصليِّ في `word` ورومنتُها في `read`،
        # والهيكلُ اللاتينيُّ يعودُ من الخطِّ الأصليِّ فارغًا فيموتُ المسحُ صفرًا
        text = word if F.skeleton(word, script) else e.get("read", "")
        if not text:
            continue
        etym_eff = str(e.get("etym", ""))
        # بعضُ المداخلِ تكتبُ تفكيكَها في حقلِ المعنى لا الاشتقاقِ
        # (dizuhþansat: `Compound of X (dissat)+ ... (-uh)+ ...`؛ مسبارُ
        # D الثالثَ عشرَ)، فتُطعَمُ عبارتُه للمحلّلِ نفسِه
        if "ompound of" in gloss or "niverbation of" in gloss:
            etym_eff = (etym_eff + " . " + gloss.split(":")[0]).strip(" .")
        cands = candidate_nuclei(text, script, table, etym_eff)
        hits = {n: how for n, how in cands.items() if n in nuclei}
        if not hits:
            continue
        # الأقواسُ الشرحيّةُ الصرفيّةُ والمعقوفاتُ التحليليّةُ وعبارةُ
        # التركيبِ قبلَ النقطتَينِ ليست معنًى فلا تدخلُ طريقَ الدلالةِ
        # (from من قوسِ nasjands، وthen من ترجمةِ dizuhþansat التحليليّة)
        g_src = gloss
        if "ompound of" in g_src or "niverbation of" in g_src:
            g_src = g_src.split(":", 1)[-1]
        g_src = re.sub(r"\[[^\]]*\]", " ", g_src)
        gtoks = words_of(re.sub(r"\([^()]*\)", " ", g_src))
        best = None
        for n, how in hits.items():
            via = []
            shared_b = gtoks & bridge.get(n, set())
            shared_e = gtoks & nuclei[n]["event_en"]
            if shared_b:
                via.append(("bridge", sorted(shared_b)[:4]))
            if shared_e:
                via.append(("event", sorted(shared_e)[:4]))
            if via and (best is None or len(via) > len(best[2])):
                best = (n, how, via)
        row = {
            "branch": word, "read": e.get("read", ""), "gloss": gloss[:120],
            "nuclei_found": sorted(hits),
        }
        # **الجذرُ أوّلًا حيثُ الهيكلُ ثلاثيٌّ** (معايرةُ المؤلّفِ 2026-08-24:
        # dragan بابُها درج لا ذر، وcride بابُها كرد/قرد/قرط لا رض): يُكتَبُ
        # الوسمُ ومروحةُ الثلاثيِّ المشهودةُ في الصفِّ نفسِه ليقرأَها القارئُ
        # قبلَ النزولِ إلى النواة.
        # الصورُ الموحَّدةُ نفسُها التي قرأَت النوى تقرأُ الجذورَ (مسبارُ D
        # الرابع)، والخامُ محجوبٌ حيثُ فكّكَ القاموسُ الكلمةَ نصًّا: gaainān
        # خامُها g-n-n فوُسِمَت جنن/قنن اختلاقًا وكلُّها ترثُ صامتَ ga-
        variants, has_decomp = skeleton_variants(text, script, etym_eff)
        # في الألسنِ الجرمانيّةِ الصورةُ التي لها ابنٌ منزوعُ اللاحقةِ
        # التصريفيّةِ لا تحكمُ الجذرَ بنفسِها؛ ابنُها المنزوعُ ينوبُ عنها
        # (maitan لا تلدُ متن من نونِ مصدرِها). ونونُ الفارسيّةِ أصلٌ فتبقى.
        v_labels = [v[1] for v in variants]
        # صورُ نزعِ الخامِ (طبقةُ suffix) أبناءُ «كما وردَت» وإن لم يحملْ
        # وسمُها اسمَ الأبِ، فيُحسَبانِ أسرةً واحدةً (درسُ daufs: الخامُ
        # d-f-s كانَ يفلتُ من حاجبِ ابنِه d-f المنزوعِ سينَ الرفع)
        # أسرةُ الجذعِ الواحدِ تجمعُ صورَ نزعِ سابقتِه أيضًا (درسُ ganauha:
        # جذعُ ganauhan وصورتُه بنزعِ ga- أسرةٌ واحدةٌ يحجبُ منزوعُها أباها)
        v_fams = [(l.split(" ثمّ ")[0] if " ثمّ " in l
                   else ("كما وردَت" if v[2] in {"raw", "suffix"} else l)
                   ).split(" بنزعِ سابقتِه")[0]
                  for l, v in zip(v_labels, variants)]
        v_keys = ["".join(v[0]) for v in variants]
        def _has_stripped_child(i: int) -> bool:
            """الصورةُ محجوبةٌ عن حكمِ الجذرِ في الجرمانيّةِ إن كانَ لها ابنٌ
            منزوعٌ، أو أختٌ في أسرتِها أعمقُ نزعًا هيكلُها بادئةٌ حقيقيّةٌ من
            هيكلِها (مسبارُ D الثامنُ NUC-GOTHIC-00010: إسقاطُ -an وحدَها من
            daubnan يتركُ نونَ لاحقةِ -nan في المروحةِ، والنزعُ الأعمقُ
            d-b ينوبُ عن d-b-n)."""
            if args.lang not in GERMANIC_LANGS:
                return False
            if any(l.startswith(v_labels[i] + " ثمّ")
                   and strip_is_certain(l)
                   for l in v_labels):
                return True
            # الحجبُ بالأختِ الأعمقِ بنفسِ قيدِ اليقينِ الموحَّدِ، والخاتمةُ
            # كالبادئةِ (نزعُ السابقةِ يجعلُ الابنَ خاتمةَ أبيه؛ درسُ ganauha)
            return any(j != i and v_fams[j] == v_fams[i]
                       and len(v_keys[j]) < len(v_keys[i])
                       and (v_keys[i].startswith(v_keys[j])
                            or v_keys[i].endswith(v_keys[j]))
                       and strip_is_certain(v_labels[j])
                       for j in range(len(variants)))
        for vi, (tsk, vlabel, tier) in enumerate(variants):
            if has_decomp and tier not in {"stem", "named", "prefix"}:
                continue
            if _has_stripped_child(vi):
                continue
            if len(tsk) != 3:
                continue
            tri = sorted({a + b + c
                          for a in table.get(tsk[0], ())
                          for b in table.get(tsk[1], ())
                          for c in table.get(tsk[2], ())} & tri_roots)
            if tri:
                row["root_first"] = True
                row["root_fan"] = tri[:12]
                row["root_fan_from"] = vlabel
                break
        if best:
            n, how, via = best
            n_shared = sum(len(s) for _, s in via)
            row.update({
                "best_nucleus": n, "how": how,
                "reading_ar": nuclei[n]["reading_ar"][:100],
                "via": [{"path": p, "shared": s} for p, s in via],
                # قوّةُ الدلالةِ تُكتَبُ ولا تُخفى: طريقانِ أقوى من طريق،
                # وتقاطعُ كلمةٍ واحدةٍ أضعفُ ما يُعرَض، فيُقرَأُ الأقوى أوّلًا
                "strength": ((30 if len(via) == 2 else
                              20 if via[0][0] == "event" else 10)
                             + min(n_shared, 9)),
            })
            both.append(row)
        else:
            sound_only.append(row)

    both.sort(key=lambda r: -r.get("strength", 0))
    print(f"{args.lang}: نواةٌ بصوتٍ ومعنًى: {len(both):,} · "
          f"نواةٌ بصوتٍ فقط: {len(sound_only):,}")
    if args.probe:
        for r in both[:10]:
            via = "؛ ".join(f"{v['path']}:{','.join(v['shared'][:3])}"
                            for v in r["via"])
            print(f"  {r['branch']:14} «{r['gloss'][:34]:34}» ~ "
                  f"{r['best_nucleus']} ({r['reading_ar'][:30]}) [{via}]")
        return 0

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    out = OUT_DIR / f"nucleus-sweep-{args.lang}.json"
    out.write_text(json.dumps({
        "language": args.lang,
        "layer": "استكشاف؛ حوضُ مرشَّحي نواةٍ للقارئ، لا حكمَ ولا عدّ",
        "note": "وحدةُ المسحِ النواةُ الثنائيّة؛ طريقا المعنى bridge/event "
                "موسومانِ ولا يُخلَطان؛ لا سقوفَ صامتة",
        "both_total": len(both), "sound_only_total": len(sound_only),
        "both": both, "sound_only": sound_only,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")
    print(f"كُتب: {out.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
