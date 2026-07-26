#!/usr/bin/env python3
"""Backfill the charter's structured obstacle line on suspended reading cards.

The recovery ledger accepts the structured ``- عائق: النوع=...؛ يتطلب=...``
line as the current state.  Older cards sometimes record the same state only
in ``حالة الإغلاق``.  This formatter copies that already-issued state into the
machine-readable field; it never changes a verdict or invents a new blocker.
"""
from __future__ import annotations

import argparse
import json
import re
from collections import Counter
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
GAPS = (
    "TOOL-GAP",
    "LAW-GAP",
    "SOURCE-GAP",
    "OPEN-CANDIDATE",
    "MORPHOLOGY-GAP",
)
REQUIRES = {
    "TOOL-GAP": "مسح الأداة أو المروحة المسماة في البطاقة",
    "LAW-GAP": "صف صوتي منشور وموقع يحسم المسار المذكور في البطاقة",
    "SOURCE-GAP": "مصدر منشور مسمى يحسم الإسناد أو المسار المذكور في البطاقة",
    "OPEN-CANDIDATE": "جسر دلالي موثق أو شاهد أقدم يحسم المرشح",
    "MORPHOLOGY-GAP": "تحليل صرفي منشور يحسم الصورة المذكورة في البطاقة",
}
CARD_START = re.compile(r"(?=^### )", re.MULTILINE)
STRUCTURED = re.compile(
    r"^-\s*عائق:\s*النوع\s*=\s*[A-Z\-]+\s*[؛;]\s*يتطلب\s*=",
    re.MULTILINE,
)
CLOSURE = re.compile(
    r"^(?P<prefix>-\s*حالةُ?\s*الإغلاق[^\n]*?:\s*)"
    r"(?P<value>[^\n]+)$",
    re.MULTILINE,
)


def first_gap(value: str) -> str:
    positions = [(value.find(gap), gap) for gap in GAPS if gap in value]
    return min(positions)[1] if positions else ""


def transform(text: str) -> tuple[str, list[dict[str, str]]]:
    blocks = CARD_START.split(text)
    additions: list[dict[str, str]] = []
    output: list[str] = []
    for block in blocks:
        if not (
            block.startswith("### بطاقة")
            or block.startswith("### إعادةُ توسيم")
        ):
            output.append(block)
            continue
        heading = block.split("\n", 1)[0]
        if "<" in heading or STRUCTURED.search(block):
            output.append(block)
            continue
        closure = CLOSURE.search(block)
        if not closure:
            output.append(block)
            continue
        gap = first_gap(closure.group("value"))
        if not gap:
            output.append(block)
            continue
        companions = [
            candidate
            for candidate in GAPS
            if candidate != gap and candidate in closure.group("value")
        ]
        line = (
            f"- عائق: النوع={gap}؛ يتطلب={REQUIRES[gap]}"
            + (
                "؛ عوائق مصاحبة=" + ",".join(companions)
                if companions
                else ""
            )
            + "؛"
        )
        start = closure.start()
        block = block[:start] + line + "\n" + block[start:]
        additions.append(
            {
                "card": heading.removeprefix("### بطاقة: ").strip(),
                "type": gap,
                "companions": ",".join(companions),
            }
        )
        output.append(block)
    return "".join(output), additions


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument(
        "--report",
        default="cache/recovery_pipeline/structured-obstacle-backfill.json",
    )
    args = parser.parse_args()

    changed: dict[str, list[dict[str, str]]] = {}
    for path in sorted(READINGS.glob("*.md")):
        original = path.read_text(encoding="utf-8")
        transformed, additions = transform(original)
        if additions:
            changed[path.relative_to(ROOT).as_posix()] = additions
            if not args.check:
                temporary = path.with_suffix(path.suffix + ".tmp")
                temporary.write_text(transformed, encoding="utf-8")
                temporary.replace(path)

    count = sum(len(rows) for rows in changed.values())
    if args.check:
        if count:
            raise SystemExit(
                f"FAIL: {count} suspended cards lack a structured obstacle"
            )
        print("structured obstacle check: CLEAN (0 missing)")
        return 0

    payload = {
        "schema": "structured-obstacle-backfill-v1",
        "changed_cards": count,
        "by_file": {
            path: len(rows) for path, rows in sorted(changed.items())
        },
        "by_type": dict(
            sorted(
                Counter(
                    row["type"]
                    for rows in changed.values()
                    for row in rows
                ).items()
            )
        ),
        "cards": changed,
    }
    report = ROOT / args.report
    report.parent.mkdir(parents=True, exist_ok=True)
    temporary = report.with_suffix(report.suffix + ".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    temporary.replace(report)
    print(json.dumps(payload, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
