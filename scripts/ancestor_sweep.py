# -*- coding: utf-8 -*-
"""مسحُ الصورةِ المستعادةِ لا الكلمةِ الحيّة (2026-08-08، بتنبيهِ المؤلّف)

**تنبيهُ المؤلّف:** «الفارسيّةُ ربّما لها قواعدُ أخرى أو طريقٌ آخرُ لكشفِ الصلات،
وسِّعْ طريقةَ تفكيرِك، فليست كلُّ لغةٍ سلكَت الطريقَ نفسَه».

**وهو محقٌّ في موضعٍ دقيق.** المسحُ الصوتيُّ يقيسُ الكلمةَ كما هي اليومَ في الفرع،
وذلك يصلحُ لفرعٍ حفِظَ صوامتَه. أمّا الفروعُ الهندوأوربيّةُ فقد **فقدَت طبقةً
كاملةً من الصوامتِ اسمُها الحنجريّات**، ولم يبقَ منها في الكلمةِ الحيّةِ إلّا
تلوينُ الصائتِ الذي جاورَها. فالمقارنةُ بالكلمةِ الحيّةِ تُقارِنُ بما بعدَ الخسارة.

    نام   «اسم»   ← إيرانيّةٌ أمّ *Hnā́ma      ← الهيكل H-n-m
    چشم   «عين»   ← إيرانيّةٌ أمّ *čášma      ← هندوأوربيّةٌ *h₃ekʷ- «يرى»
    زبان  «لسان»  ← إيرانيّةٌ أمّ *hijwáH     ← الهيكل h-j-w-H

تولّدُ المروحةُ للحَنْجريّاتِ مرشّحاتٍ من الحروفِ العربيّةِ ء ه ح ع غ خ، لكنّ
هذا توليدٌ أداتيٌّ لا قولٌ بأنّ العربيّةَ حفظت تلك الحنجريّاتِ ولا دليلُ مقابلة.

**تحذيرٌ نافذٌ (2026-08-08):** قيلَ أوّلَ الأمرِ إنّ وقوعَ الحلقيِّ العربيِّ في موضعِ
الحنجريّةِ المستعادةِ شاهدٌ على الدعوى، **وهذا باطلٌ ولا يجوزُ أن يُبنى عليه شيء**.
فجدولُ `PROTO_FAN` أدناه هو الذي يقابِلُ h₂ بـ ح ع خ ه ولا يقابِلُها بغيرِها، فكلُّ
مرشَّحٍ يخرجُ منه يحملُ حلقيًّا هناك بالبناءِ لا بالكشف. وقد أُجريَ الضابطُ في
`scripts/guttural_decoy_test.py` بأذرعِ طُعمٍ مطابقةٍ في سعةِ الصيد، فكانَ الذراعُ
الحقُّ داخلَ مدى الطُّعمِ لا فوقَه (191 مقابلَ متوسّطٍ 171 ومدًى من 126 إلى 204).
**فالدعوى الطبقيّةُ ساقطةٌ**، ومحضرُها `05-audits/2026-08-08-laryngeal-claim-refuted-by-its-own-control.md`.

**وقيمةُ هذا المسحِ باقيةٌ في غيرِ ذلك:** أنّه يقارِنُ أقدمَ صورةٍ منشورةٍ بدلَ
الكلمةِ الحيّة، وهي قاعدةُ المؤلّفِ نفسُها مطبَّقةً على الذخيرةِ كلِّها.

**ولذلك يقرأُ هذا المسحُ ما يقولُه الفرعُ عن أصلِه**، لا ما يقولُه عن نفسِه اليوم:
يستخرجُ الصورةَ المستعادةَ من نصِّ الاشتقاقِ المنشور، ويُقابِلُها بمروحةٍ مبنيّةٍ
لرموزِ الاستعادةِ لا للحروفِ الحيّة.

**وهذا طريقٌ ثانٍ إلى جانبِ الأوّلِ لا بديلٌ عنه**، ونتائجُه تُحفَظُ على حِدَة.

الاستعمال:
    python scripts/ancestor_sweep.py --lang persian
    python scripts/ancestor_sweep.py --lang latin --min-overlap 1
"""
from __future__ import annotations

