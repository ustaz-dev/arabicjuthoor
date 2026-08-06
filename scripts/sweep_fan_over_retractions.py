# -*- coding: utf-8 -*-
"""مسحُ المروحةِ على كلِّ ما رُدَّ أو حُبِس (2026-08-06)

**ما يُصلِحُه:** كنّا نقرأُ من الشمالِ إلى العربيّةِ بمرشَّحٍ واحدٍ لكلِّ حرف، والعربيّةُ
حفِظَت ما دمجَه الشمال، فحرفٌ شماليٌّ واحدٌ يُقابِلُ عدّةَ أصواتٍ عربيّة. فكلُّ بطاقةٍ
اختَرنا فيها فرعًا خاطئًا من المروحةِ سقطَت ولا ذنبَ للصلة.

**والدليلُ المقيس:** `לעס` «مضغ» أخذنا فيها `لعس` وهي سوادُ الشفة، والمروحةُ تُخرِجُ
معها `لحس` «باللسان» و`لغس` «سرعةُ الأكل». و`עסק` أخذنا فيها `عسر`، والمروحةُ تُخرِجُ
`عشق` و`عسق` و`عسك` «لصِق».

**ما يفعلُه:** يجمعُ كلَّ كلمةٍ شماليّةٍ من سجلِّ النقوضِ ومن البطاقاتِ المحبوسة، ويفتحُ
مروحتَها، ويُبقي المرشَّحاتِ **الموجودةَ فعلًا في معاجمِ العربيّة**، ثمّ يُرتِّبُ الحصيلةَ
بعددِ المرشَّحاتِ الجديدةِ التي لم تكن في البطاقة.

**ولا يُصدِرُ حكمًا.** يُخرِجُ طابورَ نظرٍ يقرؤُه الباحثُ ويختارُ بالمعنى.

الاستعمال:  python scripts/sweep_fan_over_retractions.py [--out FILE]
"""
from __future__ import annotations

import argparse
import glob
import json
import pathlib
import re
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))
import fan_northern_word as F  # noqa: E402

NORTHERN = re.compile(r"[֐-׿]{2,12}")
ARABIC_ROOT = re.compile(r"[ء-ي]{2,5}")

SOURCES = [
    ROOT / "05-audits" / "2026-08-05-recorded-retractions.md",
    ROOT / "05-audits" / "2026-08-06-semitic-row-retraction-rescreen.md",
    ROOT / "05-audits" / "2026-08-06-delegated-ruling-retraction-rescreen.md",
]
BLOCKED = sorted((ROOT / "04-cross-linguistic" / "exploration").glob("blocked-*.jsonl"))


