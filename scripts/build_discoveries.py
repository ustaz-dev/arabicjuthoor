# -*- coding: utf-8 -*-
"""إعادةُ بناءِ روزنامةِ الاكتشافاتِ بأدواتِ اليوم (2026-08-07، بقرارِ المؤلّف)

**ما كانت:** لقطةُ 2026-05-20، سجَّلَها أنبوبٌ دلاليٌّ يُعطي كلَّ زوجٍ درجةً بينَ
صفرٍ وواحد، وهي درجةُ حكمٍ على المعنى لا قياسَ شيءٍ محدَّد.

**ما صارَت:** تُبنى من المسحِ الصوتيِّ الشاملِ نفسِه الذي تُبنى منه الصلات، فيصيرُ
مدخلُ السُّلَّمِ ومخرجُه من مصدرٍ واحدٍ وطريقةٍ واحدة. **ولا درجةَ مخترَعةً فيها:**
لكلِّ صفٍّ **رتبةُ شاهدٍ** من ثلاثٍ، وهي وصفٌ لما وُجِدَ لا رقمٌ نُقدِّرُه.

    شهادةٌ مباشرة   معنى الفرعِ يلتقي معاني الجذرِ العربيِّ نفسِه في جسرِ المعنى
    قرينة           يلتقي ما حولَ المعنى لا المعنى نفسَه
    مشتبَهٌ فيه      الطرفانِ أخذا الكلمةَ من الإنجليزيّةِ الحديثةِ كلاهما

وتحملُ كلُّ روزنامةٍ **هل صدرَت فيها بطاقةٌ بعدُ**، فيرى القارئُ الطريقَ من
المرشَّحِ إلى الحكم.

المخرَج: data/discoveries.json (والقديمُ يُحفَظُ في data/legacy/)
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
import unicodedata

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import count_links as C  # noqa: E402

SWEEPS = ROOT / "04-cross-linguistic" / "exploration"
READINGS = ROOT / "04-cross-linguistic" / "readings"
OUT = ROOT / "data" / "discoveries.json"
LEGACY = ROOT / "data" / "legacy"

# الفروعُ الهندوأوربيّةُ السبعةُ التي تخصُّ هذه الصفحة، ومعها ملفُّ قراءتِها
IE = {
    "latin": ("la", "Latin", "اللاتينيّة", "Italic", "old-latin"),
    "ancient_greek": ("grc", "Ancient Greek", "اليونانيّة القديمة", "Hellenic", "ancient-greek"),
    "old_irish": ("sga", "Old Irish", "الإيرلنديّة القديمة", "Celtic", "old-irish"),
    "welsh": ("cy", "Welsh", "الويلزيّة", "Celtic", "welsh"),
    "gothic": ("got", "Gothic", "القوطيّة", "Germanic", "gothic"),
    "english_old": ("ang", "Old English", "الإنجليزيّة القديمة", "Germanic", "old-english"),
    "old_norse": ("non", "Old Norse", "النُّرديّة القديمة", "Germanic", "old-norse"),
    "english_middle": ("enm", "Middle English", "الإنجليزيّة الوسطى", "Germanic", "middle-english"),
    # الفارسيّةُ هندوأوربيّةٌ أيضًا، وهي أصعبُ الفروعِ لأنّها تُكتَبُ بالحرفِ العربيِّ
    # نفسِه، فلا يدخلُ منها الطابورَ إلّا ما ثبتَت إيرانيّتُه بحرفٍ فارسيٍّ خالصٍ
    # أو باشتقاقٍ منشورٍ يُسمّي الإيرانيّةَ أو الفارسيّةَ الوسطى
    "persian": ("fa", "Persian", "الفارسيّة", "Iranian", "persian"),
}

TIERS = [
    {"key": "direct", "en": "Direct witness", "ar": "شهادةٌ مباشرة",
     "en_note": "the branch sense meets the Arabic root's own attested senses",
     "ar_note": "معنى الفرعِ يلتقي معاني الجذرِ العربيِّ المثبتةَ نفسَها"},
    {"key": "context", "en": "Circumstantial", "ar": "قرينة",
     "en_note": "meets the wording around the sense, not the sense itself",
     "ar_note": "يلتقي ما حولَ المعنى لا المعنى نفسَه"},
    {"key": "loan-suspect", "en": "Modern loan suspected", "ar": "مشتبَهٌ فيه قرضًا حديثًا",
     "en_note": "both sides look to have taken the word from modern English",
     "ar_note": "يبدو أنّ الطرفَينِ أخذا الكلمةَ من الإنجليزيّةِ الحديثة"},
]


def iter_cards(path):
    """بطاقاتُ القراءةِ تباعًا، بحدود ``CARD_SPLIT`` نفسها ومن غير تحميل الملف."""
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


def carded_roots() -> dict[str, set[str]]:
    """أيُّ الجذورِ صدرَت فيها بطاقةٌ فعلًا، لكلِّ لسان. فالروزنامةُ تقولُ للقارئِ
    أينَ وصلَ المرشَّحُ ولا تتركُه يظنُّ أنّ كلَّ صفٍّ حكمٌ."""
    out: dict[str, set[str]] = {}
    for _, (_, _, _, _, stem) in IE.items():
        path = READINGS / f"{stem}.md"
        roots: set[str] = set()
        if path.exists():
            for raw in iter_cards(path):
                if not C.scan_card(raw):
                    continue
                roots |= {unicodedata.normalize("NFC", m)
                          for m in re.findall(r"[ء-ي]{2,6}", raw[:900])}
        out[stem] = roots
    return out


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--check", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    if args.check:
        if not OUT.exists():
            print("MISSING: data/discoveries.json")
            return 1
        d = json.loads(OUT.read_text(encoding="utf-8"))
        print(f"CLEAN: روزنامةُ الاكتشافات {len(d['records']):,} صفًّا، "
              f"{d['lang_count']} فروع، إصدار {d['version']}")
        return 0

    missing = [k for k in IE if not (SWEEPS / f"phonetic-sweep-{k}.json").exists()]
    if missing:
        print(f"SKIPPED: مسوحٌ غيرُ مبنيّة: {', '.join(missing)}")
        return 0

    carded = carded_roots()
    records, per_lang = [], {}
    for lang, (code, en, ar, branch, stem) in IE.items():
        d = json.loads((SWEEPS / f"phonetic-sweep-{lang}.json").read_text(encoding="utf-8"))
        rows = d["both"]
        per_lang[en] = {"total": len(rows), "direct": 0}
        for r in rows:
            tier = ("loan-suspect" if r.get("loan_suspect")
                    else "direct" if r.get("direct") else "context")
            if tier == "direct":
                per_lang[en]["direct"] += 1
            shared = r.get("shared", [])
            fan = [c for c in r.get("candidates_found", []) if c != r["best"]][:8]
            reasoning = (
                ("The branch sense meets this root's own attested senses: "
                 if tier == "direct" else
                 "Both sides look to have taken the word from modern English: "
                 if tier == "loan-suspect" else
                 "Meets the wording around the sense: ")
                + ", ".join(shared)
                + (". Other Arabic candidates the fan opened and the meaning did not choose: "
                   + " ".join(fan) if fan else ".")
            )
            records.append({
                # حقولٌ يقرؤُها متصفِّحُ الصفحةِ أصلًا. والدرجةُ هنا **رتبةُ شاهدٍ
                # لا تقديرَ معنًى**: 0.95 شهادةٌ مباشرة، 0.80 قرينة، 0.65 مشتبَهٌ فيه.
                # فالعتباتُ الثلاثُ في الواجهةِ تختارُ الرتبةَ لا تقيسُ قربًا.
                "score": {"direct": 0.95, "context": 0.80, "loan-suspect": 0.65}[tier],
                "pass2_score": None,
                "method": "phonetic_fan_then_meaning_bridge",
                "reasoning": reasoning,
                "verdict": "card issued" if r["best"] in carded.get(stem, set()) else None,
                "confidence": None,
                "ar_pron": "",
                "code": code, "lang_en": en, "lang_ar": ar, "branch": branch,
                "ar": r["best"],
                "tgt": r["branch"],
                "tgt_pron": (r.get("say") or "").split("(")[0].strip() or r["branch"],
                "gloss": r.get("gloss", ""),
                "tier": tier,
                "shared": shared,
                "overlap": r.get("overlap", 0),
                "depth": r.get("depth", 0),
                "fan": fan,
                "carded": r["best"] in carded.get(stem, set()),
            })

    # الشهادةُ المباشرةُ أوّلًا، ثمّ قوّةُ التقاطع، ثمّ الهيكلُ الأضيق
    order = {"direct": 0, "context": 1, "loan-suspect": 2}
    records.sort(key=lambda r: (order[r["tier"]], -r["overlap"], -r["depth"]))

    if OUT.exists():
        LEGACY.mkdir(parents=True, exist_ok=True)
        old = json.loads(OUT.read_text(encoding="utf-8"))
        if old.get("version") != "2026-08-07":
            keep = LEGACY / f"discoveries-{old.get('version', 'unknown')}.json"
            if not keep.exists():
                keep.write_text(json.dumps(old, ensure_ascii=False), encoding="utf-8")
                print(f"حُفِظَ القديمُ: {keep.relative_to(ROOT).as_posix()}")

    counts = {t["key"]: sum(1 for r in records if r["tier"] == t["key"]) for t in TIERS}
    payload = {
        "version": "2026-08-07",
        "generated_by": "scripts/build_discoveries.py",
        "method": "phonetic fan over the whole corpus, then the meaning bridge judges",
        "note": "طبقةُ استكشاف. مرشَّحونَ لا أحكام. الحكمُ في صفحةِ الصِّلات.",
        "lang_count": len(IE),
        "record_count": len(records),
        "tiers": TIERS,
        "tier_counts": counts,
        "buckets": counts,
        "carded": sum(1 for r in records if r["carded"]),
        "by_language": per_lang,
        # أسماءُ الحاوياتِ كما تقرؤُها الصفحةُ أصلًا، حتى لا تُعادَ كتابةُ متصفِّحِها
        "langs": {
            code: {"name_en": en, "name_ar": ar, "branch": branch}
            for (code, en, ar, branch, _) in IE.values()
        },
        "records": records,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False), encoding="utf-8")

    print(f"{'اللسان':22}{'صفوف':>7}{'مباشرة':>9}")
    for en, v in sorted(per_lang.items(), key=lambda kv: -kv[1]["total"]):
        print(f"  {en:22}{v['total']:>6}{v['direct']:>8}")
    print(f"\nالمجموع: {len(records):,} صفًّا")
    for t in TIERS:
        print(f"   {t['ar']:24}{counts[t['key']]:6}")
    print(f"   صدرَت فيها بطاقةٌ بعدُ {payload['carded']:>10}")
    print(f"\nكُتب: {OUT.relative_to(ROOT).as_posix()}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
