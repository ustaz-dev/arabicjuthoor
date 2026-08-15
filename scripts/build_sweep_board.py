# -*- coding: utf-8 -*-
"""لوحةُ المسحِ الصوتيِّ المباشرِ للواجهة (2026-08-15)

**ما تعرضُه، ولماذا يستحقُّ لوحةً مستقلّة.** كانت الطريقةُ في المشروعِ كلِّه:
كلمةٌ من طابورٍ رتّبناه نحن، ثمّ توليدُ مرشَّحين، ثمّ فحص. وأمرُ المؤلّفِ كان
غيرَ ذلك بنصِّه: **«ابدأْ بمقابلةِ الكلماتِ التي قد تكونُ نفسَها صوتيًّا، ثمّ
انظُرْ هل في معانيها صلة»**.

فأُجريَ المسحُ على **مادّةِ كلِّ فرعٍ الأصيلةِ من قاموسِه** لا على طابورِ قرضٍ
ولا على ترتيبٍ صنعناه: كلُّ مدخلٍ يُجرَّدُ هيكلُه الصامتيُّ، وتُفتَحُ مروحتُه
العربيّةُ كاملةً، ويُبقى المرشَّحُ **الموجودُ فعلًا في معاجمِ العربيّة**، ثمّ
يُقاسُ تقاطعُ المعنى بينَ الطرفَين.

**والطبقةُ استكشافٌ لا حكم.** هذه اللوحةُ تعرضُ مادّةً مرشَّحةً تنتظرُ البطاقةَ
بالأرجلِ الثلاث، ولا تدخلُ عدَّ الصلاتِ الصادرة. وذلك مكتوبٌ في وجهِ اللوحة.
"""
from __future__ import annotations

import glob
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
OUT = ROOT / "data" / "sweep-board.json"

NAMES = {
    "latin": ("اللاتينِيّةُ القَديمة", "Old Latin", 3),
    "ancient_greek": ("اليونانِيّةُ القَديمة", "Ancient Greek", 3),
    "persian": ("الفارِسِيّة", "Persian", 3),
    "welsh": ("الويلزِيّة", "Welsh", 3),
    "gothic": ("القوطِيّة", "Gothic", 3),
    "old_norse": ("النَّورسِيّةُ القَديمة", "Old Norse", 3),
    "old_irish": ("الإيرلَندِيّةُ القَديمة", "Old Irish", 3),
    "english_old": ("الإنجليزِيّةُ القَديمة", "Old English", 3),
    "english_middle": ("الإنجليزِيّةُ الوُسطى", "Middle English", 3),
    "egyptian": ("المِصرِيّةُ القَديمة", "Ancient Egyptian", 2),
    "coptic": ("القِبطِيّة", "Coptic", 2),
    "akkadian": ("الأَكّادِيّة", "Akkadian", 1),
    "hebrew": ("العِبرِيّة", "Hebrew", 1),
    "aramaic": ("الآرامِيّة", "Aramaic", 1),
}


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tongues, examples = [], []
    tot = direct_tot = sound_tot = 0

    for path in sorted(glob.glob(str(ROOT / "**" / "phonetic-sweep-*.json"),
                                 recursive=True)):
        payload = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if "both" not in payload:
            continue
        lang = payload["language"]
        if lang not in NAMES:
            continue
        both = payload["both"]
        direct = [r for r in both if r.get("direct") and not r.get("loan_suspect")]
        ar, en, dist = NAMES[lang]
        tongues.append({
            "key": lang, "ar": ar, "en": en, "distance": dist,
            "both": len(both), "direct": len(direct),
            "sound_only": len(payload.get("sound_only", [])),
        })
        tot += len(both)
        direct_tot += len(direct)
        sound_tot += len(payload.get("sound_only", []))
        for r in direct[:6]:
            examples.append({
                "key": lang, "ar": ar, "en": en,
                "branch": r["branch"], "say": r.get("say", ""),
                "gloss": r.get("gloss", "")[:70],
                "arabic": r["best"], "shared": r.get("shared", []),
            })

    tongues.sort(key=lambda t: -t["both"])
    payload = {
        "generated_by": "scripts/build_sweep_board.py",
        "layer": "استكشاف",
        "note": ("مادّةٌ مرشَّحةٌ من مسحِ الفروعِ الأصيلةِ: الصوتُ يُقابِلُ أوّلًا "
                 "والمعنى يحكُمُ بعدَه. لا تدخلُ عدَّ الصلاتِ الصادرة."),
        "totals": {"both": tot, "direct": direct_tot, "sound_only": sound_tot,
                   "tongues": len(tongues)},
        "tongues": tongues,
        "examples": examples,
    }
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1),
                   encoding="utf-8")
    print(f"CLEAN: لوحةُ المسح {len(tongues)} لسانًا، {tot:,} صوتًا ومعنًى، "
          f"{direct_tot:,} بشهادةٍ مباشرة [{OUT.name}]")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
