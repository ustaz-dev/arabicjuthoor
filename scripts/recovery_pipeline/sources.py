from __future__ import annotations

import hashlib
import json
import re
import xml.etree.ElementTree as ET
import zipfile
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from typing import Any, Iterator


TEI = "{http://www.tei-c.org/ns/1.0}"
XML_ID = "{http://www.w3.org/XML/1998/namespace}id"
ROMANIZATION_METADATA = {
    "archaic", "comparable", "defective", "dialectal", "irregular", "obsolete",
    "productive", "rare", "uncomparable", "unproductive",
}
INFLECTION_TAGS = {
    "ablative", "accusative", "active", "comparative", "dative", "dual", "feminine",
    "first-person", "future", "future-perfect", "genitive", "gerund", "gerundive",
    "imperative", "imperfect", "indicative", "infinitive", "locative", "masculine",
    "letter", "lowercase", "neuter", "nominative", "participle", "passive", "perfect", "person", "pluperfect",
    "plural", "present", "second-person", "singular", "subjunctive", "superlative",
    "supine", "third-person", "uppercase", "vocative",
}

# A direction hint is deliberately broader than the two literal phrases that
# Kaikki happens to use most often.  It is only a screen: a true value removes
# an entry from an inheritance queue until a human reads the named route; it
# never decides the donor or the final transmission verdict by itself.
SEMITIC_DONOR = re.compile(
    r"(?i)\b(?:proto[- ](?:west[- ]|east[- ]|central[- ]|northwest[- ]|south[- ])?)?"
    r"(?:akkadian|arabic|aramaic|canaanite|eblaite|hebrew|maltese|"
    r"phoenician|punic|sabaean|semitic|syriac|ugaritic)\b"
)
TRANSMISSION_WORDING = re.compile(
    r"(?i)\b(?:borrowed\s+from|loanword|via|calque(?:d)?|ultimately\s+from)\b"
)


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
    alternative_of: bool
    form_targets: tuple[str, ...]
    alternative_targets: tuple[str, ...]
    derived_terms: tuple[str, ...]
    related_terms: tuple[str, ...]
    source_stratum: str = ""
    source_scope_note: str = ""


def source_path(profile: dict[str, Any], root: Path) -> Path:
    source = profile.get("source")
    if not source:
        raise ValueError(f"Profile {profile['language']} has no corpus source")
    return root / source["path"]


def verify_source_pin(path: Path, source: dict[str, Any]) -> None:
    expected_size = source.get("expected_size_bytes")
    if expected_size is not None and path.stat().st_size != int(expected_size):
        raise ValueError(
            f"Pinned source size mismatch for {path}: "
            f"{path.stat().st_size} != {int(expected_size)}"
        )
    expected_hashes = {
        algorithm: str(source.get(algorithm) or "").casefold()
        for algorithm in ("md5", "sha256")
        if source.get(algorithm)
    }
    if not expected_hashes:
        return
    digesters = {algorithm: hashlib.new(algorithm) for algorithm in expected_hashes}
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            for digester in digesters.values():
                digester.update(chunk)
    for algorithm, expected in expected_hashes.items():
        actual = digesters[algorithm].hexdigest()
        if actual != expected:
            raise ValueError(
                f"Pinned source {algorithm.upper()} mismatch for {path}: {actual} != {expected}"
            )


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


def _kaikki_loan_hint(etymology: str) -> bool:
    """Detect explicit transmission direction without inferring inheritance.

    Besides direct borrowing vocabulary, a bare ``from`` is screened only
    when the following phrase names a Semitic donor.  Thus ordinary
    ``from Proto-Indo-European`` ancestry is not turned into a loan hint.
    """

    text = str(etymology or "").strip()
    if not text:
        return False
    if TRANSMISSION_WORDING.search(text):
        return True
    for match in re.finditer(r"(?i)\bfrom\b", text):
        # The donor normally occurs immediately after From, but allow a short
        # scholarly qualifier such as "probably from Proto-West Semitic".
        if SEMITIC_DONOR.search(text[match.end():match.end() + 96]):
            return True
    return False


def _is_form_of(entry: dict[str, Any]) -> bool:
    for sense in entry.get("senses", []) or []:
        tags = set(sense.get("tags") or [])
        if "form-of" in tags or sense.get("form_of"):
            return True
    return False


