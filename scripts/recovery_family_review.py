#!/usr/bin/env python3
"""Record two-lens reviews at lexical-family level and explicit member vetoes."""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

from recovery_pipeline.families import (
    FAMILY_REVIEW_STATE,
    FAMILY_REVIEW_STATUSES,
    family_card,
    family_review_queue,
    load_family_review_states,
)
from recovery_pipeline.inventory import DEFAULT_DB, connect


def write_payload(payload: dict) -> None:
    temporary = FAMILY_REVIEW_STATE.with_suffix(FAMILY_REVIEW_STATE.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(FAMILY_REVIEW_STATE)


def require_date(value: str, parser: argparse.ArgumentParser) -> None:
    try:
        date.fromisoformat(value)
    except ValueError:
        parser.error("--date must be a real ISO date in YYYY-MM-DD form")


def require_family(connection: sqlite3.Connection, family_id: str, parser: argparse.ArgumentParser) -> None:
    if connection.execute("SELECT 1 FROM families WHERE family_id=?", (family_id,)).fetchone() is None:
        parser.error(f"family ID is not present in the inventory: {family_id}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Lexical-family review ledger. Family results inherit to members unless a member veto is recorded."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    queue = sub.add_parser("queue")
    queue.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    queue.add_argument("--language")
    queue.add_argument("--processing-status")
    queue.add_argument("--limit", type=int, default=50)

    card = sub.add_parser("card")
    card.add_argument("--family-id", required=True)
    card.add_argument("--candidate-limit", type=int, default=200)

    record = sub.add_parser("record")
    record.add_argument("--family-id", required=True)
    record.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    record.add_argument("--reviewer", required=True)
    record.add_argument("--date", required=True)
    record.add_argument("--result", required=True)
    record.add_argument("--notes", required=True)
    record.add_argument("--loan-screen", choices=("clear", "issue", "unknown"))
    record.add_argument("--homonym-screen", choices=("clear", "issue", "unknown"))
    record.add_argument("--source-check", choices=("clear", "issue", "unknown"))

    status = sub.add_parser("set-status")
    status.add_argument("--family-id", required=True)
    status.add_argument("--status", choices=sorted(FAMILY_REVIEW_STATUSES), required=True)
    status.add_argument("--blocker", default="")

    override = sub.add_parser("override")
    override.add_argument("--family-id", required=True)
    override.add_argument("--entry-id", required=True)
    override.add_argument("--decision", choices=("uphold", "reject", "suspend"), required=True)
    override.add_argument("--reason", required=True)
    override.add_argument("--reviewer", required=True)
    override.add_argument("--date", required=True)

    clear = sub.add_parser("clear-override")
    clear.add_argument("--entry-id", required=True)

    sub.add_parser("validate")
    args = parser.parse_args()

    if args.command == "validate":
        payload = load_family_review_states()
        # A structurally empty ledger has no inventory references to verify.
        # Avoid taking a schema/write lock merely to prove that empty set while
        # a full inventory build is in progress.
        if args.db.exists() and (payload["families"] or payload["member_overrides"]):
            connection = connect(args.db, create=False)
            try:
                missing_families = [
                    family_id for family_id in payload["families"]
                    if connection.execute("SELECT 1 FROM families WHERE family_id=?", (family_id,)).fetchone() is None
                ]
                invalid_overrides = [
                    entry_id for entry_id, item in payload["member_overrides"].items()
                    if connection.execute(
                        "SELECT 1 FROM family_members WHERE entry_id=? AND family_id=?",
                        (entry_id, item["family_id"]),
                    ).fetchone() is None
                ]
            finally:
                connection.close()
            if missing_families or invalid_overrides:
                for family_id in missing_families:
                    print(f"FAIL: review state has no inventory family: {family_id}")
                for entry_id in invalid_overrides:
                    print(f"FAIL: override does not match current family membership: {entry_id}")
                return 1
        print(
            f"family review ledger: CLEAN ({len(payload['families'])} families; "
            f"{len(payload['member_overrides'])} member overrides)"
        )
        return 0

    connection = connect(args.db, create=False)
    try:
        if args.command == "queue":
            print(json.dumps(family_review_queue(
                connection, args.lens, args.language, args.processing_status, args.limit
            ), ensure_ascii=False, indent=2))
            return 0
        if args.command == "card":
            print(json.dumps(family_card(
                connection, args.family_id, args.candidate_limit
            ), ensure_ascii=False, indent=2))
            return 0

        payload = load_family_review_states()
        if args.command in {"record", "set-status", "override"}:
            require_family(connection, args.family_id, parser)
        if args.command == "record":
            require_date(args.date, parser)
            state = payload["families"].setdefault(args.family_id, {"status": "unreviewed"})
            if args.lens == "skeptical" and not state.get("recovery_review"):
                parser.error("skeptical review cannot precede the recovery review")
            event = {
                "reviewer": args.reviewer,
                "date": args.date,
                "result": args.result,
                "notes": args.notes,
            }
            if args.lens == "skeptical":
                missing = [
                    name for name in ("loan_screen", "homonym_screen", "source_check")
                    if getattr(args, name) is None
                ]
                if missing:
                    parser.error("skeptical review requires --loan-screen, --homonym-screen, and --source-check")
                event.update({
                    "loan_screen": args.loan_screen,
                    "homonym_screen": args.homonym_screen,
                    "source_check": args.source_check,
                })
            state[f"{args.lens}_review"] = event
            write_payload(payload)
            load_family_review_states()
            print(f"recorded {args.lens} lens for {args.family_id}")
            return 0
        if args.command == "set-status":
            state = payload["families"].setdefault(args.family_id, {"status": "unreviewed"})
            if args.status == "suspended" and not args.blocker:
                parser.error("suspended status requires --blocker")
            if args.status in {"reviewed", "loan-isolated", "closed"} and (
                not state.get("recovery_review") or not state.get("skeptical_review")
            ):
                parser.error("final family status requires both review lenses")
            state["status"] = args.status
            state["blocker"] = args.blocker
            write_payload(payload)
            load_family_review_states()
            print(f"set {args.family_id} to {args.status}")
            return 0
        if args.command == "override":
            require_date(args.date, parser)
            if connection.execute(
                "SELECT 1 FROM family_members WHERE entry_id=? AND family_id=?",
                (args.entry_id, args.family_id),
            ).fetchone() is None:
                parser.error("entry is not a member of the named family")
            payload["member_overrides"][args.entry_id] = {
                "family_id": args.family_id,
                "decision": args.decision,
                "reason": args.reason,
                "reviewer": args.reviewer,
                "date": args.date,
            }
            write_payload(payload)
            load_family_review_states()
            print(f"recorded member override for {args.entry_id}")
            return 0
        if args.command == "clear-override":
            if args.entry_id not in payload["member_overrides"]:
                parser.error("entry has no member override")
            del payload["member_overrides"][args.entry_id]
            write_payload(payload)
            print(f"cleared member override for {args.entry_id}")
            return 0
    finally:
        connection.close()
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
