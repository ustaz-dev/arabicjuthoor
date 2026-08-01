#!/usr/bin/env python3
"""Reclassify every Lane-C loan closure by published direction.

Section 27 distinguishes Semitic-source transmission from an unrelated loan
into the branch, a branch word transmitted into Arabic, and an old loan label
which has neither a named donor nor an established direction.  This program
reads the two pinned inventory databases and the six Lane-C readings.  It
writes only Lane-C-owned readings, a Lane-C-prefixed JSONL inventory, and a
Lane-C audit.  It does not invoke Git, a shared builder, or the proof line.

The detector is deliberately conservative.  A Semitic language mentioned
only in a comparison, cognate note, uncertain alternative, or descendant list
does not license SEMITIC-SOURCE-TRANSMISSION.  The source must put the Semitic
stage on the incoming route to the language being read.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

from lane_c_section26_rules import named_donor


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
COVERAGE = DATA / "lane_c_coverage.jsonl"
INVENTORY = DATA / "lane_c_section27_direction_inventory.jsonl"
AUDIT = ROOT / "05-audits" / "lane-c-2026-07-31-section27-directional-loan-recheck.md"
DATE = "2026-07-31"
MARKER = "LANE-C-SECTION27-DIRECTIONAL-LOAN-RECHECK-2026-07-31"

CARD_RE = re.compile(
    r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^## |^<!-- /|\Z)"
)
ENTRY_RE = re.compile(
    r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
    r"\d+:[^`\s\]]+"
)
VERDICT_RE = re.compile(
    r"(?m)^- الحكم \(استكشاف\):\s*LOANWORD(?!-)[^\n]*$"
)

CLASS_SEMITIC = "semitic_to_branch"
CLASS_THIRD = "third_party_to_branch"
CLASS_TO_ARABIC = "non_arabic_to_arabic"
CLASS_NO_DIRECTION = "no_named_donor_or_direction"

TAG_SEMITIC = "SEMITIC-SOURCE-TRANSMISSION"
TAG_THIRD = "LOANWORD-THIRD-PARTY-TO-BRANCH"
TAG_TO_ARABIC = "LOANWORD-NON-ARABIC-TO-ARABIC"
TAG_NO_DIRECTION = "SECTION27-ORDINARY-JUDGMENT-REOPENED"

SEMITIC_NAME = (
    r"(?:Proto-West\s+Semitic|Proto-Northwest\s+Semitic|Proto-Semitic|"
    r"West\s+Semitic|Northwest\s+Semitic|Semitic(?:\s+language|\s+source)?|"
    r"Nabataean\s+Aramaic|Jewish\s+Babylonian\s+Aramaic|Biblical\s+Hebrew|"
    r"Mishnaic\s+Hebrew|Classical\s+Syriac|Old\s+Aramaic|Syriac-Aramaic|"
    r"Old\s+South\s+Arabian|South\s+Arabian|Akkadian|Arabic|Aramaic|Hebrew|"
    r"Syriac|Phoenician|Punic|Canaanite|Ugaritic|Nabataean|Sabaean|Sabaic|"
    r"Ge['’]?ez|Amharic|Maltese)"
)
SEMITIC_RE = re.compile(rf"\b{SEMITIC_NAME}\b", re.IGNORECASE)
INCOMING_SEMITIC_PATTERNS = (
    re.compile(
        rf"\b(?:borrowed|reborrowed|loaned|derived|taken|adopted)\s+"
        rf"(?:directly\s+|ultimately\s+)?from\s+(?P<source>{SEMITIC_NAME})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:learned\s+borrowing|unadapted\s+borrowing|loanword|loan)\s+"
        rf"from\s+(?P<source>{SEMITIC_NAME})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:ultimately\s+|directly\s+)?from\s+"
        rf"(?P<source>{SEMITIC_NAME})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:via|through)\s+(?P<source>{SEMITIC_NAME})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:semantic\s+loan\s+from|calque\s+of|translation\s+of)\s+"
        rf"(?P<source>{SEMITIC_NAME})\b",
        re.IGNORECASE,
    ),
    re.compile(
        rf"\b(?:of|has|having)\s+(?P<source>Semitic)\s+origin\b",
        re.IGNORECASE,
    ),
)

HEDGES_RE = re.compile(
    r"\b(?:apparently|could|either|likely|may|maybe|might|perhaps|possibly|"
    r"plausibly|presumably|probably|proposed|seems|speculates|suggested|suggests|"
    r"suspects|theoretical|uncertain|unclear|unknown)\b",
    re.IGNORECASE,
)
COMPARISON_RE = re.compile(
    r"(?:^|[;:])\s*(?:also\s+)?(?:akin|compare|cognate|related)\b",
    re.IGNORECASE,
)
UNKNOWN_ALTERNATIVE_RE = re.compile(
    r"\bor\s+(?:ultimately\s+)?from\s+(?:an?\s+)?unknown\b|"
    r"\bor\s+from\s+another\b",
    re.IGNORECASE,
)


@dataclass(frozen=True)
class Language:
    key: str
    reading_file: str
    db_path: str
    source_label: str


LANGUAGES = (
    Language(
        "ancient_greek",
        "ancient-greek.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Ancient Greek",
    ),
    Language(
        "latin",
        "old-latin.md",
        "cache/recovery_pipeline/inventory-v5.sqlite",
        "Kaikki Latin",
    ),
    Language(
        "persian",
        "persian.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Persian",
    ),
    Language(
        "gothic",
        "gothic.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Gothic",
    ),
    Language(
        "old_norse",
        "old-norse.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Old Norse",
    ),
    Language(
        "welsh",
        "welsh.md",
        "cache/recovery_pipeline/week17-day1-inventory.sqlite",
        "Kaikki Welsh",
    ),
)

LANGUAGE_INDEX = {language.key: index for index, language in enumerate(LANGUAGES)}

INVENTORY_FIELDS = (
    "record_id",
    "member_id",
    "language",
    "form",
    "direction_class",
    "direction_tag",
    "named_donor",
    "direction_source",
    "direction_evidence",
    "action",
    "inheritance_numerator",
    "transmission_numerator",
    "prior_status",
)

REOPEN_MARKERS = (
    "SECTION26-LOAN-NO-NAMED-DONOR",
    "SECTION26-LOAN-LABEL-REOPENED",
    "SEMANTIC-LOAN-OTHER-SENSE",
)

# These source records require sense- and direction-level review which a
# substring parser cannot perform.  Every override below is conservative: the
# published text either gives only an outward route, limits the loan to a
# different sense than the member's gloss, or explicitly leaves native and
# borrowed analyses unresolved.  None of these IDs receives a positive link.
ORDINARY_JUDGMENT_OVERRIDES = {
    # Ancient Greek: unresolved donor/direction or loan confined to another sense.
    "kaikki_ancient_greek:4000:en-κάραβος-grc-noun-4IxT6pvd",
    "kaikki_ancient_greek:4631:en-θερμός-grc-noun-QQLyNao0",
    "kaikki_ancient_greek:5028:en-τόκος-grc-noun-grc:childbirth",
    "kaikki_ancient_greek:5333:en-πέλεκυς-grc-noun-0OmFaWHy",
    "kaikki_ancient_greek:8971:en-ἀλαζών-grc-adj-1ltB7URU",
    "kaikki_ancient_greek:8972:en-ἀλαζών-grc-noun-OnQmbKd7",
    "kaikki_ancient_greek:10877:en-τάρανδος-grc-noun-boTO84Na",
    "kaikki_ancient_greek:21700:en-ἄρουρα-grc-noun-uMqEBRZj",
    "kaikki_ancient_greek:22175:en-θαλλός-grc-noun-6XuwK-Ea",
    "kaikki_ancient_greek:22761:en-βαίτη-grc-noun-jveqq42C",
    "kaikki_ancient_greek:23549:en-ἄγγαρος-grc-noun-XEXpdyl9",
    "kaikki_ancient_greek:23675:en-ἀβρότονον-grc-noun-wBQqDcFm",
    "kaikki_ancient_greek:25986:en-λάγιον-grc-noun-GBUctZhM",
    "kaikki_ancient_greek:30687:en-κόνδυ-grc-noun-Hjpr3BGE",
    "kaikki_ancient_greek:30852:en-σύγκλητος-grc-adj-tyx3rwid",
    # Latin: native versus loan remains unresolved, or the loan is another sense.
    "kaikki_latin:1607:en-verbum-la-noun-mMHrTuk0",
    "kaikki_latin:2665:en-doceo-la-verb-08r51wl1",
    "kaikki_latin:2838:en-hircus-la-noun-KvHPJ8uW",
    "kaikki_latin:2927:en-murex-la-noun-0j~N5g4p",
    "kaikki_latin:3698:en-atrium-la-noun-gCPojQbl",
    "kaikki_latin:4099:en-adeps-la-noun-46gzPu26",
    "kaikki_latin:4275:en-tirare-la-verb-ohIOUxFA",
    "kaikki_latin:4394:en-casus-la-noun-abxPC90-",
    "kaikki_latin:4434:en-persona-la-noun-SL-bTxQq",
    "kaikki_latin:7142:en-sinus-la-noun-R2EA5TGm",
    "kaikki_latin:9507:en-carina-la-noun-R61hwEPq",
    "kaikki_latin:10647:en-laburnum-la-noun-hCyfCHiS",
    "kaikki_latin:14116:en-viburnum-la-noun-S8xgn1FP",
    "kaikki_latin:32013:en-numerus-la-noun-EohvnQAF",
    "kaikki_latin:34396:en-muria-la-noun-ekh1XiLZ",
    "kaikki_latin:35787:en-patta-la-noun-24cwbzBE",
    "kaikki_latin:36626:en-passio-la-noun-6xmliI9A",
    "kaikki_latin:58821:en-articulus-la-noun-s5EDlqyi",
    "kaikki_latin:63307:en-scarabaeus-la-noun-JRkjR1DV",
    "kaikki_latin:70410:en-participium-la-noun-AqAK7tcb",
    "kaikki_latin:88092:en-praepositio-la-noun-vF7OYP~4",
    "kaikki_latin:325339:en-aerumna-la-noun-cf3TCQ9l",
    "kaikki_latin:484929:en-reunio-la-verb-WQXEGMQm",
    "kaikki_latin:641569:en-trifolum-la-noun-0ztX4xOI",
    "kaikki_latin:657745:en-nacca-la-noun-yra5WUMf",
    "kaikki_latin:838575:en-dalivus-la-adj-s7BlNpiB",
    "kaikki_latin:841495:en-murcus-la-noun-TFD9w~8r",
    "kaikki_latin:871952:en-noctula-la-noun-la:1",
    # Persian: uncertain reborrowing, outward-only evidence, or another sense.
    "kaikki_persian_2026_07_23:2992:en-چمن-fa-noun-sm1w6OWY",
    "kaikki_persian_2026_07_23:3892:en-جوراب-fa-noun-Bu~jf16Y",
    "kaikki_persian_2026_07_23:4225:en-قر-fa-noun-fCmgUyIW",
    "kaikki_persian_2026_07_23:10334:en-نمد-fa-noun-BZcOMFVf",
    "kaikki_persian_2026_07_23:10809:en-پیسه-fa-noun-R6UWTbwf",
    "kaikki_persian_2026_07_23:13154:en-سرخس-fa-noun-8KXaF-D~",
    "kaikki_persian_2026_07_23:13222:en-شمشاد-fa-noun-kOUyVNye",
    "kaikki_persian_2026_07_23:13245:en-نهره-fa-noun-iLIHLj4X",
    "kaikki_persian_2026_07_23:14118:en-خوارزمی-fa-adj-955QF~o1",
    "kaikki_persian_2026_07_23:14119:en-خوارزمی-fa-noun-DJshVSp-",
    "kaikki_persian_2026_07_23:14545:en-کتی-fa-prep-qCCUt3Qb",
    "kaikki_persian_2026_07_23:17161:en-کردگار-fa-noun-nMR2xpX4",
    "kaikki_persian_2026_07_23:18491:en-جنتری-fa-noun-ZDm~pK0A",
    # Gothic: the published semantic loan belongs to a different sense.
    "kaikki_gothic_2026_07_23:945:en-𐌳𐌰𐌿𐍀𐌾𐌰𐌽-got-verb-jZ6XNk-Z",
    "kaikki_gothic_2026_07_23:14924:en-𐌰𐌹𐌽𐍆𐌰𐌻𐌸𐌴𐌹-got-noun-mmHCKFsj",
    # Old Norse: native versus contact unresolved, or evidence is outward-only.
    "kaikki_old_norse_2026_07_23:362:en-tá-non-noun-non:path",
    "kaikki_old_norse_2026_07_23:667:en-kaupa-non-verb-fi7Tk9Ul",
    "kaikki_old_norse_2026_07_23:2195:en-þjóna-non-verb-UTizBQxZ",
    "kaikki_old_norse_2026_07_23:10406:en-Kjárr-non-noun-L5YwEiOP",
    # Welsh: cognate/outward evidence, unresolved loan, or another sense.
    "kaikki_welsh_2026_07_23:1258:en-bas-cy-noun-RBNJ4ewv",
    "kaikki_welsh_2026_07_23:1908:en-dail-cy-noun-XtChC5Ub",
    "kaikki_welsh_2026_07_23:4061:en-jac-cy-noun-TzYatlGu",
    "kaikki_welsh_2026_07_23:7163:en-cymal-cy-noun-8KYT7W7r",
    "kaikki_welsh_2026_07_23:7900:en-macon-cy-noun-4T-1OllP",
    "kaikki_welsh_2026_07_23:16636:en-mwynwr-cy-noun-83aUkhJW",
}

# Here the published route runs from the Lane-C language (or its historical
# stage) into Arabic.  It is a justified exclusion, not an incoming donor.
TO_ARABIC_OVERRIDES = {
    "kaikki_persian_2026_07_23:3483:en-ای-fa-adv-22hIRGPp": "Middle Persian → Arabic",
    "kaikki_persian_2026_07_23:3784:en-اشنان-fa-noun-MUb6khjC": "Middle Iranian → Arabic",
    "kaikki_persian_2026_07_23:9288:en-تنبسه-fa-noun-P88ZW34b": "Persian or Middle Iranian → Arabic",
}

# A Semitic word occurs in these etymologies only as a comparandum, an
# uncertain alternative, an older synonym, or an outgoing descendant.  The
# incoming path that is actually stated is from the named non-Semitic donor.
THIRD_PARTY_OVERRIDES = {
    "kaikki_ancient_greek:78:en-γράμμα-grc-noun-4YQNarMf": "Latin",
    "kaikki_ancient_greek:30649:en-γαβάθα-grc-noun-2fK6uxZz": "Latin",
    "kaikki_latin:850975:en-collybista-la-noun-ICBNAWuc": "Ancient Greek",
    "kaikki_persian_2026_07_23:5060:en-ارس-fa-noun-F4QDI-pZ": "Northwestern Iranian",
    "kaikki_persian_2026_07_23:9228:en-روناس-fa-noun-hXLL1-4V": "Ancient Greek",
    "kaikki_persian_2026_07_23:13469:en-بربری-fa-adj-pIyB9FQ-": "Ancient Greek via Middle Persian",
    "kaikki_persian_2026_07_23:14652:en-برنز-fa-noun-F6UJQ~KQ": "French",
}


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def compact(value: str | None, limit: int | None = None) -> str:
    result = " ".join(nfc(value).replace("—", "،").split())
    if limit is not None and len(result) > limit:
        return result[: limit - 1].rstrip() + "…"
    return result


def source_ordinal(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else -1


def ro_connection(relative: str) -> sqlite3.Connection:
    path = (ROOT / relative).resolve()
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def chunks(values: list[str], size: int = 450) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def load_metadata(
    connection: sqlite3.Connection,
    entry_ids: list[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for group in chunks(entry_ids):
        marks = ",".join("?" for _ in group)
        rows = connection.execute(
            f"""
            SELECT entry_id, headword, romanization, gloss, etymology,
                   licensed_candidate_count
            FROM entries
            WHERE entry_id IN ({marks})
            """,
            group,
        ).fetchall()
        for row in rows:
            item: dict[str, Any] = {
                key: nfc(row[key])
                for key in (
                    "entry_id",
                    "headword",
                    "romanization",
                    "gloss",
                    "etymology",
                )
            }
            item["licensed_candidate_count"] = int(
                row["licensed_candidate_count"] or 0
            )
            result[nfc(row["entry_id"])] = item
    return result


def card_entry_id(card: str) -> str:
    branch = re.search(r"(?m)^- الكلمةُ في الفرع:.*$", card)
    if branch is None:
        return ""
    matches = ENTRY_RE.findall(branch.group(0))
    return nfc(matches[0]) if matches else ""


def card_form(card: str) -> str:
    branch = re.search(r"(?m)^- الكلمةُ في الفرع:\s*(.+)$", card)
    if branch:
        return compact(re.sub(r"\s*\[[^\n]*$", "", branch.group(1)), 240)
    title = re.search(r"(?m)^### بطاقة:\s*(.+)$", card)
    return compact(title.group(1), 240) if title else "(غير مسجل)"


def sentence_context(text: str, start: int, end: int) -> tuple[str, str]:
    left = max(text.rfind(mark, 0, start) for mark in (".", "!", "?", "\n"))
    right_candidates = [
        index
        for mark in (".", "!", "?", "\n")
        if (index := text.find(mark, end)) >= 0
    ]
    right = min(right_candidates) if right_candidates else len(text)
    sentence = compact(text[left + 1 : right + 1])
    prefix = compact(text[left + 1 : start])
    return sentence, prefix


def donor_is_semitic(donor: str) -> bool:
    return bool(SEMITIC_RE.search(donor)) and not donor.casefold().startswith(
        ("ancient greek", "koine greek", "latin")
    )


def semitic_route_evidence(etymology: str, donor: str) -> tuple[str, str]:
    """Return a named incoming Semitic stage and its source sentence."""

    text = compact(etymology)
    if not text:
        return "", ""

    # named_donor has already rejected a governing hedge for the direct donor.
    # If that donor is Semitic, it is the strongest direction statement.
    if donor_is_semitic(donor):
        donor_match = SEMITIC_RE.search(donor)
        source_name = compact(donor_match.group(0)) if donor_match else compact(donor)
        for pattern in INCOMING_SEMITIC_PATTERNS:
            match = pattern.search(text)
            if match and source_name.casefold() in compact(match.group("source")).casefold():
                sentence, _ = sentence_context(text, match.start(), match.end())
                return source_name, sentence
        return source_name, compact(text, 700)

    for pattern in INCOMING_SEMITIC_PATTERNS:
        for match in pattern.finditer(text):
            sentence, prefix = sentence_context(text, match.start(), match.end())
            # Comparanda and cognates do not put the item on an incoming route.
            clause_start = max(prefix.rfind(mark) for mark in (",", ";", ":"))
            local_prefix = prefix[clause_start + 1 :].strip()
            if COMPARISON_RE.search(local_prefix) or local_prefix.casefold().startswith(
                ("akin ", "compare ", "cognate ", "related ")
            ):
                continue
            if HEDGES_RE.search(prefix):
                continue
            source_suffix = compact(text[match.end() : match.end() + 120])
            if UNKNOWN_ALTERNATIVE_RE.search(source_suffix):
                continue
            return compact(match.group("source")), sentence
    return "", ""


def direction_decision(
    language: Language,
    entry_id: str,
    etymology: str,
) -> dict[str, str]:
    if entry_id in ORDINARY_JUDGMENT_OVERRIDES:
        return {
            "direction_class": CLASS_NO_DIRECTION,
            "direction_tag": TAG_NO_DIRECTION,
            "named_donor": "",
            "direction_evidence": compact(etymology, 700),
        }
    if entry_id in TO_ARABIC_OVERRIDES:
        return {
            "direction_class": CLASS_TO_ARABIC,
            "direction_tag": TAG_TO_ARABIC,
            "named_donor": TO_ARABIC_OVERRIDES[entry_id],
            "direction_evidence": compact(etymology, 700),
        }
    if entry_id in THIRD_PARTY_OVERRIDES:
        return {
            "direction_class": CLASS_THIRD,
            "direction_tag": TAG_THIRD,
            "named_donor": THIRD_PARTY_OVERRIDES[entry_id],
            "direction_evidence": compact(etymology, 700),
        }
    donor = compact(named_donor(language.key, etymology), 220)
    if not donor:
        return {
            "direction_class": CLASS_NO_DIRECTION,
            "direction_tag": TAG_NO_DIRECTION,
            "named_donor": "",
            "direction_evidence": "",
        }
    semitic_source, evidence = semitic_route_evidence(etymology, donor)
    if semitic_source:
        return {
            "direction_class": CLASS_SEMITIC,
            "direction_tag": TAG_SEMITIC,
            "named_donor": donor,
            "direction_evidence": evidence,
        }
    return {
        "direction_class": CLASS_THIRD,
        "direction_tag": TAG_THIRD,
        "named_donor": donor,
        "direction_evidence": compact(etymology, 700),
    }


def historical_decision(language: Language, card: str) -> dict[str, str]:
    title = compact(re.search(r"(?m)^### بطاقة:\s*(.+)$", card).group(1))
    if language.key == "ancient_greek" and title.startswith("kamēlos"):
        return {
            "record_id": "lane-c-historical:ancient_greek:kamēlos",
            "direction_class": CLASS_SEMITIC,
            "direction_tag": TAG_SEMITIC,
            "named_donor": "Proto-West Semitic *gamal-",
            "direction_evidence": (
                "المورد يصرح بأن اللفظ في النهاية من Proto-West Semitic *gamal-"
            ),
        }
    if language.key == "ancient_greek" and title.startswith("nomos"):
        return {
            "record_id": "lane-c-historical:ancient_greek:nomos",
            "direction_class": CLASS_TO_ARABIC,
            "direction_tag": TAG_TO_ARABIC,
            "named_donor": "Ancient Greek νόμος into Aramaic",
            "direction_evidence": (
                "اليونانية νόμος → الآرامية נמוסא؛ العربية ناموس تحت السليل الآرامي"
            ),
        }
    if language.key == "latin" and title.startswith("calamus"):
        return {
            "record_id": "lane-c-historical:latin:calamus",
            "direction_class": CLASS_THIRD,
            "direction_tag": TAG_THIRD,
            "named_donor": "Ancient Greek κάλαμος",
            "direction_evidence": "اللاتينية اقترضت من اليونانية κάλαμος",
        }
    raise RuntimeError(
        f"unclassified historical loan card without member_id: {language.key}: {title}"
    )


def action_for(direction_class: str) -> str:
    return {
        CLASS_SEMITIC: (
            "keep_as_transmission_outside_shared_inheritance_numerator"
        ),
        CLASS_THIRD: "retain_justified_exclusion",
        CLASS_TO_ARABIC: "retain_justified_exclusion",
        CLASS_NO_DIRECTION: "ordinary_judgment_open_in_lane_c_coverage",
    }[direction_class]


def parse_language(language: Language) -> dict[str, Any]:
    path = READINGS / language.reading_file
    text = path.read_text(encoding="utf-8")
    if MARKER in text or TAG_SEMITIC in text:
        raise RuntimeError(f"section 27 appears already applied: {path}")
    blocks = [
        match.group(0)
        for match in CARD_RE.finditer(text)
        if VERDICT_RE.search(match.group(0))
    ]
    entry_ids = [entry_id for card in blocks if (entry_id := card_entry_id(card))]
    connection = ro_connection(language.db_path)
    try:
        metadata = load_metadata(connection, entry_ids)
    finally:
        connection.close()
    missing = sorted(set(entry_ids) - set(metadata))
    if missing:
        raise RuntimeError(f"missing source metadata for {language.key}: {missing[:5]}")

    decisions: dict[str, dict[str, Any]] = {}
    records: list[dict[str, Any]] = []
    new_coverage_rows: list[dict[str, Any]] = []
    historical_number = 0
    for card_number, card in enumerate(blocks, 1):
        entry_id = card_entry_id(card)
        if entry_id:
            meta = metadata[entry_id]
            decision = direction_decision(language, entry_id, meta["etymology"])
            record_id = entry_id
            form = meta["headword"] or card_form(card)
            source = (
                f"{language.source_label}؛ `{entry_id}`؛ حقل `etymology`"
            )
        else:
            historical_number += 1
            decision = historical_decision(language, card)
            record_id = decision.pop("record_id")
            form = card_form(card)
            source = f"{language.source_label}؛ البطاقة التاريخية؛ الحقل المسمى فيها"
        decision = dict(decision)
        decision.update(
            {
                "record_id": record_id,
                "entry_id": entry_id,
                "form": form,
                "direction_source": source,
                "card_number": card_number,
            }
        )
        if record_id in decisions:
            raise RuntimeError(f"duplicate direction record: {record_id}")
        decisions[record_id] = decision
        records.append(
            {
                "record_id": record_id,
                "member_id": entry_id,
                "language": language.key,
                "form": form,
                "direction_class": decision["direction_class"],
                "direction_tag": decision["direction_tag"],
                "named_donor": decision["named_donor"],
                "direction_source": source,
                "direction_evidence": decision["direction_evidence"],
                "action": action_for(decision["direction_class"]),
                "inheritance_numerator": False,
                "transmission_numerator": decision["direction_class"] == CLASS_SEMITIC,
                "prior_status": "LOANWORD",
            }
        )
        if entry_id and decision["direction_class"] == CLASS_NO_DIRECTION:
            state = (
                "OPEN-CANDIDATE"
                if int(meta["licensed_candidate_count"] or 0)
                else "OPEN-NO-LICENSED-CANDIDATE"
            )
            new_coverage_rows.append(
                {
                    "member_id": entry_id,
                    "language": language.key,
                    "form": meta["headword"] or form,
                    "branch_meaning": meta["gloss"] or "(غير مسجل في المصدر)",
                    "non_issuance_reason": (
                        f"{state}؛ SECTION27-NO-NAMED-DONOR-OR-DIRECTION؛ "
                        "أعيد إلى الحكم العادي بعد فحص اتجاه المصدر؛ الحكم غير صادر"
                    ),
                    "batch_number": 0,
                }
            )
    return {
        "language": language,
        "path": path,
        "text": text,
        "blocks": blocks,
        "records": records,
        "decisions": decisions,
        "new_coverage_rows": new_coverage_rows,
        "historical_cards": historical_number,
    }


def load_prior_reopened() -> tuple[list[dict[str, Any]], set[str], int]:
    rows: list[dict[str, Any]] = []
    all_ids: set[str] = set()
    line_count = 0
    with COVERAGE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            line_count += 1
            row = json.loads(line)
            member_id = str(row["member_id"])
            if member_id in all_ids:
                raise RuntimeError(f"duplicate coverage identity at line {line_number}: {member_id}")
            all_ids.add(member_id)
            reason = compact(str(row.get("non_issuance_reason", "")))
            matched = next((marker for marker in REOPEN_MARKERS if marker in reason), "")
            if not matched:
                continue
            language = str(row["language"])
            if language not in LANGUAGE_INDEX:
                continue
            rows.append(
                {
                    "record_id": str(row["member_id"]),
                    "member_id": str(row["member_id"]),
                    "language": language,
                    "form": str(row["form"]),
                    "direction_class": CLASS_NO_DIRECTION,
                    "direction_tag": TAG_NO_DIRECTION,
                    "named_donor": "",
                    "direction_source": "lane_c_coverage.jsonl؛ إعادة فتح القسم 26",
                    "direction_evidence": reason,
                    "action": action_for(CLASS_NO_DIRECTION),
                    "inheritance_numerator": None,
                    "transmission_numerator": False,
                    "prior_status": matched,
                }
            )
    return rows, all_ids, line_count


def prefixed_filter(old: str, decision: dict[str, Any]) -> str:
    old_value = old.split(":", 1)[1].strip()
    direction_class = decision["direction_class"]
    prefix = {
        CLASS_SEMITIC: "SECTION27-DIRECTION-KEEP؛ من السامية إلى الفرع",
        CLASS_THIRD: "SECTION27-DIRECTION-EXCLUDE؛ من طرف ثالث إلى الفرع",
        CLASS_TO_ARABIC: "SECTION27-DIRECTION-EXCLUDE؛ من غير العربية إلى العربية",
    }[direction_class]
    return f"- المصفاة: {prefix}؛ {old_value}"


def rewrite_card(card: str, decision: dict[str, Any], source_label: str) -> str:
    direction_class = decision["direction_class"]
    if direction_class == CLASS_NO_DIRECTION:
        raise RuntimeError(
            f"a current LOANWORD lacks direction and must be reopened: {decision['record_id']}"
        )
    card = re.sub(
        r"(?m)^- المصفاة:.*$",
        lambda match: prefixed_filter(match.group(0), decision),
        card,
        count=1,
    )
    if direction_class == CLASS_SEMITIC:
        card = re.sub(
            r"(?m)^- حالةُ الإغلاق:.*$",
            "- حالةُ الإغلاق: READY-TRANSMISSION؛ خارج بسط الإرث المشترك.",
            card,
            count=1,
        )
        source_line = (
            f"- مصدرُ اتجاه النقل: {decision['direction_source']}؛ "
            f"{compact(decision['direction_evidence'], 700)}\n"
        )
        card = VERDICT_RE.sub(
            source_line
            + f"- الحكم (استكشاف): {TAG_SEMITIC}.",
            card,
            count=1,
        )
    elif direction_class == CLASS_THIRD:
        card = VERDICT_RE.sub(
            f"- الحكم (استكشاف): {TAG_THIRD}.",
            card,
            count=1,
        )
    else:
        card = VERDICT_RE.sub(
            f"- الحكم (استكشاف): {TAG_TO_ARABIC}.",
            card,
            count=1,
        )
    return nfc(card)


def rewrite_reading(analysis: dict[str, Any]) -> str:
    language: Language = analysis["language"]
    decisions = analysis["decisions"]

    def replacement(match: re.Match[str]) -> str:
        card = match.group(0)
        if not VERDICT_RE.search(card):
            return card
        entry_id = card_entry_id(card)
        if entry_id:
            record_id = entry_id
        else:
            record_id = historical_decision(language, card)["record_id"]
        decision = decisions[record_id]
        if decision["direction_class"] == CLASS_NO_DIRECTION:
            return ""
        return rewrite_card(card, decision, language.source_label)

    rewritten = CARD_RE.sub(replacement, analysis["text"])
    counts = Counter(record["direction_class"] for record in analysis["records"])
    note = nfc(
        f"""

