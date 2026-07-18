#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from recovery_pipeline.inventory import (
    DEFAULT_DB,
    build_language,
    connect,
    install_review_overlay,
    profile_check,
    refresh_family_metadata,
    review_queue,
    summary,
    upgrade_family_layer_from_v2,
    verify_inventory,
)
from recovery_pipeline.families import family_card, family_review_queue
from recovery_pipeline.normalization import available_profiles, load_profile


def source_languages() -> list[str]:
    return [language for language in available_profiles() if load_profile(language).get("source")]


def main() -> int:
    parser = argparse.ArgumentParser(description="Corpus-wide recovery inventory. Retrieval only; no verdicts.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    build = sub.add_parser("build", help="Inventory and candidate-scan an entire source snapshot.")
    build.add_argument("--language", choices=source_languages())
    build.add_argument("--all", action="store_true")
    build.add_argument("--limit", type=int, help="Diagnostic sample only; omitting it means full source coverage.")

    upgrade = sub.add_parser(
        "upgrade-v2", help="Rebuild lexical families while reusing a proven-equivalent complete schema-v2 scan."
    )
    upgrade.add_argument("--language", choices=source_languages(), required=True)
    upgrade.add_argument("--source-db", type=Path, required=True)

    refresh = sub.add_parser(
        "refresh-families", help="Refresh typed family links from the pinned source without rerunning the full scan."
    )
    refresh.add_argument("--language", choices=source_languages())
    refresh.add_argument("--all", action="store_true")

    report = sub.add_parser("summary", help="Count every processing and human-review state.")
    report.add_argument("--language", choices=source_languages())

    sub.add_parser("verify", help="Verify source snapshots, counts, mappings, and review-overlay integrity.")

    check = sub.add_parser("profile-check", help="Strictly normalize a deterministic source sample.")
    check.add_argument("--language", choices=source_languages())
    check.add_argument("--all", action="store_true")
    check.add_argument("--sample", type=int, default=1000)

    query = sub.add_parser("query", help="Inspect inventory entries without changing state.")
    query.add_argument("--language", choices=source_languages())
    query.add_argument("--review-status")
    query.add_argument("--processing-status")
    query.add_argument("--word")
    query.add_argument("--limit", type=int, default=25)

    candidates = sub.add_parser("candidates", help="Inspect every aggregated candidate for one stable entry ID.")
    candidates.add_argument("--entry-id", required=True)

    queue = sub.add_parser("review-queue", help="List work for one of the two mandatory review lenses.")
    queue.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    queue.add_argument("--language", choices=source_languages())
    queue.add_argument("--limit", type=int, default=50)

    family_queue = sub.add_parser("family-queue", help="List lexical-family cards for one review lens.")
    family_queue.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    family_queue.add_argument("--language", choices=source_languages())
    family_queue.add_argument("--processing-status")
    family_queue.add_argument("--limit", type=int, default=50)
    family_queue.add_argument(
        "--order",
        choices=("family-id", "strength"),
        default="family-id",
        help="Deterministic family-id order or retrieval-only strength order.",
    )

    card = sub.add_parser("family-card", help="Inspect one family, its members, overrides, and unified candidates.")
    card.add_argument("--family-id", required=True)
    card.add_argument("--candidate-limit", type=int, default=200)

    args = parser.parse_args()
    if args.command == "build":
        languages = source_languages() if args.all else [args.language]
        if not all(languages):
            parser.error("build requires --language or --all")
        for language in languages:
            print(json.dumps(build_language(language, db_path=args.db, limit=args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.command == "summary":
        try:
            print(json.dumps(summary(args.db, args.language), ensure_ascii=False, indent=2))
            return 0
        except (FileNotFoundError, sqlite3.Error) as error:
            print(f"inventory summary failed: {error}")
            return 1
    if args.command == "upgrade-v2":
        try:
            print(json.dumps(upgrade_family_layer_from_v2(
                args.language, source_db=args.source_db, db_path=args.db
            ), ensure_ascii=False, indent=2))
            return 0
        except (FileNotFoundError, sqlite3.Error, ValueError, RuntimeError) as error:
            print(f"schema-v2 upgrade failed: {error}")
            return 1
    if args.command == "refresh-families":
        languages = source_languages() if args.all else [args.language]
        if not all(languages):
            parser.error("refresh-families requires --language or --all")
        try:
            for language in languages:
                print(json.dumps(refresh_family_metadata(language, db_path=args.db), ensure_ascii=False, indent=2))
            return 0
        except (FileNotFoundError, sqlite3.Error, ValueError, RuntimeError) as error:
            print(f"family metadata refresh failed: {error}")
            return 1
    if args.command == "verify":
        try:
            result = verify_inventory(args.db)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return int(not result["passed"])
        except (FileNotFoundError, sqlite3.Error) as error:
            print(f"inventory verification failed: {error}")
            return 1
    if args.command == "profile-check":
        languages = source_languages() if args.all else [args.language]
        if not all(languages):
            parser.error("profile-check requires --language or --all")
        failed = False
        for language in languages:
            result = profile_check(language, sample=args.sample)
            print(json.dumps(result, ensure_ascii=False, indent=2))
            failed |= not result["passed"]
        return int(failed)
    if args.command == "review-queue":
        try:
            print(json.dumps(review_queue(args.db, args.lens, args.language, args.limit), ensure_ascii=False, indent=2))
            return 0
        except (FileNotFoundError, sqlite3.Error) as error:
            print(f"review queue failed: {error}")
            return 1
    if args.command == "family-queue":
        connection = connect(args.db, create=False)
        try:
            result = family_review_queue(
                connection, args.lens, args.language, args.processing_status, args.limit, args.order
            )
            print(json.dumps(result, ensure_ascii=False, indent=2))
            return 0
        except (FileNotFoundError, sqlite3.Error, ValueError) as error:
            print(f"family queue failed: {error}")
            return 1
        finally:
            connection.close()
    if args.command == "family-card":
        connection = connect(args.db, create=False)
        try:
            print(json.dumps(
                family_card(connection, args.family_id, args.candidate_limit), ensure_ascii=False, indent=2
            ))
            return 0
        except (FileNotFoundError, sqlite3.Error, ValueError, KeyError) as error:
            print(f"family card failed: {error}")
            return 1
        finally:
            connection.close()
    if args.command == "query":
        connection = connect(args.db, create=False)
        try:
            install_review_overlay(connection)
            clauses, params = [], []
            for column, value in (("e.language", args.language),
                                  ("COALESCE(o.status, 'unreviewed')", args.review_status),
                                  ("e.processing_status", args.processing_status)):
                if value:
                    clauses.append(f"{column}=?")
                    params.append(value)
            if args.word:
                clauses.append("e.headword LIKE ?")
                params.append(f"%{args.word}%")
            where = " WHERE " + " AND ".join(clauses) if clauses else ""
            rows = connection.execute(
                "SELECT e.entry_id, e.language, e.headword, e.romanization, e.gloss, e.processing_status, "
                "COALESCE(o.status, 'unreviewed'), e.candidate_count, e.loan_hint, "
                "e.source_stratum, e.source_scope_note FROM entries e "
                "LEFT JOIN review_overlay o ON o.entry_id=e.entry_id" + where
                + " ORDER BY e.language, e.entry_id LIMIT ?",
                (*params, args.limit),
            ).fetchall()
            fields = ("entry_id", "language", "headword", "romanization", "gloss", "processing_status",
                      "review_status", "candidate_count", "loan_hint", "source_stratum", "source_scope_note")
            print(json.dumps([dict(zip(fields, row)) for row in rows], ensure_ascii=False, indent=2))
        except (FileNotFoundError, sqlite3.Error) as error:
            print(f"inventory query failed: {error}")
            return 1
        finally:
            connection.close()
        return 0
    if args.command == "candidates":
        connection = connect(args.db, create=False)
        try:
            rows = connection.execute(
                "SELECT c.kind, c.form, a.reading, c.status, c.positions_json, c.rule_ids_json, c.route_flag "
                "FROM candidates c LEFT JOIN arabic_forms a ON a.form=c.form AND a.kind=c.kind "
                "WHERE c.entry_id=? ORDER BY CASE c.status WHEN 'licensed' THEN 0 "
                "WHEN 'manual-condition' THEN 1 ELSE 2 END, c.kind, c.form",
                (args.entry_id,),
            ).fetchall()
            fields = ("kind", "form", "reading", "status", "positions", "rule_ids", "route_required")
            payload = []
            for row in rows:
                item = dict(zip(fields, row))
                item["positions"] = json.loads(item["positions"])
                item["rule_ids"] = json.loads(item["rule_ids"])
                item["route_required"] = bool(item["route_required"])
                payload.append(item)
            print(json.dumps(payload, ensure_ascii=False, indent=2))
        except (FileNotFoundError, sqlite3.Error) as error:
            print(f"candidate query failed: {error}")
            return 1
        finally:
            connection.close()
        return 0
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
