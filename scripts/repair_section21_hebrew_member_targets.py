#!/usr/bin/env python3
"""Attach every local Hebrew live obstacle to its exact member."""
from __future__ import annotations

import argparse
import re
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
BLOCK = re.compile(
    r"(?P<block><!-- HEBREW-[^>]+ -->.*?<!-- HEBREW-[^>]+:END -->)",
    re.DOTALL,
)
CARD = re.compile(
    r"(?P<head>^### بطاقة:[^\n]*$)(?P<body>.*?)(?=^### بطاقة:|\Z)",
    re.MULTILINE | re.DOTALL,
)
ENTRY = re.compile(r"kaikki_hebrew:[^`\s،؛\]\)\.]+")
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
    obstacle_match = OBSTACLE.search(card)
    if obstacle_match is None or any(
        token in obstacle_match.group("prefix")
        for token in ("العضو=", "الأعضاء=")
    ):
        return card
    entry_ids = ENTRY.findall(card)
    if not entry_ids:
        return card
    # The biblical card names the queued judgment member first in its live
    # verdict field. A positive or terminal verdict already carries it there;
    # this repair only makes the obstacle line equally explicit.
    verdict_lines = [
        line for line in card.splitlines() if line.startswith("- الحكم (استكشاف):")
    ]
    verdict_ids = ENTRY.findall("\n".join(verdict_lines))
    entry_id = verdict_ids[0] if verdict_ids else entry_ids[0]
    obstacle = obstacle_match.group("prefix")
    replacement = obstacle.rstrip(".") + f"؛ العضو=`{entry_id}`.\n"
    return card[: obstacle_match.start()] + replacement + card[obstacle_match.end() :]


def repaired_text(text: str) -> tuple[str, int]:
    changed = 0

    def repair_block(match: re.Match[str]) -> str:
        nonlocal changed
        block = match.group("block")
        before = CARD.findall(block)
        repaired = CARD.sub(repair_card, block)
        after = CARD.findall(repaired)
        changed += sum(1 for old, new in zip(before, after) if old != new)
        return repaired

    return BLOCK.sub(repair_block, text), changed


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    text = READING.read_text(encoding="utf-8")
    output, changed = repaired_text(text)
    if args.check:
        if changed:
            raise SystemExit(f"STALE: {changed} section-21 Hebrew member targets")
        print("CLEAN: section-21 Hebrew obstacle fields name their members")
        return 0
    if changed:
        atomic_write(READING, output)
    print(f"repaired section-21 Hebrew member targets: {changed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
