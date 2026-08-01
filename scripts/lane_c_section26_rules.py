#!/usr/bin/env python3
"""Lane C's section-26 discovery rules.

This module is lane-C-owned.  It names a donor only when the source publishes
an unhedged contact route to an identifiable language.  A family label,
substrate label, possibility, or mere comparison is not a named donor.
"""

from __future__ import annotations

import re
import unicodedata


HEDGES = (
    "apparently",
    "could",
    "either",
    "likely",
    "may",
    "maybe",
    "might",
    "perhaps",
    "possibly",
    "presumably",
    "proposes",
    "probably",
    "proposed",
    "seems",
    "suggests",
    "suggested",
    "uncertain",
    "unclear",
)

GENERIC_DONORS = (
    "a celtic language",
    "a foreign",
    "a germanic language",
    "a language",
    "a non-",
    "a semitic",
    "a source",
    "a substrate",
    "a west germanic source",
    "an eastern language",
    "an indian language",
    "an unknown",
    "celtic",
    "germanic",
    "indo-european",
    "indo-iranian",
    "iranian",
    "its source",
    "one or more",
    "other language",
    "pre-greek",
    "semitic",
    "some ",
    "the same source",
    "turkic",
    "unknown",
    "whom",
)

# These are contact donors for the language being read, not its ordinary
# inherited parent stages.  The list is deliberately explicit: it licenses
# recognition of a published donor; it does not license a sound row or a link.
EXTERNAL_DONORS: dict[str, tuple[str, ...]] = {
    "ancient_greek": (
        "akkadian",
        "arabic",
        "aramaic",
        "biblical hebrew",
        "canaanite",
        "coptic",
        "egyptian",
        "gothic",
        "hebrew",
        "latin",
        "alanic",
        "old persian",
        "phoenician",
        "phrygian",
        "punic",
        "sanskrit",
        "sumerian",
    ),
    "latin": (
        "ancient greek",
        "arabic",
        "etruscan",
        "french",
        "gaulish",
        "hebrew",
        "oscan",
        "old french",
        "old polish",
        "paleo-hispanic",
        "persian",
        "phoenician",
        "punic",
        "sabine",
    ),
    "persian": (
        "ancient greek",
        "arabic",
        "aramaic",
        "azerbaijani",
        "bactrian",
        "chagatai",
        "english",
        "french",
        "hebrew",
        "hindi",
        "hindustani",
        "italian",
        "japanese",
        "khorezmian",
        "latin",
        "mongolian",
        "old turkic",
        "ottoman turkish",
        "parthian",
        "pashto",
        "polish",
        "portuguese",
        "russian",
        "sanskrit",
        "spanish",
        "turkish",
        "urdu",
    ),
    "gothic": (
        "ancient greek",
        "gaulish",
        "latin",
        "old high german",
        "old saxon",
        "proto-slavic",
        "vulgar latin",
    ),
    "old_norse": (
        "classical persian",
        "english",
        "french",
        "latin",
        "middle dutch",
        "middle english",
        "middle low german",
        "old east slavic",
        "old english",
        "old french",
        "old irish",
        "old northern french",
        "old saxon",
        "persian",
    ),
    "welsh": (
        "ancient greek",
        "anglo-norman",
        "breton",
        "cornish",
        "english",
        "french",
        "latin",
        "middle english",
        "old english",
        "old french",
        "old irish",
        "vulgar latin",
    ),
}

DIRECT_BORROWING_RE = re.compile(
    r"\b(?:(?:re)?borrowed|borrowing|loan(?:word)?)\s+from\s+"
    r"(?P<donor>.{1,140}?)(?=[,.;:\n]|$)",
    re.IGNORECASE,
)


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def compact(value: str | None) -> str:
    return " ".join(nfc(value).split())


def clause_before(text: str, start: int, width: int = 100) -> str:
    fragment = text[max(0, start - width) : start]
    return re.split(r"[.;:\n]", fragment)[-1].strip()