def _is_alternative_of(entry: dict[str, Any]) -> bool:
    for sense in entry.get("senses", []) or []:
        tags = set(sense.get("tags") or [])
        if "alt-of" in tags or sense.get("alt_of"):
            return True
    return False


def _language_link_words(sense: dict[str, Any], language: str) -> list[str]:
    normalized_language = language.casefold().replace("_", " ").strip()
    words: list[str] = []
    for link in sense.get("links", []) or []:
        if not isinstance(link, list) or len(link) < 2 or not str(link[0]).strip():
            continue
        destination = str(link[1])
        if "#" not in destination:
            continue
        fragment = destination.rsplit("#", 1)[1].casefold().replace("_", " ").strip()
        if not normalized_language or fragment == normalized_language:
            words.extend(part.strip() for part in re.split(r"\s*/\s*", str(link[0])) if part.strip())
    return list(dict.fromkeys(words))


def _foreign_link_words(sense: dict[str, Any], language: str) -> set[str]:
    normalized_language = language.casefold().replace("_", " ").strip()
    words: set[str] = set()
    for link in sense.get("links", []) or []:
        if not isinstance(link, list) or len(link) < 2 or not str(link[0]).strip():
            continue
        destination = str(link[1])
        if "#" not in destination:
            continue
        fragment = destination.rsplit("#", 1)[1].casefold().replace("_", " ").strip()
        # Kaikki also uses URL fragments for section names, so a fragment that
        # merely differs from the entry language is not proof of a foreign
        # target. English is the explicitly labelled prose leak handled here.
        if fragment == "english" and normalized_language != "english":
            words.add(str(link[0]).strip().casefold())
    return words


def _foreign_link_equivalent(value: str, foreign_words: set[str]) -> bool:
    normalized = value.strip(" \t.,;:").casefold()
    if normalized.startswith("and "):
        normalized = normalized[4:].strip()
    choices = {normalized, normalized.removesuffix("s")}
    return any(choice in foreign_words or choice.removesuffix("s") in foreign_words for choice in choices)


def _script_lemma_candidate(value: str, language: str) -> str:
    ranges = {
        "hebrew": ((0x0590, 0x05FF), (0x10900, 0x1091F)),
        "aramaic": ((0x0590, 0x05FF), (0x0700, 0x074F), (0x10840, 0x1085F)),
        # U+03E2..U+03EF are legacy Coptic letters whose Unicode names
        # explicitly begin with COPTIC.  They must not make a value Greek.
        "ancient greek": (
            (0x0370, 0x03E1),
            (0x03F0, 0x03FF),
            (0x1F00, 0x1FFF),
        ),
    }.get(language.casefold().replace("_", " ").strip())
    if not ranges:
        return value
    script_positions = [
        index for index, char in enumerate(value) if any(start <= ord(char) <= end for start, end in ranges)
    ]
    if not script_positions:
        return ""
    latin_positions = [index for index, char in enumerate(value) if char.isascii() and char.isalpha()]
    if latin_positions and min(latin_positions) < min(script_positions):
        return ""
    if latin_positions:
        return value[:min(latin_positions)].rstrip(" \t.,:;([{/-")
    return value


def _latin_structured_target_candidates(value: str) -> tuple[str, ...]:
    """Recover only lemmas explicitly named inside malformed Latin target fields."""
    candidates: list[str] = []
    contamination_prefixes = (
        "a main ", "and ", "as opposed to ", "causing ", "from ", "inherited from ", "or pertaining to ",
        "probably inherited from ", "ultimately from ", "used to ",
        "to ",
    )
    explicit_of = re.compile(
        r"^(?:(?:alternative form|medieval spelling|mediaeval spelling)\s+of\s+(.+)"
        r"|the deponent verb\s+(.+))$",
        re.IGNORECASE,
    )
    participle_of = re.compile(
        r"^(?:(.+?)\s+(?:and|or)\s+)?(?:perfect|present|future)"
        r"(?:\s+(?:active|passive))?\s+participle of\s+(.+)$",
        re.IGNORECASE,
    )
    sensed_lemma = re.compile(r"^(.+?)\s+with\s+(?:active|passive)\s+sense$", re.IGNORECASE)
    named_lemma = re.compile(
        r"^(?:frequentative of|intransitive|latin|the verb)\s+(.+)$", re.IGNORECASE
    )
    paired_lemmas = re.compile(r"^(\S+)\s+and\s+(\S+)$", re.IGNORECASE)
    pos_suffix = re.compile(r"^(\S+)\s+[mfn]$", re.IGNORECASE)

    for line in (part.strip(" \t.,;:") for part in value.splitlines()):
        if not line:
            continue
        lower = line.casefold()
        if lower.startswith(contamination_prefixes):
            continue
        if match := participle_of.match(line):
            if match.group(1):
                candidates.append(match.group(1).strip())
            candidates.append(match.group(2).strip())
            continue
        if match := explicit_of.match(line):
            candidates.append((match.group(1) or match.group(2)).strip())
            continue
        if match := sensed_lemma.match(line):
            candidates.append(match.group(1).strip())
            continue
        if match := named_lemma.match(line):
            candidates.append(match.group(1).strip())
            continue
        if match := paired_lemmas.match(line):
            candidates.extend((match.group(1), match.group(2)))
            continue
        if match := pos_suffix.match(line):
            candidates.append(match.group(1).strip())
            continue
        candidates.append(line)
    return tuple(dict.fromkeys(item for item in candidates if item))


