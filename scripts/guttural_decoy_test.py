# -*- coding: utf-8 -*-
"""ضابطُ الطُّعمِ لدعوى الحلقيّ (2026-08-08)

**فخٌّ في استدلالي وجبَ كشفُه قبلَ أن يُبنى عليه رقم.** قلتُ إنّ الحلقيَّ العربيَّ
يقعُ في موضعِ الحنجريّةِ المستعادةِ بالضبط، وذلك **صحيحٌ ولكنّه لا يُثبِتُ شيئًا
بنفسِه**، لأنّ مروحتَنا هي التي تُقابِلُ h₂ بـ ح ع خ ه ولا تُقابِلُها بغيرِها. فكلُّ
مرشَّحٍ تُخرِجُه المروحةُ يحملُ حلقيًّا في ذلك الموضعِ بالبناءِ لا بالكشف. ومقياسٌ
لا يُمكِنُ أن يُخفِقَ لا يُثبِت.

**والسؤالُ الذي يُختبَرُ فعلًا:** إذا اشترطنا حلقيًّا في ذلك الموضع، هل نجدُ جذرًا
عربيًّا **موجودًا في المعاجم** ويوافقُ المعنى، **أكثرَ ممّا نجدُ لو اشترطنا هناك
صامتًا آخرَ لا حلقيّ**؟ فإن تساوى الطرفانِ فالدعوى لا شيء، وإن رجحَ الحلقيُّ
رجحانًا بيّنًا فذلك شاهدٌ يقبلُ التكذيب.

**فالضابط:** ذراعانِ يبحثانِ في المعجمِ نفسِه بعرضِ مروحةٍ واحدٍ، ولا يفترقانِ إلّا
في موضعٍ واحد:

    الذراعُ الحقّ    h₂ ← ح ع خ ه      (الحلقيّاتُ التي تقولُها المدرسةُ القياسيّة)
    ذراعُ الطُّعم    h₂ ← ب ت ك ن      (صوامتُ لا حلقَ فيها، بالعددِ نفسِه)

وتُجرَّبُ ثلاثُ مجموعاتِ طُعمٍ لا واحدةً، حتى لا تكونَ النتيجةُ حظَّ مجموعةٍ بعينِها.
ولا عشوائيّةَ في الاختيار، فالنتيجةُ يجبُ أن تُعادَ حرفًا بحرفٍ عندَ كلِّ تشغيل.

الاستعمال:
    python scripts/guttural_decoy_test.py
    python scripts/guttural_decoy_test.py --check
"""
from __future__ import annotations

import argparse
import glob
import itertools
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402
import bulk_phonetic_sweep as B  # noqa: E402
import ancestor_sweep as A  # noqa: E402

SWEEPS = ROOT / "04-cross-linguistic" / "exploration"
OUT = ROOT / "data" / "guttural-decoy-test.json"

GUTTURAL = set("ءهحعغخ")
PROTO_GUTTURAL = {"h₁", "h₂", "h₃", "H", "ʔ", "ʕ", "ḥ", "ḫ", "ġ", "ʿ", "ʾ"}

# **الطُّعمُ يجبُ أن يُطابِقَ الحقَّ في سعةِ الصيد، لا أن يُقابِلَه بأيِّ حروف.**
# جرَّبتُ أوّلًا مجموعاتٍ مختارةً باليدِ فكانت إحداها (ك ل ر د) تغطّي 91% من معجمِ
# الجذورِ والحلقيّاتُ تغطّي 48%، فكانَ للطُّعمِ ضِعفُ فرصةِ الحقِّ في إصابةِ جذرٍ
# موجودٍ أصلًا، وذلك ضابطٌ مائلٌ ضدَّ الدعوى لا محايد.
#
# فالمجموعاتُ الآنَ تُنتقى بالحساب: تُقاسُ تغطيةُ الحلقيّاتِ في معجمِ الجذور، ثمّ
# يُبحَثُ عن مجموعاتٍ لا حلقَ فيها تغطّي القدرَ نفسَه، فلا يفترقُ الذراعانِ في سعةِ
# الصيدِ بل في طبيعةِ الحرفِ وحدَها.
GUTTURAL_FAN_SET = ("ح", "ع", "خ", "ه")
NON_GUTTURAL = "بتثجدذرزسشصضطظفقكلمنوي"
N_DECOYS = 4


def coverage(letters, roots) -> float:
    """نسبةُ جذورِ المعجمِ التي فيها حرفٌ من المجموعة، وهي سعةُ صيدِ الذراع."""
    s = set(letters)
    return sum(1 for r in roots if s & set(r)) / max(len(roots), 1)


def matched_decoys(roots) -> list[tuple[str, tuple[str, ...]]]:
    """مجموعاتُ طُعمٍ لا حلقَ فيها، تغطّي من المعجمِ ما تغطّيه الحلقيّاتُ نفسَه."""
    import itertools as _it
    target = coverage(GUTTURAL_FAN_SET, roots)
    scored = []
    for combo in _it.combinations(NON_GUTTURAL, len(GUTTURAL_FAN_SET)):
        c = coverage(combo, roots)
        scored.append((abs(c - target), c, combo))
    scored.sort()
    out, used = [], set()
    for _, c, combo in scored:
        if used & set(combo):          # لا تتشارك المجموعاتُ حرفًا فتتشابه
            continue
        used |= set(combo)
        out.append((f"تغطية {c * 100:.1f}%", combo))
        if len(out) >= N_DECOYS:
            break
    return out, target


