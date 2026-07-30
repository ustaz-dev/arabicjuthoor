#!/usr/bin/env python3
"""Build a conservative inscription inventory from validated Cooke 1903 OCR.

The only textual input is the validator's usable-page output. This builder
does not make linguistic judgments. It records source identity, section,
heading, location/date apparatus, page boundaries, consonantal text
candidates, and translation candidates. Units whose pages were quarantined
remain as visually verified inventory placeholders with no extracted text.
"""
from __future__ import annotations

import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SOURCE = (
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
PDF = ROOT / "Data raw" / "Cooke 1903.pdf"
OUTPUT = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-inscription-layer.json"
)
COLLATION_DIR = ROOT / "04-cross-linguistic" / "data"
COLLATION_GLOB = "cooke-1903-visual-collation-batch-*.json"
TRANSCRIPTION_PROTOCOL = (
    ROOT
    / "04-cross-linguistic"
    / "cooke-1903-diplomatic-transcription-protocol.md"
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

PAGE_RE = re.compile(
    r"<!-- PAGE (\d+)([^>]*) -->\n(.*?)(?=<!-- PAGE |\Z)",
    re.DOTALL,
)
HEBREW_RE = re.compile(r"[א-ת]")
HEBREW_TOKEN_RE = re.compile(r"[א-ת]+")
CIS_RE = re.compile(r"\bCIS\s+([ivx]+)\s*([0-9]+[a-z]?)", re.IGNORECASE)
DATE_RE = re.compile(
    r"(?:(?:Date|Circ\.|Prob\.|Between|End of|Same period as)\s+[^.;]+"
    r"|(?:[ivx]+(?:-[ivx]+)?\s+cent\.\s*(?:B\.\s*[Cc]\.|A\.\s*D\.))"
    r"|(?:[AB]\.\s*[CD]\.\s*\d+(?:-\d+)?)"
    r"|(?:B\.\s*[Cc]\.\s*\d+(?:-\d+)?)"
    r"|(?:\d+\s*B\.\s*[Cc]\.))",
    re.IGNORECASE,
)
HEADING_RE = re.compile(
    r"^(?P<number>\d{1,3})"
    r"(?:\s+(?P<label>[A-C](?:\s+\d+(?:-\d+)?)?(?:\s+and\s+[A-C])?))?"
    r"\.\s*(?P<title>.*)$"
)
VARIANT_HEADING_RE = re.compile(r"^(?P<label>[A-C])\.\s+(?P<title>.+)$")

HEADING_HINT_RE = re.compile(
    r"\b(?:"
    r"Moabite|Siloam|Byblus|Sidon|Tyre|Kition|Idalion|Larnax|Tamassos|"
    r"Abydos|Athens|Piraeus|Malta|Caralis|Pauli|Nora|Marseilles|"
    r"Carthage|Cirta|Thugga|Tunis|Altiburus|Jol|Gelma|Maktar|Suloi|"
    r"Zenjirli|Ne.rab|Nineveh|Cilicia|Te.ma|Memphis|Elephantina|"
    r"Carpentras|Saqqara|Papyrus|El-.Ola|El-Hejra|Petra|Medeba|"
    r"Dume.r|Hebran|Salh.ad|Bostra|Imta.n|Puteoli|Vog|Eut|"
    r"Chediac|Mu.ller|No.ld|Constantine|Tariff|Coins|Bene|Seals|Gems|"
    r"CIS|NPun|Chwolson|Littmann|Oxoniensis"
    r")\b",
    re.IGNORECASE,
)

COMMENTARY_START_RE = re.compile(
    r"^(?:"
    r"This (?:inscr|inscription|stone|text|monument)|"
    r"The (?:inscr|inscription|stone|text|monument|sarcophagus|coins)|"
    r"These (?:inscr|inscriptions|stones|texts|monuments)|"
    r"L\.\s*\d+|"
    r"Ad mng\.|"
    r"For the |"
    r"On the "
    r")",
    re.IGNORECASE,
)

# These seven numbered units begin on one of the 19 quarantined content
# pages, so they cannot be parsed from cooke1903_usable.md. Their headings
# were transcribed directly from the rendered PDF pages named here. They
# remain empty inventory placeholders until their inscription text and
# translation are manually verified from the page image.
VISUALLY_VERIFIED_PLACEHOLDERS = [
    {
        "number": 31,
        "label": "",
        "title": "Abydos. CIS i 102. Circ. iv cent. In situ.",
        "source_page": 121,
        "printed_page": 91,
        "line_number": 1000,
    },
    {
        "number": 36,
        "label": "",
        "title": "Malta. CIS i 122. Date ii cent. B.C. Louvre.",
        "source_page": 133,
        "printed_page": 103,
        "line_number": 1000,
    },
    {
        "number": 37,
        "label": "",
        "title": "Malta. CIS i 123 a. Date uncertain. Malta.",
        "source_page": 133,
        "printed_page": 103,
        "line_number": 2000,
    },
    {
        "number": 51,
        "label": "",
        "title": "Cirta (Constantine). Costa 8.",
        "source_page": 167,
        "printed_page": 137,
        "line_number": 1000,
    },
    {
        "number": 65,
        "label": "",
        "title": "Nêrab 2. Prob. same date as 64. Louvre.",
        "source_page": 219,
        "printed_page": 189,
        "line_number": 1000,
    },
    {
        "number": 122,
        "label": "",
        "title": "Vog. 16. A.D. 131.",
        "source_page": 311,
        "printed_page": 281,
        "line_number": 1000,
    },
    {
        "number": 123,
        "label": "",
        "title": "Vog. 17. A.D. 254.",
        "source_page": 313,
        "printed_page": 283,
        "line_number": 1000,
    },
]


@dataclass(frozen=True)
class Page:
    number: int
    metadata: str
    body: str

    @property
    def flagged(self) -> bool:
        return "FLAGGED" in self.metadata


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest().upper()


def apply_visual_collations(
    records: list[dict],
    pdf_sha256: str,
) -> list[dict]:
    """Apply reviewed PDF-image overlays without mutating OCR candidates."""
    by_id = {record["record_id"]: record for record in records}
    seen_records: set[str] = set()
    seen_batch_ids: set[str] = set()
    batch_refs: list[dict] = []

    for path in sorted(COLLATION_DIR.glob(COLLATION_GLOB)):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("schema_version") != "1.0":
            raise ValueError(f"unsupported visual-collation schema: {path}")
        if payload.get("source_pdf_sha256") != pdf_sha256:
            raise ValueError(f"Cooke PDF fingerprint mismatch: {path}")
        batch_id = str(payload.get("batch_id") or "").strip()
        collated_on = str(payload.get("collated_on") or "").strip()
        transcription_policy = str(
            payload.get("transcription_policy") or ""
        ).strip()
        protocol_path = str(
            payload.get("transcription_protocol_path") or ""
        ).strip()
        expected_protocol_path = str(
            TRANSCRIPTION_PROTOCOL.relative_to(ROOT)
        ).replace("\\", "/")
        items = payload.get("records")
        if (
            not batch_id
            or batch_id in seen_batch_ids
            or not collated_on
            or not transcription_policy
            or protocol_path != expected_protocol_path
            or not TRANSCRIPTION_PROTOCOL.exists()
            or not isinstance(items, list)
            or not items
        ):
            raise ValueError(f"incomplete visual-collation header: {path}")
        seen_batch_ids.add(batch_id)

        double = payload.get("double_transcription")
        expected_double_paths = {
            "pass_a_path": str(DOUBLE_PASS_A.relative_to(ROOT)).replace("\\", "/"),
            "pass_b_path": str(DOUBLE_PASS_B.relative_to(ROOT)).replace("\\", "/"),
            "comparison_path": str(DOUBLE_COMPARISON.relative_to(ROOT)).replace(
                "\\", "/"
            ),
        }
        if not isinstance(double, dict) or any(
            double.get(key) != expected
            for key, expected in expected_double_paths.items()
        ):
            raise ValueError(f"invalid double-transcription linkage: {path}")
        if not all(
            source_path.exists()
            for source_path in (DOUBLE_PASS_A, DOUBLE_PASS_B, DOUBLE_COMPARISON)
        ):
            raise ValueError(f"missing double-transcription source: {path}")
        comparison = json.loads(DOUBLE_COMPARISON.read_text(encoding="utf-8"))
        comparison_inventory = comparison.get("inventory")
        if not isinstance(comparison_inventory, dict):
            raise ValueError(f"invalid double-transcription inventory: {path}")
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
                raise ValueError(
                    f"double-transcription inventory drifted for {key}: {path}"
                )
        comparison_sources = comparison.get("sources", {})
        if (
            comparison_sources.get("pass_a", {}).get("sha256")
            != sha256(DOUBLE_PASS_A)
            or comparison_sources.get("pass_b", {}).get("sha256")
            != sha256(DOUBLE_PASS_B)
        ):
            raise ValueError(f"double-transcription source hash drifted: {path}")
        comparison_by_id = {
            f"cooke1903:{item['record_id']}": item
            for item in comparison.get("records", [])
        }
        transliteration_link = payload.get("transliteration_control")
        expected_transliteration_path = str(
            TRANSLITERATION_CONTROL.relative_to(ROOT)
        ).replace("\\", "/")
        if (
            not isinstance(transliteration_link, dict)
            or transliteration_link.get("path")
            != expected_transliteration_path
            or not TRANSLITERATION_CONTROL.exists()
        ):
            raise ValueError(f"invalid transliteration-control linkage: {path}")
        transliteration = json.loads(
            TRANSLITERATION_CONTROL.read_text(encoding="utf-8")
        )
        if (
            transliteration.get("schema_version") != "1.0"
            or transliteration.get("source_pdf_sha256") != pdf_sha256
            or transliteration.get("control_id")
            != transliteration_link.get("control_id")
        ):
            raise ValueError(f"invalid transliteration control: {path}")
        transliteration_inventory = transliteration.get("inventory")
        if not isinstance(transliteration_inventory, dict):
            raise ValueError(f"invalid transliteration inventory: {path}")
        for key in (
            "records_total",
            "records_with_same_page_checks",
            "records_without_named_same_page_transliteration",
            "checks_total",
            "checks_corrected_then_consistent",
            "unresolved_conflicts",
        ):
            if (
                transliteration_link.get(key)
                != transliteration_inventory.get(key)
            ):
                raise ValueError(
                    f"transliteration-control inventory drifted for {key}: "
                    f"{path}"
                )
        transliteration_by_id = {
            item["record_id"]: item
            for item in transliteration.get("records", [])
        }

        batch_ids: list[str] = []
        for item in items:
            record_id = str(item.get("record_id") or "")
            if record_id not in by_id:
                raise ValueError(f"unknown Cooke record in {path}: {record_id}")
            if record_id in seen_records:
                raise ValueError(
                    f"Cooke record collated in more than one batch: {record_id}"
                )
            seen_records.add(record_id)
            batch_ids.append(record_id)

            record = by_id[record_id]
            if item.get("source_page_pdf") != record["source_page_pdf"]:
                raise ValueError(
                    f"source-page mismatch for {record_id} in {path}"
                )
            checked_pages = item.get("source_pages_visually_checked")
            if (
                not isinstance(checked_pages, list)
                or not checked_pages
                or not all(
                    isinstance(page, int) and page > 0
                    for page in checked_pages
                )
                or record["source_page_pdf"] not in checked_pages
            ):
                raise ValueError(
                    f"invalid visual page list for {record_id} in {path}"
                )

            status = item.get("status")
            if status not in {
                "visually-collated",
                "visual-collation-partial",
            }:
                raise ValueError(
                    f"invalid visual status for {record_id}: {status}"
                )
            transliteration_record = transliteration_by_id.get(record_id)
            if not isinstance(transliteration_record, dict):
                raise ValueError(
                    f"missing transliteration control for {record_id}"
                )
            if (
                status == "visually-collated"
                and transliteration_record.get("status")
                == "named-transliteration-unavailable"
            ):
                raise ValueError(
                    f"record lacks named transliteration control: {record_id}"
                )
            text = item.get("consonantal_text_collated")
            translation = item.get("translation_collated")
            text_complete = item.get("text_complete")
            translation_complete = item.get("translation_complete")
            if not isinstance(text_complete, bool) or not isinstance(
                translation_complete,
                bool,
            ):
                raise ValueError(
                    f"missing completion flags for {record_id} in {path}"
                )
            if text_complete and not str(text or "").strip():
                raise ValueError(
                    f"complete text is empty for {record_id} in {path}"
                )
            if translation_complete and not str(translation or "").strip():
                raise ValueError(
                    f"complete translation is empty for {record_id} in {path}"
                )
            if status == "visually-collated" and not (
                text_complete and translation_complete
            ):
                raise ValueError(
                    f"fully collated record is incomplete: {record_id}"
                )
            changes = item.get("changes")
            method = item.get("transcription_method")
            if not isinstance(method, str) or not method.strip():
                raise ValueError(
                    f"missing transcription method for {record_id} in {path}"
                )
            if not isinstance(changes, list) or not changes or not all(
                isinstance(change, str) and change.strip()
                for change in changes
            ):
                raise ValueError(
                    f"invalid change log for {record_id} in {path}"
                )

            record["consonantal_text_collated"] = (
                unicodedata.normalize("NFC", str(text))
                if text is not None
                else None
            )
            record["translation_collated"] = (
                unicodedata.normalize("NFC", str(translation))
                if translation is not None
                else None
            )
            record["visual_collation"] = {
                "batch_id": batch_id,
                "batch_path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "collated_on": collated_on,
                "source_pages_visually_checked": checked_pages,
                "text_complete": text_complete,
                "translation_complete": translation_complete,
                "transcription_method": method,
                "changes": changes,
                "notes": item.get("notes"),
                "double_transcription": {
                    "reading_exact_match": comparison_by_id[record_id][
                        "reading_exact_match"
                    ],
                    "reading_levenshtein_distance": comparison_by_id[record_id][
                        "reading_levenshtein_distance"
                    ],
                    "reading_disagreement_rate": comparison_by_id[record_id][
                        "reading_disagreement_rate"
                    ],
                    "notation_loci_total": comparison_by_id[record_id][
                        "notation_loci_total"
                    ],
                    "notation_loci_differing": comparison_by_id[record_id][
                        "notation_loci_differing"
                    ],
                    "visual_arbitration_required": not comparison_by_id[
                        record_id
                    ]["reading_exact_match"],
                },
                "transliteration_control": {
                    "control_id": transliteration.get("control_id"),
                    "control_path": expected_transliteration_path,
                    "status": transliteration_record["status"],
                    "checks_count": len(
                        transliteration_record.get("checks", [])
                    ),
                    "blocker": transliteration_record.get("blocker"),
                },
            }
            record["status"] = status
            record["ocr_quality"][
                "requires_pdf_visual_check_before_citation"
            ] = status != "visually-collated"

        batch_refs.append(
            {
                "batch_id": batch_id,
                "path": str(path.relative_to(ROOT)).replace("\\", "/"),
                "sha256": sha256(path),
                "transcription_policy": transcription_policy,
                "transcription_protocol_path": protocol_path,
                "transcription_protocol_sha256": sha256(
                    TRANSCRIPTION_PROTOCOL
                ),
                "double_transcription": {
                    **expected_double_paths,
                    "pass_a_sha256": sha256(DOUBLE_PASS_A),
                    "pass_b_sha256": sha256(DOUBLE_PASS_B),
                    "comparison_sha256": sha256(DOUBLE_COMPARISON),
                    **comparison_inventory,
                    "agreement_is_not_completion": bool(
                        double.get("agreement_is_not_completion")
                    ),
                    "common_mode_omission_found": str(
                        double.get("common_mode_omission_found") or ""
                    ),
                },
                "transliteration_control": {
                    "path": expected_transliteration_path,
                    "sha256": sha256(TRANSLITERATION_CONTROL),
                    "control_id": transliteration.get("control_id"),
                    **transliteration_inventory,
                    "absence_keeps_record_partial": bool(
                        transliteration_link.get(
                            "absence_keeps_record_partial"
                        )
                    ),
                },
                "record_ids": batch_ids,
            }
        )
    return batch_refs


def section_for(number: int, label: str) -> tuple[str, str]:
    if number == 1:
        return "moabite", "Moabite"
    if number == 2:
        return "hebrew", "Hebrew"
    if 3 <= number <= 35:
        return "phoenician", "Phoenician"
    if 36 <= number <= 52:
        return "punic", "Punic"
    if 53 <= number <= 60:
        return "neo-punic", "Neo-Punic"
    if 61 <= number <= 77:
        return "aramaic", "Aramaic"
    if 78 <= number <= 102:
        return "nabataean", "Nabataean"
    if 103 <= number <= 109:
        return "nabataean-sinaitic", "Nabataean: Sinaitic"
    if 110 <= number <= 147:
        return "palmyrene", "Palmyrene"
    if number == 148:
        return "jewish", "Jewish"
    if number == 149:
        label = label.strip()
        if label.startswith("A"):
            return "aramaic-coins", "Aramaic coins"
        if label.startswith("B"):
            return "phoenician-coins", "Phoenician coins"
        if label.startswith("C"):
            return "jewish-coins", "Jewish coins"
        return "coins", "Coins"
    return "seals-and-gems", "Seals and gems"


def normalized_line(line: str) -> str:
    line = unicodedata.normalize("NFC", line).strip()
    line = line.replace("\u2014", "-")
    line = re.sub(r"^#+\s*", "", line)
    return line.strip()


def correct_number(page: int, number: int, seen_on_page: int) -> int:
    corrections = {
        (49, 8, 1): 3,
        (321, 180, 1): 130,
        (321, 181, 1): 131,
        (323, 182, 1): 132,
        (331, 138, 2): 139,
    }
    return corrections.get((page, number, seen_on_page), number)


def find_headings(pages: list[Page]) -> list[dict]:
    headings: list[dict] = []
    for page in pages:
        seen_numbers: dict[int, int] = {}
        for line_number, raw_line in enumerate(page.body.splitlines(), start=1):
            line = normalized_line(raw_line)
            match = HEADING_RE.match(line)
            if match:
                raw_number = int(match.group("number"))
                label = (match.group("label") or "").strip()
                title = match.group("title").strip()
                seen_numbers[raw_number] = seen_numbers.get(raw_number, 0) + 1
                number = correct_number(
                    page.number,
                    raw_number,
                    seen_numbers[raw_number],
                )
                if not 1 <= number <= 150:
                    continue
                if number == 150:
                    if title and not HEADING_HINT_RE.search(title):
                        continue
                elif not (
                    HEADING_HINT_RE.search(title)
                    or DATE_RE.search(title)
                    or CIS_RE.search(title)
                ):
                    continue
                headings.append(
                    {
                        "number": number,
                        "label": label,
                        "title": title,
                        "source_page": page.number,
                        "printed_page": page.number - 30,
                        "line_number": line_number,
                        "page_flagged": page.flagged,
                        "ocr_number": raw_number,
                        "number_corrected": number != raw_number,
                        "manual_visual_heading": False,
                    }
                )
                continue

            # Cooke numbers 148 and 149 have lettered continuations without
            # repeating the base number.
            variant = VARIANT_HEADING_RE.match(line)
            if variant and headings:
                previous = headings[-1]
                if previous["number"] in (148, 149):
                    title = variant.group("title").strip()
                    if HEADING_HINT_RE.search(title):
                        headings.append(
                            {
                                "number": previous["number"],
                                "label": variant.group("label"),
                                "title": title,
                                "source_page": page.number,
                                "printed_page": page.number - 30,
                                "line_number": line_number,
                                "page_flagged": page.flagged,
                                "ocr_number": previous["number"],
                                "number_corrected": False,
                                "manual_visual_heading": False,
                            }
                        )

    # Remove exact repeated headers while preserving lettered variants.
    unique: list[dict] = []
    keys: set[tuple] = set()
    for heading in headings:
        key = (
            heading["number"],
            heading["label"],
            heading["source_page"],
            heading["line_number"],
        )
        if key not in keys:
            unique.append(heading)
            keys.add(key)
    return unique


def page_text_from_line(page: Page, line_number: int) -> str:
    lines = page.body.splitlines()
    return "\n".join(lines[line_number:])


def record_block(
    pages_by_number: dict[int, Page],
    heading: dict,
    next_heading: dict | None,
    usable_pages: set[int],
) -> tuple[str, list[int], list[int], list[int], bool]:
    start_page = heading["source_page"]
    end_page = next_heading["source_page"] if next_heading else start_page
    chunks: list[str] = []
    source_pages: list[int] = []
    used_ocr_pages: list[int] = []
    quarantined_pages: list[int] = []
    any_flagged = False

    for page_number in range(start_page, end_page + 1):
        source_pages.append(page_number)
        if page_number not in usable_pages:
            quarantined_pages.append(page_number)
            continue
        page = pages_by_number.get(page_number)
        if page is None:
            raise RuntimeError(
                f"validated usable page missing from source: {page_number}"
            )
        any_flagged = any_flagged or page.flagged

        lines = page.body.splitlines()
        start_index = (
            heading["line_number"]
            if page_number == start_page
            else 0
        )
        end_index = len(lines)
        if next_heading and page_number == next_heading["source_page"]:
            end_index = max(next_heading["line_number"] - 1, 0)
        body = "\n".join(lines[start_index:end_index])
        chunks.append(body)
        used_ocr_pages.append(page_number)
    return (
        "\n".join(chunks),
        source_pages,
        used_ocr_pages,
        quarantined_pages,
        any_flagged,
    )


def extract_consonantal_candidate(block: str) -> str:
    lines: list[str] = []
    started = False
    for raw_line in block.splitlines():
        line = normalized_line(raw_line)
        if not line:
            if started:
                continue
            continue
        if HEBREW_RE.search(line):
            cleaned = re.sub(r"^[| ]*\d+[.)]?\s*", "", line)
            cleaned = re.sub(r"[*_`|]", " ", cleaned)
            cleaned = " ".join(HEBREW_TOKEN_RE.findall(cleaned))
            if cleaned:
                lines.append(cleaned)
                started = True
            continue
        if started and re.search(r"[A-Za-z]{3}", line):
            break
    return "\n".join(lines)


def extract_translation_candidate(block: str) -> str:
    paragraphs = [part.strip() for part in re.split(r"\n\s*\n", block)]
    seen_semitic = False
    collected: list[str] = []
    for paragraph in paragraphs:
        if not paragraph:
            continue
        if HEBREW_RE.search(paragraph):
            seen_semitic = True
            continue
        if not seen_semitic:
            continue
        compact = " ".join(normalized_line(line) for line in paragraph.splitlines())
        if not re.search(r"[A-Za-z]{3}", compact):
            continue
        if COMMENTARY_START_RE.match(compact):
            break
        if re.match(r"^(?:COOKE|[A-Z]|\[\d+)", compact):
            continue
        collected.append(compact)
        if len(" ".join(collected)) >= 2500:
            break
    return "\n\n".join(collected)


def main() -> int:
    for path in (SOURCE, VALIDATION, PDF):
        if not path.exists():
            sys.exit(f"missing required Cooke source: {path}")

    text = SOURCE.read_text(encoding="utf-8")
    validation = json.loads(VALIDATION.read_text(encoding="utf-8"))
    usable_pages = {
        row["page"]
        for row in validation["pages"]
        if row["usable"]
    }
    pages = [
        Page(int(match.group(1)), match.group(2), match.group(3))
        for match in PAGE_RE.finditer(text)
    ]
    pages_by_number = {page.number: page for page in pages}
    headings = find_headings(pages)
    headings.extend(
        {
            **placeholder,
            "page_flagged": True,
            "ocr_number": placeholder["number"],
            "number_corrected": False,
            "manual_visual_heading": True,
        }
        for placeholder in VISUALLY_VERIFIED_PLACEHOLDERS
    )
    headings.sort(
        key=lambda heading: (
            heading["source_page"],
            heading["line_number"],
        )
    )

    records: list[dict] = []
    for index, heading in enumerate(headings):
        next_heading = headings[index + 1] if index + 1 < len(headings) else None
        if heading["manual_visual_heading"]:
            block = ""
            source_pages = [heading["source_page"]]
            used_ocr_pages = []
            quarantined_pages = [heading["source_page"]]
            any_flagged = True
        else:
            (
                block,
                source_pages,
                used_ocr_pages,
                quarantined_pages,
                any_flagged,
            ) = record_block(
                pages_by_number,
                heading,
                next_heading,
                usable_pages,
            )
        section_id, section_label = section_for(
            heading["number"],
            heading["label"],
        )
        cis = CIS_RE.search(heading["title"])
        date = DATE_RE.search(heading["title"])
        record_id = f"cooke1903:{heading['number']}"
        if heading["label"]:
            record_id += ":" + re.sub(r"\s+", "-", heading["label"].lower())
        text_candidate = extract_consonantal_candidate(block)
        translation_candidate = extract_translation_candidate(block)
        # Cooke is printed in two columns. OCR reading order can cross the
        # text/translation boundary even on an otherwise clean page, so every
        # extracted field remains a retrieval candidate until the PDF image is
        # checked. Quarantined pages are never used to populate the candidate.
        requires_visual = True
        records.append(
            {
                "record_id": record_id,
                "cooke_number": heading["number"],
                "subentry": heading["label"] or None,
                "section": section_id,
                "section_label": section_label,
                "heading": heading["title"] or None,
                "source_page_pdf": heading["source_page"],
                "source_page_printed": heading["printed_page"],
                "source_pages_in_block": source_pages,
                "ocr_pages_used": used_ocr_pages,
                "quarantined_pages_skipped": quarantined_pages,
                "cis": (
                    {
                        "volume": cis.group(1).lower(),
                        "number": cis.group(2),
                    }
                    if cis
                    else None
                ),
                "date_text": date.group(0).strip() if date else None,
                "consonantal_text_candidate": text_candidate or None,
                "translation_candidate": translation_candidate or None,
                "ocr_quality": {
                    "start_page_flagged": heading["page_flagged"],
                    "block_contains_flagged_page": any_flagged,
                    "start_page_usable": (
                        heading["source_page"] in usable_pages
                    ),
                    "block_contains_quarantined_page": bool(
                        quarantined_pages
                    ),
                    "number_corrected_from_ocr": (
                        heading["ocr_number"]
                        if heading["number_corrected"]
                        else None
                    ),
                    "heading_transcribed_from_pdf": heading[
                        "manual_visual_heading"
                    ],
                    "requires_pdf_visual_check_before_citation": requires_visual,
                },
                "status": "candidate-requires-visual-check",
                "judgment": "not-issued",
            }
        )

    present_numbers = {record["cooke_number"] for record in records}
    missing_numbers = [
        number for number in range(1, 151) if number not in present_numbers
    ]
    duplicate_ids = sorted(
        record_id
        for record_id in {record["record_id"] for record in records}
        if sum(record["record_id"] == record_id for record in records) > 1
    )
    pdf_sha256 = sha256(PDF)
    collation_batches = apply_visual_collations(records, pdf_sha256)
    payload = {
        "schema_version": "1.1",
        "generated_by": "scripts/build_cooke1903_layer.py",
        "source": {
            "citation": (
                "George Albert Cooke, A Text-book of North-Semitic "
                "Inscriptions, Oxford: Clarendon Press, 1903"
            ),
            "pdf_path": "Data raw/Cooke 1903.pdf",
            "pdf_sha256": pdf_sha256,
            "validated_ocr_path": (
                "Data raw/cooke1903_text/mistral_ocr/cooke1903_usable.md"
            ),
            "validated_ocr_sha256": sha256(SOURCE),
            "quality_report_path": (
                "Data raw/cooke1903_text/mistral_ocr/quality-report.json"
            ),
            "validation_report_path": (
                "Data raw/cooke1903_text/mistral_ocr/validation-report.json"
            ),
            "pages_total": validation["summary"]["pages_total"],
            "pages_flagged_for_repetition": validation["summary"][
                "reason_counts"
            ]["repetition"],
            "pages_usable_after_validation": validation["summary"][
                "pages_usable"
            ],
            "pages_quarantined_after_validation": validation["summary"][
                "pages_quarantined"
            ],
            "vowel_points_removed": True,
            "scope_note": (
                "طبقة مصدر استرجاعية لا معجم كامل لأي لغة. النص السامي "
                "والترجمة مرشحا OCR فقط، وكل سجل يراجع على صورة PDF قبل "
                "الاستشهاد به."
            ),
            "visual_collation_batches": collation_batches,
        },
        "inventory": {
            "record_count": len(records),
            "numbered_units_present": len(present_numbers),
            "missing_numbered_units": missing_numbers,
            "duplicate_record_ids": duplicate_ids,
            "records_requiring_visual_check": sum(
                record["ocr_quality"][
                    "requires_pdf_visual_check_before_citation"
                ]
                for record in records
            ),
            "records_visually_collated": sum(
                record["status"] == "visually-collated"
                for record in records
            ),
            "records_with_partial_visual_collation": sum(
                record["status"] == "visual-collation-partial"
                for record in records
            ),
            "records_with_consonantal_candidate": sum(
                bool(record["consonantal_text_candidate"]) for record in records
            ),
            "records_with_translation_candidate": sum(
                bool(record["translation_candidate"]) for record in records
            ),
            "records_with_quarantined_page_skipped": sum(
                bool(record["quarantined_pages_skipped"])
                for record in records
            ),
            "records_starting_on_quarantined_page": sum(
                not record["ocr_quality"]["start_page_usable"]
                for record in records
            ),
        },
        "records": records,
    }

    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps(payload["inventory"], ensure_ascii=False, indent=2))
    print("wrote:", OUTPUT.relative_to(ROOT))
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
