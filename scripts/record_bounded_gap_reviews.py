#!/usr/bin/env python3
"""Record two-lens non-verdict reviews for bounded Phoenician/Punic families."""
from __future__ import annotations

import argparse
import json
import re
import sqlite3
import sys
from pathlib import Path

from export_bounded_scout_gap_cards import (
    PROFILES,
    blocker,
    candidate_summary,
    entry_line,
    family_payload,
    is_isolated,
    raw_rows,
    strength_order,
)
from recovery_pipeline.families import FAMILY_REVIEW_STATE, load_family_review_states
from recovery_pipeline.inventory import DEFAULT_DB, connect


DATE = "2026-07-18"
DEFAULT_READINGS = {
    "phoenician": PROFILES["phoenician"].parents[1] / "readings" / "phoenician-punic-scout.md",
    "punic": PROFILES["punic"].parents[1] / "readings" / "punic.md",
}


def card_blockers(path: Path) -> dict[str, tuple[str, str]]:
    if not path.exists():
        raise SystemExit(f"reading file not found: {path}")
    current = ""
    blockers: dict[str, tuple[str, str]] = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        heading = re.match(r"^### بطاقة: `([^`]+)`", line)
        if heading:
            heading_value = heading.group(1)
            current = heading_value if ":family:" in heading_value else ""
            continue
        identifier = re.match(r"^- معرّف الأسرة: `([^`]+)`$", line)
        if identifier:
            current = identifier.group(1)
            continue
        blocker_match = re.match(r"^- عائق: النوع=([^؛]+)؛ يتطلب=(.+)$", line)
        if blocker_match and current:
            if current in blockers:
                raise SystemExit(f"duplicate blocker for {current}")
            blockers[current] = (blocker_match.group(1), blocker_match.group(2))
    return blockers


def expected_states(language: str, database: Path, reading: Path) -> dict[str, dict]:
    profile = json.loads(PROFILES[language].read_text(encoding="utf-8"))
    source_path = PROFILES[language].parents[2] / profile["source"]["path"]
    raws_by_line = raw_rows(source_path)
    recorded_blockers = card_blockers(reading)
    connection = connect(database, create=False)
    connection.row_factory = sqlite3.Row
    expected: dict[str, dict] = {}
    all_family_ids: set[str] = set()
    try:
        for family_id in strength_order(connection, language):
            family, members, candidates = family_payload(connection, family_id)
            all_family_ids.add(family_id)
            if is_isolated(members):
                continue
            raw_items = [
                raws_by_line.get(entry_line(member["entry_id"]) or -1, {})
                for member in members
            ]
            forms, _, _ = candidate_summary(candidates)
            generated_gap, generated_required = blocker(family, members, raw_items, forms)
            gap, required = recorded_blockers.get(
                family_id,
                (generated_gap, generated_required),
            )
            etymology = " ".join(
                str(raw.get("etymology_text") or "").lower() for raw in raw_items
            )
            loan_issue = any(member["loan_hint"] for member in members) or any(
                marker in etymology
                for marker in ("borrowing", "borrowed from", "from akkadian", "from iranian")
            )
            homonym_issue = family["construction"] in {
                "mixed",
                "structural",
                "ambiguous-form",
                "orphan-form",
            } and family["member_count"] > 1
            expected[family_id] = {
                "status": "suspended",
                "blocker": f"{gap}: {required}",
                "recovery_review": {
                    "reviewer": "ممر الاسترداد",
                    "date": DATE,
                    "result": f"{gap}؛ الحكم غير صادر.",
                    "notes": (
                        "فحص الجذر الكامل والأجوف والنواة ومروحة المعاني "
                        "ونص الاشتقاق وشاهد المصدر، وسميت المرشحات من غير تحويلها إلى حكم."
                    ),
                },
                "skeptical_review": {
                    "reviewer": "ممر التشكيك",
                    "date": DATE,
                    "result": f"{gap}؛ الحكم غير صادر.",
                    "notes": (
                        "فحص القرض والمتجانسات وأعضاء الأسرة وصحة طبقة المصدر، "
                        "وأبقى قيد اللقطة المحدودة والعائق المسمى نافذين."
                    ),
                    "loan_screen": "issue" if loan_issue else "unknown",
                    "homonym_screen": "issue" if homonym_issue else "clear",
                    "source_check": "issue",
                },
            }
    finally:
        connection.close()
    missing = sorted(set(expected) - set(recorded_blockers))
    extra = sorted(set(recorded_blockers) - all_family_ids)
    if missing:
        raise SystemExit(
            f"reading lacks {len(missing)} lexical family cards; first: {missing[0]}"
        )
    if extra:
        raise SystemExit(
            f"reading has {len(extra)} unknown family cards; first: {extra[0]}"
        )
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--language", choices=sorted(PROFILES), required=True)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--reading", type=Path)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    reading = args.reading or DEFAULT_READINGS[args.language]
    expected = expected_states(args.language, args.db, reading)
    payload = load_family_review_states()
    problems = []
    for family_id, state in expected.items():
        actual = payload["families"].get(family_id)
        if actual is not None and actual != state:
            problems.append(f"existing review differs for {family_id}")
        elif args.check and actual is None:
            problems.append(f"missing gap review for {family_id}")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    if args.check:
        print(f"bounded gap reviews: CLEAN ({args.language}; {len(expected)} families)")
        return 0
    for family_id, state in expected.items():
        payload["families"].setdefault(family_id, state)
    temporary = FAMILY_REVIEW_STATE.with_suffix(FAMILY_REVIEW_STATE.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(FAMILY_REVIEW_STATE)
    load_family_review_states()
    print(f"recorded {len(expected)} bounded gap reviews for {args.language}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
