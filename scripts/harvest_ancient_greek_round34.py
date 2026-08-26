#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 34; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative inventory after OPEN-COMP-02220
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
import harvest_ancient_greek_round33 as R33  # noqa: E402


R32, R31, R30 = R33.R32, R33.R31, R33.R30
R29, R28, R27, R26, R25 = R33.R29, R33.R28, R33.R27, R33.R26, R33.R25
R20, R19, R18, R17, R16 = R33.R20, R33.R19, R33.R18, R33.R17, R33.R16
READING, REPORT = R33.READING, R33.REPORT
DATE = "2026-08-26"
FIRST_COMPLETION, LAST_COMPLETION = 2221, 2320
EXPECTED_PREVIOUS = 2220
EXPECTED_POOL = 139
REMAINING_AFTER = 39
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
BATCHES = ((2221, 2270), (2271, 2320))
EXPECTED_STRICT = Counter({5: 68, 6: 32})
EXPECTED_TOKENS = Counter({5: 63, 6: 26, 7: 10, 8: 1})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 93, "FUNCTION": 4, "NONLEXICAL": 3})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:21250:en-μετόπισθε-grc-adv-ysCrP6Rk"
LAST_MEMBER = "kaikki_ancient_greek:32765:en-ναυσικλυτός-grc-adj-lEL1d0-k"
EXPECTED_SURFACE_GROUPS = {
    "ἀπονόσφιν": 2,
    "πρυμνήσι'": 2,
}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:779a42449795098b1e4408b3": 2,
    "ancient_greek:family:a44a57656421cfa34a8a9a4e": 2,
    "ancient_greek:family:db46c4323c8fcc1223fa0fbe": 4,
    "ancient_greek:family:a35fc1fb89f02ec4a599fbd7": 2,
    "ancient_greek:family:18d48f33f8f85f48571704e0": 2,
    "ancient_greek:family:efe0c7d58d6db0491a34e6df": 7,
    "ancient_greek:family:581fb7d24df8bc114a41b626": 2,
    "ancient_greek:family:2ab16ee492ff8f05db90bec8": 2,
    "ancient_greek:family:41e828f95f73a6786abc1148": 2,
    "ancient_greek:family:d289304b43abebd47f42170a": 2,
    "ancient_greek:family:f1f207ce129d74b61b288583": 2,
}


# Rebind the complete historical delegation chain to the round-34 window.
# Historical scripts remain unchanged on disk; only this process is rebound.
for module in (R33, R32, R31, R30, R29, R28, R27, R26, R25, R20, R19, R18, R17):
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
for module in (R33, R32, R31, R30, R29, R28, R27, R26):
    module.REMAINING_AFTER = REMAINING_AFTER
    module.EXPECTED_SURFACE_GROUPS = EXPECTED_SURFACE_GROUPS
    module.EXPECTED_FAMILY_GROUPS = EXPECTED_FAMILY_GROUPS
R33.DATE = DATE
R32.DATE = DATE
R31.DATE = DATE
R30.DATE = DATE
R16.DATE = DATE


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed window and enforce legs, duplicates, and closures."""
    if "LANE-A DONE33 100 LANE-A-OPEN-COMP-02220" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE33 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND33-CHUNK-50:END -->" not in reading_text:
        raise AssertionError("الجولة الثالثة والثلاثون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND34-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الرابعة والثلاثين موجودة")

    cards, records, meta = R33.render_all(allow_installed=True)
    rendered_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        card = card.replace("الرسم جديد إلى 02120", "الرسم جديد إلى 02220")
        if "الرسم جديد إلى 02120" in card:
            raise AssertionError(f"بقي مرجع نافذة قديم: {record['completion_id']}")
        rendered_cards.append(card)
    closures = Counter(record["closure"] for record in records)
    if not set(closures) <= CV.LEGAL or closures != EXPECTED_VERDICTS:
        raise AssertionError(f"خرج حكم عن قاموس الإغلاق المغلق: {closures}")
    return rendered_cards, records, meta


def _advance_labels(value: str) -> str:
    """Advance only round labels in a fragment rendered by round 33."""
    replacements = (
        ("LANE-A-GREEK-ROUND33", "LANE-A-GREEK-ROUND34"),
        ("LANE-A DONE33", "LANE-A DONE34"),
        ("الجولة الثالثة والثلاثون", "الجولة الرابعة والثلاثون"),
        ("الجولة الثالثة والثلاثين", "الجولة الرابعة والثلاثين"),
    )
    for old, new in replacements:
        value = value.replace(old, new)
    return value


def batch_header(batch: int, records: list[dict]) -> list[str]:
    lines = _advance_labels("\n".join(R33.batch_header(batch, records))).splitlines()
    lines.append("")
    return lines


def report_addition(records: list[dict], meta: dict) -> str:
    return _advance_labels(R33.report_addition(records, meta))


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round34-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND33-CHUNK-50:END -->"
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
                lines += [f"<!-- LANE-A-GREEK-ROUND34-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND34-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R33.R30._anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        R33.R30._anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE33 100 LANE-A-OPEN-COMP-02220",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND34-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة الرابعة والثلاثون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND34-CHUNK-50:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND34-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND34-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND34-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, _records, _meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND34-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(
        r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE
    ))
    truncation_markers = len(re.findall(
        r"tokens truncated|chars truncated|lines truncated", section
    ))
    done = "LANE-A DONE34 100 LANE-A-OPEN-COMP-02320"
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
        or report.count("<!-- LANE-A-GREEK-ROUND34-REPORT:START -->") != 1
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
