#!/usr/bin/env python3
"""Build a provenance-preserving Akkadian lexical overlay.

The output is a retrieval index, not a linguistic verdict and not a claim that
the published Akkadian lexicon has been exhausted. Exact citation strings are
the identity key. A separate comparison key is only a review hint and never
merges source records.
"""

from __future__ import annotations

import argparse
import csv
import hashlib
from html.parser import HTMLParser
import html
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PIN_PATH = ROOT / "04-cross-linguistic/data/akkadian-auxiliary-source-pin.json"
DEFAULT_RECORDS = (
    ROOT / "Resources/akkadian/derived/akkadian-lexical-source-records.jsonl"
)
DEFAULT_HEADWORDS = (
    ROOT / "Resources/akkadian/derived/akkadian-lexical-headwords.jsonl"
)
DEFAULT_SUMMARY = (
    ROOT / "Resources/akkadian/derived/akkadian-lexical-overlay-summary.json"
)
ID_PATTERN = re.compile(r"(?:P\d{4}|PN\d{3})")
CUNEIFORM_RANGE = range(0x12000, 0x12550)


def digest(path: Path, algorithm: str) -> str:
    hasher = hashlib.new(algorithm)
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def verify_pin(item: dict[str, Any]) -> Path:
    path = ROOT / item["path"]
    if not path.is_file():
        raise ValueError(f"missing pinned source: {item['path']}")
    if path.stat().st_size != item["bytes"]:
        raise ValueError(
            f"size mismatch for {item['id']}: "
            f"{path.stat().st_size} != {item['bytes']}"
        )
    for algorithm in ("md5", "sha256"):
        actual = digest(path, algorithm)
        if actual != item[algorithm]:
            raise ValueError(
                f"{algorithm} mismatch for {item['id']}: "
                f"{actual} != {item[algorithm]}"
            )
    return path


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def surface_key(value: str) -> str:
    return nfc(value).casefold()


def comparison_key(value: str) -> str:
    """Return an explicitly non-authoritative duplicate-review hint."""
    result = surface_key(value)
    result = result.replace("’", "ʾ").replace("'", "ʾ")
    result = result.replace("š", "sh").replace("ḫ", "kh").replace("j", "y")
    result = re.sub(r"^\*", "", result)
    result = result.replace("[", "").replace("]", "")
    result = re.sub(r"\((?:m|n|f|pl|sg)\.?\)", "", result, flags=re.I)
    result = re.sub(r"\s+\([A-Z0-9ŠṢṬḪ]+\)$", "", result)
    result = re.sub(r"([aiuāīūâîû])m$", r"\1", result)
    result = re.sub(r"[?.,;:]$", "", result)
    return re.sub(r"\s+", " ", result).strip()


def has_cuneiform(value: str) -> bool:
    return any(ord(character) in CUNEIFORM_RANGE for character in value)


