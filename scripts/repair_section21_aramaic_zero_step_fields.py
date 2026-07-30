#!/usr/bin/env python3
"""Repair the literal RECOVERY-v2 zero-step field in local section-21 cards."""
from __future__ import annotations

import argparse
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
MARKERS = (
    "ARAMAIC-ONE-SHORT-SOURCE-RICH-BATCH-01",
    "ARAMAIC-ONE-SHORT-IDENTITY-BATCH-02",
    "ARAMAIC-ONE-SHORT-IDENTITY-BATCH-03",
)
OLD = (
    "- الخطوةُ صفر (صرف الآرامية): ألف الحالة واللواحق المسماة في المصدر "
    "لا تدخل الجذر؛ لا تنزع زيادة أخرى بالتخمين، والعضو المسمى وحده وحدة الحكم."
)
NEW = (
    "- الخطوةُ صفر (التعرية بصرف الفرع): في الآرامية لا تدخل ألف الحالة "
    "واللواحق المسماة في المصدر الجذر؛ لا تنزع زيادة أخرى بالتخمين، "
    "والعضو المسمى وحده وحدة الحكم."
)
EXPECTED = 143


def selected_blocks(text: str) -> list[str]:
    blocks = []
    for marker in MARKERS:
        start_token = f"<!-- {marker} -->"
        end_token = f"<!-- {marker}:END -->"
        start = text.index(start_token)
        end = text.index(end_token, start) + len(end_token)
        blocks.append(text[start:end])
    return blocks


def atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = READING.read_text(encoding="utf-8")
    blocks = selected_blocks(text)
    old_count = sum(block.count(OLD) for block in blocks)
    new_count = sum(block.count(NEW) for block in blocks)
    if args.check:
        if old_count or new_count != EXPECTED:
            raise SystemExit(
                f"section-21 Aramaic zero-step drift: old={old_count}; "
                f"new={new_count}; expected={EXPECTED}"
            )
        print(f"CLEAN: {new_count} section-21 Aramaic zero-step fields")
        return 0
    if old_count != EXPECTED or new_count:
        raise SystemExit(
            f"refusing non-exact repair: old={old_count}; new={new_count}; "
            f"expected={EXPECTED}"
        )
    atomic_write(READING, text.replace(OLD, NEW))
    print(f"repaired {EXPECTED} section-21 Aramaic zero-step fields")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