def arm_fan(skeleton: list[str], replacement: tuple[str, ...] | None,
            limit: int = 400) -> list[str]:
    """مروحةُ الصورةِ المستعادة. فإن أُعطِيَ بديلٌ استُبدِلَ به كلُّ موضعِ حلقيٍّ
    وبقيَ ما سواه على حالِه، فلا يفترقُ الذراعانِ إلّا في ذلك الموضع."""
    options = []
    for c in skeleton:
        if c in PROTO_GUTTURAL:
            options.append(replacement if replacement is not None else A.PROTO_FAN.get(c, ()))
        else:
            options.append(A.PROTO_FAN.get(c, ()))
    if any(not o for o in options):
        return []
    return ["".join(x) for x in itertools.islice(itertools.product(*options), limit)]


def best_overlap(cands, ar, head, gloss, branch_words):
    """أقوى مرشَّحٍ موجودٍ في المعاجم، وهل شهادتُه مباشرة."""
    hits = [c for c in cands if c in ar]
    if not hits:
        return None
    best = None
    for c in hits:
        direct = branch_words & head.get(c, set())
        near = (branch_words & gloss.get(c, set())) - direct
        score = 3 * len(direct) + len(near)
        if best is None or score > best[1]:
            best = (c, score, bool(direct))
    return best


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.check:
        if not OUT.exists():
            print("MISSING: data/guttural-decoy-test.json")
            return 1
        d = json.loads(OUT.read_text(encoding="utf-8"))
        r = d["result"]
        print(f"CLEAN: ضابطُ الطُّعم {r['rows']} صفًّا، "
              f"الحقُّ {r['real_direct']} والطُّعمُ {r['decoy_direct_mean']:.1f}")
        return 0

    print("تحميلُ الجذورِ وجسرِ المعنى...")
    ar = F.load_arabic_roots()
    head, gloss = B.load_bridge()
    print(f"جذورٌ: {len(ar):,} · جسر: {len(head):,}")
    DECOYS, target = matched_decoys(list(ar))
    print(f"تغطيةُ الحلقيّاتِ {' '.join(GUTTURAL_FAN_SET)}: {target * 100:.1f}% من المعجم")
    print("مجموعاتُ الطُّعمِ المطابِقةُ لها في سعةِ الصيد:")
    for name, rep in DECOYS:
        print(f"   {' '.join(rep):12} {name}")
    print()

    rows = []
    for f in sorted(glob.glob(str(SWEEPS / "ancestor-sweep-*.json"))):
        d = json.loads(pathlib.Path(f).read_text(encoding="utf-8"))
        lang = d.get("language", pathlib.Path(f).stem)
        for r in d["both"] + d.get("sound_only", []):
            if not r.get("laryngeal"):
                continue
            rows.append((lang, r))
    print(f"صفوفٌ فيها حلقيٌّ مستعاد: {len(rows):,}\n")

    real_found = real_direct = 0
    decoy_found = [0] * len(DECOYS)
    decoy_direct = [0] * len(DECOYS)
    examples = []

    for lang, r in rows:
        sk = r["skeleton"].split("-")
        branch_words = B.words_of(r.get("gloss", ""))
        if not branch_words:
            continue

        real = best_overlap(arm_fan(sk, None), ar, head, gloss, branch_words)
        if real:
            real_found += 1
            if real[2]:
                real_direct += 1
                if len(examples) < 30:
                    examples.append({
                        "language": lang, "branch": r["branch"],
                        "ancestor": r["ancestor"], "skeleton": r["skeleton"],
                        "arabic": real[0], "gloss": r.get("gloss", "")[:70],
                    })
        for i, (_, rep) in enumerate(DECOYS):
            dec = best_overlap(arm_fan(sk, rep), ar, head, gloss, branch_words)
            if dec:
                decoy_found[i] += 1
                if dec[2]:
                    decoy_direct[i] += 1

    n = len(rows)
    dfm = sum(decoy_found) / len(DECOYS)
    ddm = sum(decoy_direct) / len(DECOYS)

    print(f"{'':34}{'وجدَ جذرًا':>12}{'بشهادةٍ مباشرة':>16}")
    print(f"{'الذراعُ الحقُّ (حلقيّ)':34}{real_found:>12}{real_direct:>16}")
    for i, (name, rep) in enumerate(DECOYS):
        print(f"{'طُعم: ' + name:34}{decoy_found[i]:>12}{decoy_direct[i]:>16}"
              f"   [{' '.join(rep)}]")
    print(f"{'متوسّطُ الطُّعم':34}{dfm:>12.1f}{ddm:>16.1f}")
    print()
    if ddm > 0:
        print(f"نسبةُ الحقِّ إلى الطُّعمِ في الشهادةِ المباشرة: {real_direct / ddm:.2f}")
    print(f"الصفوفُ المفحوصة: {n:,}")

    payload = {
        "generated_by": "scripts/guttural_decoy_test.py",
        "note": "طبقةُ استكشاف. ضابطٌ منهجيٌّ لا رقمٌ منشور.",
        "design": "ذراعان بعرضِ مروحةٍ واحدٍ لا يفترقانِ إلّا في موضعِ الحلقيّ",
        "decoy_sets": [{"name": n_, "letters": list(r_)} for n_, r_ in DECOYS],
        "result": {
            "rows": n,
            "real_found": real_found, "real_direct": real_direct,
            "decoy_found": decoy_found, "decoy_direct": decoy_direct,
            "decoy_found_mean": dfm, "decoy_direct_mean": ddm,
            "ratio_direct": (real_direct / ddm) if ddm else None,
        },
        "examples": examples,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
