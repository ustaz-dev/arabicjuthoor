#!/usr/bin/env python3
"""Recover direct Aramaic-to-Arabic surface-root fans outside the frozen registry.

The frozen Arabic registry is authoritative for project readings, but a sister
language card must not silently miss an old-dictionary root merely because that
root has no frozen registry entry yet.  This retrieval-only audit maps a
three-consonant Aramaic lemma, after the already signed emphatic-aleph zero step,
to its conservative Arabic-script counterpart and searches the approved local
old lexica.  Unregistered hits remain TOOL-GAP candidates; this script never
supplies a frozen reading or a verdict.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import unicodedata
from pathlib import Path

from search_arabic_root_senses import (
    DEFAULT_RESOURCES,
    independent_fan,
    matches_for_roots,
)


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
DEFAULT_OUTPUT = (
    ROOT / "cache" / "recovery_pipeline" / "aramaic-direct-surface-fans.json"
)

# These are spelling-preserving sister-language retrieval anchors, not a new
# correspondence table.  Any non-identity historical use still has to cite an
# already signed network row in the human card.
SCRIPT_TO_ARABIC = {
    "ב": "ب", "ג": "ج", "ד": "د", "ה": "ه", "ו": "و", "ז": "ز",
    "ח": "ح", "ט": "ط", "י": "ي", "כ": "ك", "ך": "ك", "ל": "ل",
    "מ": "م", "ם": "م", "נ": "ن", "ן": "ن", "ס": "س", "ע": "ع",
    "פ": "ف", "ף": "ف", "צ": "ص", "ץ": "ص", "ק": "ق", "ר": "ر",
    "ש": "ش", "ת": "ت",
    "𐡁": "ب", "𐡂": "ج", "𐡃": "د", "𐡄": "ه", "𐡅": "و",
    "𐡆": "ز", "𐡇": "ح", "𐡈": "ط", "𐡉": "ي", "𐡊": "ك",
    "𐡋": "ل", "𐡌": "م", "𐡍": "ن", "𐡎": "س", "𐡏": "ع",
    "𐡐": "ف", "𐡑": "ص", "𐡒": "ق", "𐡓": "ر", "𐡔": "ش",
    "𐡕": "ت",
    "ܒ": "ب", "ܓ": "ج", "ܕ": "د", "ܗ": "ه", "ܘ": "و", "ܙ": "ز",
    "ܚ": "ح", "ܛ": "ط", "ܝ": "ي", "ܟ": "ك", "ܠ": "ل", "ܡ": "م",
    "ܢ": "ن", "ܣ": "س", "ܥ": "ع", "ܦ": "ف", "ܨ": "ص", "ܩ": "ق",
    "ܪ": "ر", "ܫ": "ش", "ܬ": "ت",
}
EMPHATIC_ALEPHS = {"א", "𐡀", "ܐ"}


def letters(value: str) -> list[str]:
    return [
        character
        for character in unicodedata.normalize("NFD", value)
        if unicodedata.category(character)[0] != "M"
        and character in SCRIPT_TO_ARABIC | {key: "" for key in EMPHATIC_ALEPHS}
    ]


def direct_form(headword: str, pos: str) -> str | None:
    items = letters(headword)
    if pos in {"noun", "adj"} and items and items[-1] in EMPHATIC_ALEPHS:
        items = items[:-1]
    if len(items) != 3 or any(item not in SCRIPT_TO_ARABIC for item in items):
        return None
    return "".join(SCRIPT_TO_ARABIC[item] for item in items)


def build(db: Path, resources: Path) -> dict:
    connection = sqlite3.connect(db)
    connection.row_factory = sqlite3.Row
    try:
        entries = [
            dict(row)
            for row in connection.execute(
                """
                SELECT entry_id, headword, romanization, pos, gloss, etymology,
                       loan_hint
                FROM entries
                WHERE language='aramaic' AND processing_status!='ineligible-nonlexical'
                ORDER BY entry_id
                """
            )
        ]
        registered_by_entry = {
            row[0]: set()
            for row in connection.execute(
                "SELECT entry_id FROM entries WHERE language='aramaic'"
            )
        }
        for entry_id, form in connection.execute(
            """
            SELECT c.entry_id, c.form
            FROM candidates c
            JOIN entries e ON e.entry_id=c.entry_id
            WHERE e.language='aramaic'
              AND c.kind IN ('root', 'hollow-root')
              AND c.status='licensed'
            """
        ):
            registered_by_entry[entry_id].add(form)
    finally:
        connection.close()

    forms = {
        form
        for entry in entries
        if (form := direct_form(entry["headword"], entry["pos"]))
    }
    matches = matches_for_roots(resources, forms, None)
    records = []
    for entry in entries:
        form = direct_form(entry["headword"], entry["pos"])
        if not form:
            continue
        fan = independent_fan(matches.get(form, []))
        if not fan["judgment_ready"]:
            continue
        registered = form in registered_by_entry.get(entry["entry_id"], set())
        records.append(
            {
                **entry,
                "direct_surface_root": form,
                "already_licensed_candidate": registered,
                "registry_gap": not registered,
                "independent_fan": fan,
            }
        )
    return {
        "schema": "aramaic-direct-surface-fans-v1",
        "contract": {
            "retrieval_only": True,
            "signed_emphatic_aleph_zero_step_only": True,
            "unregistered_hit_is_tool_gap_not_verdict": True,
            "verdicts_written": False,
            "frozen_registry_modified": False,
            "proof_executed": False,
        },
        "summary": {
            "three_consonant_surface_form_count": len(forms),
            "entry_hit_count": len(records),
            "registered_entry_hit_count": sum(
                item["already_licensed_candidate"] for item in records
            ),
            "registry_gap_entry_hit_count": sum(item["registry_gap"] for item in records),
        },
        "records": records,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--resources", type=Path, default=DEFAULT_RESOURCES)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build(args.db.resolve(), args.resources.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Aramaic direct-surface fan audit is missing or stale")
        print(json.dumps(payload["summary"], ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps(payload["summary"], ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
