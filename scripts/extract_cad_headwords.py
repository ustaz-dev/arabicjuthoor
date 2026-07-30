#!/usr/bin/env python3
"""Evaluate deterministic CAD headword extraction against DAL-P 1.1.

This is a structural retrieval tool. It does not issue linguistic verdicts
and it does not generalize beyond volume P. The evaluation uses the 970
stable DAL-P IDs as a multiset gold standard, while also reporting the 877
distinct published citation strings.
"""

from __future__ import annotations

import argparse
from collections import Counter, defaultdict
import hashlib
import html
import json
from pathlib import Path
import re
import tempfile
import unicodedata
from typing import Any, Callable


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_CAD = ROOT / "Data raw/Assyrian_cad/cad_p_djvu.txt"
DEFAULT_DAL = ROOT / "Resources/akkadian/dal-p-v1.1/dal-p.html"
DEFAULT_OUTPUT = (
    ROOT / "04-cross-linguistic/data/cad-p-headword-evaluation.json"
)

DAL_SECTION = re.compile(
    r'<section id="(?P<id>P(?:N\d{3}|\d{4}))"[^>]*>'
    r"(?P<body>.*?)</section>",
    re.DOTALL,
)
DAL_HEADING = re.compile(
    r'<h2 class="anchored"[^>]*>(?P<title>.*?)</h2>',
    re.DOTALL,
)
POS_PATTERN = re.compile(
    r"^(?P<citation>p.{0,100}?)\s+"
    r"(?P<pos>s\.|v\.|adj\.|adv\.|pron\.|prep\.|conj\.|interj\.|"
    r"num\.|part\.|particle|enclitic)"
    r"(?P<qualifier>[^;]{0,35});",
    re.IGNORECASE,
)
CROSS_REFERENCE = re.compile(
    r"^(?P<head>p[^,;:\[\]]{0,55}?)"
    r"(?:\s+\(AHw\.\s+\d+[ab]\))?\s+see\s+"
    r"(?P<target>[a-zʾʿ][^.;:]{0,60})\.$",
    re.IGNORECASE,
)
GRAMMATICAL_PARENTHESIS = re.compile(
    r"\((?:m|n|f|m\.|f\.|pl|pl\.|sg|sg\.|\?)\)",
    re.IGNORECASE,
)
HOMONYM_LABEL = re.compile(r"\s+(?:[A-F]|I{1,4}|V?I{0,3})$")
FINAL_CASE_M = re.compile(r"([aeiou])m$")
TRANSLITERATION_TOKEN = re.compile(
    r"^[a-zšṣṭḫāēīūâêîûʾʿ’'^/.-]+$",
    re.IGNORECASE,
)
ENTRY_START = "pa’adu v.;"
EXPECTED_DAL_IDS = {
    *(f"P{index:04d}" for index in range(1, 830)),
    *(f"PN{index:03d}" for index in range(1, 142)),
}


def digest(path: Path) -> str:
    hasher = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            hasher.update(chunk)
    return hasher.hexdigest()


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value).strip()


def compact(value: str) -> str:
    return re.sub(r"\s+", " ", nfc(value)).strip()


def strip_tags(value: str) -> str:
    return compact(html.unescape(re.sub(r"<[^>]+>", "", value)))


def dal_headword(title: str) -> str:
    """Apply the pinned overlay's published-title headword rule."""
    if " “" in title:
        return nfc(title.split(" “", 1)[0])
    cut: int | None = None
    for match in re.finditer(r"\s+\(([^)]*)\)", title):
        inner = match.group(1).strip().casefold()
        if inner not in {"m", "f", "m.", "f.", "pl", "pl.", "?"} and not re.fullmatch(
            r"[a-z]?akk", inner
        ):
            cut = match.start()
            break
    return nfc(title if cut is None else title[:cut])


