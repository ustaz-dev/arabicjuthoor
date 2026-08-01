# -*- coding: utf-8 -*-
"""بصمةُ عملِ المساراتِ الوسيط (2026-08-01)

**المشكلة:** مجلّدُ `04-cross-linguistic/data/` بلغَ 1,060 ميغابايت، وفيه ملفٌّ واحدٌ
بحجمِ 134 ميغا، وحدُّ GitHub الأقصى للملفِّ الواحدِ 100. وهذه المادّةُ ليست أحكامًا،
فالأحكامُ في ملفّاتِ القراءة، وإنّما هي مسوحُ المرشَّحينَ والمراجعاتُ والترتيباتُ
التي بُنِيَت عليها البطاقات.

**الحلُّ المتّبَعُ نفسُه في التغطية:** تبقى المادّةُ على القرصِ خارجَ git، ويُودَعُ
بدلَها هذا البيانُ ببصمةِ SHA-256 لكلِّ ملفّ. **فالبصمةُ تُثبِتُ أنّ المادّةَ لم
تُبدَّلْ، ولا تُغني عن المادّةِ نفسِها.** ومن أرادَ التحقّقَ طلبَ الملفَّ وقابلَ بصمتَه.

الاستعمال:  python scripts/build_lane_data_manifest.py
"""
from __future__ import annotations

import hashlib
import json
import pathlib
import subprocess
import sys

ROOT = pathlib.Path(__file__).resolve().parent.parent
SCAN_DIRS = (
    ROOT / "04-cross-linguistic" / "data",
    ROOT / "Data raw" / "coverage",
)
OUT = ROOT / "data" / "lane-data-manifest.json"
CHUNK = 1 << 20


def sha256(path: pathlib.Path) -> tuple[str, int, int]:
    """أعِدْ (البصمة، البايتات، الأسطر) بمرورٍ واحدٍ على الملفّ."""
    h = hashlib.sha256()
    size = lines = 0
    with path.open("rb") as fh:
        while chunk := fh.read(CHUNK):
            h.update(chunk)
            size += len(chunk)
            lines += chunk.count(b"\n")
    return h.hexdigest(), size, lines


def schema_of(path: pathlib.Path) -> str:
    """اسمُ المخطَّطِ من أوّلِ سجلٍّ، إن أعلنَه الملفُّ عن نفسِه."""
    try:
        with path.open("r", encoding="utf-8") as fh:
            head = fh.read(4096)
        for key in ('"schema"', '"schema_version"'):
            i = head.find(key)
            if i >= 0:
                j = head.find('"', head.find(":", i) + 1)
                k = head.find('"', j + 1)
                if 0 < j < k:
                    return head[j + 1:k][:80]
    except (OSError, UnicodeDecodeError):
        pass
    return ""


def tracked_paths() -> set[str]:
    try:
        r = subprocess.run(["git", "ls-files"], cwd=ROOT, capture_output=True, text=True,
                           timeout=120)
        return {line.strip() for line in r.stdout.splitlines() if line.strip()}
    except (OSError, subprocess.SubprocessError):
        return set()


def main() -> int:
    sys.stdout.reconfigure(encoding="utf-8")
    tracked = tracked_paths()
    entries = []
    total = 0

    for directory in SCAN_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.rglob("*")):
            if not path.is_file():
                continue
            rel = path.relative_to(ROOT).as_posix()
            digest, size, lines = sha256(path)
            total += size
            entries.append({
                "path": rel,
                "bytes": size,
                "lines": lines,
                "sha256": digest,
                "schema": schema_of(path),
                "in_git": rel in tracked,
            })

    payload = {
        "generated_by": "scripts/build_lane_data_manifest.py",
        "note": (
            "بصمة مادّة المسارات "
            "الوسيطة؛ الأحكام في "
            "04-cross-linguistic/readings/ وليست هنا. البصمة "
            "تُثبت أنّ المادّة لم "
            "تُبدّل ولا تُغني عنها."
        ),
        "files": len(entries),
        "total_bytes": total,
        "in_git": sum(1 for e in entries if e["in_git"]),
        "entries": entries,
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(json.dumps(payload, ensure_ascii=False, indent=1), encoding="utf-8")

    print(f"ملفّات مبصومة: {len(entries)}   المجموع: {total / 1e6:,.0f} MB")
    print(f"منها في git: {payload['in_git']}   وخارجَه: {len(entries) - payload['in_git']}")
    over = [e for e in entries if e["bytes"] > 100_000_000]
    if over:
        print(f"\nفوق حدّ GitHub (100 MB) فلا تُودَع بحال:")
        for e in over:
            print(f"   {e['bytes'] / 1e6:7.1f} MB  {e['path']}")
    print(f"\nكُتب البيان: {OUT.relative_to(ROOT).as_posix()} ({OUT.stat().st_size / 1024:.0f} KB)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
