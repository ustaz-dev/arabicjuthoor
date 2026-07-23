#!/usr/bin/env python3
"""Inventory every structured difficult-word card for the Week 17 clinic.

This is retrieval and accountability infrastructure only.  It reads the
language reading files, identifies cards whose structured closure/blocker
fields contain OPEN-CANDIDATE or MORPHOLOGY-GAP, and writes a deterministic
queue.  It recognizes either the card-specific clinic marker or a named
Week 17 deep-reading marker as attempt evidence.  It does not refresh the
shared recovery ledger, alter a verdict, or run the proof line.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DEFAULT_OUTPUT = (
    ROOT / "cache" / "recovery_pipeline" / "week17-day6-difficult-word-clinic.json"
)
TARGET_STATES = ("OPEN-CANDIDATE", "MORPHOLOGY-GAP")
ATTEMPT_MARKER = re.compile(
    r"<!--\s*WEEK17-CLINIC-ATTEMPT:([0-9a-f]{16})\s*-->"
)
DEEP_ATTEMPT_MARKER = re.compile(
    r"<!--\s*(WEEK17-WELSH-DEEP:\d{3})\s*-->"
)
HEADING = re.compile(r"^### بطاقة.*$", re.MULTILINE)
PLACEHOLDER_HEADING = re.compile(r"<[^>]+>")
STRUCTURED_STATE_LINE = re.compile(
    r"^-\s*(?:حالةُ?\s+الإغلاق|عائق)\s*:\s*(.+)$",
    re.MULTILINE,
)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def normalized_text(path: Path) -> str:
    text = path.read_text(encoding="utf-8")
    if unicodedata.normalize("NFC", text) != text:
        raise ValueError(f"Reading file is not NFC: {path.relative_to(ROOT)}")
    return text


def line_number(body: str, offset: int) -> int:
    return body.count("\n", 0, offset) + 1


def field(section: str, names: tuple[str, ...]) -> str:
    for name in names:
        match = re.search(rf"^-\s*{re.escape(name)}:\s*(.+)$", section, re.MULTILINE)
        if match:
            return match.group(1).strip()
    return ""


def clinic_id(relative_path: str, heading: str, ordinal: int) -> str:
    material = f"{relative_path}\0{heading}\0{ordinal}".encode("utf-8")
    return sha256_bytes(material)[:16]


def cards_from_file(path: Path) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    body = normalized_text(path)
    relative = path.relative_to(ROOT).as_posix()
    starts = list(HEADING.finditer(body))
    difficult: list[dict[str, Any]] = []
    all_cards: list[dict[str, Any]] = []
    heading_counts: Counter[str] = Counter()
    for index, match in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(body)
        section = body[match.start():end]
        heading = match.group(0)
        # Several reading files preserve the literal RECOVERY-v2 example card
        # above the real ledger.  It is a protocol template, not a lexical
        # candidate, and must never enter the clinic denominator.
        if PLACEHOLDER_HEADING.search(heading):
            continue
        heading_counts[heading] += 1
        ordinal = heading_counts[heading]
        identifier = clinic_id(relative, heading, ordinal)
        structured_lines = STRUCTURED_STATE_LINE.findall(section)
        states = [
            state
            for state in TARGET_STATES
            if any(state in value for value in structured_lines)
        ]
        marker_ids = ATTEMPT_MARKER.findall(section)
        deep_marker_ids = DEEP_ATTEMPT_MARKER.findall(section)
        if marker_ids and marker_ids != [identifier]:
            raise ValueError(
                f"Clinic marker mismatch in {relative}:{line_number(body, match.start())}: "
                f"expected={identifier}, found={marker_ids}"
            )
        if len(deep_marker_ids) > 1:
            raise ValueError(
                f"Multiple deep-attempt markers in {relative}:"
                f"{line_number(body, match.start())}: {deep_marker_ids}"
            )
        attempt_evidence = marker_ids or deep_marker_ids
        record = {
            "clinic_id": identifier,
            "path": relative,
            "line": line_number(body, match.start()),
            "heading": heading,
            "heading_ordinal": ordinal,
            "card_sha256": sha256_bytes(section.encode("utf-8")),
            "state_tokens": states,
            "structured_state_lines": structured_lines,
            "branch_word": field(section, ("الكلمةُ في الفرع", "الكلمة في الفرع")),
            "oldest_form": field(
                section, ("أقدمُ صورةٍ مستعادة", "أقدم صورة مستعادة")
            ),
            "comparison_degree": field(
                section, ("درجةُ المقارنة", "درجة المقارنة")
            ),
            "sound_path": field(section, ("مسارُ الصوت", "مسار الصوت")),
            "closure": field(section, ("حالةُ الإغلاق", "حالة الإغلاق")),
            "blocker": field(section, ("عائق",)),
            "attempt_marker": attempt_evidence[0] if attempt_evidence else None,
            "attempt_evidence_kind": (
                "clinic-id" if marker_ids else
                "named-deep-reading" if deep_marker_ids else
                None
            ),
            "attempt_recorded": bool(attempt_evidence),
        }
        all_cards.append(record)
        if states:
            difficult.append(record)
    return all_cards, difficult


def build_payload() -> dict[str, Any]:
    all_cards: list[dict[str, Any]] = []
    queue: list[dict[str, Any]] = []
    files = sorted(path for path in READINGS.glob("*.md") if path.name != "README.md")
    for path in files:
        cards, difficult = cards_from_file(path)
        all_cards.extend(cards)
        queue.extend(difficult)
    queue.sort(key=lambda item: (
        item["attempt_recorded"],
        item["path"],
        item["line"],
        item["clinic_id"],
    ))
    duplicate_ids = [
        identifier
        for identifier, count in Counter(item["clinic_id"] for item in all_cards).items()
        if count > 1
    ]
    if duplicate_ids:
        raise ValueError(f"Duplicate clinic ids: {duplicate_ids[:5]}")
    state_counts = Counter(
        state for item in queue for state in item["state_tokens"]
    )
    attempted_ids = {
        item["clinic_id"] for item in all_cards if item["attempt_recorded"]
    }
    still_difficult_ids = {item["clinic_id"] for item in queue}
    attempted_still_difficult = attempted_ids.intersection(still_difficult_ids)
    resolved_attempt_ids = attempted_ids.difference(still_difficult_ids)
    return {
        "schema": "week17-difficult-word-clinic-v1",
        "contract": {
            "retrieval_only": True,
            "shared_ledger_touched": False,
            "verdicts_written": False,
            "proof_executed": False,
            "attempt_marker_is_not_a_positive_verdict": True,
            "named_deep_reading_marker_is_attempt_evidence": True,
            "required_ladder": ["root", "hollow", "nucleus", "orbit"],
        },
        "readings_directory": READINGS.relative_to(ROOT).as_posix(),
        "reading_file_count": len(files),
        "card_count": len(all_cards),
        "difficult_card_count": len(queue),
        "state_counts": dict(sorted(state_counts.items())),
        "attempted_count": len(attempted_ids),
        "attempted_still_difficult_count": len(attempted_still_difficult),
        "resolved_attempt_count": len(resolved_attempt_ids),
        "remaining_count": sum(not item["attempt_recorded"] for item in queue),
        "queue": queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Week 17 OPEN-CANDIDATE/MORPHOLOGY-GAP clinic queue."
    )
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_payload()
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Week 17 difficult-word clinic queue is missing or stale")
        print(json.dumps({
            "check": "passed",
            "cards": payload["card_count"],
            "difficult": payload["difficult_card_count"],
            "attempted": payload["attempted_count"],
            "resolved_attempts": payload["resolved_attempt_count"],
            "remaining": payload["remaining_count"],
        }, ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({
        "output": str(output),
        "cards": payload["card_count"],
        "difficult": payload["difficult_card_count"],
        "attempted": payload["attempted_count"],
        "resolved_attempts": payload["resolved_attempt_count"],
        "remaining": payload["remaining_count"],
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