def parse_dal(path: Path) -> list[dict[str, Any]]:
    source = path.read_text(encoding="utf-8")
    records: list[dict[str, Any]] = []
    for section in DAL_SECTION.finditer(source):
        heading = DAL_HEADING.search(section.group("body"))
        if heading is None:
            raise ValueError(f"DAL-P heading missing in {section.group('id')}")
        records.append(
            {
                "id": section.group("id"),
                "title": strip_tags(heading.group("title")),
                "has_cad_reference": bool(
                    re.search(
                        r"<strong>CAD</strong>",
                        section.group("body"),
                    )
                ),
            }
        )
    ids = {record["id"] for record in records}
    if ids != EXPECTED_DAL_IDS or len(records) != len(EXPECTED_DAL_IDS):
        raise ValueError(
            "DAL-P ID inventory mismatch: "
            f"records={len(records)} missing={sorted(EXPECTED_DAL_IDS - ids)} "
            f"extra={sorted(ids - EXPECTED_DAL_IDS)}"
        )
    for record in records:
        record["headword"] = dal_headword(record["title"])
    distinct = {record["headword"].casefold() for record in records}
    if len(distinct) != 877:
        raise ValueError(f"DAL-P distinct citation count mismatch: {len(distinct)}")
    cad_referenced = sum(record["has_cad_reference"] for record in records)
    if cad_referenced != 899:
        raise ValueError(
            f"DAL-P CAD-reference subset mismatch: {cad_referenced}"
        )
    return records


def plausible_citation(value: str) -> bool:
    value = compact(value)
    if not value or len(value) > 80 or not value.casefold().startswith("p"):
        return False
    if re.search(
        r"\d|=|\b(?:ibid|passim|context|section|text|report|see)\b",
        value,
        re.I,
    ):
        return False
    if value.count("(") != value.count(")"):
        return False
    first = value.split()[0].strip("(){}")
    return bool(TRANSLITERATION_TOKEN.fullmatch(first))


def primary_and_aliases(citation: str) -> tuple[str, list[str]]:
    citation = compact(citation)
    boundary = len(citation)
    for marker in ("(", "{"):
        position = citation.find(marker)
        if position >= 0:
            boundary = min(boundary, position)
    primary = compact(citation[:boundary])
    aliases: list[str] = []
    for raw in re.findall(r"[\(\{]([^)}]+)[\)}]", citation):
        raw = re.sub(r"^(?:or|also)\s+", "", compact(raw), flags=re.I)
        for item in re.split(r"\s*(?:,|\bor\b)\s*", raw):
            item = compact(item)
            if (
                item
                and len(item.split()) <= 3
                and not re.search(
                    r"\b(?:fem|fern|masc|pl|sing|mng|occ|AHw|cf)\b",
                    item,
                    re.I,
                )
                and all(
                    TRANSLITERATION_TOKEN.fullmatch(token)
                    for token in item.split()
                )
            ):
                aliases.append(item)
    return primary, sorted({nfc(alias) for alias in aliases})


def extract_cad(path: Path) -> list[dict[str, Any]]:
    lines = path.read_text(encoding="utf-8", errors="strict").splitlines()
    try:
        start = next(
            index
            for index, line in enumerate(lines)
            if line.strip().startswith(ENTRY_START)
        )
    except StopIteration as error:
        raise ValueError("CAD P dictionary entry start was not found") from error

    candidates: list[dict[str, Any]] = []
    occupied_lines: set[int] = set()
    for index in range(start, len(lines)):
        line_number = index + 1
        raw_line = compact(lines[index])
        match = POS_PATTERN.match(raw_line)
        if match is None:
            continue
        citation = compact(match.group("citation"))
        if not plausible_citation(citation):
            continue
        primary, aliases = primary_and_aliases(citation)
        candidates.append(
            {
                "candidate_id": f"cad-p-djvu:line-{line_number}",
                "line_number": line_number,
                "kind": "entry",
                "raw_line": raw_line,
                "raw_citation": citation,
                "headword": primary,
                "aliases": aliases,
                "pos": match.group("pos").casefold(),
            }
        )
        occupied_lines.add(line_number)

    for index in range(start, len(lines)):
        line_number = index + 1
        if line_number in occupied_lines:
            continue
        raw_line = compact(lines[index])
        match = CROSS_REFERENCE.match(raw_line)
        if match is None:
            continue
        citation = compact(match.group("head"))
        target = compact(match.group("target"))
        if (
            not plausible_citation(citation)
            or len(citation.split()) > 3
            or target.casefold().startswith(("s.v", "mng", "ibid"))
        ):
            continue
        primary, aliases = primary_and_aliases(citation)
        candidates.append(
            {
                "candidate_id": f"cad-p-djvu:line-{line_number}",
                "line_number": line_number,
                "kind": "cross-reference",
                "raw_line": raw_line,
                "raw_citation": citation,
                "headword": primary,
                "aliases": aliases,
                "target": target,
            }
        )

    candidates.sort(key=lambda item: (item["line_number"], item["kind"]))
    ids = [candidate["candidate_id"] for candidate in candidates]
    if len(ids) != len(set(ids)):
        raise ValueError("duplicate CAD candidate IDs")
    return candidates