import argparse
import collections
import glob
import itertools
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402
import bulk_phonetic_sweep as B  # noqa: E402

OUT_DIR = ROOT / "04-cross-linguistic" / "exploration"

# طبقاتُ الأصلِ مرتَّبةً من الأقدمِ إلى الأحدث. الأقدمُ أثمنُ لأنّه أبعدُ عن الخسارة.
ANCESTORS = [
    ("Proto-Indo-European", 1), ("Proto-Indo-Iranian", 2), ("Proto-Iranian", 2),
    ("Proto-Iranic", 2), ("Proto-Germanic", 2), ("Proto-West Germanic", 3),
    ("Proto-Celtic", 2), ("Proto-Italic", 2), ("Proto-Hellenic", 2),
    ("Proto-Balto-Slavic", 2), ("Old Persian", 3), ("Avestan", 3),
    ("Middle Persian", 4), ("Parthian", 4), ("Sanskrit", 3),
    # **والساميّةُ مثلُ الهندوأوربيّةِ في هذا البابِ سواء.** الأكّاديّةُ فقدَت
    # الحلقيّاتِ كلَّها فلم يبقَ منها إلّا تلوينُ الصائت، والعبريّةُ دمجَت ح مع خ
    # وع مع غ، والاستعادةُ تردُّ ما فقدَ كلُّ فرعٍ منها. والعربيّةُ لم تفقِدْ منها شيئًا.
    ("Proto-Semitic", 1), ("Proto-West Semitic", 2),
    ("Proto-Northwest Semitic", 2), ("Proto-Central Semitic", 2),
    ("Proto-Afroasiatic", 1), ("Ugaritic", 3),
]

# الصورةُ المستعادةُ تُكتَبُ بنجمةٍ بعدَ اسمِ الطبقة: `from Proto-Iranian *čášma`
RX_STAR = re.compile(
    r"(" + "|".join(re.escape(a) for a, _ in ANCESTORS) + r")"
    r"[^*\n]{0,80}?\*\s*([^\s,;.)\]（【]{2,24})")
# وأحيانًا تُكتَبُ بين شرطتَينِ مائلتَينِ بلا نجمة: `(ʾwzwʾn' /⁠uzwān⁠/)`
RX_SLASH = re.compile(
    r"(" + "|".join(re.escape(a) for a, _ in ANCESTORS) + r")"
    r"[^\n]{0,90}?/⁠?([^/\n]{2,24}?)⁠?/")

