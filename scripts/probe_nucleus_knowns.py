# -*- coding: utf-8 -*-
"""مسبارُ الأجوبةِ المعلومةِ لأداةِ المسحِ النوويِّ (صمّامةُ الأمان).

عشرُ حالاتٍ حكمَ فيها المؤلّفُ أو مسبارُ المسارِ D حكمًا صارَ قانونًا،
تُفحَصُ كلُّها بعدَ أيِّ تعديلٍ على `build_nucleus_sweep.py` أو
`fan_any_script.py`، فلا يكسرُ إصلاحُ اليومِ إصلاحَ الأمس. المرجعُ:
`05-audits/2026-08-24-author-nucleus-calibration.md` وملاحقُه.

يخرجُ بصفرٍ عندَ عبورِ العشرِ كلِّها، وبواحدٍ عندَ أوّلِ سقوط.
"""
from __future__ import annotations

import json
import pathlib
import re
import sys

sys.stdout.reconfigure(encoding="utf-8")
ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_nucleus_sweep as NS  # noqa: E402
import fan_any_script as F  # noqa: E402

def root_first_fan(word: str, etym: str, lang: str,
                   table: dict, tri: set) -> tuple | None:
    """محاكاةُ قرارِ «الجذرِ أوّلًا» كما في main، حرفًا بحرف."""
    variants, has2 = NS.skeleton_variants(word, "latin", etym)
    labels = [v[1] for v in variants]
    fams = [(l.split(" ثمّ ")[0] if " ثمّ " in l
             else ("كما وردَت" if v[2] in {"raw", "suffix"} else l)
             ).split(" بنزعِ سابقتِه")[0]
            for l, v in zip(labels, variants)]
    keys = ["".join(v[0]) for v in variants]

    def blocked(i: int) -> bool:
        if lang not in NS.GERMANIC_LANGS:
            return False
        if any(l.startswith(labels[i] + " ثمّ")
               and NS.strip_is_certain(l)
               for l in labels):
            return True
        return any(j != i and fams[j] == fams[i]
                   and len(keys[j]) < len(keys[i])
                   and (keys[i].startswith(keys[j])
                        or keys[i].endswith(keys[j]))
                   and NS.strip_is_certain(labels[j])
                   for j in range(len(variants)))

    for i, (tsk, vlabel, tier) in enumerate(variants):
        if has2 and tier not in {"stem", "named", "prefix"}:
            continue
        if blocked(i):
            continue
        if len(tsk) != 3:
            continue
        fan = sorted({a + b + c for a in table.get(tsk[0], ())
                      for b in table.get(tsk[1], ())
                      for c in table.get(tsk[2], ())} & tri)
        if fan:
            return fan, vlabel
    return None


def main() -> int:
    table = F.FANS["latin"]
    tri = NS.load_tri_roots()
    lex = json.load((ROOT / "data" / "branch-lexicons" / "gothic.json")
                    .open(encoding="utf-8"))

    def etym_of(read_name: str) -> str:
        want = NS._fold_roman(read_name)
        e = next(x for x in lex["entries"]
                 if NS._fold_roman(x.get("read") or "") == want)
        return str(e.get("etym", ""))

    failures = []

    def check(name: str, cond: bool, detail: str) -> None:
        mark = "عبر" if cond else "سقط"
        print(f"{mark}: {name} ({detail})")
        if not cond:
            failures.append(name)

    # 1..4: مراوح مختلقة يجب أن تبقى ميتة
    for w, why in (("gaainan", "جنن ترث جيم السابقة ga-"),
                   ("afmaitan", "متن ترث نون مصدر maitan"),
                   ("afdaubnan", "ضبن ترث نون لاحقة -nan"),
                   ("fruma", "برم ترث ميم لاحقة -uma"),
                   ("daufs", "دبس ترث سين الرفع")):
        rf = root_first_fan(w, etym_of(w), "gothic", table, tri)
        check(w, rf is None, why + "؛ لا وسم جذر")

    # 6..8: مراوح صحيحة يجب أن تبقى حية بصورتها
    rf = root_first_fan("dragan", etym_of("dragan"), "gothic", table, tri)
    check("dragan", bool(rf) and rf[0][0] == "درج",
          "حكم المؤلف: بابها درج من نزع -an")
    rf = root_first_fan("usbraidjan", etym_of("usbraidjan"),
                        "gothic", table, tri)
    check("usbraidjan", bool(rf) and "برد" in rf[0],
          "برد من جذع braidjan منزوع -jan")
    gq = next(x for x in lex["entries"]
              if (x.get("read") or "").startswith("gaqum"))
    rf = root_first_fan(gq["read"], str(gq.get("etym", "")),
                        "gothic", table, tri)
    check("gaqumths", bool(rf) and "ققم" in rf[0],
          "ققم من صورة منزوعة مسماة؛ درس الحجب بمطابقة -um العارضة")

    # 9: نون الفارسية أصل محفوظ خارج القيد الجرماني
    rf = root_first_fan("samana", "From X (saman /saman) + Y (-a /-e).",
                        "persian", table, tri)
    check("samana", bool(rf) and "سمن" in rf[0],
          "نون الفارسية أصل لا صرف")

    # 10: صيغة الإحالة تستخرج اللمة، والمعنى منزوع الأقواس الشرحية
    et = etym_of("nasjands")
    stems, has = NS.decomp_parts(et)
    variants, _ = NS.skeleton_variants("nasjands", "latin", et)
    lead = variants[0] if variants else (None, "", "")
    e = next(x for x in lex["entries"] if (x.get("read") or "") == "nasjands")
    gtoks = NS.words_of(re.sub(r"\([^()]*\)", " ", str(e.get("en", ""))))
    check("nasjands",
          has and "nasjan" in stems and lead[2] == "stem"
          and "from" not in gtoks,
          "لمة اسم الفاعل جذع يتصدر، وfrom الشرحية لا تدخل طريق المعنى")

    # 13: نهاية التصريف -on يقين من الجدول الموسوم نفسه (ushulon)
    rf = root_first_fan("ushulōn", etym_of("ushulōn"), "gothic", table, tri)
    check("ushulon", rf is None,
          "هرن وهلن ترثان نون نهاية التصريف -on؛ لا وسم جذر")

    # 11ب: جذع ganauhan غير المنزوع لا يتصدر بجنح الوارثة جيم ga-
    rf = root_first_fan("ganauha", etym_of("ganauha"), "gothic", table, tri)
    check("ganauha", rf is None,
          "ابن نزع السابقة يحجب أباه؛ جنح وكنه ترثان جيم ga-")

    # 11: النزعان المسميان يتركبان على السطح الواحد فتولد skadw
    et = etym_of("gaskadweins")
    variants, _ = NS.skeleton_variants("gaskadweins", "latin", et)
    keys = {"".join(sk) for sk, _lab, _tier in variants}
    check("gaskadweins", "skdw" in keys,
          "صورة skadw تولد بنزع ga- و-eins معا")

    print()
    if failures:
        print(f"سقطت {len(failures)}: {', '.join(failures)}")
        return 1
    print("CLEAN: مسبار الأجوبة المعلومة يعبر كاملا")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
