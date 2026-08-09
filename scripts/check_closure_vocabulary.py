# -*- coding: utf-8 -*-
"""حارسُ قاموسِ الإغلاق (2026-08-08، بأمرِ المؤلّف)

**العطبُ الذي يُنهيه، وهو عطبٌ متكرِّرٌ لا حادثةٌ واحدة.** حينَ يشُكُّ عاملٌ في
دعوى عامّةٍ، فإنّه يميلُ إلى اختراعِ **وسمِ حجبٍ جديدٍ** يُغلِقُ به البطاقاتِ
المفردة، فيتسرَّبُ شكٌّ يخصُّ طبقةَ النشرِ إلى طبقةِ الاستكشافِ ويقتُلُ مرشَّحينَ
أحياءً. آخرُ ما وقعَ منه: اختُرِعَ وسمُ `LARYNGEAL-CLASS-MISMATCH` في أثناءِ جولةٍ،
فأُغلِقَ به `cano ~ كهن` و`periculum ~ بره`، وهما زوجانِ قويّانِ في المعنى، لسببٍ
هو أنّ فئةَ الحنجريّةِ لم توافقْ فئةَ الحلقيِّ العربيّ، **ودعوى الفئاتِ تلك لم
تثبُتْ أصلًا**. فأُغلِقَت بطاقاتٌ بقانونٍ لا وجودَ له.

**والجردُ كشفَ أنّها ليست حادثةً مفردة:** في حقولِ الحكمِ اليومَ وسومٌ مثل
`ORBIT-NOT-IDENTICAL` و`CONSTRUCTED-SEMANTIC-BRIDGE` و`UNLISTED-CORRESPONDENCE`
و`CHRONOLOGY-BRIDGE-OLD`، وكلُّها أسبابُ حجبٍ وُلِدَت في أثناءِ العملِ لا في
الميثاق. و`UNLISTED-CORRESPONDENCE` بعينِه هو شرطُ الصفِّ الموقَّعِ الذي عطّلَ
الاستكشافَ أسابيعَ حتى نقضَه المؤلّف.

**القانون:** لا يُغلَقُ مرشَّحٌ إلّا بوسمٍ من قاموسٍ مغلَقٍ يُقرِّرُه المؤلّف. ومن
احتاجَ وسمًا جديدًا رفعَ ورقةَ قرارٍ ولم يكتُبْه في بطاقة. **والشكُّ في قانونٍ
عامٍّ لا يُغلِقُ بطاقةً مفردةً أبدًا**، لأنّ البطاقةَ تُحكَمُ بما فيها هي: صورتُها
ومعناها ومدارُها ومصدرُها.

يُخرِجُ الحارسُ ثلاثةَ أشياء:
  1. **يُسقِطُ البناءَ** إن ظهرَ وسمٌ ليس في القاموسِ ولا في المتوارَث.
  2. **يعُدُّ المتوارَث**، وهو ما أُغلِقَ قبلَ هذا الحارسِ بوسمٍ مخترَع.
  3. **يكتبُ قائمةَ إعادةِ الفتح**: كلُّ بطاقةٍ أُغلِقَت بوسمٍ مخترَعٍ، ليقرِّرَ
     المؤلّفُ فتحَها. وهذه ليست تنظيفًا، بل **استرجاعُ صيدٍ سقطَ بغيرِ حقّ**.

الاستعمال:
    python scripts/check_closure_vocabulary.py            جردٌ وقائمةُ فتح
    python scripts/check_closure_vocabulary.py --check    حارسُ النشر
"""
from __future__ import annotations

import argparse
import collections
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as C  # noqa: E402

READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "closure-vocabulary.json"
REOPEN = ROOT / "05-audits" / "2026-08-08-cards-closed-on-invented-labels.md"

# ------------------------------------------------------------------ القاموس
# أحكامُ الصلةِ الموجَبة، سُلَّمُ الدستور
POSITIVE = {
    "ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE",
}
# الإغلاقاتُ النهائيّةُ التي يُجيزُها الميثاق
CLOSURES = {
    "NO-TRACE", "CLOSED-NO-TRACE", "LOANWORD", "LOANWORD-THIRD-PARTY-TO-BRANCH",
    "LOANWORD-NON-ARABIC-TO-ARABIC", "SEMITIC-SOURCE-TRANSMISSION",
    "INTRA-HOUSE-TRANSFER", "LOAN-ROUTE-ISOLATED", "FORM-OF-ISOLATED",
    "MIXED-ISOLATED", "ABBREVIATION", "COMPOUND-BOUNDARY", "OUT-OF-SCOPE",
    "OPEN-CANDIDATE",
}
# الفجواتُ المسمّاة: تقولُ ما ينقُصُنا نحن، لا ما يُبطِلُ المرشَّح
GAPS = {
    "SOURCE-GAP", "TOOL-GAP", "LAW-GAP", "MORPHOLOGY-GAP", "DIRECTION-GAP",
    "HISTORICAL-STRATUM-GAP",
}
LEGAL = POSITIVE | CLOSURES | GAPS

