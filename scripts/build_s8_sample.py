# -*- coding: utf-8 -*-
"""بناءُ عيّنةِ جولةِ التحقُّقِ الكبرى (دستور §8) معمّاةً (2026-08-17)

**النصُّ المنفَّذُ حرفيًّا** (الدستور §8): «تُقرأُ عيّنةٌ حقيقيّةٌ وعيّنةٌ
عشوائيّةٌ ضابطةٌ بنفسِ حرّيّةِ المداراتِ ونفسِ الشبكة، ويُقارَنُ المعدّلان.
الإشارةُ الحقيقيّةُ هي تفوّقُ الحقيقيِّ على الضابطِ، لا الرقمُ المطلق.»
وشرطُ الميثاق: جولةٌ مسجَّلةٌ مسبقًا، ولا يُشغِّلُها إلّا المؤلّف، وقد أذِنَ
بكلمتِه في 2026-08-17.

**تصميمُ الضابط: تبديلُ المعنى لا تشويهُ الصوت.** بندُ الضابطِ صورتُه ونطقُه
وهيكلُه حقيقيّةٌ من القاموسِ نفسِه، ومعناه مأخوذٌ من مدخلةٍ أخرى بتبديلٍ
دائريٍّ داخلَ بنودِ الضابطِ وحدَها. فساقُ الصوتِ تتوزّعُ في الفريقَينِ توزُّعًا
واحدًا بالبناء، والفارقُ الوحيدُ صدقُ اقترانِ المعنى بالصورة. إن كانت حرّيّةُ
المداراتِ تنسجُ مدارًا لأيِّ شيءٍ تساوى المعدّلان، وإن كان الاقترانُ الحقيقيُّ
وحدَه يحملُ المدارَ تفوّقَ الحقيقيُّ.

**التعميةُ ببرهانٍ لا بوعد**: تُكتَبُ القائمةُ مخلوطةً بمعرّفاتٍ محايدةٍ
`S8-GRC-NNN` بلا أيِّ وسم، ويُكتَبُ مفتاحُ الفكِّ خارجَ المستودعِ، وتُودَعُ
بصمتُه SHA-256 في وثيقةِ التسجيلِ المسبقِ قبلَ أن يقرأَ القارئُ بندًا واحدًا.
بعدَ إيداعِ قراءاتِه كاملةً يُكشَفُ المفتاحُ ويُقارَنُ بالبصمة.

الاستعمال:
    python scripts/build_s8_sample.py --seed 20260817 --n 75 \
        --key-out "<مسار خارج المستودع>"
"""
from __future__ import annotations

import argparse
import hashlib
import json
import pathlib
import random
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
LEXICON = ROOT / "data" / "branch-lexicons" / "ancient-greek.json"
READINGS = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
QUEUE = ROOT / "04-cross-linguistic" / "exploration" / "s8-greek-queue.json"


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--seed", type=int, required=True)
    ap.add_argument("--n", type=int, default=75, help="حجمُ كلِّ فريق")
    ap.add_argument("--key-out", required=True,
                    help="ملفُّ المفتاحِ، خارجَ المستودعِ وجوبًا")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    key_path = pathlib.Path(args.key_out)
    if ROOT in key_path.resolve().parents:
        print("!! ملفُّ المفتاحِ داخلَ المستودع، وهذا يفسدُ التعمية")
        return 1

    entries = json.load(LEXICON.open(encoding="utf-8"))["entries"]
    carded = READINGS.read_text(encoding="utf-8", errors="replace")
    # يُستبعَدُ ما له بطاقةٌ سابقةٌ بأيِّ صفةٍ، فالقارئُ لا يلقى ما قد حُكِم،
    # ويُشترَطُ معنًى إنجليزيٌّ غيرُ فارغٍ ليصحَّ التبديل
    fresh = [e for e in entries
             if e.get("word") and e.get("en")
             and len(e["word"]) <= 26
             and e["word"] not in carded]
    rng = random.Random(args.seed)
    picked = rng.sample(fresh, args.n * 2)
    real, control = picked[:args.n], picked[args.n:]

    # تبديلٌ دائريٌّ للمعاني داخلَ الضابطِ وحدَه: كلُّ بندٍ يحملُ معنى جارِه،
    # فكلُّ المعاني حقيقيّةٌ من القاموسِ وكلُّ اقترانٍ فيه كاذبٌ بالبناء
    glosses = [e["en"] for e in control]
    swapped = glosses[1:] + glosses[:1]

    items = []
    for e in real:
        items.append({"word": e["word"], "read": e.get("read", ""),
                      "pos": e.get("pos", ""), "en": e["en"], "arm": "REAL"})
    for e, g in zip(control, swapped):
        items.append({"word": e["word"], "read": e.get("read", ""),
                      "pos": e.get("pos", ""), "en": g, "arm": "CONTROL"})
    rng.shuffle(items)

    key = {}
    queue = []
    for i, x in enumerate(items, 1):
        sid = f"S8-GRC-{i:03d}"
        key[sid] = x.pop("arm")
        queue.append({"id": sid, **x})

    QUEUE.write_text(json.dumps({
        "layer": "تحقُّقٌ مقيسٌ قيدَ التنفيذ (دستور §8)",
        "note": "قائمةُ قراءةٍ معمّاة. يقرؤُها القارئُ بالبروتوكولِ القياسيِّ "
                "كاملَ الحرّيّةِ، ولا يعلمُ تركيبَها. مفتاحُ الفكِّ خارجَ "
                "المستودعِ وبصمتُه في وثيقةِ التسجيلِ المسبق.",
        "seed_published": args.seed,
        "items": queue,
    }, ensure_ascii=False, indent=1), encoding="utf-8", newline="\n")

    key_text = json.dumps(key, ensure_ascii=False, indent=0, sort_keys=True)
    key_path.write_text(key_text, encoding="utf-8", newline="\n")
    digest = hashlib.sha256(key_text.encode("utf-8")).hexdigest()

    n_real = sum(1 for v in key.values() if v == "REAL")
    print(f"كُتِبَت القائمةُ: {QUEUE.relative_to(ROOT).as_posix()} "
          f"({len(queue)} بندًا: {n_real} حقيقيًّا و{len(queue)-n_real} ضابطًا، مخلوطةً)")
    print(f"المفتاحُ خارجَ المستودع: {key_path}")
    print(f"SHA-256 للمفتاح: {digest}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