def citation_base(value: str) -> str:
    value = compact(value).casefold()
    value = value.replace("’", "'").replace("ʾ", "'").replace("ʿ", "'")
    value = value.replace("^", "'")
    value = value.replace("[", "").replace("]", "")
    value = GRAMMATICAL_PARENTHESIS.sub("", value)
    value = HOMONYM_LABEL.sub("", value)
    value = unicodedata.normalize("NFKD", value)
    value = "".join(
        character
        for character in value
        if not unicodedata.combining(character)
    )
    value = value.replace("'", "")
    value = re.sub(r"[^a-z/ -]", "", value)
    return re.sub(r"\s+", " ", value).strip(" .-")


def exact_key(value: str) -> str:
    value = compact(value).casefold()
    value = value.replace("[", "").replace("]", "")
    value = GRAMMATICAL_PARENTHESIS.sub("", value)
    value = HOMONYM_LABEL.sub("", value)
    return compact(value)


def folded_key(value: str) -> str:
    return citation_base(value)


def final_m_key(value: str) -> str:
    return FINAL_CASE_M.sub(r"\1", citation_base(value))


def candidate_keys(
    candidate: dict[str, Any],
    key_function: Callable[[str], str],
    include_aliases: bool,
) -> set[str]:
    values = [candidate["headword"]]
    if include_aliases:
        values.extend(candidate["aliases"])
    return {
        key
        for value in values
        if (key := key_function(value))
    }


def maximum_matching(
    candidates: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    key_function: Callable[[str], str],
    include_aliases: bool,
) -> tuple[dict[int, int], dict[int, set[str]]]:
    gold_by_key: dict[str, list[int]] = defaultdict(list)
    for gold_index, record in enumerate(gold):
        key = key_function(record["headword"])
        if key:
            gold_by_key[key].append(gold_index)

    keys_by_candidate: dict[int, set[str]] = {}
    edges: dict[int, list[int]] = {}
    for candidate_index, candidate in enumerate(candidates):
        keys = candidate_keys(candidate, key_function, include_aliases)
        keys_by_candidate[candidate_index] = keys
        edges[candidate_index] = sorted(
            {
                gold_index
                for key in keys
                for gold_index in gold_by_key.get(key, [])
            },
            key=lambda index: gold[index]["id"],
        )

    gold_to_candidate: dict[int, int] = {}

    def augment(candidate_index: int, seen: set[int]) -> bool:
        for gold_index in edges[candidate_index]:
            if gold_index in seen:
                continue
            seen.add(gold_index)
            previous = gold_to_candidate.get(gold_index)
            if previous is None or augment(previous, seen):
                gold_to_candidate[gold_index] = candidate_index
                return True
        return False

    for candidate_index in range(len(candidates)):
        augment(candidate_index, set())
    candidate_to_gold = {
        candidate_index: gold_index
        for gold_index, candidate_index in gold_to_candidate.items()
    }
    return candidate_to_gold, keys_by_candidate


def evaluate_definition(
    name: str,
    description: str,
    candidates: list[dict[str, Any]],
    gold: list[dict[str, Any]],
    key_function: Callable[[str], str],
    include_aliases: bool,
) -> tuple[dict[str, Any], dict[int, int]]:
    matches, keys = maximum_matching(
        candidates,
        gold,
        key_function,
        include_aliases,
    )
    matched_candidates = len(matches)
    matched_gold = len(set(matches.values()))
    gold_keys = {
        key_function(record["headword"])
        for record in gold
        if key_function(record["headword"])
    }
    recovered_gold_keys = {
        key_function(gold[gold_index]["headword"])
        for gold_index in matches.values()
    }
    candidate_key_counts = Counter(
        key
        for candidate_index in range(len(candidates))
        for key in keys[candidate_index]
    )
    candidate_kind_counts = Counter(
        candidate["kind"] for candidate in candidates
    )
    matched_kind_counts = Counter(
        candidates[index]["kind"] for index in matches
    )
    result = {
        "name": name,
        "description": description,
        "metric_status": (
            "DAL-ID overlap proxy, not true extraction precision/recall"
        ),
        "includes_parenthetical_aliases": include_aliases,
        "candidate_count": len(candidates),
        "gold_id_count": len(gold),
        "gold_distinct_exact_surface_count": len(
            {record["headword"].casefold() for record in gold}
        ),
        "gold_distinct_keys_under_definition": len(gold_keys),
        "candidate_distinct_keys_under_definition": len(candidate_key_counts),
        "matched_candidate_count": matched_candidates,
        "matched_gold_id_count": matched_gold,
        "matched_candidate_fraction_against_dal_id_proxy": (
            matched_candidates / len(candidates)
        ),
        "dal_id_proxy_coverage": matched_gold / len(gold),
        "recovered_distinct_gold_key_count": len(recovered_gold_keys),
        "distinct_gold_key_proxy_coverage": (
            len(recovered_gold_keys) / len(gold_keys)
        ),
        "candidate_kind_proxy": {
            kind: {
                "candidate_count": count,
                "matched_candidate_count": matched_kind_counts[kind],
                "matched_candidate_fraction": (
                    matched_kind_counts[kind] / count
                ),
            }
            for kind, count in sorted(candidate_kind_counts.items())
        },
        "unmatched_candidate_count": len(candidates) - matched_candidates,
        "unrecovered_gold_id_count": len(gold) - matched_gold,
    }
    return result, matches