# **وسومٌ وُلِدَت في أثناءِ العملِ لا في الميثاق.** تُحتمَلُ لأنّها مكتوبةٌ في بطاقاتٍ
# سابقةٍ ولا يُمحى من السجلِّ شيء، ولكن **لا يُزادُ عليها**، وكلُّ بطاقةٍ أُغلِقَت
# بواحدٍ منها تدخلُ قائمةَ إعادةِ الفتحِ لينظرَ فيها المؤلّف.
LEGACY_INVENTED = {
    "ORIGINAL-CONSONANT-DROP", "NUCLEUS-ORIGINAL-CONSONANT-DROP",
    "ORBIT-NOT-IDENTICAL", "ORBIT-GAP", "NUCLEUS-ORBIT-GAP",
    "CONSTRUCTED-SEMANTIC-BRIDGE", "UNLISTED-CORRESPONDENCE",
    "CHRONOLOGY-BRIDGE-OLD", "DIRECTIONAL-TRANSMISSION",
    "LARYNGEAL-CLASS-MISMATCH", "LARYNGEAL-AGREE",
    # جردُ 2026-08-08: هذه كلُّها أسبابُ حجبٍ وُجِدَت مكتوبةً في بطاقاتٍ سابقة.
    # تُجمَّدُ هنا حتى لا يتوقّفَ النشرُ على ماضٍ لا يُمحى، **ولا يُزادُ عليها حرف**:
    # الحارسُ يُسقِطُ البناءَ على أيِّ سببِ حجبٍ جديدٍ بعدَ هذا اليوم.
    "ARABIC-MATERIAL-SPLIT", "ARABIC-QUOTE-GAP", "ARABIC-SOURCE-GAP",
    "BELOW-NUCLEUS-AFTER-MORPHOLOGY", "ENTRY-GAP", "HISTORICAL-CONSONANT-GAP",
    "LOAN-DIRECTION-GAP", "MATERIAL-SPLIT", "MATERIAL-UNITY-GAP",
    "MEANING-FAIL", "NO-CANDIDATE-IN-FAN", "NO-ROOT-TRACE", "NOT-IDENTICAL",
    "OLD-ENGLISH-CARD-GAP", "ORIGINAL-CONSONANT-UNACCOUNTED",
    "ROW-TAG-CONDITION-UNMET", "SEMANTIC-BRIDGE-GAP", "SEMANTIC-GAP",
    "SENSE-SELECTED-AFTER-THE-FACT",
}

# **صيغةُ سببِ الحجب.** الوسمُ المخترَعُ يُعرَفُ من لفظِه: فجوةٌ أو إخفاقٌ أو عدمُ
# مطابقةٍ أو شرطٌ لم يتحقّق. وكلُّ ما جاءَ على هذه الصيغةِ وليسَ في القاموسِ فهو
# سببُ حجبٍ وُلِدَ في أثناءِ العمل، ويدخلُ صاحبُه قائمةَ إعادةِ الفتح.
BLOCKING_SHAPE = re.compile(
    r"(?:-GAP$|^GAP-|FAIL|MISMATCH|UNMET|UNACCOUNTED|^NOT-|-NOT-|^NO-(?!TRACE$)"
    r"|CONDITION|SPLIT$|AFTER-THE-FACT|UNLISTED|CONSTRUCTED|NOT-IDENTICAL"
    r"|BELOW-|-DROP$|UNAVAILABLE|MISSING)")

# ما ليسَ وسمَ حكمٍ أصلًا: معرّفاتُ مصادرَ وصفوفُ شبكةٍ وأرقامُ لقطات
NOT_A_LABEL = re.compile(
    r"^(?:[A-Z]{2,4}-\d{2}$|BR-|SIB-|DENT-|IDN-|SEM-|LAB-|VEL-|EMPH-|"
    r"WEEK-|LANE-|RECOVERY-|KELLIA|CRUM|TLA|AED|CAD|CDA|IPA|POS|JSONL?|"
    r"UTF|NFC|JSON|CSV|XML|HTML|URL|README|DRAFT-LOCKED|READY|LEAD)")
TOKEN = re.compile(r"\b[A-Z][A-Z0-9]*(?:-[A-Z0-9]+)+\b|\b[A-Z]{4,}\b")


