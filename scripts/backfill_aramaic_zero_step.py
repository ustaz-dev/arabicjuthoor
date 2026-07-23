#!/usr/bin/env python3
"""Backfill the signed Aramaic emphatic-state zero step in local shards.

This is a structural formatter only.  It records the attested surface form,
the mechanically stripped retrieval form, and the two already approved
grammatical sources.  It does not choose a cognate, alter a verdict, refresh
the central ledger, or run the proof line.
"""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
SHARDS = tuple(
    ROOT / "scratch" / f"aramaic-completion-shard-{letter}.md"
    for letter in ("a", "b", "c")
)
MEMBER = re.compile(
    r"^- العضو:\s*`(?P<entry>kaikki_aramaic:[^`]+)`(?P<body>.*)$",
    re.MULTILINE,
)
EMPHATIC_ALEPHS = ("א", "𐡀", "ܐ")


def zero_step_entries() -> dict[str, tuple[str, str]]:
    output: dict[str, tuple[str, str]] = {}
    with sqlite3.connect(DB) as connection:
        for entry_id, headword, pos in connection.execute(
            """
            SELECT entry_id, headword, pos
            FROM entries
            WHERE language='aramaic' AND pos IN ('noun', 'adj')
            """
        ):
            if headword.endswith(EMPHATIC_ALEPHS):
                output[entry_id] = (headword, headword[:-1])
    return output


def field(surface: str, stripped: str) -> str:
    return (
        " الخطوة الصفر=ARAM-ZERO-01؛ "
        f"الصورة المؤكدة={surface}؛ الصورة المجردة={stripped}؛ "
        "السند=Rosenthal, A Grammar of Biblical Aramaic, nominal states؛ "
        "Muraoka and Porten, A Grammar of Egyptian Aramaic, nominal states."
    )


def transform(path: Path, entries: dict[str, tuple[str, str]]) -> tuple[str, int]:
    text = path.read_text(encoding="utf-8")
    count = 0

    def replace(match: re.Match[str]) -> str:
        nonlocal count
        line = match.group(0)
        item = entries.get(match.group("entry"))
        if not item or "الصورة المؤكدة=" in line:
            return line
        count += 1
        return line.rstrip() + field(*item)

    return MEMBER.sub(replace, text), count


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    entries = zero_step_entries()
    results: dict[str, int] = {}
    for path in SHARDS:
        if not path.exists():
            raise ValueError(f"missing shard: {path.relative_to(ROOT)}")
        transformed, additions = transform(path, entries)
        results[path.name] = additions
        if args.check:
            if additions:
                raise ValueError(
                    f"{path.name} misses {additions} signed zero-step fields"
                )
            continue
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(transformed, encoding="utf-8")
        temporary.replace(path)
    print(json.dumps(results, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