# ------------------------------------------------------------------ المروحة
# تكتبُ الاستعادةُ الحنجريّاتِ h₁ h₂ h₃ وH للمجهولة. تُبقَى في الهيكل كي لا
# تُفقِدَ الصورةَ المنشورةَ صامتًا، لكنَّ بدائلَها العربيّةَ مولِّداتُ مرشحين لا
# قانونُ مقابلةٍ ولا دليلُ حكم. وقيمُها المستعادةُ في المدرسةِ القياسيّة:
#   h₁ سكتةٌ أو هاء     h₂ حلقيّةٌ خلفيّةٌ تُلوِّنُ الصائتَ ألفًا     h₃ مستديرةٌ تُلوِّنُه واوًا
PROTO_FAN: dict[str, tuple[str, ...]] = {
    "h₁": ("ء", "ه"), "h₂": ("ح", "ع", "خ", "ه"), "h₃": ("ع", "غ", "ه", "ء"),
    "H": ("ء", "ه", "ح", "ع", "غ", "خ"),
    # المهموسةُ والمجهورةُ والمنفوخة
    "bʰ": ("ب", "ف"), "dʰ": ("د", "ذ", "ض"), "gʰ": ("ج", "غ", "ق"),
    "ǵʰ": ("ج", "غ", "ز"), "gʷʰ": ("ج", "غ", "ق", "ب"),
    "kʷ": ("ك", "ق"), "gʷ": ("ج", "ق", "ب", "غ"),
    "ḱ": ("ك", "ق", "ش", "س"), "ǵ": ("ج", "ز", "ق", "غ"),
    # الأسنانيّةُ والصفيريّةُ في الهندوإيرانيّة
    "ć": ("ش", "س", "ص"), "ś": ("ش", "س"), "ṣ": ("ص", "س", "ش"),
    "č": ("ج", "ش", "ص", "ك"), "ǰ": ("ج", "ز"), "ź": ("ز", "ج", "ذ"),
    "ž": ("ز", "ج"), "š": ("ش", "س", "ث"), "ṭ": ("ط", "ت"), "ḍ": ("ض", "د"),
    "ṇ": ("ن",), "ṛ": ("ر", "ل"), "ḷ": ("ل", "ر"), "ṃ": ("م",),
    "ẓ": ("ظ", "ز"), "θ": ("ث", "ت"), "ð": ("ذ", "د"), "ɣ": ("غ", "ج"),
    "x": ("خ", "ك"), "ʿ": ("ع", "غ"), "ʾ": ("ء",),
    # حلقيّاتُ الاستعادةِ الساميّةِ ورموزُها. وهي في الأكّاديّةِ صفرٌ منطوق،
    # وفي العبريّةِ مدغَمةٌ في اثنَين، وفي العربيّةِ ستٌّ متمايزةٌ إلى اليوم.
    "ʔ": ("ء",), "ʕ": ("ع",), "ḥ": ("ح",), "ḫ": ("خ",), "ġ": ("غ",),
    "ɡ": ("ج", "غ", "ق"), "ḏ": ("ذ", "ز", "ض"),
    # والمُطبَقةُ الجانبيّةُ ṣ́ لم يحفظْها إلّا العربيّةُ ضادًا، وهي أشهرُ ما ضاعَ
    # من الفروعِ الساميّةِ كلِّها. وظاؤُها ṯ̣ مثلُها.
    "ṣ́": ("ض",), "ś": ("ش", "س"), "ṯ̣": ("ظ",), "ṱ": ("ظ", "ط"),
    "ṯ": ("ث", "ت"), "ẖ": ("خ", "ح"),
    # البسيطة
    "b": ("ب",), "p": ("ب", "ف"), "d": ("د", "ض", "ذ"), "t": ("ت", "ط", "ث"),
    "g": ("ج", "غ", "ق"), "k": ("ك", "ق"), "q": ("ق", "ك"),
    "s": ("س", "ص", "ش", "ز"), "z": ("ز", "ذ", "ص"), "f": ("ف", "ب"),
    "v": ("و", "ف", "ب"), "w": ("و",), "y": ("ي",), "j": ("ي", "ج"),
    "m": ("م",), "n": ("ن",), "l": ("ل", "ر"), "r": ("ر", "ل"),
    "h": ("ه", "ح", "خ"),
}
# رموزٌ من حرفَينِ فأكثرَ تُقرَأُ قبلَ الحرفِ المفرد
MULTI = tuple(sorted((k for k in PROTO_FAN if len(k) > 1), key=len, reverse=True))
PROTO_VOWELS = set("aeiouāēīōūáéíóúàèìòùâêîôûăĕĭŏŭəɐɛɔʊɪæœø")


def normalize_form(s: str) -> str:
    """يُنظَّفُ ما استُخرِجَ من نصِّ الاشتقاق: تُنزَعُ النجمةُ والشرطاتُ وعلاماتُ
    النبرِ وتبقى الرموزُ الصوتيّةُ المميِّزة."""
    s = unicodedata.normalize("NFC", str(s)).strip()
    s = s.strip("*-–—()[]{}'’ʼ,.;:")
    s = re.sub(r"[̀-̄̆-̣̱̌]", "", s)  # نبرٌ وطولٌ فقط
    return s.strip("*-").strip()


