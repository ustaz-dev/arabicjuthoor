#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 31; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative inventory after OPEN-COMP-01920
with two fixed batches of fifty cards. Each card either carries all three
proof legs or records an honourable, reason-named non-positive verdict. Only
the repository's closed closure vocabulary is permitted.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_closure_vocabulary as CV  # noqa: E402
import harvest_ancient_greek_round30 as R30  # noqa: E402


R29, R28, R27, R26, R25 = R30.R29, R30.R28, R30.R27, R30.R26, R30.R25
R20, R19, R18, R17, R16 = R30.R20, R30.R19, R30.R18, R30.R17, R30.R16
READING, REPORT = R30.READING, R30.REPORT
DATE = "2026-08-26"
FIRST_COMPLETION, LAST_COMPLETION = 1921, 2020
EXPECTED_PREVIOUS = 1920
EXPECTED_POOL = 439
REMAINING_AFTER = 339
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
BATCHES = ((1921, 1970), (1971, 2020))
EXPECTED_STRICT = Counter({4: 100})
EXPECTED_TOKENS = Counter({4: 94, 5: 6})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 90, "NONLEXICAL": 5, "FUNCTION": 5})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:27378:en-κοττίς-grc-noun-2HMjrzA0"
LAST_MEMBER = "kaikki_ancient_greek:22963:en-ἀπερείσιος-grc-adj-8BxP7bxt"
EXPECTED_SURFACE_GROUPS = {
    "μέχρις": 3,
    "νόσφιν": 2,
    "ἔντοσθε": 2,
    "ἀπάνευθεν": 2,
}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:36cfabe232d224a98caeb315": 2,
    "ancient_greek:family:b32da70aa2777906c6a101da": 2,
    "ancient_greek:family:a74aaaa75f25947fbde6d6d8": 2,
    "ancient_greek:family:c00d2770e58b071e5735e987": 2,
    "ancient_greek:family:a1772f824471a273e4609ee2": 2,
    "ancient_greek:family:9c3053eb5520f5921e074052": 2,
    "ancient_greek:family:94c572ddb1a4a2184812ff03": 2,
    "ancient_greek:family:ffc088527d9c8bb90e96ea91": 2,
}


# Rebind the complete historical delegation chain to the round-31 window.
# Historical scripts remain unchanged on disk; only this process is rebound.
for module in (R30, R29, R28, R27, R26, R25, R20, R19, R18, R17):
    module.FIRST_COMPLETION = FIRST_COMPLETION
    module.LAST_COMPLETION = LAST_COMPLETION
    module.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    module.EXPECTED_POOL = EXPECTED_POOL
    module.BATCH_SIZE = BATCH_SIZE
    module.BATCHES = BATCHES
    module.EXPECTED_STRICT = EXPECTED_STRICT
    module.EXPECTED_TOKENS = EXPECTED_TOKENS
    module.EXPECTED_CATEGORIES = EXPECTED_CATEGORIES
    module.EXPECTED_VERDICTS = EXPECTED_VERDICTS
    module.FIRST_MEMBER = FIRST_MEMBER
    module.LAST_MEMBER = LAST_MEMBER
for module in (R30, R29, R28, R27, R26):
    module.REMAINING_AFTER = REMAINING_AFTER
    module.EXPECTED_SURFACE_GROUPS = EXPECTED_SURFACE_GROUPS
    module.EXPECTED_FAMILY_GROUPS = EXPECTED_FAMILY_GROUPS