def _typed_targets(entry: dict[str, Any], field: str, tag: str) -> tuple[str, ...]:
    targets: list[str] = []
    language = str(entry.get("lang") or "").strip()
    for sense in entry.get("senses", []) or []:
        tags = set(sense.get("tags") or [])
        if not sense.get(field) and tag not in tags:
            continue
        linked_words = _language_link_words(sense, language)
        foreign_words = _foreign_link_words(sense, language)
        structured_targets = [
            str(item["word"]).strip()
            for item in (sense.get(field, []) or [])
            if isinstance(item, dict) and item.get("word") and str(item["word"]).strip()
        ]
        for target in structured_targets:
            if (
                field == "form_of" and not tags.intersection(INFLECTION_TAGS)
                and _foreign_link_equivalent(target, foreign_words)
            ):
                continue
            linked_prefixes = [
                word for word in linked_words
                if target == word or (
                    target.startswith(word) and len(target) > len(word)
                    and target[len(word)] in " \t#.,:;([{"
                )
            ]
            if linked_prefixes:
                targets.append(max(linked_prefixes, key=len))
            elif linked_words:
                # A same-language source link is stronger than prose accidentally
                # serialized into form_of/alt_of. Do not turn the unmatched prose
                # into a phantom lexical target.
                continue
            else:
                candidates = (
                    _latin_structured_target_candidates(target)
                    if language.casefold().strip() == "latin" else (target,)
                )
                for candidate in candidates:
                    if script_target := _script_lemma_candidate(candidate, language):
                        targets.append(script_target)
        if not structured_targets and tag in tags and linked_words:
            targets.append(linked_words[0])
    return tuple(dict.fromkeys(target for target in targets if target))


def _relation_terms(entry: dict[str, Any], field: str) -> tuple[str, ...]:
    return tuple(dict.fromkeys(
        str(item["word"]).strip()
        for item in entry.get(field, []) or []
        if isinstance(item, dict) and item.get("word") and str(item["word"]).strip()
    ))


def _kaikki_category_names(entry: dict[str, Any]) -> tuple[str, ...]:
    categories: list[str] = []
    for value in entry.get("categories", []) or []:
        categories.append(str(value.get("name") or "") if isinstance(value, dict) else str(value))
    for sense in entry.get("senses", []) or []:
        for value in sense.get("categories", []) or []:
            categories.append(str(value.get("name") or "") if isinstance(value, dict) else str(value))
    return tuple(item for item in categories if item)


def _kaikki_attestation_text(entry: dict[str, Any]) -> str:
    parts: list[str] = []
    for sense in entry.get("senses", []) or []:
        for field in ("examples", "quotations"):
            for example in sense.get(field, []) or []:
                if isinstance(example, dict):
                    parts.extend(str(example.get(key) or "") for key in ("ref", "type", "text"))
                else:
                    parts.append(str(example))
    return " ".join(parts).casefold()


