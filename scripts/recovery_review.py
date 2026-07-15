#!/usr/bin/env python3
"""Record the two independent review lenses without making their decisions.

The recovery lens searches for missed candidates. The skeptical lens separately
checks loan routes, homonyms, and source accuracy. Final states require both.
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import date
from pathlib import Path

from recovery_pipeline.inventory import DEFAULT_DB, REVIEW_STATE, REVIEW_STATUSES, load_review_states, review_queue


def load_payload() -> dict:
    return json.loads(REVIEW_STATE.read_text(encoding="utf-8"))


def write_payload(payload: dict) -> None:
    temporary = REVIEW_STATE.with_suffix(REVIEW_STATE.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(REVIEW_STATE)


def missing_entry_ids(path: Path, entry_ids: set[str]) -> list[str]:
    if not path.exists():
        raise FileNotFoundError(f"Recovery inventory does not exist: {path}")
    connection = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    try:
        return sorted(
            entry_id for entry_id in entry_ids
            if connection.execute("SELECT 1 FROM entries WHERE entry_id=?", (entry_id,)).fetchone() is None
        )
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description="Balanced human review ledger; the tool never chooses a result.")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    sub = parser.add_subparsers(dest="command", required=True)

    queue = sub.add_parser("queue")
    queue.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    queue.add_argument("--language")
    queue.add_argument("--limit", type=int, default=50)

    record = sub.add_parser("record")
    record.add_argument("--entry-id", required=True)
    record.add_argument("--lens", choices=("recovery", "skeptical"), required=True)
    record.add_argument("--reviewer", required=True)
    record.add_argument("--date", required=True, help="YYYY-MM-DD")
    record.add_argument("--result", required=True)
    record.add_argument("--notes", required=True)
    record.add_argument("--loan-screen", choices=("clear", "issue", "unknown"))
    record.add_argument("--homonym-screen", choices=("clear", "issue", "unknown"))
    record.add_argument("--source-check", choices=("clear", "issue", "unknown"))

    status = sub.add_parser("set-status")
    status.add_argument("--entry-id", required=True)
    status.add_argument("--status", choices=sorted(REVIEW_STATUSES), required=True)
    status.add_argument("--blocker", default="")

    sub.add_parser("validate")
    args = parser.parse_args()

    if args.command == "queue":
        print(json.dumps(review_queue(args.db, args.lens, args.language, args.limit), ensure_ascii=False, indent=2))
        return 0
    if args.command == "validate":
        states = load_review_states()
        if args.db.exists():
            orphaned = missing_entry_ids(args.db, set(states))
            if orphaned:
                for entry_id in orphaned:
                    print(f"FAIL: review state has no inventory entry: {entry_id}")
                return 1
        print(f"balanced review ledger: CLEAN ({len(states)} explicit states)")
        return 0

    payload = load_payload()
    try:
        missing = missing_entry_ids(args.db, {args.entry_id})
    except (FileNotFoundError, sqlite3.Error) as error:
        parser.error(str(error))
    if missing:
        parser.error(f"entry ID is not present in the inventory: {args.entry_id}")
    state = payload["entries"].setdefault(args.entry_id, {"status": "unreviewed"})
    if args.command == "record":
        try:
            date.fromisoformat(args.date)
        except ValueError:
            parser.error("--date must be a real ISO date in YYYY-MM-DD form")
        event = {"reviewer": args.reviewer, "date": args.date, "result": args.result, "notes": args.notes}
        if args.lens == "skeptical":
            missing = [name for name in ("loan_screen", "homonym_screen", "source_check") if getattr(args, name) is None]
            if missing:
                parser.error("skeptical review requires --loan-screen, --homonym-screen, and --source-check")
            event.update({
                "loan_screen": args.loan_screen,
                "homonym_screen": args.homonym_screen,
                "source_check": args.source_check,
            })
        state[f"{args.lens}_review"] = event
        write_payload(payload)
        load_review_states()
        print(f"recorded {args.lens} lens for {args.entry_id}")
        return 0
    if args.command == "set-status":
        if args.status == "suspended" and not args.blocker:
            parser.error("suspended status requires --blocker")
        if args.status in {"reviewed", "loan-isolated", "closed"} and (
            not state.get("recovery_review") or not state.get("skeptical_review")
        ):
            parser.error("final status requires both recovery and skeptical reviews")
        state["status"] = args.status
        state["blocker"] = args.blocker
        write_payload(payload)
        load_review_states()
        print(f"set {args.entry_id} to {args.status}")
        return 0
    return 1


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