def unique_text(values: list[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        normalized = nfc(value)
        if normalized and normalized not in seen:
            seen.add(normalized)
            result.append(normalized)
    return result


class DalParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.entries: list[dict[str, str]] = []
        self.current: dict[str, Any] | None = None
        self.section_depth = 0
        self.capture_title = False
        self.capture_first_paragraph = False

    def handle_starttag(
        self, tag: str, attrs: list[tuple[str, str | None]]
    ) -> None:
        attributes = dict(attrs)
        if tag == "section":
            if self.current is not None:
                self.section_depth += 1
            elif ID_PATTERN.fullmatch(attributes.get("id", "")):
                self.current = {
                    "id": attributes["id"],
                    "title_parts": [],
                    "meta_parts": [],
                    "text_parts": [],
                    "first_paragraph_complete": False,
                }
                self.section_depth = 1
            return
        if self.current is None:
            return
        if tag == "h2":
            self.capture_title = True
        elif tag == "p" and not self.current["first_paragraph_complete"]:
            self.capture_first_paragraph = True

    def handle_endtag(self, tag: str) -> None:
        if self.current is None:
            return
        if tag == "h2":
            self.capture_title = False
        elif tag == "p" and self.capture_first_paragraph:
            self.capture_first_paragraph = False
            self.current["first_paragraph_complete"] = True
        elif tag == "section":
            self.section_depth -= 1
            if self.section_depth == 0:
                self.entries.append(
                    {
                        "id": self.current["id"],
                        "title": compact(self.current["title_parts"]),
                        "meta": compact(self.current["meta_parts"]),
                        "text": compact(self.current["text_parts"]),
                    }
                )
                self.current = None

    def handle_data(self, data: str) -> None:
        if self.current is None:
            return
        self.current["text_parts"].append(data)
        if self.capture_title:
            self.current["title_parts"].append(data)
        if self.capture_first_paragraph:
            self.current["meta_parts"].append(data)


def compact(parts: list[str]) -> str:
    return re.sub(r"\s+", " ", html.unescape(" ".join(parts))).strip()


def dal_headword(title: str) -> tuple[str, str]:
    if " “" in title:
        headword, gloss = title.split(" “", 1)
        return nfc(headword), "“" + gloss
    cut: int | None = None
    for match in re.finditer(r"\s+\(([^)]*)\)", title):
        inner = match.group(1).strip().casefold()
        if inner not in {"m", "f", "m.", "f.", "pl", "pl.", "?"} and not re.fullmatch(
            r"[a-z]?akk", inner
        ):
            cut = match.start()
            break
    if cut is None:
        return nfc(title), ""
    return nfc(title[:cut]), nfc(title[cut:])


def kaikki_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            entry = json.loads(line)
            if entry.get("lang_code") != "akk":
                raise ValueError(f"Kaikki language mismatch at line {line_number}")
            if entry.get("pos") == "character":
                continue
            source_word = nfc(str(entry.get("word", "")))
            headword = source_word
            state = "ready"
            if has_cuneiform(source_word):
                romanizations = [
                    str(form.get("form", ""))
                    for form in entry.get("forms", [])
                    if "romanization" in form.get("tags", []) and form.get("form")
                ]
                if romanizations:
                    headword = nfc(romanizations[0])
                else:
                    headword = ""
                    state = "romanization-gap"
            glosses = unique_text(
                [
                    gloss
                    for sense in entry.get("senses", [])
                    for gloss in (
                        sense.get("glosses")
                        or sense.get("raw_glosses")
                        or []
                    )
                ]
            )
            records.append(
                {
                    "source_record_id": f"kaikki:{line_number}",
                    "source": "kaikki_akkadian_2026_07_16",
                    "source_word": source_word,
                    "headword": headword,
                    "pos": str(entry.get("pos") or "unknown"),
                    "glosses": glosses or ["meaning not supplied"],
                    "classification": (
                        "proper-name" if entry.get("pos") == "name" else "lexical"
                    ),
                    "retrieval_state": state,
                }
            )
    return records


def kaggle_records(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames != ["word", "translation"]:
            raise ValueError(f"unexpected Kaggle columns: {reader.fieldnames}")
        for row_number, row in enumerate(reader, 2):
            word = nfc(row["word"])
            gloss = nfc(row["translation"])
            if not word or not gloss:
                raise ValueError(f"empty Kaggle field at row {row_number}")
            is_name = bool(
                re.search(r"(^|[;,( ])(?:PN|DN|TN)([;,) ]|$)", gloss, re.I)
            )
            records.append(
                {
                    "source_record_id": f"kaggle-v25:{row_number}",
                    "source": "kaggle_akkadianenglish_lexical_index_v25",
                    "source_word": word,
                    "headword": word,
                    "pos": "name" if is_name else "unknown",
                    "glosses": [gloss],
                    "classification": "proper-name" if is_name else "lexical",
                    "retrieval_state": "ready",
                }
            )
    return records


def dal_records(path: Path) -> list[dict[str, Any]]:
    parser = DalParser()
    parser.feed(path.read_text(encoding="utf-8"))
    ids = {entry["id"] for entry in parser.entries}
    expected = {
        *(f"P{index:04d}" for index in range(1, 830)),
        *(f"PN{index:03d}" for index in range(1, 142)),
    }
    if ids != expected:
        missing = sorted(expected - ids)
        extra = sorted(ids - expected)
        raise ValueError(f"DAL ID mismatch: missing={missing} extra={extra}")

    records: list[dict[str, Any]] = []
    for entry in parser.entries:
        headword, gloss = dal_headword(entry["title"])
        pos = entry["meta"].split("|", 1)[0].strip() or "unknown"
        records.append(
            {
                "source_record_id": f"dal-p-1.1:{entry['id']}",
                "source": "dal_p_1_1",
                "source_word": entry["title"],
                "headword": headword,
                "pos": pos.casefold(),
                "glosses": [gloss or entry["title"]],
                "classification": (
                    "proper-name" if pos == "PROPN" else "lexical"
                ),
                "retrieval_state": "ready",
                "published_reference_text": entry["text"],
                "url": f"https://www.dnms.org/dal/p#{entry['id']}",
            }
        )
    return records


def render_jsonl(records: list[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n"
        for record in records
    )


def build_headwords(records: list[dict[str, Any]]) -> list[dict[str, Any]]:
    groups: dict[str, list[dict[str, Any]]] = {}
    for record in records:
        if not record["headword"]:
            continue
        groups.setdefault(surface_key(record["headword"]), []).append(record)

    headwords: list[dict[str, Any]] = []
    for index, key in enumerate(sorted(groups), 1):
        members = groups[key]
        known_pos = {
            str(member["pos"]).casefold()
            for member in members
            if str(member["pos"]).casefold() not in {"", "unknown"}
        }
        pos = next(iter(known_pos)) if len(known_pos) == 1 else "unknown"
        glosses = unique_text(
            [gloss for member in members for gloss in member["glosses"]]
        )
        headword = nfc(members[0]["headword"])
        headwords.append(
            {
                "word": headword,
                "lang": "Akkadian",
                "lang_code": "akk",
                "pos": pos,
                "senses": [
                    {
                        "glosses": glosses,
                        "id": f"akkadian-overlay-{index:05d}",
                    }
                ],
                "surface_key": key,
                "comparison_key": comparison_key(headword),
                "source_record_ids": [
                    member["source_record_id"] for member in members
                ],
                "source_ids": sorted({member["source"] for member in members}),
                "classifications": sorted(
                    {member["classification"] for member in members}
                ),
                "scope_note": (
                    "اتحاد استرجاعي متعدد المصادر؛ لا يمثل حكم صلة ولا "
                    "اكتمال المعجم الأكادي المنشور."
                ),
            }
        )
    return headwords


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w", encoding="utf-8", newline="\n", delete=False, dir=path.parent
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--records", type=Path, default=DEFAULT_RECORDS)
    parser.add_argument("--headwords", type=Path, default=DEFAULT_HEADWORDS)
    parser.add_argument("--summary", type=Path, default=DEFAULT_SUMMARY)
    args = parser.parse_args()

    pin = json.loads(PIN_PATH.read_text(encoding="utf-8"))
    paths = {item["id"]: verify_pin(item) for item in pin["sources"]}
    records = [
        *kaikki_records(paths["kaikki_akkadian_2026_07_16"]),
        *kaggle_records(paths["kaggle_akkadianenglish_lexical_index_v25"]),
        *dal_records(paths["dal_p_1_1"]),
    ]
    headwords = build_headwords(records)
    comparison_groups = {
        comparison_key(item["word"]) for item in headwords
    }
    source_counts: dict[str, int] = {}
    source_unique: dict[str, set[str]] = {}
    for record in records:
        source_counts[record["source"]] = source_counts.get(record["source"], 0) + 1
        if record["headword"]:
            source_unique.setdefault(record["source"], set()).add(
                surface_key(record["headword"])
            )
    summary = {
        "schema": "akkadian-lexical-overlay-summary-v1",
        "source_records": len(records),
        "source_record_counts": source_counts,
        "source_unique_exact_headwords": {
            source: len(values) for source, values in source_unique.items()
        },
        "exact_surface_headwords": len(headwords),
        "comparison_hint_groups": len(comparison_groups),
        "blocked_without_romanization": sum(
            record["retrieval_state"] == "romanization-gap"
            for record in records
        ),
        "proper_name_records": sum(
            record["classification"] == "proper-name" for record in records
        ),
        "linguistic_verdicts": False,
        "complete_published_lexicon_claim": False,
    }

    rendered_records = render_jsonl(records)
    rendered_headwords = render_jsonl(headwords)
    rendered_summary = json.dumps(summary, ensure_ascii=False, indent=2) + "\n"
    targets = {
        args.records: rendered_records,
        args.headwords: rendered_headwords,
        args.summary: rendered_summary,
    }
    if args.check:
        stale = [
            str(path)
            for path, expected_content in targets.items()
            if not path.is_file()
            or path.read_text(encoding="utf-8") != expected_content
        ]
        if stale:
            raise SystemExit(f"akkadian lexical overlay is stale: {stale}")
        print(json.dumps({"check": "CLEAN", **summary}, ensure_ascii=False))
        return 0

    for path, content in targets.items():
        atomic_write(path, content)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