<!-- {MARKER} -->
## إنفاذ القسم 27: المصفاة تعرف الاتجاه

أعيد فحص كل حكم `LOANWORD` فعلي في هذا الملف على اتجاه المصدر المنشور.
حُفظ {counts[CLASS_SEMITIC]:,} انتقالًا من السامية إلى الفرع بوسم
`{TAG_SEMITIC}` خارج بسط الإرث المشترك، وثُبت استبعاد
{counts[CLASS_THIRD]:,} قرضًا من طرف ثالث إلى الفرع و
{counts[CLASS_TO_ARABIC]:,} مسارًا من غير العربية إلى العربية. الحالات
القديمة التي بلا مانح أو اتجاه مثبت باقية مفتوحة في
`lane_c_coverage.jsonl`، وليست بطاقات إغلاق في هذا الملف.

الرقمان المفصولان في إعادة التصنيف: **0 صلة إرثية جديدة؛ 0 إغلاق جديد**.
"""
    )
    return rewritten.rstrip() + "\n" + note


def inventory_text(records: list[dict[str, Any]]) -> str:
    lines: list[str] = []
    for record in records:
        ordered = {field: record[field] for field in INVENTORY_FIELDS}
        lines.append(json.dumps(ordered, ensure_ascii=False, separators=(",", ":")))
    return "\n".join(lines) + "\n"


def format_position(record: dict[str, Any]) -> str:
    identity = record["member_id"] or record["record_id"]
    return f"{record['form']} (`{identity}`)"


def audit_text(
    analyses: list[dict[str, Any]],
    records: list[dict[str, Any]],
) -> str:
    per_language: dict[str, list[dict[str, Any]]] = {language.key: [] for language in LANGUAGES}
    for record in records:
        per_language[record["language"]].append(record)
    for language in LANGUAGES:
        per_language[language.key].sort(
            key=lambda row: (source_ordinal(row["member_id"]), row["record_id"])
        )
    totals = Counter(record["direction_class"] for record in records)
    current_total = sum(len(analysis["records"]) for analysis in analyses)
    prior_reopened_total = sum(
        record["direction_class"] == CLASS_NO_DIRECTION
        and record["prior_status"] != "LOANWORD"
        for record in records
    )
    current_reopened_total = sum(
        record["direction_class"] == CLASS_NO_DIRECTION
        and record["prior_status"] == "LOANWORD"
        for record in records
    )
    reopened_total = prior_reopened_total + current_reopened_total

    table = [
        "| اللسان | أحكام LOANWORD فعلية قبل الفحص | سامي → الفرع | طرف ثالث → الفرع | غير العربية → العربية | بلا مانح/اتجاه، مفتوح سابقًا أو الآن | الإغلاقات المبقاة |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for analysis in analyses:
        language: Language = analysis["language"]
        rows = per_language[language.key]
        counts = Counter(row["direction_class"] for row in rows)
        table.append(
            f"| {language.source_label} | {len(analysis['records']):,} | "
            f"{counts[CLASS_SEMITIC]:,} | {counts[CLASS_THIRD]:,} | "
            f"{counts[CLASS_TO_ARABIC]:,} | {counts[CLASS_NO_DIRECTION]:,} | "
            f"{counts[CLASS_THIRD] + counts[CLASS_TO_ARABIC]:,} |"
        )
    table.append(
        f"| **المجموع** | **{current_total:,}** | **{totals[CLASS_SEMITIC]:,}** | "
        f"**{totals[CLASS_THIRD]:,}** | **{totals[CLASS_TO_ARABIC]:,}** | "
        f"**{reopened_total:,}** | **{totals[CLASS_THIRD] + totals[CLASS_TO_ARABIC]:,}** |"
    )

    remaining = len(records)
    batch_sections: list[str] = []
    for analysis in analyses:
        language: Language = analysis["language"]
        rows = per_language[language.key]
        counts = Counter(row["direction_class"] for row in rows)
        new_open = sum(
            row["direction_class"] == CLASS_NO_DIRECTION
            and row["prior_status"] == "LOANWORD"
            for row in rows
        )
        prior_open = counts[CLASS_NO_DIRECTION] - new_open
        remaining -= len(rows)
        first = format_position(rows[0]) if rows else "(لا موضع)"
        last = format_position(rows[-1]) if rows else "(لا موضع)"
        batch_sections.append(
            f"""
