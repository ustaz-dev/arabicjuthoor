#!/usr/bin/env python3
"""أعد الأسطر التاريخية المحذوفة من قراءة، من غير حذف أي سطر حالي.

الأداة ضابط إصلاح لمرة واحدة عند اكتشاف أن مولدًا أعاد كتابة مقطع قائم. تبني
تسلسلًا فائقًا يحفظ نص HEAD الحالي ونص ملف العمل كليهما وبترتيبهما، ثم تتحقق
أن كليهما ما زال حاضرًا سطرًا فسطرًا قبل الحفظ.
"""

from __future__ import annotations

import argparse
import difflib
import subprocess
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def is_subsequence(needle: list[str], haystack: list[str]) -> bool:
    cursor = iter(haystack)
    return all(any(candidate == line for candidate in cursor) for line in needle)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("path")
    args = parser.parse_args()
    relative = Path(args.path)
    if relative.is_absolute() or ".." in relative.parts:
        raise SystemExit("المسار يجب أن يكون نسبيًا داخل المستودع")
    path = ROOT / relative

    base_text = subprocess.run(
        ["git", "show", f"HEAD:{relative.as_posix()}"],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    ).stdout
    current_text = path.read_text(encoding="utf-8")
    base = base_text.splitlines()
    current = current_text.splitlines()

    prefix = 0
    limit = min(len(base), len(current))
    while prefix < limit and base[prefix] == current[prefix]:
        prefix += 1

    old_tail = base[prefix:]
    new_tail = current[prefix:]
    matcher = difflib.SequenceMatcher(None, old_tail, new_tail, autojunk=False)
    merged = current[:prefix]
    restored = 0
    for tag, old_start, old_end, new_start, new_end in matcher.get_opcodes():
        if tag == "equal":
            merged.extend(new_tail[new_start:new_end])
        elif tag == "insert":
            merged.extend(new_tail[new_start:new_end])
        elif tag == "delete":
            segment = old_tail[old_start:old_end]
            merged.extend(segment)
            restored += len(segment)
        elif tag == "replace":
            old_segment = old_tail[old_start:old_end]
            merged.extend(old_segment)
            merged.extend(new_tail[new_start:new_end])
            restored += len(old_segment)

    if not is_subsequence(base, merged):
        raise AssertionError("فشل حفظ نص HEAD كاملًا في التسلسل الناتج")
    if not is_subsequence(current, merged):
        raise AssertionError("فشل حفظ نص ملف العمل كاملًا في التسلسل الناتج")
    latest = path.read_text(encoding="utf-8")
    if latest != current_text:
        raise AssertionError("تغير الملف أثناء الإصلاح؛ أوقف الحفظ")
    path.write_text("\n".join(merged) + "\n", encoding="utf-8", newline="\n")
    print(f"restored_lines={restored} total_lines={len(merged)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
