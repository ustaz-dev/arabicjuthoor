#!/usr/bin/env python3
"""Build a conservative inscription inventory from Cooke 1903 OCR.

The source is the quality-filtered Mistral batch OCR. This builder does not
make linguistic judgments. It records source identity, section, heading,
location/date apparatus, page boundaries, consonantal text candidates, and
translation candidates. OCR-suspect pages remain visible and are marked for
visual review instead of being silently dropped.
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
    / "cooke1903_clean.md"
)
QUALITY = (
    ROOT
    / "Data raw"
    / "cooke1903_text"
    / "mistral_ocr"
    / "quality-report.json"
)
PDF = ROOT / "Data raw" / "Cooke 1903.pdf"
OUTPUT = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "cooke-1903-inscription-layer.json"
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
) -> tuple[str, list[int], bool]:
    start_page = heading["source_page"]
    end_page = next_heading["source_page"] if next_heading else start_page
    chunks: list[str] = []
    used_pages: list[int] = []
    any_flagged = False

    for page_number in range(start_page, end_page + 1):
        page = pages_by_number.get(page_number)
        if page is None:
            continue
        if page_number == start_page:
            body = page_text_from_line(page, heading["line_number"])
        else:
            body = page.body
        if next_heading and page_number == next_heading["source_page"]:
            body = "\n".join(
                body.splitlines()[: max(next_heading["line_number"] - 1, 0)]
            )
        chunks.append(body)
        used_pages.append(page_number)
        any_flagged = any_flagged or page.flagged
    return "\n".join(chunks), used_pages, any_flagged


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
    for path in (SOURCE, QUALITY, PDF):
        if not path.exists():
            sys.exit(f"missing required Cooke source: {path}")

    text = SOURCE.read_text(encoding="utf-8")
    quality = json.loads(QUALITY.read_text(encoding="utf-8"))
    pages = [
        Page(int(match.group(1)), match.group(2), match.group(3))
        for match in PAGE_RE.finditer(text)
    ]
    pages_by_number = {page.number: page for page in pages}
    headings = find_headings(pages)

    records: list[dict] = []
    for index, heading in enumerate(headings):
        next_heading = headings[index + 1] if index + 1 < len(headings) else None
        block, source_pages, any_flagged = record_block(
            pages_by_number,
            heading,
            next_heading,
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
        requires_visual = any_flagged or heading["number_corrected"]
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
                    "number_corrected_from_ocr": (
                        heading["ocr_number"]
                        if heading["number_corrected"]
                        else None
                    ),
                    "requires_pdf_visual_check_before_citation": requires_visual,
                },
                "status": (
                    "candidate-requires-visual-check"
                    if requires_visual
                    else "candidate-from-clean-ocr"
                ),
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
    payload = {
        "schema_version": "1.0",
        "generated_by": "scripts/build_cooke1903_layer.py",
        "source": {
            "citation": (
                "George Albert Cooke, A Text-book of North-Semitic "
                "Inscriptions, Oxford: Clarendon Press, 1903"
            ),
            "pdf_path": "Data raw/Cooke 1903.pdf",
            "pdf_sha256": sha256(PDF),
            "clean_ocr_path": (
                "Data raw/cooke1903_text/mistral_ocr/cooke1903_clean.md"
            ),
            "clean_ocr_sha256": sha256(SOURCE),
            "quality_report_path": (
                "Data raw/cooke1903_text/mistral_ocr/quality-report.json"
            ),
            "pages_total": quality["pages_total"],
            "pages_flagged_for_repetition": quality["summary"][
                "pages_flagged_for_repetition"
            ],
            "vowel_points_removed": True,
            "scope_note": (
                "طبقة مصدر استرجاعية لا معجم كامل لأي لغة. النص السامي "
                "مرشح OCR صامتي، ولا يستشهد بصفحة موسومة قبل فحص صورة PDF."
            ),
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
            "records_with_consonantal_candidate": sum(
                bool(record["consonantal_text_candidate"]) for record in records
            ),
            "records_with_translation_candidate": sum(
                bool(record["translation_candidate"]) for record in records
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