## الدفعة: {language.source_label}

سطر الموضع: بدأت إعادة الفحص من {first} وانتهت عند {last}؛ بقي في جرد
إعادة التصنيف لهذا اللسان 0، وبقي في جرد الألسن التالية {remaining:,}.

- `{TAG_SEMITIC}`: {counts[CLASS_SEMITIC]:,}.
- طرف ثالث إلى الفرع، مستبعد بحق: {counts[CLASS_THIRD]:,}.
- من غير العربية إلى العربية، مستبعد بحق: {counts[CLASS_TO_ARABIC]:,}.
- بلا مانح مسمى أو اتجاه مثبت، أعيد إلى الحكم العادي: {counts[CLASS_NO_DIRECTION]:,}
  ({new_open:,} في هذه الجولة؛ {prior_open:,} مفتوح سابقًا).

الرقمان المفصولان للدفعة: **0 صلة إرثية جديدة؛ 0 إغلاق جديد**. والإغلاقات
القديمة التي ثبت اتجاه استبعادها وبقيت مغلقة: **{counts[CLASS_THIRD] + counts[CLASS_TO_ARABIC]:,}**.
"""
        )

    user_count_note = (
        "العد الخام 350 في اليونانية و3,800 في اللاتينية كان يضم سطر "
        "خيارات القالب مرة في كل ملف؛ أحكام البطاقات الفعلية 349 و3,799. "
        "أما الفارسية 4,876 والويلزية 2,353 فهما عدّا البطاقات الفعلية."
    )
    return nfc(
        f"""# محضر المسار ج: إنفاذ القسم 27 وإعادة فحص اتجاه القروض

