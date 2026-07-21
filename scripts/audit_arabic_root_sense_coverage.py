#!/usr/bin/env python3
"""Inventory old-Arabic lexicon coverage for every generated root candidate.

This is retrieval infrastructure only. It records whether a dictionary entry is
present, empty, or missing and which two independent works a later human review
may use. It never chooses a meaning or a linguistic verdict.
"""

from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
import tempfile
from pathlib import Path

from recovery_pipeline.inventory import DEFAULT_DB
from search_arabic_root_senses import (
    CANONICAL_SOURCES,
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "arabic-root-lexicon-completeness.json"
ARABIC_ROOT = re.compile(r"^[\u0621-\u064a]+$")


def candidate_roots(database: Path) -> list[str]:
    connection = sqlite3.connect(database)
    try:
        rows = connection.execute(
            "SELECT DISTINCT form FROM candidates "
            "WHERE kind IN ('root','hollow-root') ORDER BY form"
        )
        return [
            str(row[0])
            for row in rows
            if row[0] and ARABIC_ROOT.fullmatch(str(row[0]))
        ]
    finally:
        connection.close()


def build_inventory(database: Path, resources: Path) -> dict:
    roots = candidate_roots(database)
    matches_by_root = matches_for_roots(resources, set(roots), limit=None)
    records = []
    for root in roots:
        matches = matches_by_root.get(root, [])
        fan = independent_fan(matches)
        records.append(
            {
                "root": root,
                "complete_two_source_fan": fan["complete"],
                "fallback_used": fan["fallback_used"],
                "selected_sources": [
                    {
                        "source_id": item["source_id"],
                        "source_label": item["source_label"],
                        "resource_record": item["source"],
                    }
                    for item in fan["selected_sources"]
                ],
                # Canonical sources absent from this list are present. Keeping only
                # the exceptions makes the committed audit compact without losing
                # any missing-versus-empty information.
                "missing_or_empty": fan["missing_or_empty"],
            }
        )
    return {
        "schema_version": "1.0",
        "status": "INTERNAL-RETRIEVAL-AUDIT",
        "judgment_scope": "none",
        "candidate_source": str(database.relative_to(ROOT)).replace("\\", "/"),
        "candidate_kinds": ["root", "hollow-root"],
        "policy": {
            "minimum_independent_nonempty_sources": 2,
            "preferred_sources": ["lisan", "taj_al_arus"],
            "fallback": "next non-empty independent old lexicon in canonical priority order",
            "canonical_sources": [
                {"source_id": source_id, "source_label": label}
                for source_id, label in CANONICAL_SOURCES
            ],
        },
        "root_count": len(records),
        "roots": records,
    }


def render(payload: dict) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", dir=path.parent, delete=False
    ) as handle:
        handle.write(text)
        temporary = Path(handle.name)
    temporary.replace(path)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audit independent old-Arabic lexicon coverage for root candidates."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    payload = build_inventory(args.db.resolve(), args.resources.resolve())
    expected = render(payload)
    if args.check:
        if not args.output.exists() or args.output.read_text(encoding="utf-8") != expected:
            print("FAIL: Arabic root lexicon completeness inventory is stale")
            return 1
        print(
            "Arabic root lexicon completeness inventory: fresh "
            f"({payload['root_count']} candidate roots)"
        )
        return 0
    write_atomic(args.output, expected)
    print(
        f"wrote {args.output}: {payload['root_count']} candidate roots; "
        "retrieval audit only"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
