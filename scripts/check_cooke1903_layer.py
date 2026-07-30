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
DOUBLE_PASS_A = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-diplomatic-pass-a.json"
)
DOUBLE_PASS_B = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-diplomatic-pass-b.json"
)
DOUBLE_COMPARISON = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-double-transcription-comparison.json"
)
TRANSLITERATION_CONTROL = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-transliteration-control-batch-01.json"
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
    if payload.get("schema_version") != "1.1":
        fail("Cooke layer schema must be 1.1 after visual-collation support")

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
    batch_members: set[str] = set()
    batch_ids: set[str] = set()
    for batch in source.get("visual_collation_batches", []):
        batch_path = ROOT / batch["path"]
        if not batch_path.exists():
            fail(f"visual-collation batch is missing: {batch['path']}")
        if sha256(batch_path) != batch["sha256"]:
            fail(f"visual-collation batch fingerprint drifted: {batch['path']}")
        batch_payload = json.loads(batch_path.read_text(encoding="utf-8"))
        if batch_payload.get("schema_version") != "1.0":
            fail(f"unsupported visual-collation schema: {batch['path']}")
        batch_id = batch_payload.get("batch_id")
        if (
            not isinstance(batch_id, str)
            or not batch_id
            or batch_id in batch_ids
            or batch_id != batch["batch_id"]
        ):
            fail(f"visual-collation batch identity drifted: {batch['path']}")
        batch_ids.add(batch_id)
        if batch_payload.get("source_pdf_sha256") != source["pdf_sha256"]:
            fail(f"visual-collation PDF fingerprint drifted: {batch['path']}")
        transcription_policy = batch_payload.get("transcription_policy")
        if (
            not isinstance(transcription_policy, str)
            or not transcription_policy.strip()
            or transcription_policy != batch.get("transcription_policy")
        ):
            fail(f"visual-collation transcription policy drifted: {batch['path']}")
        protocol_path = batch_payload.get("transcription_protocol_path")
        if (
            not isinstance(protocol_path, str)
            or not protocol_path
            or protocol_path != batch.get("transcription_protocol_path")
        ):
            fail(f"visual-collation protocol linkage drifted: {batch['path']}")
        protocol = ROOT / protocol_path
        if not protocol.exists():
            fail(f"visual-collation protocol is missing: {protocol_path}")
        if sha256(protocol) != batch.get("transcription_protocol_sha256"):
            fail(f"visual-collation protocol fingerprint drifted: {protocol_path}")
        double = batch.get("double_transcription")
        expected_double_paths = {
            "pass_a_path": str(DOUBLE_PASS_A.relative_to(ROOT)).replace("\\", "/"),
            "pass_b_path": str(DOUBLE_PASS_B.relative_to(ROOT)).replace("\\", "/"),
            "comparison_path": str(DOUBLE_COMPARISON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
        }
        if not isinstance(double, dict) or any(
            double.get(key) != value
            for key, value in expected_double_paths.items()
        ):
            fail(f"double-transcription linkage drifted: {batch['path']}")
        for source_path, hash_key in (
            (DOUBLE_PASS_A, "pass_a_sha256"),
            (DOUBLE_PASS_B, "pass_b_sha256"),
            (DOUBLE_COMPARISON, "comparison_sha256"),
        ):
            if not source_path.exists():
                fail(
                    "double-transcription source is missing: "
                    f"{source_path.relative_to(ROOT)}"
                )
            if double.get(hash_key) != sha256(source_path):
                fail(
                    "double-transcription source fingerprint drifted: "
                    f"{source_path.relative_to(ROOT)}"
                )
        comparison = json.loads(
            DOUBLE_COMPARISON.read_text(encoding="utf-8")
        )
        comparison_inventory = comparison.get("inventory", {})
        for key in (
            "records_total",
            "records_exactly_agreeing_after_shared_notation",
            "records_requiring_visual_arbitration",
            "reading_characters_compared",
            "reading_levenshtein_distance_total",
            "reading_disagreement_rate",
            "notation_loci_total",
            "notation_loci_differing",
            "notation_disagreement_rate",
        ):
            if double.get(key) != comparison_inventory.get(key):
                fail(
                    f"double-transcription inventory drifted for {key}: "
                    f"{batch['path']}"
                )
        if (
            not double.get("agreement_is_not_completion")
            or not double.get("common_mode_omission_found")
            or comparison.get("known_common_mode_failure", {}).get("record_id")
            != 3
        ):
            fail(f"common-mode transcription gate disappeared: {batch['path']}")
        comparison_by_id = {
            f"cooke1903:{item['record_id']}": item
            for item in comparison.get("records", [])
        }
        transliteration_link = batch.get("transliteration_control")
        expected_transliteration_path = str(
            TRANSLITERATION_CONTROL.relative_to(ROOT)
        ).replace("\\", "/")
        if (
            not isinstance(transliteration_link, dict)
            or transliteration_link.get("path")
            != expected_transliteration_path
            or not TRANSLITERATION_CONTROL.exists()
            or transliteration_link.get("sha256")
            != sha256(TRANSLITERATION_CONTROL)
        ):
            fail(f"transliteration-control linkage drifted: {batch['path']}")
        transliteration = json.loads(
            TRANSLITERATION_CONTROL.read_text(encoding="utf-8")
        )
        if (
            transliteration.get("schema_version") != "1.0"
            or transliteration.get("source_pdf_sha256")
            != source["pdf_sha256"]
            or transliteration.get("control_id")
            != transliteration_link.get("control_id")
        ):
            fail(f"transliteration control drifted: {batch['path']}")
        transliteration_inventory = transliteration.get("inventory", {})
        for key in (
            "records_total",
            "records_with_same_page_checks",
            "records_without_named_same_page_transliteration",
            "checks_total",
            "checks_corrected_then_consistent",
            "unresolved_conflicts",
        ):
            if transliteration_link.get(key) != transliteration_inventory.get(key):
                fail(
                    f"transliteration-control inventory drifted for {key}: "
                    f"{batch['path']}"
                )
        if (
            transliteration_inventory.get("unresolved_conflicts") != 0
            or not transliteration_link.get("absence_keeps_record_partial")
        ):
            fail(f"transliteration control gate weakened: {batch['path']}")
        transliteration_by_id = {
            item["record_id"]: item
            for item in transliteration.get("records", [])
        }
        expected_control_ids = {
            f"cooke1903:{number}" for number in range(3, 13)
        }
        if set(transliteration_by_id) != expected_control_ids:
            fail(f"transliteration-control membership drifted: {batch['path']}")
        control_rows = list(transliteration_by_id.values())
        checks = [
            check
            for item in control_rows
            for check in item.get("checks", [])
        ]
        measured_inventory = {
            "records_total": len(control_rows),
            "records_with_same_page_checks": sum(
                bool(item.get("checks")) for item in control_rows
            ),
            "records_without_named_same_page_transliteration": sum(
                item.get("status") == "named-transliteration-unavailable"
                for item in control_rows
            ),
            "checks_total": len(checks),
            "checks_consistent_without_change": sum(
                check.get("result") == "consistent" for check in checks
            ),
            "checks_corrected_then_consistent": sum(
                check.get("result") == "corrected-then-consistent"
                for check in checks
            ),
            "unresolved_conflicts": sum(
                check.get("result") not in {
                    "consistent",
                    "corrected-then-consistent",
                }
                for check in checks
            ),
        }
        for key, value in measured_inventory.items():
            if transliteration_inventory.get(key) != value:
                fail(
                    f"measured transliteration inventory drifted for {key}: "
                    f"{batch['path']}"
                )
        batch_records = batch_payload.get("records")
        if not isinstance(batch_records, list) or not batch_records:
            fail(f"visual-collation batch has no records: {batch['path']}")
        payload_record_ids = [item.get("record_id") for item in batch_records]
        if payload_record_ids != batch["record_ids"]:
            fail(f"visual-collation batch membership drifted: {batch['path']}")
        for record_id in batch["record_ids"]:
            if record_id in batch_members:
                fail(f"record occurs in multiple collation batches: {record_id}")
            batch_members.add(record_id)
            record = by_id.get(record_id)
            if record is None:
                fail(f"collation batch names unknown record: {record_id}")
            if record.get("visual_collation", {}).get("batch_id") != batch["batch_id"]:
                fail(f"collation batch linkage drifted: {record_id}")
            comparison_record = comparison_by_id.get(record_id)
            record_double = record.get("visual_collation", {}).get(
                "double_transcription",
                {},
            )
            if (
                comparison_record is None
                or record_double.get("reading_exact_match")
                != comparison_record.get("reading_exact_match")
                or record_double.get("reading_levenshtein_distance")
                != comparison_record.get("reading_levenshtein_distance")
                or record_double.get("reading_disagreement_rate")
                != comparison_record.get("reading_disagreement_rate")
                or record_double.get("notation_loci_total")
                != comparison_record.get("notation_loci_total")
                or record_double.get("notation_loci_differing")
                != comparison_record.get("notation_loci_differing")
                or record_double.get("visual_arbitration_required")
                == comparison_record.get("reading_exact_match")
            ):
                fail(f"record comparison linkage drifted: {record_id}")
            transliteration_record = transliteration_by_id.get(record_id)
            record_transliteration = record.get("visual_collation", {}).get(
                "transliteration_control",
                {},
            )
            if (
                not isinstance(transliteration_record, dict)
                or record_transliteration.get("control_id")
                != transliteration.get("control_id")
                or record_transliteration.get("control_path")
                != expected_transliteration_path
                or record_transliteration.get("status")
                != transliteration_record.get("status")
                or record_transliteration.get("checks_count")
                != len(transliteration_record.get("checks", []))
            ):
                fail(f"record transliteration linkage drifted: {record_id}")
            if (
                record.get("status") == "visually-collated"
                and transliteration_record.get("status")
                == "named-transliteration-unavailable"
            ):
                fail(f"record bypassed absent transliteration gate: {record_id}")
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

    first_phoenician_batch = {
        f"cooke1903:{number}" for number in range(3, 13)
    }
    for record_id in first_phoenician_batch:
        if by_id[record_id]["status"] != "visual-collation-partial":
            fail(f"rejected first-batch promotion returned: {record_id}")
    strict_literal_regressions = {
        "cooke1903:3": {
            "required": (
                "[כ שמע]",
                "בתכת אבן",
                "אית יחומל[ך]",
                "אית האדם",
                "אש בח[צ]ר ז הפתח",
                "על פן פתחי ז והערת",
                "ועמרה",
                "וה....ם",
                "עלהם",
            ),
            "forbidden": (
                "[כי שמע]",
                "בתוך אבן",
                "את יחומלך",
                "את האדם",
                "אש בחצרי ופתח",
                "על פן פתחי והערפת",
                "ועמדה",
                "עליהם",
                "כי מלך",
            ),
        },
        "cooke1903:4": {
            "required": (
                "תפק אית",
                "אדלן",
                "בארן",
                "י[כ]ן ל[ך]",
                "משר",
            ),
            "forbidden": (
                "חפץ את",
                "אדלון",
                "בארון",
                "יכן לך",
                "משד",
            ),
        },
        "cooke1903:5": {
            "required": (
                "יפתח אית משכב",
                "ישא אית חלת",
                "בן ורע",
                "צתנם אית ממלכת",
                "ואית זרע",
                "אית [בת עשתרת]",
                "וישבני",
                "אית דאר",
            ),
            "forbidden": (
                "יפתח את משכב",
                "ישא את חלת",
                "בן וזרע",
                "צתנם את ממלכת",
                "ואת זרע",
                "את [בת עשרת]ת",
                "וישבנהו",
                "את דאר",
            ),
        },
        "cooke1903:6": {
            "required": (
                "מ[פע]",
                "מלכ[ן]",
                "בדעשתרת",
                "אית שרן",
                "לעשתרת",
            ),
            "forbidden": (
                "מפ[ע]",
                "ברעשתת",
                "ברעשתרת",
                "את שרן",
                "לעשתת",
            ),
        },
        "cooke1903:8": {
            "required": (
                "ש̇מ̇א̇ל̇ק̇צ̇ר̇י̇",
                "אדנבעל",
                "פעל אית חצי",
                "יתן אית החצי",
                "צ̇א̇ת̇",
                "[ע̇ב̇ד̇ב̇ע̇ל̇]",
                "[1070]",
            ),
            "forbidden": (
                "שמאלקצרי",
                "ארנבעל",
                "פעל את חצי",
                "יתן את החצי",
                "+∧∧∧",
            ),
        },
        "cooke1903:9": {
            "required": (
                "אית השער",
                "והדלהת",
                "בשת",
                "[143] שת לעם",
                "לסכר",
                "[180:2/5]",
                "[180:3/5]",
                "לכני לי",
            ),
            "forbidden": (
                "את השער",
                "והדלת",
                "בשנת",
                "וזו",
                "שנת לעם",
                "לזכר",
                "בשת [180]\n",
                "צר לכנ לי",
            ),
        },
        "cooke1903:10": {
            "required": (
                "בעל חמן",
                "בשת [50]",
                "לפתלמים",
                "חמשם שת לעם",
                "אית כל",
                "אלן [אח]\nים",
                "... ם אש בארץ",
            ),
            "forbidden": (
                "בעל חמץ",
                "בשנת [50]",
                "לפלמים",
                "חמשם שנת לעם",
                "את כל",
                "... אם אש בארץ",
            ),
        },
        "cooke1903:11": {
            "required": (
                "עבד חרם",
                "מלך צדנם",
                "a ..ו",
                "a′ ...",
                "b .. טב",
                "c [לב]על",
            ),
            "forbidden": (
                "עבד חרס",
                "מלך צרנם",
                "c לבעל",
                "c [לבעל]",
            ),
        },
        "cooke1903:12": {
            "required": (
                "בימם [6]",
                "פמיתן",
                "אדיל ותמשש",
                "וארום",
                "לאדני",
                "בדא כהן",
            ),
            "forbidden": (
                "בימים [6]",
                "פמייתן",
                "אריל ותמש",
                "וארומם",
                "לארני",
                "ברא כהן",
            ),
        },
    }
    for record_id, rules in strict_literal_regressions.items():
        text = by_id[record_id].get("consonantal_text_collated") or ""
        for required in rules["required"]:
            if required not in text:
                fail(f"strict Cooke reading disappeared in {record_id}: {required}")
        for forbidden in rules["forbidden"]:
            if forbidden in text:
                fail(f"modernized Cooke reading returned in {record_id}: {forbidden}")

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
        status = record["status"]
        if status not in {
            "candidate-requires-visual-check",
            "visual-collation-partial",
            "visually-collated",
        }:
            fail(f"unknown visual state: {record['record_id']}")
        gate = record["ocr_quality"][
            "requires_pdf_visual_check_before_citation"
        ]
        collation = record.get("visual_collation")
        if (collation is not None) != (record["record_id"] in batch_members):
            fail(f"visual-collation source linkage drifted: {record['record_id']}")
        if status == "candidate-requires-visual-check":
            if not gate or collation is not None:
                fail(f"candidate bypassed visual review: {record['record_id']}")
        elif status == "visual-collation-partial":
            if not gate or not isinstance(collation, dict):
                fail(f"partial collation opened citation gate: {record['record_id']}")
        else:
            if gate or not isinstance(collation, dict):
                fail(f"completed collation remains gated: {record['record_id']}")
            if not (
                collation.get("text_complete")
                and collation.get("translation_complete")
                and str(record.get("consonantal_text_collated") or "").strip()
                and str(record.get("translation_collated") or "").strip()
            ):
                fail(f"completed collation is incomplete: {record['record_id']}")
        rendered = json.dumps(record, ensure_ascii=False, sort_keys=True)
        if any(0x0600 <= ord(char) <= 0x06FF for char in (
            record.get("consonantal_text_collated") or ""
        )):
            fail(f"foreign Arabic character entered Cooke text: {record['record_id']}")
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
    gated = sum(
        record["ocr_quality"][
            "requires_pdf_visual_check_before_citation"
        ]
        for record in records
    )
    collated = sum(
        record["status"] == "visually-collated"
        for record in records
    )
    partial = sum(
        record["status"] == "visual-collation-partial"
        for record in records
    )
    if inventory["records_requiring_visual_check"] != gated:
        fail("visual-gate inventory disagrees with records")
    if inventory["records_visually_collated"] != collated:
        fail("completed-collation inventory disagrees with records")
    if inventory["records_with_partial_visual_collation"] != partial:
        fail("partial-collation inventory disagrees with records")

    print(
        "CLEAN: Cooke layer "
        f"{len(records)} records, 150 numbered units, "
        f"{collated} visually collated, {partial} partial, {gated} gated"
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