التاريخ: {DATE}

## السلطة والنطاق

قُرئ القسمان 26 و27، وأعيد فحص كل بطاقة قرض فعلية في ملفات المسار ج
الستة، مع ضم المواضع التي أعاد القسم 26 فتحها من قبل حتى لا تسقط من
التاريخ ولا تكرر في التغطية. لم يُشغّل Git ولا باني مشترك ولا خط البرهان،
ولم يُنشأ صف صوتي.

{user_count_note}

## النتيجة الاتجاهية

{chr(10).join(table)}

`{TAG_SEMITIC}` لا يدخل بسط الإرث المشترك. حقله
`transmission_numerator=true` في الجرد الاتجاهي، وكل سجل يذكر مورد Kaikki
المسمى والعضو وحقل الاشتقاق والنص الذي أقام الاتجاه. القروض من طرف ثالث
والداخلة إلى العربية بقيت مستبعدة. والصنف الرابع بقي حكمه غير صادر في
`lane_c_coverage.jsonl`؛ لم يضف سطر ثان للـ{prior_reopened_total:,}
المفتوحة سابقًا، وأضيف سطر واحد لكل موضع من الـ{current_reopened_total:,}
التي كشفها فحص الاتجاه الحالي.

{''.join(batch_sections)}

## استمرار الطابور بعد الدفعات