def has_governing_hedge(fragment: str) -> bool:
    words = set(re.findall(r"[a-z-]+", fragment.casefold()))
    return any(hedge in words for hedge in HEDGES)


def identifiable_donor(donor: str) -> bool:
    lowered = donor.casefold().strip()
    if not lowered or lowered.startswith(GENERIC_DONORS):
        return False
    if has_governing_hedge(lowered):
        return False
    # A reconstructed language is a named donor if the source itself states
    # the borrowing.  This does not turn the reconstruction into a sound law.
    if re.search(r"\bproto-[a-z-]+\b", lowered):
        return True
    named_donors = {
        donor_name
        for donors in EXTERNAL_DONORS.values()
        for donor_name in donors
    }
    if any(
        re.search(rf"\b{re.escape(name)}\b", lowered)
        for name in named_donors
    ):
        return True
    # Direct source language names in the dictionaries are capitalized
    # (Thracian, Sogdian, Koine Greek, Old Church Slavonic, and so on).
    # Accepting that explicit name is not inventing a donor; rejecting an
    # unenumerated but plainly named language would recreate the old void.
    return bool(re.search(r"\b[A-Z][A-Za-z-]{2,}\b", donor))


def named_donor(language: str, etymology: str | None) -> str:
    """Return a published named donor, or an empty string.

    The function is intentionally stricter than the old substring marker.
    It accepts an unhedged explicit borrowing statement, an unhedged calque or
    semantic-loan statement, or an unhedged ancestry chain that reaches a
    language explicitly listed as an external donor for the language at hand.
    """

    text = compact(etymology)
    if not text or language not in EXTERNAL_DONORS:
        return ""
    lowered = text.casefold()

    for match in DIRECT_BORROWING_RE.finditer(text):
        before = clause_before(lowered, match.start())
        donor = compact(match.group("donor"))
        if has_governing_hedge(before):
            continue
        if identifiable_donor(donor):
            return donor

    donors = sorted(
        EXTERNAL_DONORS[language],
        key=len,
        reverse=True,
    )
    donor_pattern = "|".join(re.escape(item) for item in donors)
    route_patterns = (
        rf"\bcalque\s+of\s+(?P<donor>{donor_pattern})\b",
        rf"\bsemantic\s+loan\s+from\s+(?P<donor>{donor_pattern})\b",
        rf"\bvia\s+(?P<donor>{donor_pattern})\b",
        rf"\b(?:derived\s+)?from\s+(?P<donor>{donor_pattern})\b",
    )
    for pattern in route_patterns:
        for match in re.finditer(pattern, text, re.IGNORECASE):
            before = clause_before(lowered, match.start())
            if has_governing_hedge(before):
                continue
            if before.endswith(("not", "neither")):
                continue
            return compact(match.group("donor"))
    return ""


def self_test() -> None:
    cases = (
        (
            "ancient_greek",
            "Borrowed from Biblical Hebrew אָמֵן.",
            True,
        ),
        (
            "ancient_greek",
            "Borrowed from a Semitic source, usually assumed Phoenician.",
            False,
        ),
        (
            "latin",
            "Likely borrowed from Ancient Greek κάρα.",
            False,
        ),
        (
            "gothic",
            "Borrowed from Latin lēctiō. The date is uncertain.",
            True,
        ),
        (
            "welsh",
            "From Proto-Brythonic *pal, from Latin pala.",
            True,
        ),
        (
            "ancient_greek",
            "It is unclear who borrowed from whom.",
            False,
        ),
        (
            "persian",
            "A generic trademark named after Dayton Engineering.",
            False,
        ),
        (
            "gothic",
            "Likely a calque of Ancient Greek ἀκρασία.",
            False,
        ),
    )
    for language, etymology, expected in cases:
        actual = bool(named_donor(language, etymology))
        if actual != expected:
            raise AssertionError(
                f"{language}: expected {expected}, got {actual}: {etymology}"
            )


if __name__ == "__main__":
    self_test()
