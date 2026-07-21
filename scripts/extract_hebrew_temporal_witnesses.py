#!/usr/bin/env python3
"""Extract explicit old-Hebrew example references from the pinned Kaikki file.

The extractor is retrieval-only.  It records what the example's ``ref`` field
actually names and does not infer an old stratum from an unreferenced example.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import unicodedata
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Resources" / "hebrew" / "kaikki.org-dictionary-Hebrew.jsonl"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
OUTPUT = ROOT / "data" / "hebrew-temporal-witnesses.json"

BIBLICAL = re.compile(r"\b(?:Tanach|Tanakh|Hebrew Bible|Bible)\b", re.IGNORECASE)
MISHNAIC = re.compile(r"\b(?:Mishnah|Mishnaic)\b", re.IGNORECASE)
RABBINIC = re.compile(
    r"\b(?:Babylonian Talmud|Jerusalem Talmud|Talmud|Tosefta|Midrash|Midrashic)\b",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def classify(reference: str) -> str:
    if BIBLICAL.search(reference):
        return "biblical"
    if MISHNAIC.search(reference):
        return "mishnaic"
    if RABBINIC.search(reference):
        return "rabbinic-other"
    return "other-referenced"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    if not SOURCE.is_file() or not DB.is_file():
        raise SystemExit("missing pinned Hebrew source or current recovery inventory")

    connection = sqlite3.connect(DB)
    line_to_entry: dict[int, tuple[str, str]] = {}
    for entry_id, headword in connection.execute(
        "SELECT entry_id, headword FROM entries WHERE language = 'hebrew'"
    ):
        match = re.match(r"kaikki_hebrew:(\d+):", entry_id)
        if match:
            line_to_entry[int(match.group(1))] = (entry_id, headword)
    entry_to_family = dict(
        connection.execute(
            """
            SELECT fm.entry_id, fm.family_id
            FROM family_members AS fm
            JOIN entries AS e ON e.entry_id = fm.entry_id
            WHERE e.language = 'hebrew'
            """
        )
    )

    witnesses: list[dict[str, object]] = []
    referenced_examples = 0
    all_examples = 0
    with SOURCE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            row = json.loads(line)
            entry = line_to_entry.get(line_number)
            if entry is None:
                raise SystemExit(f"source line {line_number} has no inventory entry")
            entry_id, inventory_headword = entry
            for sense_index, sense in enumerate(row.get("senses", []), 1):
                for example_index, example in enumerate(sense.get("examples", []), 1):
                    all_examples += 1
                    reference = str(example.get("ref", "")).strip()
                    if not reference:
                        continue
                    referenced_examples += 1
                    witnesses.append(
                        {
                            "source_line": line_number,
                            "entry_id": entry_id,
                            "family_id": entry_to_family[entry_id],
                            "headword": inventory_headword,
                            "part_of_speech": row.get("pos", ""),
                            "sense_index": sense_index,
                            "example_index": example_index,
                            "stratum": classify(reference),
                            "reference": reference,
                            "example_text": example.get("text", ""),
                        }
                    )

    counts = Counter(item["stratum"] for item in witnesses)
    family_counts = Counter()
    for stratum in counts:
        family_counts[stratum] = len(
            {item["family_id"] for item in witnesses if item["stratum"] == stratum}
        )
    document = {
        "schema_version": 1,
        "status": "RETRIEVAL-ONLY-NOT-A-TEMPORAL-VERDICT",
        "source": {
            "id": "kaikki_hebrew",
            "path": str(SOURCE.relative_to(ROOT)).replace("\\", "/"),
            "size_bytes": SOURCE.stat().st_size,
            "sha256": sha256(SOURCE),
        },
        "contract": {
            "scope": "explicit ref fields inside examples only",
            "biblical_rule": "reference names Tanach, Tanakh, Hebrew Bible, or Bible",
            "mishnaic_rule": "reference names Mishnah or Mishnaic",
            "rabbinic_other_rule": "reference names Talmud, Tosefta, or Midrash but not Mishnah",
            "absence_rule": "no explicit reference means no old-stratum claim",
        },
        "coverage": {
            "source_entries": len(line_to_entry),
            "examples_seen": all_examples,
            "referenced_examples": referenced_examples,
            "witnesses_by_stratum": dict(sorted(counts.items())),
            "families_by_stratum": dict(sorted(family_counts.items())),
        },
        "witnesses": witnesses,
    }
    rendered = unicodedata.normalize(
        "NFC", json.dumps(document, ensure_ascii=False, indent=2) + "\n"
    )

    if args.check:
        if not OUTPUT.is_file() or OUTPUT.read_text(encoding="utf-8") != rendered:
            raise SystemExit("Hebrew temporal-witness inventory is stale")
        print("Hebrew temporal-witness inventory: CLEAN")
        return 0

    OUTPUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(json.dumps(document["coverage"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
