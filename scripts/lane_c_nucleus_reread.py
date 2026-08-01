#!/usr/bin/env python3
"""Rank lane C's six lexicons for a human binary-nucleus rereading.

The shared recovery databases, the frozen nucleus index, the shift network,
and the Arabic lexical source are read-only.  This script writes one
lane-owned ranked JSON file.  Its similarity score is retrieval order only:
it never issues a verdict and never changes the sound or semantic standard.

The rereading differs from the older broad recovery pass in four ways:

* inflection-only rows are removed in favour of dictionary lexical members;
* only positions 1-2 of the comparison skeleton are treated as the nucleus;
* an empty sound route is retained only for literal phoneme identity.
* basic vocabulary is read before general, derived, technical, and compound
  vocabulary, while every source member keeps its pre-existing coverage fate.

All non-identity substitutions must therefore carry one or more signed row
identifiers already present in the frozen candidate database.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import numpy as np
import pyarrow.parquet as pq
from sentence_transformers import SentenceTransformer
from recovery_pipeline.network import ShiftRule, compile_network


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
CORE = ROOT / "data" / "juthoor-core-levels.json"
CATALOG = ROOT / "03-scholar-extracts" / "jabal-nuclei-catalog.md"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
ARABIC_ROOTS = (
    ROOT / "Resources" / "arabic_roots_hf" / "train-00000-of-00001.parquet"
)
OUTPUT = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_c_nucleus_reread_ranked.json"
)
EMBEDDING_CACHE = ROOT / "cache" / "lane_c_nucleus_reread_embeddings"
MODEL_ID = "sentence-transformers/all-MiniLM-L6-v2"
DATE = "2026-08-01"
SCHEMA = "lane-c-nucleus-reread-ranked-v3"

LEXICAL_POS = {
    "adj",
    "adv",
    "article",
    "conj",
    "det",
    "intj",
    "num",
    "particle",
    "postp",
    "prep",
    "pron",
    "noun",
    "verb",
}
SOURCE_NAMES = {
    "لسان العرب لابن منظور",
    "تاج العروس لمرتضى الزبيدي",
}

# This order is an explicit reading order, not a sampling filter.  The source
# denominator and lane_c_coverage.jsonl remain untouched.  Patterns operate on
# English source glosses because that is the common field across all six
# Kaikki snapshots.
BASIC_CATEGORIES: tuple[tuple[str, tuple[str, ...]], ...] = (
    (
        "body",
        (
            "body", "head", "hair", "eye", "ear", "nose", "mouth",
            "tongue", "tooth", "teeth", "lip", "hand", "arm", "finger",
            "nail", "foot", "feet", "leg", "knee", "heart", "blood",
            "bone", "skin", "flesh", "neck", "breast", "belly", "back",
        ),
    ),
    (
        "kinship",
        (
            "mother", "father", "parent", "brother", "sister", "son",
            "daughter", "child", "husband", "wife", "man", "woman",
            "kin", "kindred",
        ),
    ),
    (
        "nature",
        (
            "water", "fire", "earth", "soil", "land", "sky", "sun",
            "moon", "star", "rain", "wind", "river", "sea", "mountain",
            "stone", "sand", "smoke", "tree", "wood",
        ),
    ),
    (
        "primary-action",
        (
            "take", "put", "set", "place", "give", "get", "cut",
            "break", "strike", "hit", "beat", "walk", "go", "come",
            "stand", "sit", "lie", "sleep", "wake", "eat", "drink",
            "see", "hear", "say", "speak", "know", "die", "live",
            "kill", "burn", "fall", "rise", "carry", "hold", "open",
            "close",
        ),
    ),
    (
        "number",
        (
            "zero", "one", "two", "three", "four", "five", "six",
            "seven", "eight", "nine", "ten", "hundred", "thousand",
        ),
    ),
    (
        "deictic-interrogative",
        (
            "who", "what", "where", "when", "why", "how", "which",
            "this", "that", "these", "those", "here", "there",
        ),
    ),
)
BASIC_CATEGORY_ORDER = {
    name: index for index, (name, _terms) in enumerate(BASIC_CATEGORIES)
}
FUNCTION_POS = {"article", "conj", "det", "particle", "postp", "prep", "pron"}
LATE_POS = {"adj", "adv", "noun", "verb"}
TECHNICAL_GLOSS = re.compile(
    r"(?i)\b(?:chemistry|physics|medicine|anatomy|botany|zoology|taxonomy|"
    r"linguistics|grammar|rhetoric|mathematics|geometry|astronomy|legal|"
    r"theology|philosophy|computing|programming|unit of|chemical element|"
    r"species of|genus of)\b"
)
COMPOUND_ETYMOLOGY = re.compile(
    r"(?i)\b(?:compound|univerbation|calque)\b|\s\+\s"
)
EXPLICIT_AFFIX = re.compile(
    r"(?i)\b(?:prefix|suffix|prefixed|suffixed|mutation of|mutated form|"
    r"denominative suffix|agentive suffix|nominal suffix|verbal suffix|"
    r"action-noun suffix|abstract-noun suffix)\b"
)
DERIVED_FORM_GLOSS = re.compile(
    r"(?i)\b(?:form|spelling|alternative spelling|participle|gerundive|"
    r"comparative(?: degree)?|superlative(?: degree)?|diminutive|contraction|"
    r"abbreviation)(?:\s*\))?\s+(?:of|for)\b"
)
WELSH_MUTATION = re.compile(
    r"(?i)\b(?:soft|nasal|aspirate|mixed)?\s*mutation of\s+([^\s,;.()]+)"
)
AFFIX_BASE = re.compile(
    r"(?i)(?:^|\bfrom\s+)([^\s,;.()+]+)(?:\s*\([^)]*\))?\s*\+\s*"
)
PERSIAN_GLOSS_PREFIX = re.compile(
    r"(?i)\bsee\s+([^,;:]+),\s*([^;:]+):"
)
GREEK_ENDINGS = (
    ("os", "s"), ("on", "n"), ("as", "s"), ("es", "s"),
    ("is", "s"), ("ous", "s"),
)
LATIN_ENDINGS = (
    ("us", "s"), ("um", "m"), ("am", "m"), ("em", "m"),
    ("as", "s"), ("es", "s"), ("is", "s"), ("os", "s"),
)
GENERIC_ORBIT_WORDS = {
    "act", "action", "be", "being", "become", "change", "come", "do",
    "exist", "go", "make", "move", "movement", "object", "process",
    "put", "state", "thing", "turn",
}


@dataclass(frozen=True)
class Language:
    key: str
    reading_file: str
    db_path: str
    label: str


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

# Literal phoneme identity only.  Mouth-family anchors are retrieval aids, not
# signed historical rows, and are deliberately absent from this map.
IDENTITY: dict[str, set[str]] = {
    "ء": {"qstop"},
    "ب": {"b"},
    "ت": {"t"},
    "ث": {"th"},
    "ج": {"j"},
    "خ": {"kh"},
    "د": {"d"},
    "ذ": {"dh"},
    "ر": {"r"},
    "ز": {"z"},
    "س": {"s"},
    "ش": {"sh"},
    "ف": {"f"},
    "ق": {"q"},
    "ك": {"k"},
    "ل": {"l"},
    "م": {"m"},
    "ن": {"n"},
    "ه": {"h"},
    "و": {"w"},
    "ي": {"y", "j"},
}


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def ro_connection(path: Path) -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{path.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def normalize_arabic(value: str) -> str:
    value = re.sub(r"[^ء-ي]", "", nfc(value))
    return value.translate(str.maketrans({"أ": "ء", "إ": "ء", "آ": "ء"}))


def arabic_root_shape(value: str) -> tuple[int, str]:
    """Return the author-ordered Arabic root-shape band.

    The order is operational only: hollow, geminate, other weak, then sound.
    It changes which candidate is read first, never its retrieval score or
    verdict.  Non-trilateral witnesses stay with the sound/general tail.
    """

    root = normalize_arabic(value)
    if len(root) == 3 and root[1] in {"و", "ي"}:
        return 0, "hollow"
    if len(root) == 3 and root[1] == root[2]:
        return 1, "geminate"
    if len(root) == 3 and any(letter in {"و", "ي"} for letter in root):
        return 2, "weak"
    return 3, "sound-or-other"


def gloss_has_term(gloss: str, term: str) -> bool:
    """Match a basic concept only when it heads a published sense.

    Incidental mentions such as ``vessel for water`` or ``one of the priests``
    must not promote a technical or derived entry into the basic band.
    """

    escaped = re.escape(term)
    suffix = "" if term.endswith("s") else r"(?:s|es|ed|ing)?"
    for clause in re.split(r"[;,]", gloss):
        clause = re.sub(r"^\s*(?:\([^)]*\)\s*)+", "", clause)
        clause = re.sub(r"^\s*(?:(?:to|a|an|the)\s+)", "", clause)
        clause = clause.strip()
        # Keep lexicalized metaphors such as "ear of grain" and "body of
        # water" out of the body-part band.  They remain in the denominator
        # and are merely read later with general vocabulary.
        if re.match(
            r"(?i)^(?:ear of (?:grain|corn)|eye of (?:a |the )?(?:needle|storm)|"
            r"body of water|foot of (?:a |the )?(?:mountain|hill)|"
            r"arm of (?:a |the )?(?:sea|river)|mouth of (?:a |the )?river)\b",
            clause,
        ):
            continue
        if re.match(rf"(?i)^{escaped}{suffix}(?![A-Za-z-])", clause):
            return True
    return False


def reading_priority(entry: dict[str, Any]) -> dict[str, Any]:
    """Return the explicit basic-first reading band for one source member.

    This changes queue order only.  It does not delete the member, alter the
    source denominator, or issue a semantic judgment.
    """

    gloss = nfc(str(entry.get("gloss", "")))
    pos = nfc(str(entry.get("pos", ""))).casefold()
    etymology = nfc(str(entry.get("etymology", "")))
    headword = nfc(str(entry.get("headword", "")))
    compound = bool(
        COMPOUND_ETYMOLOGY.search(etymology)
        or re.search(r"[\s-]", headword.strip("-"))
    )
    technical = bool(TECHNICAL_GLOSS.search(gloss))
    derived = bool(
        EXPLICIT_AFFIX.search(etymology)
        or DERIVED_FORM_GLOSS.search(gloss)
        or DERIVED_FORM_GLOSS.search(etymology)
    )

    matches: list[tuple[str, str]] = []
    for category, terms in BASIC_CATEGORIES:
        if category == "number" and pos != "num":
            continue
        if category == "deictic-interrogative" and pos not in FUNCTION_POS | {"adv"}:
            continue
        for term in terms:
            # English "lie" is polysemous.  Definitions headed "lying" in
            # the sense of speaking falsely are not the primary bodily verb.
            if term == "lie" and re.match(
                r"(?i)^\s*lying(?:\b|,).*(?:false|untruth|deceit)",
                gloss,
            ):
                continue
            if gloss_has_term(gloss, term):
                matches.append((category, term))
    if pos in FUNCTION_POS:
        category = "function-word"
        matches.append((category, pos))
    elif pos == "num" and not any(item[0] == "number" for item in matches):
        matches.append(("number", "pos:num"))

    if compound or technical or derived:
        band = 2
        label = "late-derived-technical-or-compound"
    elif matches:
        band = 0
        label = "basic-vocabulary"
    else:
        band = 1
        label = "general-lexicon"

    categories = [item[0] for item in matches]
    category_rank = min(
        (
            BASIC_CATEGORY_ORDER.get(category, len(BASIC_CATEGORY_ORDER))
            for category in categories
        ),
        default=len(BASIC_CATEGORY_ORDER) + 1,
    )
    return {
        "reading_priority_band": band,
        "reading_priority_label": label,
        "basic_categories": list(dict.fromkeys(categories)),
        "basic_matches": [item[1] for item in matches],
        "basic_category_rank": category_rank,
        "late_flags": [
            name
            for name, present in (
                ("derived", derived),
                ("technical", technical),
                ("compound", compound),
            )
            if present
        ],
    }


def lookup_key(value: str) -> str:
    return re.sub(r"[\W_]+", "", nfc(value).casefold(), flags=re.UNICODE)


def explicit_base_target(language: str, source_morphology: str) -> str:
    """Extract only a source-explicit base for an affix or Welsh mutation."""

    if language == "welsh":
        match = WELSH_MUTATION.search(source_morphology)
        if match:
            return nfc(match.group(1)).strip("`*'")
    if language == "persian":
        match = PERSIAN_GLOSS_PREFIX.search(source_morphology)
        if match:
            return nfc(match.group(2)).strip("`*' ")
    match = AFFIX_BASE.search(source_morphology)
    if match:
        return nfc(match.group(1)).strip("`*'")
    return ""


def morphology_resolution(
    language: str,
    entry: dict[str, Any],
    lexical_lookup: dict[str, tuple[str, ...]],
) -> dict[str, Any]:
    """Keep affix consonants and Welsh mutation consonants out of the pair.

    An explicit derivation is redirected to its independently inventoried base
    when that base is present.  If the source names no resolvable base, the
    member stays covered but is blocked from nucleus counting.  Ordinary Greek
    and Latin consonantal endings are stripped mechanically only at the right
    edge, where they cannot silently become the second nucleus consonant.
    """

    surface = tuple(nfc(str(item)) for item in entry.get("tokens", ()))
    etymology = nfc(str(entry.get("etymology", "")))
    gloss = nfc(str(entry.get("gloss", "")))
    source_morphology = f"{etymology}\n{gloss}"
    headword = nfc(str(entry.get("headword", "")))
    romanization = nfc(str(entry.get("romanization", "")))
    affixed = bool(EXPLICIT_AFFIX.search(source_morphology))
    mutated = language == "welsh" and bool(WELSH_MUTATION.search(source_morphology))
    prefixed = language == "persian" and bool(
        re.search(r"(?i)\b(?:prefix|prefixed)\b", source_morphology)
        or PERSIAN_GLOSS_PREFIX.search(source_morphology)
    )
    if affixed or mutated or prefixed:
        target = explicit_base_target(language, source_morphology)
        target_tokens = lexical_lookup.get(lookup_key(target), ()) if target else ()
        if target_tokens:
            return {
                "morphology_gate": "REDIRECTED-TO-BASE-MEMBER",
                "morphology_note": (
                    f"source-explicit base {target}; derivative/mutated member "
                    "does not receive an independent nucleus count"
                ),
                "comparison_tokens": list(target_tokens),
                "base_target": target,
                "eligible_for_nucleus_count": False,
            }
        return {
            "morphology_gate": "MORPHOLOGY-BLOCKED",
            "morphology_note": (
                "source marks an affix or initial mutation, but no independent "
                "base member was resolved; no affix consonant is counted"
            ),
            "comparison_tokens": [],
            "base_target": target,
            "eligible_for_nucleus_count": False,
        }

    tokens = list(surface)
    spelling = romanization.casefold() or headword.casefold()
    endings = GREEK_ENDINGS if language == "ancient_greek" else LATIN_ENDINGS if language == "latin" else ()
    stripped = ""
    for ending, final_token in endings:
        if spelling.endswith(ending) and tokens and tokens[-1] == final_token:
            stripped = ending
            tokens.pop()
            break
    # In Greek third-declension nominatives, final ξ/ψ contains the stem
    # stop plus nominative -s.  The inventory expands that spelling into two
    # consonant tokens, so remove only the final inflectional s before the
    # nucleus pair is counted (e.g. ὄνυξ n-k-s -> n-k).
    if (
        language == "ancient_greek"
        and not stripped
        and nfc(str(entry.get("pos", ""))).casefold() in {"noun", "adj"}
        and tokens
        and tokens[-1] == "s"
        and (headword.endswith(("ξ", "ψ", "ς")) or romanization.casefold().endswith(("x", "ps", "s")))
    ):
        stripped = "Greek nominative -s"
        tokens.pop()
    if len(tokens) < 2:
        return {
            "morphology_gate": "MORPHOLOGY-BLOCKED",
            "morphology_note": (
                f"stripping the branch ending {stripped!r} leaves fewer than "
                "two stem consonants; the ending is not counted"
            ),
            "comparison_tokens": tokens,
            "base_target": "",
            "eligible_for_nucleus_count": False,
        }
    return {
        "morphology_gate": "STEM-PAIR-READY",
        "morphology_note": (
            f"right-edge branch ending {stripped!r} stripped before counting"
            if stripped
            else "no source-explicit affix or Welsh mutation owns the comparison pair"
        ),
        "comparison_tokens": tokens,
        "base_target": "",
        "eligible_for_nucleus_count": True,
    }


def core_rows() -> dict[str, dict[str, Any]]:
    payload = json.loads(CORE.read_text(encoding="utf-8"))
    rows: dict[str, dict[str, Any]] = {}
    for row in payload["levels"]["level_2_binary_nuclei"]["nuclei"]:
        key = normalize_arabic(str(row["nucleus"]))
        # This pass is expressly a two-consonant pass.
        if len(key) != 2:
            continue
        reading = nfc(
            row.get("jabal_lexicon_reading_ar")
            or row.get("composed_reading_ar")
            or ""
        ).strip()
        if reading:
            rows[key] = dict(row)
    return rows


def sample_roots() -> dict[str, tuple[str, ...]]:
    output: dict[str, tuple[str, ...]] = {}
    pattern = re.compile(
        r"^\| \*\*(?P<nucleus>[^*]+)\*\*.*\|\s*\d+\s*\|\s*(?P<roots>[^|]+?)\s*\|\s*$"
    )
    for line in CATALOG.read_text(encoding="utf-8").splitlines():
        match = pattern.match(line)
        if not match:
            continue
        nucleus = normalize_arabic(match.group("nucleus"))
        roots = tuple(
            dict.fromkeys(
                root
                for root in (
                    normalize_arabic(item)
                    for item in re.split(r"[،,]", match.group("roots"))
                )
                if root
            )
        )
        output[nucleus] = roots
    return output


def arabic_lexica() -> tuple[dict[str, str], dict[str, tuple[str, ...]]]:
    table = pq.read_table(
        ARABIC_ROOTS,
        columns=["root", "definition", "book_name"],
    )
    definitions: dict[str, str] = {}
    sources: dict[str, set[str]] = defaultdict(set)
    for row in table.to_pylist():
        root = normalize_arabic(str(row["root"]))
        book = nfc(str(row["book_name"]))
        if book == "المعجم العربي الإنجليزي":
            definitions[root] = nfc(str(row["definition"]))
        elif book in SOURCE_NAMES:
            sources[root].add(book)
    return definitions, {
        root: tuple(sorted(names)) for root, names in sources.items()
    }


def definition_chunks(text: str, limit: int = 520) -> list[str]:
    compact = re.sub(r"\s+", " ", nfc(text)).strip()
    if not compact:
        return []
    pieces = re.split(r"(?=\bb\d+:)|(?=\bA\d*:)|(?<=\.)\s+(?=[A-Z\[])", compact)
    chunks: list[str] = []
    current = ""
    for piece in pieces:
        piece = piece.strip()
        if not piece:
            continue
        if current and len(current) + 1 + len(piece) > limit:
            chunks.append(current)
            current = piece
        else:
            current = f"{current} {piece}".strip()
    if current:
        chunks.append(current)
    # Preserve wide sense fans without letting a single huge Lane entry own
    # the entire retrieval budget.
    return chunks[:18]


def literal_identity(tokens: tuple[str, ...], nucleus: str) -> bool:
    if len(tokens) < 2 or len(nucleus) != 2:
        return False
    return all(tokens[index] in IDENTITY.get(letter, set()) for index, letter in enumerate(nucleus))


def route_covers_pair(
    tokens: tuple[str, ...],
    nucleus: str,
    rule_ids: tuple[str, ...],
    rules: dict[str, ShiftRule],
) -> bool:
    if len(tokens) < 2 or len(nucleus) != 2:
        return False
    graph: dict[str, set[str]] = defaultdict(set)
    for arabic, foreign_tokens in IDENTITY.items():
        for foreign in foreign_tokens:
            graph[arabic].add(foreign)
            graph[foreign].add(arabic)
    for row_id in rule_ids:
        rule = rules.get(row_id)
        if rule is None:
            return False
        for left in rule.left_tokens:
            for right in rule.right_tokens:
                graph[left].add(right)
                graph[right].add(left)

    def reaches(source: str, target: str) -> bool:
        queue = [source]
        seen = {source}
        while queue:
            current = queue.pop()
            if current == target:
                return True
            for neighbour in graph.get(current, ()):
                if neighbour not in seen:
                    seen.add(neighbour)
                    queue.append(neighbour)
        return False

    return all(reaches(tokens[index], letter) for index, letter in enumerate(nucleus))


def existing_card_ids(path: Path) -> set[str]:
    pattern = re.compile(r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):\d+:[^`\s\]]+")
    result: set[str] = set()
    with path.open(encoding="utf-8") as handle:
        for line in handle:
            if line.startswith("- الكلمةُ في الفرع:") or line.startswith("### بطاقة:"):
                result.update(pattern.findall(line))
    return result


def encode(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
) -> np.ndarray:
    if not texts:
        return np.empty((0, model.get_sentence_embedding_dimension()), dtype=np.float32)
    return np.asarray(
        model.encode(
            texts,
            batch_size=batch_size,
            normalize_embeddings=True,
            show_progress_bar=True,
            convert_to_numpy=True,
        ),
        dtype=np.float32,
    )


def cached_encode(
    model: SentenceTransformer,
    texts: list[str],
    batch_size: int,
    name: str,
) -> np.ndarray:
    fingerprint = hashlib.sha256(
        (MODEL_ID + "\0" + "\0".join(texts)).encode("utf-8")
    ).hexdigest()
    path = EMBEDDING_CACHE / f"{name}.npz"
    if path.exists():
        with np.load(path, allow_pickle=False) as cached:
            cached_fingerprint = str(cached["fingerprint"].item())
            embeddings = np.asarray(cached["embeddings"], dtype=np.float32)
        if cached_fingerprint == fingerprint and len(embeddings) == len(texts):
            print(f"embedding cache hit: {name}", flush=True)
            return embeddings
    embeddings = encode(model, texts, batch_size)
    EMBEDDING_CACHE.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp.npz")
    np.savez(temporary, fingerprint=np.asarray(fingerprint), embeddings=embeddings)
    temporary.replace(path)
    return embeddings


def load_language(
    language: Language,
    core: dict[str, dict[str, Any]],
    rules: dict[str, ShiftRule],
) -> tuple[list[dict[str, Any]], dict[tuple[str, str], tuple[str, ...]], dict[str, int]]:
    con = ro_connection(ROOT / language.db_path)
    try:
        placeholders = ",".join("?" for _ in LEXICAL_POS)
        params = (language.key, *sorted(LEXICAL_POS))
        lexical_lookup: dict[str, tuple[str, ...]] = {}
        for base in con.execute(
            f"""
            SELECT headword, romanization, tokens_json
            FROM entries
            WHERE language=? AND form_of=0 AND alternative_of=0
              AND pos IN ({placeholders})
            """,
            params,
        ):
            tokens = tuple(
                nfc(str(item))
                for item in json.loads(base["tokens_json"] or "[]")
                if item
            )
            if not tokens:
                continue
            for spelling in (base["headword"], base["romanization"]):
                key = lookup_key(nfc(str(spelling or "")))
                if key and key not in lexical_lookup:
                    lexical_lookup[key] = tokens
        rows = con.execute(
            f"""
            SELECT rowid AS source_rowid, entry_id, headword, romanization, pos, gloss, etymology,
                   source_stratum, source_scope_note, tokens_json, skeleton
            FROM entries
            WHERE language=? AND form_of=0 AND alternative_of=0 AND loan_hint=0
              AND pos IN ({placeholders})
              AND EXISTS (
                  SELECT 1 FROM candidates c
                  WHERE c.entry_id=entries.entry_id
                    AND c.kind='nucleus' AND c.status='licensed'
                    AND c.route_flag=0 AND c.positions_json='["1-2"]'
              )
            ORDER BY rowid
            """,
            params,
        ).fetchall()
        entries: list[dict[str, Any]] = []
        entry_tokens: dict[str, tuple[str, ...]] = {}
        morphology_counts: dict[str, int] = defaultdict(int)
        for row in rows:
            tokens = tuple(nfc(str(item)) for item in json.loads(row["tokens_json"] or "[]"))
            if len(tokens) < 2:
                continue
            entry = {key: nfc(str(row[key] or "")) for key in row.keys()}
            entry["source_rowid"] = int(row["source_rowid"])
            entry["tokens"] = list(tokens)
            entry.update(reading_priority(entry))
            morphology = morphology_resolution(language.key, entry, lexical_lookup)
            entry.update(morphology)
            morphology_counts[morphology["morphology_gate"]] += 1
            if not morphology["eligible_for_nucleus_count"]:
                continue
            comparison_tokens = tuple(morphology["comparison_tokens"])
            entries.append(entry)
            entry_tokens[entry["entry_id"]] = comparison_tokens

        routes: dict[tuple[str, str], tuple[str, ...]] = {}
        invalid_anchor_routes = 0
        for row in con.execute(
            f"""
            SELECT e.entry_id, c.form, c.rule_ids_json
            FROM entries e JOIN candidates c ON c.entry_id=e.entry_id
            WHERE e.language=? AND e.form_of=0 AND e.alternative_of=0 AND e.loan_hint=0
              AND e.pos IN ({placeholders})
              AND c.kind='nucleus' AND c.status='licensed'
              AND c.route_flag=0 AND c.positions_json='["1-2"]'
            """,
            params,
        ):
            entry_id = nfc(str(row["entry_id"]))
            if entry_id not in entry_tokens:
                continue
            nucleus = normalize_arabic(str(row["form"]))
            if nucleus not in core:
                continue
            rule_ids = tuple(nfc(str(item)) for item in json.loads(row["rule_ids_json"] or "[]"))
            if not route_covers_pair(
                entry_tokens[entry_id], nucleus, rule_ids, rules
            ):
                invalid_anchor_routes += 1
                continue
            key = (entry_id, nucleus)
            previous = routes.get(key)
            if previous is None or (len(rule_ids), rule_ids) < (len(previous), previous):
                routes[key] = rule_ids

        entry_ids = {entry["entry_id"] for entry in entries}
        routed_ids = {key[0] for key in routes}
        entries = [entry for entry in entries if entry["entry_id"] in routed_ids]
        retained_ids = {entry["entry_id"] for entry in entries}
        routes = {key: value for key, value in routes.items() if key[0] in retained_ids}
        stats = {
            "candidate_bearing_lexical_members_before_route_filter": len(entry_ids),
            "candidate_bearing_lexical_members_after_route_filter": len(entries),
            "entry_nucleus_pairs_after_route_filter": len(routes),
            "discarded_routes_not_fully_covered_by_signed_rows": invalid_anchor_routes,
            "explicit_loan_members_excluded": int(
                con.execute(
                    "SELECT count(*) FROM entries WHERE language=? AND form_of=0 AND loan_hint=1",
                    (language.key,),
                ).fetchone()[0]
            ),
            "inflection_rows_excluded": int(
                con.execute(
                    "SELECT count(*) FROM entries WHERE language=? AND form_of=1",
                    (language.key,),
                ).fetchone()[0]
            ),
            "alternative_rows_excluded": int(
                con.execute(
                    "SELECT count(*) FROM entries WHERE language=? AND form_of=0 AND alternative_of=1",
                    (language.key,),
                ).fetchone()[0]
            ),
            "morphology_gate_counts": dict(sorted(morphology_counts.items())),
            "reading_priority_counts": dict(
                sorted(
                    Counter(
                        entry["reading_priority_label"] for entry in entries
                    ).items()
                )
            ),
        }
        return entries, routes, stats
    finally:
        con.close()


def rank_language(
    language: Language,
    entries: list[dict[str, Any]],
    routes: dict[tuple[str, str], tuple[str, ...]],
    core: dict[str, dict[str, Any]],
    nucleus_support: dict[str, tuple[str, ...]],
    root_chunks: dict[str, list[tuple[str, int]]],
    nucleus_core_chunks: dict[str, int],
    query_embeddings: np.ndarray,
    chunk_embeddings: np.ndarray,
    top: int,
    top_per_nucleus: int,
) -> list[dict[str, Any]]:
    entry_index = {entry["entry_id"]: index for index, entry in enumerate(entries)}
    by_nucleus: dict[str, list[str]] = defaultdict(list)
    for entry_id, nucleus in routes:
        if nucleus_support.get(nucleus):
            by_nucleus[nucleus].append(entry_id)

    ranked: list[dict[str, Any]] = []
    for nucleus, member_ids in by_nucleus.items():
        chunk_refs: list[tuple[str, int]] = []
        for root in nucleus_support[nucleus]:
            chunk_refs.extend(
                (root, chunk_index)
                for _, chunk_index in root_chunks.get(root, ())
            )
        if not chunk_refs:
            continue
        member_indices = np.asarray([entry_index[item] for item in member_ids], dtype=np.int64)
        chunk_indices = np.asarray([item[1] for item in chunk_refs], dtype=np.int64)
        root_similarities = query_embeddings[member_indices] @ chunk_embeddings[chunk_indices].T
        root_winners = root_similarities.argmax(axis=1)
        root_scores = root_similarities[np.arange(len(member_ids)), root_winners]
        root_columns: dict[str, list[int]] = defaultdict(list)
        for column, (root, _chunk_index) in enumerate(chunk_refs):
            root_columns[root].append(column)
        per_root_scores = np.stack(
            [
                root_similarities[:, columns].max(axis=1)
                for root, columns in sorted(root_columns.items())
            ],
            axis=1,
        )
        ordered_root_scores = np.sort(per_root_scores, axis=1)[:, ::-1]
        neighbourhood_scores = (
            ordered_root_scores[:, 1]
            if ordered_root_scores.shape[1] >= 2
            else np.zeros(len(member_ids), dtype=np.float32)
        )
        core_index = nucleus_core_chunks.get(nucleus)
        if core_index is None:
            scores = root_scores
            semantic_bases = ["classical-root-sense-fan"] * len(member_ids)
        else:
            core_scores = query_embeddings[member_indices] @ chunk_embeddings[core_index]
            scores = np.maximum(root_scores, core_scores)
            semantic_bases = [
                "frozen-core-reading-en" if core > root else "classical-root-sense-fan"
                for core, root in zip(core_scores.tolist(), root_scores.tolist())
            ]
        for member_id, winner, score, semantic_basis, root_score, neighbourhood_score in zip(
            member_ids,
            root_winners.tolist(),
            scores.tolist(),
            semantic_bases,
            root_scores.tolist(),
            neighbourhood_scores.tolist(),
        ):
            entry = entries[entry_index[member_id]]
            support_root, chunk_index = chunk_refs[winner]
            root_shape_band, root_shape_label = arabic_root_shape(support_root)
            rule_ids = routes[(member_id, nucleus)]
            ranked.append(
                {
                    "language": language.key,
                    "member_id": member_id,
                    "form": entry["headword"],
                    "romanization": entry["romanization"],
                    "pos": entry["pos"],
                    "branch_gloss": entry["gloss"],
                    "etymology": entry["etymology"],
                    "source_stratum": entry["source_stratum"],
                    "source_scope_note": entry["source_scope_note"],
                    "comparison_skeleton": entry["skeleton"],
                    "surface_tokens": entry["tokens"],
                    "comparison_tokens": entry["comparison_tokens"],
                    "morphology_gate": entry["morphology_gate"],
                    "morphology_note": entry["morphology_note"],
                    "base_target": entry["base_target"],
                    "source_rowid": entry["source_rowid"],
                    "reading_priority_band": entry["reading_priority_band"],
                    "reading_priority_label": entry["reading_priority_label"],
                    "basic_categories": entry["basic_categories"],
                    "basic_matches": entry["basic_matches"],
                    "basic_category_rank": entry["basic_category_rank"],
                    "late_flags": entry["late_flags"],
                    "nucleus": nucleus,
                    "nucleus_reading_ar": nfc(
                        core[nucleus].get("jabal_lexicon_reading_ar")
                        or core[nucleus].get("composed_reading_ar")
                        or ""
                    ),
                    "nucleus_reading_en": nfc(core[nucleus].get("composed_reading_en") or ""),
                    "support_root": support_root,
                    "arabic_root_shape_band": root_shape_band,
                    "arabic_root_shape_label": root_shape_label,
                    "support_excerpt_en": root_chunks[support_root][
                        [item[1] for item in root_chunks[support_root]].index(chunk_index)
                    ][0],
                    "classical_sources": sorted(SOURCE_NAMES),
                    "licensed_rules": list(rule_ids),
                    "route_label": "+".join(rule_ids) if rule_ids else "IDENTITY",
                    "semantic_retrieval_score": round(float(score), 6),
                    "semantic_best_root_score": round(float(root_score), 6),
                    "semantic_root_neighbourhood_score": round(
                        float(neighbourhood_score), 6
                    ),
                    "semantic_support_root_count": len(root_columns),
                    "semantic_retrieval_basis": semantic_basis,
                    "status": "RANKED-FOR-HUMAN-ORBIT-REVIEW; NOT-A-VERDICT",
                }
            )
    by_member: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for item in ranked:
        by_member[item["member_id"]].append(item)
    for member_rows in by_member.values():
        member_rows.sort(
            key=lambda item: item["semantic_retrieval_score"], reverse=True
        )
        for index, item in enumerate(member_rows):
            competing = max(
                (
                    float(other["semantic_root_neighbourhood_score"])
                    for other in member_rows
                    if other["nucleus"] != item["nucleus"]
                ),
                default=0.0,
            )
            margin = float(item["semantic_root_neighbourhood_score"]) - competing
            support_words = {
                word.casefold()
                for word in re.findall(r"[A-Za-z]+", item["support_excerpt_en"])
            }
            specific_words = support_words - GENERIC_ORBIT_WORDS
            distinctive = (
                float(item["semantic_best_root_score"]) >= 0.38
                and float(item["semantic_root_neighbourhood_score"]) >= 0.30
                and margin >= 0.03
                and len(specific_words) >= 2
            )
            item["semantic_orbit_competing_score"] = round(competing, 6)
            item["semantic_orbit_margin"] = round(margin, 6)
            item["semantic_orbit_gate"] = (
                "DISTINCTIVE-ORBIT-REVIEW"
                if distinctive
                else "SEMANTIC-ORBIT-NOT-DISTINCTIVE"
            )
            item["semantic_orbit_rank_within_member"] = index + 1

    def ranking_key(item: dict[str, Any]) -> tuple[Any, ...]:
        return (
            int(item["reading_priority_band"]),
            int(item["basic_category_rank"]),
            int(item["arabic_root_shape_band"]),
            item["semantic_orbit_gate"] != "DISTINCTIVE-ORBIT-REVIEW",
            -float(item["semantic_orbit_margin"]),
            -float(item["semantic_retrieval_score"]),
            len(item["licensed_rules"]),
            int(item["source_rowid"]),
            item["member_id"],
            item["nucleus"],
        )

    ranked.sort(key=ranking_key)
    selected: dict[tuple[str, str], dict[str, Any]] = {
        (item["member_id"], item["nucleus"]): item
        for item in ranked
        if item["reading_priority_band"] == 0
    }
    selected.update(
        {
            (item["member_id"], item["nucleus"]): item
            for item in ranked
            if item["reading_priority_band"] != 0
        }
        if top == 0
        else {
            (item["member_id"], item["nucleus"]): item
            for item in [
                candidate
                for candidate in ranked
                if candidate["reading_priority_band"] != 0
            ][:top]
        }
    )
    per_nucleus: dict[str, int] = defaultdict(int)
    for item in ranked:
        nucleus = item["nucleus"]
        if per_nucleus[nucleus] >= top_per_nucleus:
            continue
        selected[(item["member_id"], nucleus)] = item
        per_nucleus[nucleus] += 1
    output = list(selected.values())
    output.sort(key=ranking_key)
    for index, item in enumerate(output, 1):
        item["reading_order"] = index
    return output


def build(args: argparse.Namespace) -> None:
    print("loading frozen nuclei and Arabic source fans", flush=True)
    core = core_rows()
    rules = {rule.row_id: rule for rule in compile_network(NETWORK)}
    samples = sample_roots()
    definitions, sources = arabic_lexica()
    nucleus_support: dict[str, tuple[str, ...]] = {}
    for nucleus in core:
        nucleus_support[nucleus] = tuple(
            root
            for root in samples.get(nucleus, ())
            if definitions.get(root) and set(sources.get(root, ())) == SOURCE_NAMES
        )

    chunk_texts: list[str] = []
    root_chunks: dict[str, list[tuple[str, int]]] = defaultdict(list)
    for root in sorted({root for roots in nucleus_support.values() for root in roots}):
        for chunk in definition_chunks(definitions[root]):
            index = len(chunk_texts)
            chunk_texts.append(chunk)
            root_chunks[root].append((chunk, index))
    nucleus_core_chunks: dict[str, int] = {}
    for nucleus in sorted(core):
        reading = nfc(core[nucleus].get("composed_reading_en") or "").strip()
        if reading:
            nucleus_core_chunks[nucleus] = len(chunk_texts)
            chunk_texts.append(reading)

    print(f"loading local ranking model: {MODEL_ID}", flush=True)
    model = SentenceTransformer(MODEL_ID, device="cpu", local_files_only=True)
    model.max_seq_length = 128
    print(f"encoding Arabic support chunks: {len(chunk_texts)}", flush=True)
    chunk_embeddings = cached_encode(
        model,
        chunk_texts,
        args.batch_size,
        "arabic-support",
    )

    payload: dict[str, Any] = {
        "schema": SCHEMA,
        "date": DATE,
        "contract": {
            "judgment": "none; semantic similarity ranks human review only",
            "comparison_unit": "first two consonants of the comparison skeleton",
            "reading_order": (
                "basic vocabulary first across all six languages; then general "
                "lexicon; derived, technical, and compound vocabulary last; "
                "inside each lexical band Arabic support roots are read hollow, "
                "geminate, other weak, then sound; this is ordering, not sampling"
            ),
            "coverage_denominator": (
                "unchanged; every member fate remains in lane_c_coverage.jsonl "
                "or an issued reading/name ledger"
            ),
            "morphology": (
                "form_of rows excluded; source-explicit affixes and Welsh "
                "mutations redirect to a base or are blocked; Greek and Latin "
                "right-edge endings are stripped before consonant counting"
            ),
            "sound": "signed rows only, except literal phoneme identity",
            "meaning": (
                "semantic neighborhood plus competing-nucleus margin; a broad "
                "or non-distinctive orbit is rejected before adjudication"
            ),
            "arabic_sources": sorted(SOURCE_NAMES),
            "loans": "loan_hint rows excluded; prior SEMITIC-SOURCE-TRANSMISSION ledger retained",
            "shared_tools": "not invoked; shared databases opened read-only",
        },
        "pins": {
            "core_sha256": sha256(CORE),
            "network_sha256": sha256(NETWORK),
            "arabic_roots_sha256": sha256(ARABIC_ROOTS),
            "ranking_model": MODEL_ID,
        },
        "frozen_nuclei_with_reading_and_two_graphemes": len(core),
        "frozen_nuclei_with_two_named_arabic_source_support": sum(
            bool(value) for value in nucleus_support.values()
        ),
        "languages": {},
    }

    for language in LANGUAGES:
        print(f"loading {language.key}", flush=True)
        entries, routes, stats = load_language(language, core, rules)
        query_texts = [entry["gloss"] for entry in entries]
        print(f"encoding {language.key}: {len(query_texts)} lexical members", flush=True)
        query_embeddings = cached_encode(
            model,
            query_texts,
            args.batch_size,
            language.key,
        )
        ranked = rank_language(
            language,
            entries,
            routes,
            core,
            nucleus_support,
            root_chunks,
            nucleus_core_chunks,
            query_embeddings,
            chunk_embeddings,
            args.top,
            args.top_per_nucleus,
        )
        cards = existing_card_ids(
            ROOT / "04-cross-linguistic" / "readings" / language.reading_file
        )
        for item in ranked:
            item["already_has_reading_card"] = item["member_id"] in cards
        payload["languages"][language.key] = {
            "label": language.label,
            "reading_file": language.reading_file,
            **stats,
            "ranked_rows_retained": len(ranked),
            "ranked_basic_rows": sum(
                item["reading_priority_band"] == 0 for item in ranked
            ),
            "ranked_distinctive_orbit_rows": sum(
                item["semantic_orbit_gate"] == "DISTINCTIVE-ORBIT-REVIEW"
                for item in ranked
            ),
            "ranked": ranked,
        }
        OUTPUT.write_text(
            nfc(json.dumps(payload, ensure_ascii=False, indent=2)) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(OUTPUT.relative_to(ROOT), flush=True)


def validate() -> None:
    payload = json.loads(OUTPUT.read_text(encoding="utf-8"))
    if payload.get("schema") != SCHEMA:
        raise RuntimeError("ranked output schema drift")
    if payload["pins"]["core_sha256"] != sha256(CORE):
        raise RuntimeError("core index drift")
    if payload["pins"]["network_sha256"] != sha256(NETWORK):
        raise RuntimeError("shift network drift")
    if set(payload["languages"]) != {item.key for item in LANGUAGES}:
        raise RuntimeError("not all six languages were ranked")
    rules = {rule.row_id: rule for rule in compile_network(NETWORK)}
    for language, block in payload["languages"].items():
        seen: set[tuple[str, str]] = set()
        previous_order_key: tuple[Any, ...] | None = None
        for row in block["ranked"]:
            key = (row["member_id"], row["nucleus"])
            if key in seen:
                raise RuntimeError(f"{language}: duplicate ranked pair {key}")
            seen.add(key)
            if len(normalize_arabic(row["nucleus"])) != 2:
                raise RuntimeError(f"{language}: non-binary nucleus {row['nucleus']}")
            if set(row["classical_sources"]) != SOURCE_NAMES:
                raise RuntimeError(f"{language}: incomplete Arabic sources {key}")
            tokens = tuple(row["comparison_tokens"])
            if not route_covers_pair(
                tokens,
                row["nucleus"],
                tuple(row["licensed_rules"]),
                rules,
            ):
                raise RuntimeError(f"{language}: incomplete signed route {key}")
            if row["status"] != "RANKED-FOR-HUMAN-ORBIT-REVIEW; NOT-A-VERDICT":
                raise RuntimeError(f"{language}: score leaked into verdict {key}")
            if row["morphology_gate"] != "STEM-PAIR-READY":
                raise RuntimeError(f"{language}: morphology-blocked row entered queue {key}")
            if row["reading_priority_label"] == "basic-vocabulary" and row["reading_priority_band"] != 0:
                raise RuntimeError(f"{language}: basic row lost priority {key}")
            expected_shape = arabic_root_shape(row["support_root"])
            actual_shape = (
                int(row["arabic_root_shape_band"]),
                row["arabic_root_shape_label"],
            )
            if actual_shape != expected_shape:
                raise RuntimeError(
                    f"{language}: Arabic root-shape priority drift {key}: "
                    f"{actual_shape!r} != {expected_shape!r}"
                )
            if row["semantic_orbit_gate"] not in {
                "DISTINCTIVE-ORBIT-REVIEW",
                "SEMANTIC-ORBIT-NOT-DISTINCTIVE",
            }:
                raise RuntimeError(f"{language}: invalid semantic orbit gate {key}")
            order_key = (
                int(row["reading_priority_band"]),
                int(row["basic_category_rank"]),
                int(row["arabic_root_shape_band"]),
                row["semantic_orbit_gate"] != "DISTINCTIVE-ORBIT-REVIEW",
                -float(row["semantic_orbit_margin"]),
                -float(row["semantic_retrieval_score"]),
                len(row["licensed_rules"]),
                int(row["source_rowid"]),
                row["member_id"],
                row["nucleus"],
            )
            if previous_order_key is not None and order_key < previous_order_key:
                raise RuntimeError(f"{language}: reading order drift at {key}")
            previous_order_key = order_key
        expected_orders = list(range(1, len(block["ranked"]) + 1))
        actual_orders = [int(row["reading_order"]) for row in block["ranked"]]
        if actual_orders != expected_orders:
            raise RuntimeError(f"{language}: non-contiguous reading order")
    if nfc(OUTPUT.read_text(encoding="utf-8")) != OUTPUT.read_text(encoding="utf-8"):
        raise RuntimeError("ranked output is not NFC")
    print("CLEAN\tlane-c nucleus reread ranking")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--build", action="store_true")
    parser.add_argument("--validate", action="store_true")
    parser.add_argument("--top", type=int, default=1600)
    parser.add_argument("--top-per-nucleus", type=int, default=12)
    parser.add_argument("--batch-size", type=int, default=256)
    args = parser.parse_args()
    if args.top < 0:
        parser.error("--top must be zero (retain all) or positive")
    if args.top_per_nucleus < 1:
        parser.error("--top-per-nucleus must be positive")
    return args


def main() -> int:
    args = parse_args()
    if args.build == args.validate:
        raise SystemExit("choose exactly one of --build or --validate")
    if args.build:
        build(args)
    else:
        validate()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