def proto_skeleton(form: str) -> list[str]:
    """الهيكلُ الصامتيُّ لصورةٍ مستعادة، والحنجريّةُ صامتٌ كاملٌ فيه لا حركة."""
    w = normalize_form(form)
    out, i = [], 0
    while i < len(w):
        for k in MULTI:
            if w[i:i + len(k)] == k:
                out.append(k)
                i += len(k)
                break
        else:
            c = w[i]
            if c in PROTO_FAN and c not in PROTO_VOWELS:
                out.append(c)
            i += 1
    return [c for i, c in enumerate(out) if i == 0 or c != out[i - 1]]


# **الحنجريّةُ المستعادةُ صفرٌ منطوقٌ في كلِّ فرعٍ حيٍّ بلا استثناء**، وهذا قولُ
# المدرسةِ القياسيّةِ نفسِها لا قولُنا: لاتينيّةُ pater ويونانيّةُ patḗr ليسَ فيهما
# أثرٌ صامتٌ لـ h₂ في `*ph₂tḗr`. فسقوطُها احتمالٌ قائمٌ يجبُ أن تفتحَه المروحةُ،
# وإلّا استحالَ أن يُقابَلَ هيكلٌ رباعيٌّ فيه حنجريّةٌ بجذرٍ عربيٍّ ثلاثيّ.
ZERO = ("",)


def proto_fan(form: str, limit: int = 600) -> list[str]:
    sk = proto_skeleton(form)
    if not (2 <= len(sk) <= 5):
        return []
    options = []
    for c in sk:
        opts = PROTO_FAN.get(c, ())
        if not opts:
            return []
        if c in {"h₁", "h₂", "h₃", "H"}:
            opts = tuple(opts) + ZERO
        options.append(opts)
    out, seen = [], set()
    for combo in itertools.islice(itertools.product(*options), limit * 3):
        w = "".join(combo)
        if 2 <= len(w) <= 5 and w not in seen:
            seen.add(w)
            out.append(w)
        if len(out) >= limit:
            break
    return out


