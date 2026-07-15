from __future__ import annotations

import hashlib
import json
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterator


TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ROMANIZATION_METADATA = {
    "archaic", "comparable", "defective", "dialectal", "irregular", "obsolete",
    "productive", "rare", "uncomparable", "unproductive",
}


@dataclass(frozen=True)
class LexiconEntry:
    entry_id: str
    source_entry_id: str
    headword: str
    romanization: str
    variants: tuple[str, ...]
    pos: str
    gloss: str
    etymology: str
    loan_hint: bool
    form_of: bool


def source_path(profile: dict[str, Any], root: Path) -> Path:
    source = profile.get("source")
    if not source:
        raise ValueError(f"Profile {profile['language']} has no corpus source")
    return root / source["path"]


def _stable_id(source_id: str, preferred: str, raw: str) -> tuple[str, str]:
    source_entry_id = preferred or hashlib.sha256(raw.encode("utf-8")).hexdigest()[:24]
    return f"{source_id}:{source_entry_id}", source_entry_id


def _first_gloss(entry: dict[str, Any]) -> str:
    for sense in entry.get("senses", []) or []:
        glosses = sense.get("glosses") or sense.get("raw_glosses") or []
        if glosses:
            return str(glosses[0])
    return ""


def _romanization(entry: dict[str, Any]) -> str:
    def usable(value: object) -> str:
        text = str(value or "").strip()
        return "" if text.casefold() in ROMANIZATION_METADATA else text

    for form in entry.get("forms", []) or []:
        value = usable(form.get("form"))
        if "romanization" in (form.get("tags") or []) and value:
            return value
    for form in entry.get("forms", []) or []:
        value = usable(form.get("roman"))
        if value:
            return value
    return ""


def _is_form_of(entry: dict[str, Any]) -> bool:
    for sense in entry.get("senses", []) or []:
        tags = set(sense.get("tags") or [])
        if "form-of" in tags or sense.get("form_of"):
            return True
    return False


def iter_kaikki(path: Path, source_id: str) -> Iterator[LexiconEntry]:
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}: {error}") from error
            senses = raw.get("senses", []) or []
            preferred = next((str(s.get("id")) for s in senses if s.get("id")), "")
            _, source_entry_id = _stable_id(source_id, preferred, line)
            # Kaikki sense IDs are not globally unique, and exact duplicate rows
            # can occur. The line position is stable inside the pinned snapshot
            # and prevents either raw row from disappearing on a collision.
            entry_id = f"{source_id}:{line_number}:{source_entry_id}"
            etymology = str(raw.get("etymology_text") or "")
            lower_etymology = etymology.casefold()
            variants = tuple(
                dict.fromkeys(
                    str(form.get("form"))
                    for form in (raw.get("forms", []) or [])
                    if form.get("form") and "romanization" not in (form.get("tags") or [])
                )
            )
            yield LexiconEntry(
                entry_id=entry_id,
                source_entry_id=source_entry_id,
                headword=str(raw.get("word") or ""),
                romanization=_romanization(raw),
                variants=variants,
                pos=str(raw.get("pos") or ""),
                gloss=_first_gloss(raw),
                etymology=etymology,
                loan_hint="borrowed from" in lower_etymology or "loanword" in lower_etymology,
                form_of=_is_form_of(raw),
            )


def _texts(element: ET.Element, path: str) -> list[str]:
    return [" ".join("".join(item.itertext()).split()) for item in element.findall(path) if "".join(item.itertext()).strip()]


def iter_coptic_tei(path: Path, source_id: str) -> Iterator[LexiconEntry]:
    for _, entry in ET.iterparse(path, events=("end",)):
        if entry.tag != f"{TEI}entry":
            continue
        source_entry_id = entry.attrib.get(XML_ID, "")
        lemma_form = entry.find(f"./{TEI}form[@type='lemma']")
        if lemma_form is None:
            lemma_form = entry.find(f"./{TEI}form")
        headword = ""
        if lemma_form is not None:
            orth = lemma_form.find(f"./{TEI}orth")
            if orth is not None:
                headword = "".join(orth.itertext()).strip()
        raw_identity = ET.tostring(entry, encoding="unicode")
        entry_id, source_entry_id = _stable_id(source_id, source_entry_id, raw_identity)
        variants = tuple(dict.fromkeys(_texts(entry, f"./{TEI}form/{TEI}orth")))
        pos = next(iter(_texts(entry, f"./{TEI}gramGrp/{TEI}pos")), "")
        glosses = []
        for tag in ("quote", "def"):
            for item in entry.findall(f".//{TEI}{tag}"):
                lang = item.attrib.get("{http://www.w3.org/XML/1998/namespace}lang", "")
                if lang == "en":
                    glosses.append(" ".join("".join(item.itertext()).split()))
        etymology_parts = _texts(entry, f".//{TEI}etym/{TEI}note") + _texts(entry, f".//{TEI}etym/{TEI}ref")
        greek_loan = entry.find(f".//{TEI}ref[@type='greek_lemma::grl_lemma']") is not None
        foreign = entry.attrib.get("type") == "foreign"
        yield LexiconEntry(
            entry_id=entry_id,
            source_entry_id=source_entry_id,
            headword=headword,
            romanization="",
            variants=variants,
            pos=pos,
            gloss=next((item for item in glosses if item), ""),
            etymology="; ".join(etymology_parts),
            loan_hint=foreign or greek_loan,
            form_of=False,
        )
        entry.clear()


def iter_entries(profile: dict[str, Any], root: Path) -> Iterator[LexiconEntry]:
    source = profile.get("source")
    if not source:
        raise ValueError(f"Profile {profile['language']} has no source")
    path = source_path(profile, root)
    if not path.exists():
        raise FileNotFoundError(path)
    if source["format"] == "kaikki-jsonl":
        yield from iter_kaikki(path, source["id"])
    elif source["format"] == "coptic-tei":
        yield from iter_coptic_tei(path, source["id"])
    else:
        raise ValueError(f"Unsupported source format: {source['format']}")
