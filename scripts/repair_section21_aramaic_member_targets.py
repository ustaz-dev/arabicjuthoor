#!/usr/bin/env python3
"""Attach every section-21 Aramaic live obstacle to its exact member.

The eligibility counter cannot apply a parked state to an unnamed member in a
multi-member family. Early local section-21 generators named the entry in the
card but not in the live obstacle field. This bounded repair adds the stable
entry ID to that field without changing any verdict or obstacle state.
"""
from __future__ import annotations

import argparse
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "aramaic.md"
BLOCK = re.compile(
    r"(?P<block>"
    r"<!-- ARAMAIC-ONE-SHORT-[^>]+ -->"
    r".*?"
    r"<!-- ARAMAIC-ONE-SHORT-[^>]+:END -->"
    r")",
    re.DOTALL,
)
CARD = re.compile(
    r"(?P<head>^### بطاقة:[^\n]*$)(?P<body>.*?)(?=^### بطاقة:|\Z)",
    re.MULTILINE | re.DOTALL,
)
ENTRY = re.compile(r"^- الكلمةُ في الفرع:.*?`(?P<entry>kaikki_aramaic:[^`]+)`", re.MULTILINE)
OBSTACLE = re.compile(r"^(?P<prefix>- عائق:[^\n]*)(?P<ending>\n)", re.MULTILINE)


def atomic_write(path: Path, text: str) -> None:
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(unicodedata.normalize("NFC", text))
        temporary = Path(handle.name)
    temporary.replace(path)


def repair_card(match: re.Match[str]) -> str:
    card = match.group(0)
    entry_match = ENTRY.search(card)
    obstacle_match = OBSTACLE.search(card)
    if entry_match is None or obstacle_match is None:
        return card
    obstacle = obstacle_match.group("prefix")
    if "العضو=" in obstacle:
        return card
    replacement = obstacle.rstrip(".") + f"؛ العضو=`{entry_match.group('entry')}`.\n"
    return card[: obstacle_match.start()] + replacement + card[obstacle_match.end() :]


def repaired_text(text: str) -> tuple[str, int]:
    changed = 0

    def repair_block(match: re.Match[str]) -> str:
        nonlocal changed
        block = match.group("block")
        repaired = CARD.sub(repair_card, block)
        changed += sum(
            1
            for before, after in zip(CARD.findall(block), CARD.findall(repaired))
            if before != after
        )
        return repaired

    output = BLOCK.sub(repair_block, text)
    return output, changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = READING.read_text(encoding="utf-8")
    output, changed = repaired_text(text)
    if args.check:
        if changed:
            raise SystemExit(f"STALE: {changed} section-21 Aramaic member targets")
        print("CLEAN: section-21 Aramaic obstacle fields name their members")
        return 0
    if changed:
        atomic_write(READING, output)
    print(f"repaired section-21 Aramaic member targets: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
