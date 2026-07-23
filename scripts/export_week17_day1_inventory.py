#!/usr/bin/env python3
"""Build the four author-named Week 17 source inventories and deterministic queues.

Retrieval only: this never writes readings, review states, frozen tools, or proof data.
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from recovery_pipeline.families import member_strength_family_queue
from recovery_pipeline.inventory import build_language, connect, summary, verify_inventory


LANGUAGES = ("persian", "gothic", "old_norse", "welsh")
ROOT = Path(__file__).resolve().parents[1]


def write_json(path: Path, value: object) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def week17_verify(db: Path) -> dict[str, object]:
    """Verify only this isolated retrieval cache, never the shared review ledger."""
    report = verify_inventory(db)
    sources = {item["language"]: item for item in report["sources"]}
    problems: list[str] = []
    if set(sources) != set(LANGUAGES):
        problems.append("four named language sources are not all present")
    for language in LANGUAGES:
        item = sources.get(language, {})
        if not item.get("coverage_complete") or not item.get("source_unchanged"):
            problems.append(f"source pin or complete coverage failed: {language}")
    if report.get("sqlite_quick_check") != "ok":
        problems.append("SQLite quick check failed")
    for key in ("candidate_count_mismatches", "entries_without_family", "family_member_count_mismatches", "forms_without_link_record", "forms_pending_resolution", "oversized_families"):
        if report.get(key):
            problems.append(f"inventory invariant failed: {key}")
    return {
        "week17_passed": not problems,
        "week17_problems": problems,
        "sources": [sources[language] for language in LANGUAGES if language in sources],
        "invariants": {key: report.get(key) for key in (
            "sqlite_quick_check", "candidate_count_mismatches", "entries_without_family",
            "family_member_count_mismatches", "forms_without_link_record",
            "forms_pending_resolution", "oversized_families",
        )},
        "not_a_shared_ledger_check": True,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Week 17 day 1: retrieval-only source inventory and family queues.")
    parser.add_argument("--db", type=Path, default=ROOT / "cache" / "recovery_pipeline" / "week17-day1-inventory.sqlite")
    parser.add_argument("--output-dir", type=Path, default=ROOT / "cache" / "recovery_pipeline" / "week17-day1")
    parser.add_argument("--check", action="store_true", help="Verify a previously built isolated inventory and its exports.")
    parser.add_argument("--export-only", action="store_true", help="Write summaries and queues from a complete existing isolated inventory.")
    args = parser.parse_args()
    db = args.db.resolve()
    output = args.output_dir.resolve()

    if args.check and args.export_only:
        parser.error("--check and --export-only cannot be combined")
    if args.check:
        report = week17_verify(db)
        expected = output / "inventory-summary.json"
        queues = output / "member-strength-queues.json"
        if not expected.exists() or not queues.exists():
            raise FileNotFoundError("Week 17 exported summary or queue is missing")
        summary_payload = json.loads(expected.read_text(encoding="utf-8"))
        if tuple(summary_payload.get("languages", ())) != LANGUAGES:
            raise ValueError("Week 17 summary language order differs")
        if not report["week17_passed"]:
            raise ValueError("Week 17 inventory verification failed")
        print(json.dumps({"check": "passed", "database": str(db), "languages": list(LANGUAGES)}, ensure_ascii=False))
        return 0

    if args.export_only:
        verification = week17_verify(db)
        found = {item["language"] for item in verification["sources"]}
        if found != set(LANGUAGES) or not verification["week17_passed"]:
            raise ValueError("Week 17 export requires a complete verified four-language inventory")
        builds = []
    else:
        builds = [build_language(language, db_path=db) for language in LANGUAGES]
    inventories = {language: summary(db, language) for language in LANGUAGES}
    connection = connect(db, create=False)
    try:
        queues = {
            language: member_strength_family_queue(connection, language, 1_000_000)
            for language in LANGUAGES
        }
    finally:
        connection.close()
    verification = week17_verify(db)
    if not verification["week17_passed"]:
        raise ValueError("Generated Week 17 inventory did not verify")
    write_json(output / "inventory-summary.json", {
        "schema": "week17-day1-inventory-v1",
        "languages": list(LANGUAGES),
        "database": str(db.relative_to(ROOT)).replace("\\", "/"),
        "builds": builds,
        "inventories": inventories,
        "verification": verification,
    })
    write_json(output / "member-strength-queues.json", {
        "schema": "week17-day1-member-strength-queue-v1",
        "languages": list(LANGUAGES),
        "ranking": "best original lexical member: licensed full root, required-row count, meaning richness, stable entry id",
        "queues": queues,
    })
    print(json.dumps({"built": list(LANGUAGES), "database": str(db), "output": str(output)}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