def scan() -> tuple[collections.Counter, list[dict]]:
    labels = collections.Counter()
    closed_on_invented: list[dict] = []
    for path in sorted(READINGS.glob("*.md")):
        text = C.bare(path.read_text(encoding="utf-8"))
        for raw in C.CARD_SPLIT.split(text)[1:]:
            head = raw.split("\n", 1)[0]
            if C.is_template(head):
                continue
            for value in C.VERDICT_FIELDS.findall(raw):
                toks = [t for t in TOKEN.findall(value) if not NOT_A_LABEL.match(t)]
                if not toks:
                    continue
                for t in toks:
                    labels[t] += 1
                # بطاقةٌ لا حكمَ موجَبًا فيها وفيها سببُ حجبٍ خارجَ القاموس:
                # أُغلِقَت بقانونٍ لا وجودَ له
                invented = {x for x in toks
                            if x not in LEGAL
                            and (x in LEGACY_INVENTED or BLOCKING_SHAPE.search(x))}
                if not (set(toks) & POSITIVE) and invented:
                    closed_on_invented.append({
                        "language": path.stem,
                        "card": head[:110],
                        "verdict": value.strip()[:160],
                        "labels": sorted(invented),
                    })
    return labels, closed_on_invented


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    labels, closed = scan()
    # الحارسُ يُسقِطُ البناءَ على **سببِ الحجبِ الجديدِ** وحدَه. أمّا الوسمُ الوصفيُّ
    # الذي لا يحجُبُ فيُذكَرُ ولا يُوقِفُ العمل، فالتشديدُ على الوصفِ تشديدٌ في غيرِ محلّه.
    unknown = {k: v for k, v in labels.items()
               if k not in LEGAL and k not in LEGACY_INVENTED and BLOCKING_SHAPE.search(k)}

    if args.check:
        if unknown:
            print("FAIL: وسومُ حكمٍ خارجَ القاموسِ المُقَرّ، ولا يُغلَقُ بها مرشَّح:")
            for k, v in sorted(unknown.items(), key=lambda kv: -kv[1])[:12]:
                print(f"   {k}  ({v})")
            print("   من احتاجَ وسمًا جديدًا رفعَ ورقةَ قرارٍ ولم يكتُبْه في بطاقة.")
            return 1
        print(f"CLEAN: قاموسُ الإغلاق {len(LEGAL)} وسمًا مُقَرًّا، "
              f"ومتوارَثٌ مخترَعٌ {sum(labels[k] for k in LEGACY_INVENTED if k in labels)} "
              f"في {len(closed)} بطاقةً مرشَّحةً لإعادةِ الفتح")
        return 0

    print(f"{'الوسم':40}{'مرّات':>8}  الحال")
    for k, v in labels.most_common(60):
        if k in POSITIVE:
            state = "حكمٌ موجَب"
        elif k in CLOSURES:
            state = "إغلاقٌ مُقَرّ"
        elif k in GAPS:
            state = "فجوةٌ مسمّاة"
        elif k in LEGACY_INVENTED or BLOCKING_SHAPE.search(k):
            state = "** سببُ حجبٍ مخترَع **"
        else:
            state = "خارجَ القاموس (لا يحجُب)"
        print(f"{k:40}{v:>8}  {state}")

    print(f"\nبطاقاتٌ أُغلِقَت بوسمٍ مخترَعٍ ولا حكمَ موجَبَ فيها: {len(closed)}")
    per = collections.Counter(c["language"] for c in closed)
    for lang, n in per.most_common():
        print(f"   {lang:26}{n:5}")

    OUT.write_text(json.dumps({
        "generated_by": "scripts/check_closure_vocabulary.py",
        "legal": sorted(LEGAL), "legacy_invented": sorted(LEGACY_INVENTED),
        "counts": dict(labels.most_common()),
        "closed_on_invented": len(closed),
        "closed_by_language": dict(per),
    }, ensure_ascii=False, indent=1), encoding="utf-8")

    lines = [
        "# بطاقاتٌ أُغلِقَت بوسمٍ مخترَعٍ، مرشَّحةٌ لإعادةِ الفتح، 2026-08-08",
        "",
        "**الطبقة:** استكشاف. **قائمةُ عرضٍ على المؤلّفِ لا قرارٌ نافذ.**",
        "",
        "كلُّ بطاقةٍ أدناه أُغلِقَت بوسمٍ **ليس في ميثاقِ الاستكشافِ ولا في الدستور**،",
        "بل وُلِدَ في أثناءِ العمل. والإغلاقُ بقانونٍ لا وجودَ له إغلاقٌ بغيرِ حقّ،",
        "فهذه القائمةُ **استرجاعُ صيدٍ سقطَ**، لا تنظيفُ سجلّ.",
        "",
        f"**العدد: {len(closed)} بطاقة.**",
        "",
        "| اللسان | البطاقة | الحكمُ المكتوب | الوسمُ المخترَع |",
        "|---|---|---|---|",
    ]
    for c in closed[:400]:
        lines.append(f"| {c['language']} | {c['card']} | {c['verdict']} | "
                     f"{' · '.join(c['labels'])} |")
    if len(closed) > 400:
        lines.append(f"\nوبقيّتُها {len(closed) - 400} في `data/closure-vocabulary.json`.")
    lines += [
        "",
        "---",
        "",
        "*English abstract:* Every card listed here was closed with a label that appears",
        "neither in the exploration charter nor in the constitution, but was coined during",
        "a working round. Closing a candidate under a law that does not exist is closing it",
        "without warrant, so this list is the recovery of catches wrongly dropped, not a",
        "tidying of the record. It is put to the author for a decision; nothing is reopened",
        "automatically.",
    ]
    REOPEN.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    print(f"كُتب: {REOPEN.relative_to(ROOT).as_posix()}")
    if unknown:
        print(f"\n!! وسومٌ خارجَ القاموسِ تمامًا: {', '.join(sorted(unknown))}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