def _kaikki_scout_stratum(entry: dict[str, Any]) -> str:
    categories = _kaikki_category_names(entry)
    tags = tuple(
        str(tag)
        for sense in entry.get("senses", []) or []
        for tag in sense.get("tags", []) or []
    )
    marker_text = " ".join((
        str(entry.get("word") or ""),
        str(entry.get("title") or ""),
        str(entry.get("original_title") or ""),
        *categories,
        *tags,
    )).casefold()
    if (
        str(entry.get("word") or "").startswith("*")
        or "reconstruction" in marker_text
        or "reconstructed" in marker_text
    ):
        return "reconstruction"
    if (
        str(entry.get("pos") or "") in {"name", "proper-noun", "proper_noun"}
        or any(
            "given names" in category.casefold() or "proper nouns" in category.casefold()
            for category in categories
        )
    ):
        return "proper-name"
    attestation_text = _kaikki_attestation_text(entry)
    has_explicit_attestation = bool(entry.get("attestations")) or bool(attestation_text)
    for sense in entry.get("senses", []) or []:
        has_explicit_attestation |= bool(sense.get("examples") or sense.get("quotations"))
    if has_explicit_attestation:
        inscription_markers = (
            "inscription", "sarcophagus", "cippus", "cippi", "stele", "stela",
            "cis ", "kanaanäische und aramäische inschriften",
        )
        if any(marker in attestation_text for marker in inscription_markers):
            return "inscription-attestation"
        return "other-textual-attestation"
    if any("attested" in category.casefold() for category in categories):
        return "attestation-claimed"
    return "attestation-unspecified"


def iter_kaikki(
    path: Path,
    source_id: str,
    *,
    expected_language_code: str = "",
    source_scope_note: str = "",
    expected_entries: int | None = None,
    bounded_scout: bool = False,
) -> Iterator[LexiconEntry]:
    entries_seen = 0
    with path.open("r", encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            try:
                raw = json.loads(line)
            except json.JSONDecodeError as error:
                raise ValueError(f"Invalid JSON in {path} at line {line_number}: {error}") from error
            if not isinstance(raw, dict):
                raise ValueError(f"Kaikki row is not an object in {path} at line {line_number}")
            if expected_language_code and raw.get("lang_code") != expected_language_code:
                raise ValueError(
                    f"Unexpected language code in {path} at line {line_number}: "
                    f"{raw.get('lang_code')!r} != {expected_language_code!r}"
                )
            if bounded_scout:
                if not isinstance(raw.get("word"), str) or not raw["word"].strip():
                    raise ValueError(f"Bounded Kaikki row lacks word in {path} at line {line_number}")
                if not isinstance(raw.get("lang"), str) or not raw["lang"].strip():
                    raise ValueError(f"Bounded Kaikki row lacks lang in {path} at line {line_number}")
                if not isinstance(raw.get("pos"), str) or not raw["pos"].strip():
                    raise ValueError(f"Bounded Kaikki row lacks pos in {path} at line {line_number}")
                if not isinstance(raw.get("senses"), list) or not raw["senses"]:
                    raise ValueError(f"Bounded Kaikki row lacks a nonempty senses list in {path} at line {line_number}")
            entries_seen += 1
            senses = raw.get("senses", []) or []
            preferred = next((str(s.get("id")) for s in senses if s.get("id")), "")
            _, source_entry_id = _stable_id(source_id, preferred, line)
            # Kaikki sense IDs are not globally unique, and exact duplicate rows
            # can occur. The line position is stable inside the pinned snapshot
            # and prevents either raw row from disappearing on a collision.
            entry_id = f"{source_id}:{line_number}:{source_entry_id}"
            etymology = str(raw.get("etymology_text") or "")
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
                loan_hint=_kaikki_loan_hint(etymology),
                form_of=_is_form_of(raw),
                alternative_of=_is_alternative_of(raw),
                form_targets=_typed_targets(raw, "form_of", "form-of"),
                alternative_targets=_typed_targets(raw, "alt_of", "alt-of"),
                derived_terms=_relation_terms(raw, "derived"),
                related_terms=_relation_terms(raw, "related"),
                source_stratum=_kaikki_scout_stratum(raw) if source_scope_note else "",
                source_scope_note=source_scope_note,
            )
    if expected_entries is not None and entries_seen != expected_entries:
        raise ValueError(
            f"Kaikki entry count mismatch for {path}: {entries_seen} != {expected_entries}"
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
            alternative_of=False,
            form_targets=(),
            alternative_targets=(),
            derived_terms=(),
            related_terms=(),
        )
        entry.clear()