R30.DATE = DATE
R16.DATE = DATE


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed window and enforce legs, duplicates, and closures."""
    if "LANE-A DONE30 100 LANE-A-OPEN-COMP-01920" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE30 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND30-CHUNK-50:END -->" not in reading_text:
        raise AssertionError("الجولة الثلاثون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND31-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الحادية والثلاثين موجودة")

    cards, records, meta = R30.render_all(allow_installed=True)
    rendered_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        card = card.replace("الرسم جديد إلى 01820", "الرسم جديد إلى 01920")
        if "الرسم جديد إلى 01820" in card:
            raise AssertionError(f"بقي مرجع نافذة قديم: {record['completion_id']}")
        rendered_cards.append(card)
    closures = Counter(record["closure"] for record in records)
    if not set(closures) <= CV.LEGAL or closures != EXPECTED_VERDICTS:
        raise AssertionError(f"خرج حكم عن قاموس الإغلاق المغلق: {closures}")
    return rendered_cards, records, meta


def _advance_labels(value: str) -> str:
    """Advance only round labels in a fragment rendered by round 30."""
    replacements = (
        ("LANE-A-GREEK-ROUND30", "LANE-A-GREEK-ROUND31"),
        ("LANE-A DONE30", "LANE-A DONE31"),
        ("الجولة الثلاثون", "الجولة الحادية والثلاثون"),
        ("الجولة الثلاثين", "الجولة الحادية والثلاثين"),
    )
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def batch_header(batch: int, records: list[dict]) -> list[str]:
    lines = _advance_labels("\n".join(R30.batch_header(batch, records))).splitlines()
    lines.append("")
    return lines


def report_addition(records: list[dict], meta: dict) -> str:
    return _advance_labels(R30.report_addition(records, meta))


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round31-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND30-CHUNK-50:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, CHUNK_SIZE):
            chunk_number += 1
            lines: list[str] = []
            if offset == 0:
                lines += batch_header(batch, batch_records)
            for card in batch_cards[offset:offset + CHUNK_SIZE]:
                lines += [card, ""]
            if offset + CHUNK_SIZE == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND31-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND31-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R30._anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        R30._anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE30 100 LANE-A-OPEN-COMP-01920",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND31-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة الحادية والثلاثون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND31-CHUNK-50:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND31-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND31-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND31-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, _records, _meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND31-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(
        r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE
    ))
    truncation_markers = len(re.findall(
        r"tokens truncated|chars truncated|lines truncated", section
    ))
    done = "LANE-A DONE31 100 LANE-A-OPEN-COMP-02020"
    report = REPORT.read_text(encoding="utf-8")
    if (
        ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1))
        or batch_counts != [BATCH_SIZE, BATCH_SIZE]
        or len(cards) != CARD_COUNT
        or exact_cards != CARD_COUNT
        or len(markers) != 50
        or max_bytes > 5_120
        or repeat_lines != CARD_COUNT
        or leg_lines != CARD_COUNT
        or truncation_markers
        or report.count(done) != 1
        or report.count("<!-- LANE-A-GREEK-ROUND31-REPORT:START -->") != 1
    ):
        raise AssertionError(
            f"فشل التحقق: ids={len(ids)} batches={batch_counts} cards={len(cards)} "
            f"exact={exact_cards} chunks={len(markers)} max={max_bytes} repeats={repeat_lines} "
            f"legs={leg_lines} truncation={truncation_markers} done={report.count(done)}"
        )
    return {
        "cards": len(cards),
        "batches": batch_counts,
        "chunks": len(markers),
        "first": ids[0],
        "last": ids[-1],
        "max_bytes": max_bytes,
        "exact_generated_cards": exact_cards,
        "duplicate_audit_lines": repeat_lines,
        "three_leg_disposition_lines": leg_lines,
        "truncation_markers": truncation_markers,
        "done": done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    parser.add_argument("--records", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2))
        return 0
    if args.stage:
        print(stage_patches())
        return 0
    _cards, records, meta = render_all()
    print(json.dumps({
        **meta,
        "cards": len(records),
        "closures": dict(Counter(record["closure"] for record in records)),
        "verdicts": dict(Counter(record["verdict"] for record in records)),
        "categories": dict(Counter(record["category"] for record in records)),
        "max_bytes": max(record["bytes"] for record in records),
        "last": records[-1]["completion_id"],
    }, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
