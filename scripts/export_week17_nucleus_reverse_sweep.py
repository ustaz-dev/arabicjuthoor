#!/usr/bin/env python3
"""Reverse-scan the 28 leading frozen field-card nuclei across ten lexicons.

The output is a retrieval queue, not a verdict.  It reads the two isolated,
already complete recovery inventories and never touches review states, the
shared ledger, frozen tools, or proof execution.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
FIELD_CARDS = ROOT / "03-scholar-extracts" / "nucleus-field-cards-draft.md"
DEFAULT_DATABASES = (
    ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite",
    ROOT / "cache" / "recovery_pipeline" / "week17-day1-inventory.sqlite",
)
DEFAULT_OUTPUT = ROOT / "cache" / "recovery_pipeline" / "week17-day5-nucleus-reverse-sweep.json"
TARGET_LANGUAGES = (
    "aramaic", "hebrew", "coptic", "egyptian", "latin", "ancient_greek",
    "persian", "gothic", "old_norse", "welsh",
)
NONLEXICAL_POS = {
    "name", "character", "symbol", "punct", "suffix", "prefix", "affix",
    "infix", "circumfix", "interfix", "combining_form",
}
FORM_GLOSS = re.compile(
    r"^\s*(?:alternative form|alternative spelling|inflection|form|romanization)"
    r"\s+of\b",
    re.IGNORECASE,
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def leading_nuclei(path: Path) -> list[dict[str, Any]]:
    pattern = re.compile(r"^### بطاقة ([^\s(]+)")
    cards: list[dict[str, Any]] = []
    for line in path.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        display = match.group(1)
        form = display.replace("-", "")
        dissolved = form == "مو"
        cards.append({
            "display": display,
            "nucleus": form,
            "effective_nucleus": "مه" if dissolved else form,
            "dissolved_redirect": dissolved,
        })
    if len(cards) != 28:
        raise ValueError(f"Expected 28 leading field cards, found {len(cards)}")
    if len({item["nucleus"] for item in cards}) != 28:
        raise ValueError("Leading field-card nucleus identifiers are not unique")
    return cards


def database_languages(connection: sqlite3.Connection) -> set[str]:
    return {row[0] for row in connection.execute("SELECT DISTINCT language FROM entries")}


def scan_database(
    database: Path,
    nuclei: list[dict[str, Any]],
    queue_limit: int,
) -> tuple[dict[tuple[str, str], dict[str, Any]], dict[str, Any]]:
    connection = sqlite3.connect(database)
    connection.row_factory = sqlite3.Row
    output: dict[tuple[str, str], dict[str, Any]] = {}
    try:
        present = database_languages(connection)
        selected_languages = [language for language in TARGET_LANGUAGES if language in present]
        for card in nuclei:
            effective = card["effective_nucleus"]
            for language in selected_languages:
                raw_rows = connection.execute(
                    """
                    SELECT e.language, e.entry_id, e.headword, e.romanization,
                           e.pos, e.gloss, e.loan_hint, e.form_of,
                           e.processing_status, fm.family_id, fm.role AS family_role,
                           c.status, c.rule_ids_json, c.route_flag
                    FROM candidates AS c
                    JOIN entries AS e ON e.entry_id=c.entry_id
                    JOIN family_members AS fm ON fm.entry_id=e.entry_id
                    WHERE e.language=? AND c.kind='nucleus' AND c.form=?
                    ORDER BY e.entry_id, c.status, c.route_flag, c.rule_ids_json
                    """,
                    (language, effective),
                ).fetchall()
                grouped: dict[str, dict[str, Any]] = {}
                excluded = Counter()
                for row in raw_rows:
                    if row["form_of"] or row["family_role"] in {"form", "nonlexical"}:
                        excluded["form_or_nonlexical"] += 1
                        continue
                    # Some Kaikki alternative-form rows retain a blank form_of
                    # target and may be promoted to a family root by the family
                    # resolver.  Their published gloss still names the relation.
                    # Keep the exclusion explicit rather than silently treating
                    # a spelling/form pointer as an independent lexical member.
                    if FORM_GLOSS.match(row["gloss"] or ""):
                        excluded["form_gloss_without_target"] += 1
                        continue
                    if row["pos"] in NONLEXICAL_POS:
                        excluded["proper_or_morpheme"] += 1
                        continue
                    if row["loan_hint"]:
                        excluded["source_marked_loan"] += 1
                        continue
                    item = grouped.setdefault(row["entry_id"], {
                        "entry_id": row["entry_id"],
                        "family_id": row["family_id"],
                        "headword": row["headword"],
                        "romanization": row["romanization"],
                        "pos": row["pos"],
                        "gloss": row["gloss"],
                        "processing_status": row["processing_status"],
                        "paths": [],
                    })
                    item["paths"].append({
                        "status": row["status"],
                        "rule_ids": json.loads(row["rule_ids_json"]),
                        "route_required": bool(row["route_flag"]),
                    })
                entries = list(grouped.values())
                for item in entries:
                    item["paths"].sort(key=lambda path: (
                        0 if path["status"] == "licensed" else 1,
                        path["route_required"],
                        len(path["rule_ids"]),
                        path["rule_ids"],
                    ))
                    best = item["paths"][0]
                    item["best_status"] = best["status"]
                    item["best_rule_count"] = len(best["rule_ids"])
                    item["best_route_required"] = best["route_required"]
                entries.sort(key=lambda item: (
                    0 if item["best_status"] == "licensed" else 1,
                    item["best_route_required"],
                    item["best_rule_count"],
                    -len(item["gloss"].strip()),
                    item["entry_id"],
                ))
                family_seen: set[str] = set()
                family_queue = []
                for item in entries:
                    if item["family_id"] in family_seen:
                        continue
                    family_seen.add(item["family_id"])
                    family_queue.append(item)
                    if len(family_queue) >= queue_limit:
                        break
                output[(card["nucleus"], language)] = {
                    "requested_nucleus": card["nucleus"],
                    "effective_nucleus": effective,
                    "dissolved_redirect": card["dissolved_redirect"],
                    "language": language,
                    "raw_candidate_paths": len(raw_rows),
                    "eligible_entries": len(entries),
                    "eligible_families": len({item["family_id"] for item in entries}),
                    "excluded_paths": dict(sorted(excluded.items())),
                    "queue_limit": queue_limit,
                    "queue": family_queue,
                }
        metadata = {
            "database": str(database.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(database),
            "languages": selected_languages,
        }
        return output, metadata
    finally:
        connection.close()


def build_payload(databases: tuple[Path, ...], queue_limit: int) -> dict[str, Any]:
    nuclei = leading_nuclei(FIELD_CARDS)
    combined: dict[tuple[str, str], dict[str, Any]] = {}
    database_metadata = []
    seen_languages: set[str] = set()
    for database in databases:
        scanned, metadata = scan_database(database, nuclei, queue_limit)
        overlap = set(scanned).intersection(combined)
        if overlap:
            raise ValueError(f"Languages appear in multiple reverse-sweep databases: {sorted(overlap)[:3]}")
        combined.update(scanned)
        database_metadata.append(metadata)
        seen_languages.update(metadata["languages"])
    if seen_languages != set(TARGET_LANGUAGES):
        raise ValueError(
            "Ten-language reverse sweep is incomplete: "
            f"missing={sorted(set(TARGET_LANGUAGES) - seen_languages)}, "
            f"extra={sorted(seen_languages - set(TARGET_LANGUAGES))}"
        )
    missing_pairs = [
        (card["nucleus"], language)
        for card in nuclei
        for language in TARGET_LANGUAGES
        if (card["nucleus"], language) not in combined
    ]
    if missing_pairs:
        raise ValueError(f"Reverse sweep lacks nucleus-language pairs: {missing_pairs[:5]}")
    rows = [
        combined[(card["nucleus"], language)]
        for card in nuclei
        for language in TARGET_LANGUAGES
    ]
    leaked_form_glosses = [
        item["entry_id"]
        for row in rows
        for item in row["queue"]
        if FORM_GLOSS.match(item["gloss"] or "")
    ]
    if leaked_form_glosses:
        raise ValueError(
            "Alternative/form glosses leaked into the reverse queue: "
            f"{leaked_form_glosses[:5]}"
        )
    redirects = [card for card in nuclei if card["dissolved_redirect"]]
    if (
        len(redirects) != 1
        or redirects[0]["nucleus"] != "مو"
        or redirects[0]["effective_nucleus"] != "مه"
    ):
        raise ValueError("The dissolved مو field card must redirect once and only once to مه")
    return {
        "schema": "week17-leading-nuclei-reverse-sweep-v1",
        "contract": {
            "retrieval_only": True,
            "verdicts_written": False,
            "proof_executed": False,
            "shared_ledger_touched": False,
            "queue_is_not_a_trace_claim": True,
        },
        "field_cards": {
            "path": str(FIELD_CARDS.relative_to(ROOT)).replace("\\", "/"),
            "sha256": sha256(FIELD_CARDS),
            "nuclei": nuclei,
        },
        "languages": list(TARGET_LANGUAGES),
        "databases": database_metadata,
        "pair_count": len(rows),
        "pairs": rows,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reverse-scan the 28 leading frozen nuclei across ten lexicons."
    )
    parser.add_argument("--main-db", type=Path, default=DEFAULT_DATABASES[0])
    parser.add_argument("--week17-db", type=Path, default=DEFAULT_DATABASES[1])
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--queue-limit", type=int, default=50)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if args.queue_limit < 1:
        parser.error("--queue-limit must be positive")
    payload = build_payload(
        (args.main_db.resolve(), args.week17_db.resolve()),
        args.queue_limit,
    )
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Week 17 nucleus reverse-sweep output is missing or stale")
        print(json.dumps({
            "check": "passed",
            "pairs": payload["pair_count"],
            "languages": len(payload["languages"]),
            "nuclei": len(payload["field_cards"]["nuclei"]),
        }, ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({
        "output": str(output),
        "pairs": payload["pair_count"],
        "languages": len(payload["languages"]),
        "nuclei": len(payload["field_cards"]["nuclei"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