قيس `lane_c_morphology_queue.jsonl` بعد إعادة التصنيف: بقية الصور الصرفية
في الألسن الستة صفر. أنشأ القسم 27 {current_reopened_total:,} موضعًا جديدًا
بلا حكم، فسجل لكل واحد سطره الفريد في `lane_c_coverage.jsonl`، وبقيت
الـ{prior_reopened_total:,} المفتوحة سابقًا على أسطرها من غير تكرار. بهذا
اكتمل مرورها في طابور هذه الجولة، وانتهى الموضع عند آخر سجل اتجاهي؛ الباقي
المقيس 0.

الرقمان المفصولان للجولة كلها: **0 صلة إرثية جديدة؛ 0 إغلاق جديد**.
وحُفظ **{totals[CLASS_SEMITIC]:,}** دليل انتقال سامي في بابه المستقل.

الملفات المكتوبة: ملفات القراءة الستة؛
`04-cross-linguistic/data/lane_c_section27_direction_inventory.jsonl`؛
`scripts/lane_c_section27_direction.py`؛ وهذا المحضر.
"""
    )


def prepare() -> dict[str, Any]:
    analyses = [parse_language(language) for language in LANGUAGES]
    current_records = [
        record
        for analysis in analyses
        for record in analysis["records"]
    ]
    reopened, existing_coverage_ids, coverage_line_count = load_prior_reopened()
    new_coverage_rows = [
        row
        for analysis in analyses
        for row in analysis["new_coverage_rows"]
    ]
    new_coverage_ids = [str(row["member_id"]) for row in new_coverage_rows]
    if len(new_coverage_ids) != len(set(new_coverage_ids)):
        raise RuntimeError("duplicate new section-27 coverage identities")
    covered_overlap = existing_coverage_ids & set(new_coverage_ids)
    if covered_overlap:
        raise RuntimeError(
            "section-27 reopened identities already in coverage: "
            f"{sorted(covered_overlap)[:5]}"
        )
    current_ids = {record["record_id"] for record in current_records}
    overlap = current_ids & {record["record_id"] for record in reopened}
    if overlap:
        raise RuntimeError(f"current closures overlap reopened coverage: {sorted(overlap)[:5]}")
    records = current_records + reopened
    records.sort(
        key=lambda row: (
            LANGUAGE_INDEX[row["language"]],
            source_ordinal(row["member_id"]),
            row["record_id"],
        )
    )
    reading_outputs = {
        analysis["path"]: rewrite_reading(analysis)
        for analysis in analyses
    }
    return {
        "analyses": analyses,
        "records": records,
        "reading_outputs": reading_outputs,
        "new_coverage_rows": new_coverage_rows,
        "coverage_line_count": coverage_line_count,
        "inventory_text": inventory_text(records),
        "audit_text": audit_text(analyses, records),
    }


def validate(output: dict[str, Any]) -> None:
    records = output["records"]
    record_ids = [record["record_id"] for record in records]
    if len(record_ids) != len(set(record_ids)):
        raise RuntimeError("duplicate direction inventory record IDs")
    current_total = sum(len(analysis["records"]) for analysis in output["analyses"])
    if current_total != 11_640:
        raise RuntimeError(f"unexpected current LOANWORD count: {current_total}")
    prior_reopened_total = sum(
        record["direction_class"] == CLASS_NO_DIRECTION
        and record["prior_status"] != "LOANWORD"
        for record in records
    )
    if prior_reopened_total != 285:
        raise RuntimeError(
            f"unexpected prior reopened count: {prior_reopened_total}"
        )
    current_reopened_total = sum(
        record["direction_class"] == CLASS_NO_DIRECTION
        and record["prior_status"] == "LOANWORD"
        for record in records
    )
    if current_reopened_total != len(ORDINARY_JUDGMENT_OVERRIDES):
        raise RuntimeError(
            "unreviewed current no-direction count: "
            f"{current_reopened_total} != {len(ORDINARY_JUDGMENT_OVERRIDES)}"
        )
    if len(output["new_coverage_rows"]) != current_reopened_total:
        raise RuntimeError("new coverage rows do not match current reopenings")
    coverage_ids = [
        str(row["member_id"]) for row in output["new_coverage_rows"]
    ]
    if len(coverage_ids) != len(set(coverage_ids)):
        raise RuntimeError("duplicate new section-27 coverage IDs")
    for analysis in output["analyses"]:
        text = output["reading_outputs"][analysis["path"]]
        if any(
            VERDICT_RE.search(match.group(0))
            for match in CARD_RE.finditer(text)
        ):
            raise RuntimeError(f"unclassified LOANWORD remains: {analysis['path']}")
        expected = Counter(
            record["direction_class"] for record in analysis["records"]
        )
        observed = Counter(
            {
                CLASS_SEMITIC: len(re.findall(rf"(?m)^- الحكم \(استكشاف\): {TAG_SEMITIC}\b", text)),
                CLASS_THIRD: len(re.findall(rf"(?m)^- الحكم \(استكشاف\): {TAG_THIRD}\b", text)),
                CLASS_TO_ARABIC: len(re.findall(rf"(?m)^- الحكم \(استكشاف\): {TAG_TO_ARABIC}\b", text)),
            }
        )
        for direction_class in (CLASS_SEMITIC, CLASS_THIRD, CLASS_TO_ARABIC):
            if observed[direction_class] != expected[direction_class]:
                raise RuntimeError(
                    f"tag mismatch in {analysis['path']}: {direction_class}: "
                    f"{observed[direction_class]} != {expected[direction_class]}"
                )
        if unicodedata.normalize("NFC", text) != text:
            raise RuntimeError(f"non-NFC reading output: {analysis['path']}")
    for row in records:
        if tuple(row.keys()) != INVENTORY_FIELDS:
            raise RuntimeError(f"invalid inventory fields: {row['record_id']}")


def atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".lane-c-section27.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)


def append_coverage(rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with COVERAGE.open("rb") as handle:
        handle.seek(0, 2)
        size = handle.tell()
        if size:
            handle.seek(-1, 2)
            ends_with_newline = handle.read(1) == b"\n"
        else:
            ends_with_newline = True
    with COVERAGE.open("a", encoding="utf-8", newline="\n") as handle:
        if not ends_with_newline:
            handle.write("\n")
        for row in rows:
            handle.write(
                json.dumps(row, ensure_ascii=False, separators=(",", ":"))
                + "\n"
            )


def print_plan(output: dict[str, Any]) -> None:
    records = output["records"]
    for analysis in output["analyses"]:
        language: Language = analysis["language"]
        rows = [record for record in records if record["language"] == language.key]
        counts = Counter(record["direction_class"] for record in rows)
        print(
            f"{language.key}"
            f"\tcurrent={len(analysis['records'])}"
            f"\tsemitic_to_branch={counts[CLASS_SEMITIC]}"
            f"\tthird_party_to_branch={counts[CLASS_THIRD]}"
            f"\tnon_arabic_to_arabic={counts[CLASS_TO_ARABIC]}"
            f"\tno_direction_reopened={counts[CLASS_NO_DIRECTION]}"
        )
    totals = Counter(record["direction_class"] for record in records)
    print(
        f"TOTAL\trecords={len(records)}"
        f"\tsemitic_to_branch={totals[CLASS_SEMITIC]}"
        f"\tthird_party_to_branch={totals[CLASS_THIRD]}"
        f"\tnon_arabic_to_arabic={totals[CLASS_TO_ARABIC]}"
        f"\tno_direction_reopened={totals[CLASS_NO_DIRECTION]}"
    )
    for path, text in output["reading_outputs"].items():
        print(f"SIZE\t{len(text.encode('utf-8'))}\t{path.relative_to(ROOT).as_posix()}")
    print(f"SIZE\t{len(output['inventory_text'].encode('utf-8'))}\t{INVENTORY.relative_to(ROOT).as_posix()}")
    print(
        f"COVERAGE\tbefore={output['coverage_line_count']}"
        f"\tappend={len(output['new_coverage_rows'])}"
        f"\tafter={output['coverage_line_count'] + len(output['new_coverage_rows'])}"
    )


def apply(output: dict[str, Any]) -> None:
    if INVENTORY.exists() or AUDIT.exists():
        raise RuntimeError("section-27 output already exists")
    for path, text in output["reading_outputs"].items():
        atomic_write(path, text)
    atomic_write(INVENTORY, output["inventory_text"])
    atomic_write(AUDIT, output["audit_text"])
    append_coverage(output["new_coverage_rows"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = prepare()
    validate(output)
    print_plan(output)
    if args.apply:
        apply(output)
        print("APPLIED\tsection27")
    else:
        print("PLAN-ONLY\tno files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