def _aed_text(parts: list[str]) -> str:
    return " ".join("".join(parts).replace("\xa0", " ").split()).removeprefix("•").strip()


class _AEDPageParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.title_parts: list[str] = []
        self.headword_parts: list[str] = []
        self.tooltips: dict[str, str] = {}
        self.same_root_links: list[str] = []
        self._capture_title = False
        self._capture_headword = False
        self._heading_parts: list[str] | None = None
        self._section = ""
        self._link_parts: list[str] | None = None
        self._tooltip_depth = 0
        self._tooltip_value: list[str] = []
        self._tooltip_label: list[str] = []
        self._tooltip_in_label = False

    @staticmethod
    def _classes(attributes: list[tuple[str, str | None]]) -> set[str]:
        value = dict(attributes).get("class") or ""
        return set(value.split())

    def handle_starttag(self, tag: str, attributes: list[tuple[str, str | None]]) -> None:
        classes = self._classes(attributes)
        if self._tooltip_depth:
            self._tooltip_depth += 1
            if tag == "span" and "tooltiptext" in classes:
                self._tooltip_in_label = True
            return
        if tag == "div" and "tooltip" in classes:
            self._tooltip_depth = 1
            self._tooltip_value = []
            self._tooltip_label = []
            self._tooltip_in_label = False
            return
        if tag == "title":
            self._capture_title = True
        elif tag == "h1" and "main_title" in classes:
            self._capture_headword = True
        elif tag == "h2":
            self._heading_parts = []
        elif tag == "a" and self._section.casefold() == "same root as":
            self._link_parts = []
        elif tag == "br":
            if self._link_parts is not None:
                self._link_parts.append(" ")

    def handle_endtag(self, tag: str) -> None:
        if self._tooltip_depth:
            if tag == "span" and self._tooltip_in_label:
                self._tooltip_in_label = False
            self._tooltip_depth -= 1
            if not self._tooltip_depth:
                label = _aed_text(self._tooltip_label).casefold()
                value = _aed_text(self._tooltip_value)
                if self._section.casefold() == "main information":
                    if not label:
                        raise ValueError("AED main-information tooltip lacks its field label")
                    if label in self.tooltips:
                        raise ValueError(f"AED page repeats main-information field {label!r}")
                    self.tooltips[label] = value
            return
        if tag == "title":
            self._capture_title = False
        elif tag == "h1":
            self._capture_headword = False
        elif tag == "h2" and self._heading_parts is not None:
            self._section = _aed_text(self._heading_parts)
            self._heading_parts = None
        elif tag == "a" and self._link_parts is not None:
            value = _aed_text(self._link_parts)
            if value:
                self.same_root_links.append(value)
            self._link_parts = None

    def handle_data(self, data: str) -> None:
        if self._tooltip_depth:
            (self._tooltip_label if self._tooltip_in_label else self._tooltip_value).append(data)
        if self._capture_title:
            self.title_parts.append(data)
        if self._capture_headword:
            self.headword_parts.append(data)
        if self._heading_parts is not None:
            self._heading_parts.append(data)
        if self._link_parts is not None:
            self._link_parts.append(data)


def _aed_field(fields: dict[str, str], label: str) -> str:
    if f"{label} missing" in fields:
        return ""
    return fields.get(label, "")


def _aed_loan_hint(english: str, german: str) -> bool:
    text = f"{english} {german}".casefold()
    explicit_markers = (
        "loan word",
        "loanword",
        "loan-word",
        "semitisches wort",
        "foreign word",
        "fremdwort",
        "lehnwort",
    )
    return any(marker in text for marker in explicit_markers)