def build_evaluation(cad_path: Path, dal_path: Path) -> dict[str, Any]:
    gold = parse_dal(dal_path)
    candidates = extract_cad(cad_path)
    definitions = [
        (
            "exact-primary",
            "NFC casefolded primary citation; grammatical parentheses and "
            "CAD homonym labels removed; transliteration distinctions retained.",
            exact_key,
            False,
        ),
        (
            "folded-primary",
            "Primary citation only; vowel length, subscript diacritics, "
            "emphatic marks, and glottal marks folded because the legacy OCR "
            "usually omits them.",
            folded_key,
            False,
        ),
        (
            "folded-primary-final-m",
            "Folded primary citation with a final case m removed only after a "
            "vowel.",
            final_m_key,
            False,
        ),
        (
            "folded-alias-final-m",
            "Operational definition: folded primary citation plus explicitly "
            "printed parenthetical citation aliases, with final case m "
            "removed only after a vowel.",
            final_m_key,
            True,
        ),
    ]
    metrics: list[dict[str, Any]] = []
    operational_matches: dict[int, int] = {}
    for name, description, function, include_aliases in definitions:
        result, matches = evaluate_definition(
            name,
            description,
            candidates,
            gold,
            function,
            include_aliases,
        )
        metrics.append(result)
        if name == "folded-alias-final-m":
            operational_matches = matches

    proxy_candidate_threshold = 0.95
    proxy_dal_threshold = 0.90
    true_precision_threshold = 0.99
    true_recall_threshold = 0.97
    operational = next(
        item for item in metrics if item["name"] == "folded-alias-final-m"
    )
    cad_referenced_gold = [
        record for record in gold if record["has_cad_reference"]
    ]
    cad_subset_metric, _ = evaluate_definition(
        "folded-alias-final-m-cad-referenced-subset",
        "The operational proxy restricted to the 899 DAL IDs whose article "
        "contains a named CAD reference.",
        candidates,
        cad_referenced_gold,
        final_m_key,
        True,
    )
    proxy_pass_threshold = (
        operational["matched_candidate_fraction_against_dal_id_proxy"]
        >= proxy_candidate_threshold
        and operational["dal_id_proxy_coverage"] >= proxy_dal_threshold
    )
    local_cad_pdf_paths = sorted(cad_path.parent.rglob("*.pdf"))
    manual_gold_available = False
    pass_threshold = proxy_pass_threshold and manual_gold_available

    rendered_candidates: list[dict[str, Any]] = []
    for index, candidate in enumerate(candidates):
        item = dict(candidate)
        gold_index = operational_matches.get(index)
        item["operational_match"] = (
            None
            if gold_index is None
            else {
                "dal_id": gold[gold_index]["id"],
                "dal_headword": gold[gold_index]["headword"],
                "dal_title": gold[gold_index]["title"],
            }
        )
        rendered_candidates.append(item)

    matched_gold_indices = set(operational_matches.values())
    return {
        "schema": "cad-p-headword-extraction-evaluation-v1",
        "generated_on": "2026-07-25",
        "purpose": (
            "Structural retrieval evaluation only; no linguistic judgments "
            "and no claim of full CAD extraction."
        ),
        "sources": {
            "cad_p_djvu": {
                "path": str(cad_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": cad_path.stat().st_size,
                "sha256": digest(cad_path),
            },
            "dal_p_1_1": {
                "path": str(dal_path.relative_to(ROOT)).replace("\\", "/"),
                "bytes": dal_path.stat().st_size,
                "sha256": digest(dal_path),
                "stable_id_count": len(gold),
                "stable_ids_with_named_cad_reference": sum(
                    record["has_cad_reference"] for record in gold
                ),
                "stable_ids_without_named_cad_reference": sum(
                    not record["has_cad_reference"] for record in gold
                ),
                "distinct_exact_surface_count": len(
                    {record["headword"].casefold() for record in gold}
                ),
            },
        },
        "extraction": {
            "candidate_count": len(candidates),
            "entry_header_count": sum(
                candidate["kind"] == "entry" for candidate in candidates
            ),
            "cross_reference_count": sum(
                candidate["kind"] == "cross-reference"
                for candidate in candidates
            ),
            "identity_rule": "candidate ID is the immutable djvu line number",
            "duplicates_by_candidate_id": 0,
        },
        "matching_definitions": metrics,
        "cad_referenced_subset_operational_proxy": cad_subset_metric,
        "generalization_gate": {
            "operational_definition": "folded-alias-final-m",
            "minimum_candidate_match_fraction_proxy": proxy_candidate_threshold,
            "minimum_dal_id_proxy_coverage": proxy_dal_threshold,
            "proxy_threshold_passed": proxy_pass_threshold,
            "manual_page_gold_required": True,
            "manual_page_gold_available": manual_gold_available,
            "manual_page_gold_source_status": (
                "local-cad-pdf-present-but-gold-not-built"
                if local_cad_pdf_paths
                else "source-gap-no-local-cad-pdf"
            ),
            "local_cad_pdf_paths": [
                str(path.relative_to(ROOT)).replace("\\", "/")
                for path in local_cad_pdf_paths
            ],
            "source_decision_required": (
                "Name an existing local CAD PDF path or authorize downloading "
                "the free ISAC CAD PDFs before manual page gold is built."
            ),
            "minimum_manual_gold_occurrences": 300,
            "minimum_manual_gold_cross_references": 50,
            "minimum_manual_gold_edge_cases": 50,
            "minimum_true_precision_on_manual_page_gold": (
                true_precision_threshold
            ),
            "minimum_true_recall_on_manual_page_gold": (
                true_recall_threshold
            ),
            "maximum_known_running_head_or_continuation_leaks": 0,
            "passed": pass_threshold,
            "decision": (
                "eligible-for-all-volume-pilot"
                if pass_threshold
                else "blocked-no-generalization"
            ),
            "note": (
                "DAL-P is not a gold transcription of CAD headings: 71 IDs "
                "have no named CAD reference, some DAL IDs represent forms "
                "inside a CAD article, and CAD cross-references are not all "
                "independent DAL citations. Therefore DAL overlap is coverage "
                "proxy only. True precision and recall require a manually "
                "labelled sample of printed CAD heading pages. Passing both "
                "parts permits only an all-volume pilot and does not make "
                "extracted strings citable without source verification."
            ),
        },
        "candidates": rendered_candidates,
        "unrecovered_dal_ids_under_operational_definition": [
            gold[index]
            for index in range(len(gold))
            if index not in matched_gold_indices
        ],
    }


def atomic_write(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        delete=False,
        dir=path.parent,
    ) as handle:
        handle.write(content)
        temporary = Path(handle.name)
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--cad", type=Path, default=DEFAULT_CAD)
    parser.add_argument("--dal", type=Path, default=DEFAULT_DAL)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    evaluation = build_evaluation(args.cad, args.dal)
    rendered = json.dumps(
        evaluation,
        ensure_ascii=False,
        indent=2,
        sort_keys=True,
    ) + "\n"
    if args.check:
        if not args.output.is_file():
            raise SystemExit(f"missing evaluation output: {args.output}")
        if args.output.read_text(encoding="utf-8") != rendered:
            raise SystemExit(f"stale evaluation output: {args.output}")
        print(
            json.dumps(
                {
                    "check": "CLEAN",
                    "candidate_count": evaluation["extraction"][
                        "candidate_count"
                    ],
                    "generalization_gate": evaluation[
                        "generalization_gate"
                    ],
                },
                ensure_ascii=False,
            )
        )
        return 0

    atomic_write(args.output, rendered)
    print(
        json.dumps(
            {
                "written": str(args.output),
                "candidate_count": evaluation["extraction"]["candidate_count"],
                "matching_definitions": evaluation["matching_definitions"],
                "generalization_gate": evaluation["generalization_gate"],
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