def ancestors_of(etymology: str) -> list[tuple[str, str, int]]:
    """كلُّ ما ذكرَه الاشتقاقُ من صورٍ أقدم، بطبقتِها ورتبةِ قِدَمِها."""
    depth = dict(ANCESTORS)
    found: list[tuple[str, str, int]] = []
    seen = set()
    for rx in (RX_STAR, RX_SLASH):
        for m in rx.finditer(etymology or ""):
            layer, form = m.group(1), normalize_form(m.group(2))
            if not form or len(form) < 2 or (layer, form) in seen:
                continue
            if not re.search(r"[a-zʰʷ₁₂₃ḱǵćśčǰźžšθðɣʔʕḥḫġṣṯẖ]", form):
                continue
            # «شجرةُ الاشتقاق» في رأسِ المدخلِ تسردُ عقدًا ناقصةً مثل `*peh₂-?`،
            # وهي جذرٌ مجرَّدٌ لا صورةُ الكلمة. وأخذُها أضاعَ `*ph₂tḗr` في الأبِ كلِّه.
            if "?" in form:
                continue
            # `*-tḗr` لاحقةٌ لا كلمة، و`*peh₂-` جذرٌ مجرَّدٌ لا صورة. وقد قابلَت
            # الأداةُ `pater` باللاحقةِ وحدَها فقارنَت «ـتَر» بدلَ الكلمةِ كلِّها.
            if m.group(2).lstrip("*").startswith("-") or form.endswith("-"):
                continue
            seen.add((layer, form))
            found.append((layer, form, depth.get(layer, 4)))
    # الأعمقُ طبقةً أوّلًا، ثمّ الأتمُّ صوامتَ في الطبقةِ الواحدة. فالشجرةُ تسردُ
    # الجذرَ المجرَّدَ واللاحقةَ والصورةَ التامّةَ معًا، والتامّةُ هي المقصودة.
    found.sort(key=lambda x: (x[2], -len(proto_skeleton(x[1]))))
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--lang", default="persian")
    ap.add_argument("--min-overlap", type=int, default=1)
    ap.add_argument("--max-cands", type=int, default=16)
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("تحميلُ ذخيرةِ الجذورِ العربيّة...")
    ar = F.load_arabic_roots()
    head, gloss = B.load_bridge()
    print(f"جذورٌ: {len(ar):,} · جسرُ المعنى: {len(head):,}\n")

    rows = []
    for f in glob.glob(str(ROOT / "Resources" / args.lang / "*.jsonl")):
        with open(f, encoding="utf-8") as fh:
            for line in fh:
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ety = str(e.get("etymology_text") or "")
                if not ety:
                    continue
                glosses = [
                    str(g) for s in (e.get("senses") or [])[:4]
                    for g in (s.get("glosses") or [])[:2]
                ]
                if not glosses or not B.entry_is_lexical(str(e.get("word") or ""), glosses):
                    continue
                rows.append({"word": str(e.get("word") or ""), "glosses": glosses,
                             "etymology": ety})
    print(f"مداخلُ {args.lang} ذاتُ اشتقاقٍ مكتوب: {len(rows):,}\n")

    both, sound_only = [], []
    layers = collections.Counter()
    with_laryngeal = 0
    for r in rows:
        # **الصورةُ الأتمُّ هي المقابَلة، ولو اتّسعَت مروحتُها.** كانَ السقفُ يُسقِطُ
        # `*ph₂tḗr` لأنّها تفتحُ ستّينَ مرشَّحًا، فينزلُ المسحُ إلى اللاحقةِ `*tḗr`
        # فيقابِلُ «ـتَر» بدلَ الكلمة. والسقفُ ضابطُ ضجيجٍ لا يجوزُ أن يُبدِّلَ
        # المادّةَ المقارَنة، فإن ضاقَ عن الأتمِّ وُسِّعَ له ولم يُستبدَلْ بها غيرُها.
        for layer, form, depth in ancestors_of(r["etymology"])[:1]:
            sk = proto_skeleton(form)
            cands = proto_fan(form)
            if not cands:
                continue
            hits = [c for c in cands if c in ar]
            if not hits:
                continue
            # وسمٌ وصفيٌّ للطابور فقط؛ المروحةُ تفرضُ حلقيًّا عربيًّا في هذا
            # الموضع، فلا يكونُ توافقُ الموضعِ شاهدًا ولا يدخلُ الحكم.
            laryngeal = any(c in {"h₁", "h₂", "h₃", "H",
                                  "ʔ", "ʕ", "ḥ", "ḫ", "ġ", "ʿ", "ʾ"} for c in sk)
            branch_words = B.words_of(" ".join(r["glosses"]))
            scored = []
            for c in hits:
                direct = branch_words & head.get(c, set())
                near = (branch_words & gloss.get(c, set())) - direct
                scored.append((c, 3 * len(direct) + len(near),
                               sorted(direct)[:4] or sorted(near)[:3], bool(direct)))
            scored.sort(key=lambda x: (-x[1], len(x[0])))
            best = scored[0]
            row = {
                "branch": r["word"], "ancestor": form, "layer": layer, "depth": depth,
                "skeleton": "-".join(sk), "laryngeal": laryngeal,
                "gloss": "; ".join(r["glosses"][:2])[:90],
                "candidates_found": [c for c, _, _, _ in scored],
                "best": best[0], "overlap": best[1], "shared": best[2],
                "direct": best[3],
            }
            if best[1] >= args.min_overlap:
                both.append(row)
                layers[layer] += 1
                if laryngeal:
                    with_laryngeal += 1
            else:
                sound_only.append(row)
            break                      # أقدمُ طبقةٍ متاحةٍ تكفي، ولا تُكرَّرُ الكلمة

    # الحنجريّةُ أوّلًا بوصفها طابورَ صورٍ قديمةٍ ذاتِ معنى، لا بوصفها شاهدًا؛
    # ثمّ القِدَمُ، ثمّ الشهادةُ المباشرة.
    both.sort(key=lambda r: (not r["laryngeal"], not r["direct"], r["depth"], -r["overlap"]))

    direct = sum(1 for r in both if r["direct"])
    print(f"مطابقةُ صوتٍ ومعنًى في الصورةِ المستعادة: {len(both):,}"
          f"  (بشهادةٍ مباشرة: {direct:,})")
    print(f"منها ما فيه حنجريّةٌ مستعادة: {with_laryngeal:,}")
    print(f"مطابقةُ صوتٍ وحدَه: {len(sound_only):,}\n")
    print("طبقاتُ الأصلِ التي أعطَت:")
    for k, v in layers.most_common():
        print(f"   {k:26}{v:6}")

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    base = OUT_DIR / f"ancestor-sweep-{args.lang}"
    json.dump({"language": args.lang, "method": "reconstructed ancestor, not the living word",
               "with_laryngeal": with_laryngeal,
               "both": both, "sound_only": sound_only[:2000]},
              open(base.with_suffix(".json"), "w", encoding="utf-8"),
              ensure_ascii=False, indent=1)

    lines = [
        f"# مسحُ الصورةِ المستعادة: {args.lang}",
        "",
        "**الطبقة:** استكشاف. **لا حكمَ ولا عدَّ ولا نشر.**",
        "",
        "**الطريقة:** لا تُقارَنُ الكلمةُ الحيّةُ بل الصورةُ التي يقولُ الاشتقاقُ المنشورُ",
        "إنّها أصلُها، لأنّ الصورةَ الأقدمَ تحفظُ مادةً صوتيّةً لا تظهرُ في اللفظِ الحيّ.",
        "**وسمُ الحنجريّةِ طابورٌ وصفيٌّ فقط:** المروحةُ تفرضُ حلقيًّا عربيًّا في موضعِها،",
        "فلا يكونُ توافقُ الموضعِ دليلًا. تُحكَمُ الأزواجُ بالصورةِ والمعنى والإشعاع.",
        "",
        f"**مطابقة: {len(both):,}** · بشهادةٍ مباشرة: {direct:,} · **فيها حنجريّةٌ مستعادة: {with_laryngeal:,}**",
        "",
        "| الكلمةُ الحيّة | الصورةُ المستعادة | طبقتُها | الهيكل | معناها | العربيّ | التقاطع |",
        "|---|---|---|---|---|---|---|",
    ]
    for r in both[:500]:
        mark = " ⟵ حنجريّة" if r["laryngeal"] else ""
        lines.append(
            f"| `{r['branch']}` | `*{r['ancestor']}`{mark} | {r['layer']} | "
            f"{r['skeleton']} | {r['gloss']} | **{r['best']}** | "
            f"{'مباشر' if r['direct'] else 'قرينة'} {r['overlap']}: {' '.join(r['shared'])} |"
        )
    base.with_suffix(".md").write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nكُتب: {base.with_suffix('.md').relative_to(ROOT).as_posix()}")

    print("\nأقوى ما فيه حنجريّةٌ مستعادة:")
    for r in [x for x in both if x["laryngeal"]][:15]:
        print(f"   {r['branch'][:12]:14}*{r['ancestor'][:16]:18}{r['skeleton'][:12]:14}"
              f"{r['gloss'][:30]:32}~ {r['best']:7}[{' '.join(r['shared'][:3])}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
