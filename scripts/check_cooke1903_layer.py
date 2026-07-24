#!/usr/bin/env python3
"""Fail closed when the conservative Cooke 1903 source layer drifts."""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
import unicodedata
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LAYER = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-inscription-layer.json"
)
PDF = ROOT / "Data raw" / "Cooke 1903.pdf"
VALIDATED_OCR = (
    ROOT
    / "Data raw"
    / "cooke1903_text"
    / "mistral_ocr"
    / "cooke1903_usable.md"
)
VALIDATION = (
    ROOT
    / "Data raw"
    / "cooke1903_text"
    / "mistral_ocr"
    / "validation-report.json"
)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def fail(message: str) -> None:
    print(f"FAIL: {message}", file=sys.stderr)
    raise SystemExit(1)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--require-sources",
        action="store_true",
        help="fail unless the ignored local PDF and OCR validation files exist",
    )
    args = parser.parse_args()

    if not LAYER.exists():
        fail(f"missing required file: {LAYER.relative_to(ROOT)}")

    payload = json.loads(LAYER.read_text(encoding="utf-8"))
    records = payload["records"]
    source = payload["source"]
    inventory = payload["inventory"]

    local_sources = (PDF, VALIDATED_OCR, VALIDATION)
    if args.require_sources and not all(path.exists() for path in local_sources):
        missing = [
            str(path.relative_to(ROOT))
            for path in local_sources
            if not path.exists()
        ]
        fail(f"missing local Cooke sources: {missing}")

    if PDF.exists() and source["pdf_sha256"] != sha256(PDF):
        fail("PDF fingerprint drifted; rebuild and review the layer")
    if (
        VALIDATED_OCR.exists()
        and source["validated_ocr_sha256"] != sha256(VALIDATED_OCR)
    ):
        fail("validated OCR fingerprint drifted; rebuild and review the layer")

    numbers = {record["cooke_number"] for record in records}
    if numbers != set(range(1, 151)):
        fail(f"numbered Cooke units are incomplete: {sorted(set(range(1, 151)) - numbers)}")

    ids = [record["record_id"] for record in records]
    duplicate_ids = sorted(
        record_id
        for record_id, count in Counter(ids).items()
        if count > 1
    )
    if duplicate_ids:
        fail(f"duplicate record ids: {duplicate_ids}")

    expected_split_ids = {
        "cooke1903:148:a",
        "cooke1903:148:b",
        "cooke1903:149:a-1-6",
        "cooke1903:149:b-1-15",
        "cooke1903:149:c",
    }
    if not expected_split_ids.issubset(ids):
        fail("lettered units 148 or 149 were lost")

    by_id = {record["record_id"]: record for record in records}
    corrected = {
        "cooke1903:3": 8,
        "cooke1903:130": 180,
        "cooke1903:131": 181,
        "cooke1903:132": 182,
        "cooke1903:139": 138,
    }
    for record_id, raw_number in corrected.items():
        actual = by_id[record_id]["ocr_quality"]["number_corrected_from_ocr"]
        if actual != raw_number:
            fail(f"measured OCR number correction drifted for {record_id}")

    visual_placeholders = {
        "cooke1903:31": 121,
        "cooke1903:36": 133,
        "cooke1903:37": 133,
        "cooke1903:51": 167,
        "cooke1903:65": 219,
        "cooke1903:122": 311,
        "cooke1903:123": 313,
    }
    for record_id, page in visual_placeholders.items():
        record = by_id[record_id]
        if record["source_page_pdf"] != page:
            fail(f"visual placeholder page drifted for {record_id}")
        if not record["ocr_quality"]["heading_transcribed_from_pdf"]:
            fail(f"quarantined unit lost its visual heading gate: {record_id}")
        if record["consonantal_text_candidate"] is not None:
            fail(f"quarantined unit recovered text from rejected OCR: {record_id}")
        if record["translation_candidate"] is not None:
            fail(f"quarantined unit recovered translation from rejected OCR: {record_id}")

    for record in records:
        if record["judgment"] != "not-issued":
            fail(f"source layer issued a linguistic judgment: {record['record_id']}")
        if record["status"] != "candidate-requires-visual-check":
            fail(f"record bypassed visual review: {record['record_id']}")
        if not record["ocr_quality"]["requires_pdf_visual_check_before_citation"]:
            fail(f"visual citation gate is open: {record['record_id']}")
        rendered = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if unicodedata.normalize("NFC", rendered) != rendered:
            fail(f"record is not NFC: {record['record_id']}")

    if source["pages_total"] != 472:
        fail("source page count drifted")
    if source["pages_usable_after_validation"] != 220:
        fail("validated usable-page count drifted")
    if source["pages_quarantined_after_validation"] != 252:
        fail("validated quarantine count drifted")

    if VALIDATION.exists():
        validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
        odd_pages = [row for row in validation["pages"] if row["page"] % 2]
        if len(odd_pages) != 236:
            fail("unexpected number of content-side pages")
        if sum(row["usable"] for row in odd_pages) != 217:
            fail("validated usable content-side page count drifted")

    if inventory["record_count"] != len(records):
        fail("inventory record count disagrees with records")
    if inventory["records_requiring_visual_check"] != len(records):
        fail("not every record is gated for visual review")

    print(
        "CLEAN: Cooke layer "
        f"{len(records)} records, 150 numbered units, "
        "all candidate-only and visually gated"
        + (
            ", local source fingerprints verified"
            if all(path.exists() for path in local_sources)
            else ", portable structural check"
        )
    )
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