def harvest() -> dict[str, dict]:
    """كلمةٌ شماليّةٌ -> {الجذورُ العربيّةُ التي ذُكِرَت معها، المصدر}."""
    found: dict[str, dict] = {}

    for path in SOURCES:
        if not path.is_file():
            continue
        for line in path.read_text(encoding="utf-8").splitlines():
            words = NORTHERN.findall(line)
            if not words:
                continue
            arabic = set(ARABIC_ROOT.findall(line))
            for w in words:
                sk = F.skeleton(w)
                if not (2 <= len(sk) <= 4):
                    continue
                e = found.setdefault(sk, {"forms": set(), "tried": set(), "where": set()})
                e["forms"].add(w)
                e["tried"] |= arabic
                e["where"].add(path.stem)

    for path in BLOCKED:
        lang = path.stem.replace("blocked-", "")
        for line in path.read_text(encoding="utf-8").splitlines():
            try:
                r = json.loads(line)
            except Exception:
                continue
            blob = f"{r.get('head', '')} {r.get('word', '')} {r.get('excerpt', '')[:400]}"
            for w in NORTHERN.findall(blob):
                sk = F.skeleton(w)
                if not (2 <= len(sk) <= 4):
                    continue
                e = found.setdefault(sk, {"forms": set(), "tried": set(), "where": set()})
                e["forms"].add(w)
                e["tried"] |= set(ARABIC_ROOT.findall(blob))
                e["where"].add(f"blocked:{lang}")
    return found


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="04-cross-linguistic/exploration/fan-sweep-queue.md")
    ap.add_argument("--min-new", type=int, default=1, help="أدنى عدد مرشّحات جديدة")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    print("تحميلُ ذخيرةِ الجذورِ العربيّة...")
    roots = F.load_arabic_roots()
    print(f"جذورٌ عربيّةٌ متاحة: {len(roots):,}")

    found = harvest()
    print(f"كلماتٌ شماليّةٌ مجموعةٌ من النقوضِ والمحبوسات: {len(found):,}\n")

    rows = []
    for sk, e in found.items():
        cands = [c for c in F.fan(sk) if c in roots]
        if not cands:
            continue
        fresh = [c for c in cands if c not in e["tried"]]
        if len(fresh) < args.min_new:
            continue
        rows.append({
            "skeleton": sk,
            "forms": sorted(e["forms"])[:4],
            "tried": sorted(e["tried"])[:6],
            "candidates": cands,
            "fresh": fresh,
            "where": sorted(e["where"])[:3],
        })
    rows.sort(key=lambda r: -len(r["fresh"]))

    out = ROOT / args.out
    lines = [
        "# طابورُ المروحة: مرشّحاتٌ عربيّةٌ لم تُفحَصْ في بطاقاتٍ رُدَّت أو حُبِسَت",
        "",
        "**الطبقة:** استكشاف. **لا حكمَ في هذا الملفِّ ولا عدَّ ولا نشر.**",
        "",
        "**سببُه:** العربيّةُ حفِظَت ما دمجَه الشمال، فالحرفُ الشماليُّ الواحدُ بابٌ على",
        "عدّةِ أصواتٍ عربيّة: `צ` تُقابِلُ ص وض وظ، و`ש` تُقابِلُ ش وس وث، و`ע` تُقابِلُ",
        "ع وغ وض وح. وكنّا نأخذُ فرعًا واحدًا من المروحةِ ونبني عليه الحكم، فإذا أخطأناه",
        "سقطَتِ الصلةُ الصحيحةُ ولا ذنبَ لها.",
        "",
        "**عمودُ «لم يُفحَصْ» هو المقصود:** جذورٌ عربيّةٌ **موجودةٌ فعلًا في المعاجم**",
        "توافقُ هيكلَ الكلمةِ الشماليّةِ ولم تُذكَرْ في البطاقةِ التي رُدَّت.",
        "",
        f"**الحصيلة:** {len(rows):,} كلمةً شماليّةً لها مرشَّحاتٌ لم تُفحَصْ بعد.",
        "",
        "| الهيكل | صورُ الكلمة | ما جُرِّبَ في البطاقة | لم يُفحَصْ | الموضع |",
        "|---|---|---|---|---|",
    ]
    for r in rows[:400]:
        lines.append(
            f"| `{r['skeleton']}` | {' · '.join(r['forms'])} | "
            f"{' · '.join(r['tried']) or 'لا شيء'} | **{' · '.join(r['fresh'][:8])}** | "
            f"{' · '.join(r['where'])} |"
        )
    if len(rows) > 400:
        lines.append("")
        lines.append(f"وبقيَ {len(rows) - 400:,} صفًّا لم يُطبَعْ هنا، وهي في ملفِّ JSON المرافق.")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8", newline="\n")

    js = out.with_suffix(".json")
    js.write_text(json.dumps(rows, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"كلماتٌ لها مرشَّحاتٌ لم تُفحَصْ: {len(rows):,}")
    print(f"كُتب: {out.relative_to(ROOT).as_posix()}")
    print(f"       {js.relative_to(ROOT).as_posix()}")
    print("\nأعلى عشرةٍ بعددِ المرشَّحاتِ الجديدة:")
    for r in rows[:10]:
        print(f"   {r['skeleton']:6} {' · '.join(r['forms'][:2]):22} "
              f"جُرِّب={' '.join(r['tried'][:3]) or '-':14} جديد={' '.join(r['fresh'][:5])}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