def iter_aed_html_zip(
    path: Path,
    source_id: str,
    *,
    expected_members: int | None = None,
    expected_html_members: int | None = None,
    expected_entries: int | None = None,
) -> Iterator[LexiconEntry]:
    seen_ids: set[str] = set()
    entry_pages = 0
    with zipfile.ZipFile(path) as archive:
        members = archive.infolist()
        html_members = [member for member in members if member.filename.endswith(".html")]
        if expected_members is not None and len(members) != expected_members:
            raise ValueError(
                f"AED archive member count mismatch: {len(members)} != {expected_members}"
            )
        if expected_html_members is not None and len(html_members) != expected_html_members:
            raise ValueError(
                f"AED HTML member count mismatch: {len(html_members)} != {expected_html_members}"
            )
        for member in sorted(html_members, key=lambda item: item.filename):
            try:
                raw = archive.read(member).decode("utf-8")
            except UnicodeDecodeError as error:
                raise ValueError(f"AED page is not valid UTF-8: {member.filename}") from error
            if "<title>AED - Dictionary entry:" not in raw:
                continue
            entry_pages += 1
            parser = _AEDPageParser()
            try:
                parser.feed(raw)
                parser.close()
            except ValueError as error:
                raise ValueError(f"Malformed AED entry page {member.filename}: {error}") from error
            title = _aed_text(parser.title_parts)
            if not title.startswith("AED - Dictionary entry:"):
                raise ValueError(f"AED entry marker/title mismatch in {member.filename}: {title!r}")
            headword = _aed_text(parser.headword_parts)
            lemma_id = _aed_field(parser.tooltips, "lemma id")
            if not headword or not lemma_id:
                raise ValueError(
                    f"AED entry page lacks headword or lemma id: {member.filename}"
                )
            if not lemma_id.isdecimal():
                raise ValueError(f"AED lemma id is not numeric in {member.filename}: {lemma_id!r}")
            if Path(member.filename).stem != lemma_id:
                raise ValueError(
                    f"AED filename/lemma mismatch: {member.filename} != lemma {lemma_id}"
                )
            if lemma_id in seen_ids:
                raise ValueError(f"AED duplicate lemma id: {lemma_id}")
            seen_ids.add(lemma_id)
            german = _aed_field(parser.tooltips, "german translation")
            english = _aed_field(parser.tooltips, "english translation")
            gloss = " | ".join(
                part for part in (
                    f"EN: {english}" if english else "",
                    f"DE: {german}" if german else "",
                ) if part
            )
            bibliography = _aed_field(parser.tooltips, "bibliographical information")
            related_terms = tuple(dict.fromkeys(
                value.split(",", 1)[0].strip()
                for value in parser.same_root_links
                if value.split(",", 1)[0].strip()
            ))
            entry_id, source_entry_id = _stable_id(source_id, lemma_id, raw)
            yield LexiconEntry(
                entry_id=entry_id,
                source_entry_id=source_entry_id,
                headword=headword,
                romanization=headword,
                variants=(),
                pos=_aed_field(parser.tooltips, "part of speech"),
                gloss=gloss,
                # The current inventory schema predates a generic source-note
                # field. Keep AED's exact bibliography visibly labelled here;
                # loan_hint is derived separately from explicit gloss markers,
                # never from a bibliography title.
                etymology=f"[AED bibliography] {bibliography}" if bibliography else "",
                loan_hint=_aed_loan_hint(english, german),
                form_of=False,
                alternative_of=False,
                form_targets=(),
                alternative_targets=(),
                derived_terms=(),
                related_terms=related_terms,
            )
    if expected_entries is not None and entry_pages != expected_entries:
        raise ValueError(f"AED entry-page count mismatch: {entry_pages} != {expected_entries}")
    if entry_pages != len(seen_ids):
        raise ValueError(
            f"AED entry/identity count mismatch: pages={entry_pages}, ids={len(seen_ids)}"
        )


def iter_entries(profile: dict[str, Any], root: Path) -> Iterator[LexiconEntry]:
    source = profile.get("source")
    if not source:
        raise ValueError(f"Profile {profile['language']} has no source")
    path = source_path(profile, root)
    if not path.exists():
        raise FileNotFoundError(path)
    verify_source_pin(path, source)
    if source["format"] == "kaikki-jsonl":
        yield from iter_kaikki(
            path,
            source["id"],
            expected_language_code=str(source.get("expected_language_code") or ""),
            source_scope_note=str(source.get("scope_note") or ""),
            expected_entries=source.get("expected_entries"),
            bounded_scout=bool(source.get("bounded_scout")),
        )
    elif source["format"] == "coptic-tei":
        yield from iter_coptic_tei(path, source["id"])
    elif source["format"] == "aed-html-zip":
        yield from iter_aed_html_zip(
            path,
            source["id"],
            expected_members=source.get("expected_members"),
            expected_html_members=source.get("expected_html_members"),
            expected_entries=source.get("expected_entries"),
        )
    else:
        raise ValueError(f"Unsupported source format: {source['format']}")
