# -*- coding: utf-8 -*-
"""تجزئةُ ملفِّ قراءةٍ تجاوزَ حدَّ الاستضافة، بلا حذفِ حرفٍ واحد (2026-08-15)

**الحالُ التي أوجبَتها.** جيت‑هَب يرفضُ أيَّ ملفٍّ يتجاوزُ 100 ميجا رفضًا في
خطّافِ الاستقبال، فبقيَ أحدَ عشرَ إيداعًا محبوسًا على الجهازِ ولم يُنشَرْ شيء.
وقد قُلِّمَ المنسوخُ أوّلًا (610 ← 246 ميجا في اللاتينيّةِ و338 ← 137 في
الفارسيّة)، ولم يكفِ.

**والتجزئةُ لا تحذفُ شيئًا البتّة**: تُقسَمُ البطاقاتُ على ملفّاتٍ متتابعةٍ
عندَ حدودِ البطاقاتِ نفسِها (`### `)، فلا تنقطعُ بطاقةٌ في نصفِها. والاسمُ
`old-latin.part02.md`، واللسانُ يُشتَقُّ من `stem.split(".")[0]` في الأدواتِ
التي تقرأُ المجلَّد، فيبقى `old-latin` واحدًا كما كان.

**والجزءُ الأوّلُ يحتفظُ بالاسمِ الأصليِّ** (`old-latin.md`) فلا تنكسرُ إحالةٌ
خارجيّةٌ تشيرُ إليه، ويُذيَّلُ بسطرٍ يدلُّ على بقيّةِ الأجزاء.

الاستعمال:
    python scripts/split_reading_file.py --check old-latin.md
    python scripts/split_reading_file.py --write old-latin.md persian.md
"""
from __future__ import annotations

import argparse
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
READINGS = ROOT / "04-cross-linguistic" / "readings"
TARGET = 80 * 1024 * 1024        # هدفُ الجزءِ، دونَ الحدِّ بهامشٍ مريح


def split(path: pathlib.Path, write: bool) -> dict:
    raw = path.read_bytes()
    if len(raw) <= TARGET:
        return {"parts": 1, "sizes": [len(raw)]}

    text = raw.decode("utf-8", "replace")
    del raw
    # حدودُ البطاقاتِ وحدَها، فلا تنقطعُ بطاقةٌ في نصفِها
    marks = [0]
    idx = text.find("\n### ")
    while idx != -1:
        marks.append(idx + 1)
        idx = text.find("\n### ", idx + 1)
    marks.append(len(text))

    parts: list[str] = []
    start = 0
    cur = 0
    for i in range(1, len(marks)):
        seg = marks[i] - marks[i - 1]
        cur += seg
        if cur >= TARGET and marks[i] < len(text):
            parts.append(text[start:marks[i]])
            start = marks[i]
            cur = 0
    parts.append(text[start:])

    sizes = [len(p.encode("utf-8")) for p in parts]
    if write:
        stem = path.stem
        head = parts[0].rstrip("\n")
        tail = (f"\n\n> تُتمَّةُ هذا الملفِّ في {len(parts) - 1} جزءًا: "
                + "، ".join(f"`{stem}.part{n:02d}.md`"
                            for n in range(2, len(parts) + 1))
                + ". قُسِمَ عندَ حدودِ البطاقاتِ بلا حذفِ حرفٍ واحد، لأنّ حدَّ"
                  " الاستضافةِ مئةُ ميجابايتٍ للملفّ.\n")
        path.write_text(head + tail, encoding="utf-8", newline="\n")
        for n, body in enumerate(parts[1:], start=2):
            out = path.with_name(f"{stem}.part{n:02d}.md")
            out.write_text(f"# {stem} · الجزء {n}\n\n"
                           f"> تتمّةُ `{path.name}`. لا يُقرأُ وحدَه، والأدواتُ"
                           f" تجمعُ الأجزاءَ بلسانٍ واحد.\n\n"
                           + body.lstrip("\n"),
                           encoding="utf-8", newline="\n")
    return {"parts": len(parts), "sizes": sizes}


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("files", nargs="+")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")

    for name in args.files:
        p = READINGS / name
        if not p.exists():
            print(f"!! غيرُ موجود: {name}")
            continue
        before = p.stat().st_size
        r = split(p, args.write)
        sizes = " · ".join(f"{s/1048576:.0f}م" for s in r["sizes"])
        print(f"{name:22}{before/1048576:>6.0f}م ← {r['parts']} جزءًا: {sizes}"
              f"  ({'كُتِبَ' if args.write else 'قياسٌ بلا كتابة'})")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
