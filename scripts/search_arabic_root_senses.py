#!/usr/bin/env python3
"""Return the full local lexicographic sense fan for an Arabic root.

This is a recovery aid, not a classifier. It never proposes a reading or verdict.
It searches the independent Arabic dictionaries already indexed in Resources/ so
an exploration card cannot reduce a root to the first gloss that happened to be
present in an older roster.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import sys
import unicodedata
from pathlib import Path
from typing import Any


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_RESOURCES = REPO_ROOT / "Resources"
ARABIC_MARKS = re.compile(
    "[\u0610-\u061a\u064b-\u065f\u0670\u06d6-\u06ed\u0640]"
)


def normalize_root(value: str) -> str:
    value = unicodedata.normalize("NFKC", value)
    value = ARABIC_MARKS.sub("", value)
    value = value.strip().strip("*[](){}'").replace(" ", "")
    return value


def clipped(value: str, limit: int | None) -> str:
    value = " ".join(value.split())
    if limit is None or len(value) <= limit:
        return value
    return value[: max(0, limit - 1)].rstrip() + "…"


def parquet_matches(resources: Path, root: str, limit: int | None) -> list[dict[str, Any]]:
    path = resources / "arabic_roots_hf" / "train-00000-of-00001.parquet"
    if not path.exists():
        return []

    try:
        import pyarrow.dataset as ds
    except ImportError:
        return []

    table = ds.dataset(path, format="parquet").to_table(filter=ds.field("root") == root)
    matches: list[dict[str, Any]] = []
    for row in table.to_pylist():
        matches.append(
            {
                "collection": "arabic_roots_hf",
                "source": row.get("book_name") or path.name,
                "root": row.get("root") or root,
                "definition": clipped(row.get("definition") or "", limit),
                "url": row.get("url") or None,
            }
        )
    return matches


def csv_matches(resources: Path, root: str, limit: int | None) -> list[dict[str, Any]]:
    directory = resources / "Ten dictionaries for Arabic language"
    if not directory.exists():
        return []

    try:
        csv.field_size_limit(sys.maxsize)
    except OverflowError:
        csv.field_size_limit(2_147_483_647)

    matches: list[dict[str, Any]] = []
    for path in sorted(directory.glob("*.csv")):
        # mukhtar.csv is a word-to-root morphology index, not a definition table.
        if path.name.lower() == "mukhtar.csv":
            continue
        with path.open("r", encoding="utf-8-sig", errors="replace", newline="") as handle:
            reader = csv.reader(handle, delimiter=";")
            for row in reader:
                if not row or normalize_root(row[0]) != root:
                    continue
                definition = row[-1] if len(row) > 1 else ""
                matches.append(
                    {
                        "collection": "Ten dictionaries for Arabic language",
                        "source": path.name,
                        "root": row[0],
                        "definition": clipped(definition, limit),
                        "url": None,
                    }
                )
    return matches


def deduplicate(matches: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[tuple[str, str]] = set()
    result: list[dict[str, Any]] = []
    for item in matches:
        key = (str(item["source"]), str(item["definition"]))
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Search all local Arabic lexica for every attested sense of one root."
    )
    parser.add_argument("root", help="Unvowelled Arabic root, for example: شنف")
    parser.add_argument(
        "--resources",
        type=Path,
        default=DEFAULT_RESOURCES,
        help="Resources directory (defaults to the repository Resources/ folder).",
    )
    parser.add_argument(
        "--max-chars",
        type=int,
        default=1200,
        help="Maximum definition length per source; use 0 for no clipping.",
    )
    parser.add_argument("--json", action="store_true", help="Emit machine-readable JSON.")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    args = parse_args()
    root = normalize_root(args.root)
    if not root:
        raise SystemExit("The normalized root is empty.")

    limit = None if args.max_chars == 0 else args.max_chars
    matches = deduplicate(
        parquet_matches(args.resources, root, limit)
        + csv_matches(args.resources, root, limit)
    )
    payload = {"root": root, "match_count": len(matches), "matches": matches}

    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"الجذر: {root} | الشواهد: {len(matches)}")
        for index, item in enumerate(matches, start=1):
            print(f"\n[{index}] {item['source']} ({item['collection']})")
            print(item["definition"])
            if item.get("url"):
                print(item["url"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
