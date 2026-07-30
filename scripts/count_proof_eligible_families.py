#!/usr/bin/env python3
"""Count proof-eligible Aramaic and Hebrew families from the reading files.

The preregistration defines a strict member-completeness denominator. A family
counts only when every inventory member has an issued verdict or a recorded
terminal closure. A family-level positive never propagates to unnamed members.

The ignored working inventory is used only to refresh a committed, fingerprinted
population snapshot. Normal builds and CI read that snapshot and the two reading
files, so the official count is reproducible without the local SQLite cache.

Usage:
  python scripts/count_proof_eligible_families.py --refresh-population
  python scripts/count_proof_eligible_families.py
  python scripts/count_proof_eligible_families.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
PREREGISTRATION = ROOT / "data" / "recovery-proof-preregistration.json"
POPULATION = ROOT / "data" / "proof-family-population.json"
REPORT = ROOT / "data" / "proof-eligible-families.json"
FAMILY_STATES = ROOT / "data" / "family-review-states.json"
DATABASE = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
READINGS = {
    "aramaic": ROOT / "04-cross-linguistic" / "readings" / "aramaic.md",
    "hebrew": ROOT / "04-cross-linguistic" / "readings" / "hebrew.md",
}

POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}
TERMINAL_CLOSURES = {
    "NO-TRACE",
    "LOANWORD",
    "PROPER-NAME-ISOLATED",
    "NONLEXICAL-ISOLATED",
    "MIXED-ISOLATED",
    "FORM-OF-ISOLATED",
    "INTRA-HOUSE-TRANSFER",
    "COMPOUND-BOUNDARY",
    "LOAN-ROUTE-ISOLATED",
    "PHRASE-LINK",
    "FUNCTION-WORD",
    "CONTACT-ISOLATED",
    "OUT-OF-SCOPE",
    "ABBREVIATION",
}
PARKED_STATES = {
    "SOURCE-GAP",
    "TOOL-GAP",
    "MORPHOLOGY-GAP",
    "LAW-GAP",
    "OPEN-CANDIDATE",
}
FINAL_STATES = POSITIVE_VERDICTS | TERMINAL_CLOSURES

# These closures dispose a member but do not turn a family made solely of
# excluded material into an original lexical family in the primary population.
EXCLUDED_MEMBER_CLOSURES = TERMINAL_CLOSURES - {"NO-TRACE"}

CARD_HEADING = re.compile(
    r"^### (?:بطاقة|مراجعة عضوية|إعادةُ توسيم).*$",
    re.MULTILINE,
)
FAMILY_ID = re.compile(r"(?:aramaic|hebrew):family:[0-9a-f]+")
ENTRY_ID = re.compile(r"kaikki_(?:aramaic|hebrew):[^`\s،؛\]\)\.]+")
MEMBER_LINE = re.compile(
    r"^- العضو:\s*`(?P<entry>kaikki_(?:aramaic|hebrew):[^`]+)`"
    r"(?P<body>.*)$",
    re.MULTILINE,
)
LIVE_FIELD = re.compile(
    r"^-\s*(?:الحكم[^\n]*?|حالةُ الإغلاق|عائق):(?P<body>.*)$",
    re.MULTILINE,
)
SOURCE_REFERENCE = re.compile(
    r"Kaikki\s+(?:Aramaic|Hebrew)[^0-9\n]{0,50}"
    r"(?:الأسطر|السطر|المداخل|المدخلين|المدخل)\s+"
    r"(?P<start>[0-9]+)(?:\s*[-]\s*(?P<end>[0-9]+))?"
)
WESTERN_NUMBER = re.compile(r"(?<![0-9])[0-9]+(?![0-9])")
OUTCOME_TOKEN = re.compile(
    r"\b("
    + "|".join(
        sorted(
            FINAL_STATES | PARKED_STATES | {"READY", "REFERRED", "REFER-EXISTING"},
            key=len,
            reverse=True,
        )
    )
    + r")\b"
)


def read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def stable_json(payload: object) -> str:
    return json.dumps(payload, ensure_ascii=False, indent=1, sort_keys=False) + "\n"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    normalized = unicodedata.normalize("NFC", text)
    with tempfile.NamedTemporaryFile(
        "w",
        encoding="utf-8",
        newline="\n",
        dir=path.parent,
        delete=False,
    ) as handle:
        handle.write(normalized)
        temporary = Path(handle.name)
    temporary.replace(path)


def population_from_database() -> dict[str, Any]:
    if not DATABASE.exists():
        raise FileNotFoundError(
            "local family inventory is absent; refresh-families before refreshing "
            "the proof population snapshot"
        )
    preregistration = read_json(PREREGISTRATION)
    connection = sqlite3.connect(f"file:{DATABASE}?mode=ro", uri=True)
    connection.row_factory = sqlite3.Row
    try:
        metadata = {
            row["key"]: row["value"]
            for row in connection.execute("SELECT key,value FROM meta ORDER BY key")
        }
        languages: dict[str, Any] = {}
        for language in READINGS:
            families = []
            family_rows = connection.execute(
                """
                SELECT family_id,anchor_headword,construction,member_count,
                       lemma_count,form_count,nonlexical_count
                FROM families
                WHERE language=?
                ORDER BY family_id
                """,
                (language,),
            ).fetchall()
            member_rows: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for row in connection.execute(
                """
                SELECT fm.family_id,fm.entry_id,fm.role,e.headword,e.romanization,
                       e.pos,e.gloss,e.processing_status
                FROM family_members AS fm
                JOIN entries AS e ON e.entry_id=fm.entry_id
                WHERE e.language=?
                ORDER BY fm.family_id,fm.entry_id
                """,
                (language,),
            ):
                member_rows[row["family_id"]].append(
                    {
                        "entry_id": row["entry_id"],
                        "role": row["role"],
                        "headword": row["headword"],
                        "pos": row["pos"],
                        "gloss": row["gloss"],
                    }
                )
            for row in family_rows:
                members = member_rows[row["family_id"]]
                if len(members) != row["member_count"]:
                    raise ValueError(
                        f"{row['family_id']}: member count differs from inventory"
                    )
                families.append(
                    {
                        "family_id": row["family_id"],
                        "anchor_headword": row["anchor_headword"],
                        "member_count": row["member_count"],
                        "members": members,
                    }
                )
            languages[language] = {
                "family_metadata_version": metadata.get(
                    f"family_metadata_version:{language}", ""
                ),
                "family_count": len(families),
                "member_count": sum(item["member_count"] for item in families),
                "families": families,
            }
    finally:
        connection.close()

    return {
        "schema_version": 1,
        "generated_by": "scripts/count_proof_eligible_families.py --refresh-population",
        "contract": {
            "structural_only": True,
            "verdicts_copied": False,
            "family_membership_source": "cache/recovery_pipeline/inventory-v5.sqlite",
            "normal_count_does_not_require_local_cache": True,
        },
        "inventory": {
            "path": "cache/recovery_pipeline/inventory-v5.sqlite",
            "sha256": sha256_file(DATABASE),
            "schema_version": metadata.get("schema_version", ""),
        },
        "source_snapshots": preregistration["population"]["source_snapshots"],
        "languages": languages,
    }


def validate_population(population: dict[str, Any]) -> None:
    if population.get("schema_version") != 1:
        raise ValueError("unsupported proof population snapshot")
    preregistration = read_json(PREREGISTRATION)
    expected_sources = preregistration["population"]["source_snapshots"]
    if population.get("source_snapshots") != expected_sources:
        raise ValueError(
            "proof population source fingerprints differ from preregistration"
        )
    for language in READINGS:
        block = population.get("languages", {}).get(language)
        if not isinstance(block, dict) or not isinstance(block.get("families"), list):
            raise ValueError(f"proof population lacks {language}")
        family_ids: set[str] = set()
        entry_ids: set[str] = set()
        for family in block["families"]:
            family_id = family.get("family_id", "")
            if family_id in family_ids:
                raise ValueError(f"duplicate family in proof population: {family_id}")
            family_ids.add(family_id)
            members = family.get("members", [])
            if len(members) != family.get("member_count"):
                raise ValueError(f"{family_id}: stale member count")
            for member in members:
                entry_id = member.get("entry_id", "")
                if entry_id in entry_ids:
                    raise ValueError(
                        f"entry appears in two proof families: {entry_id}"
                    )
                entry_ids.add(entry_id)


def card_blocks(text: str) -> list[tuple[int, str]]:
    headings = list(CARD_HEADING.finditer(text))
    output = []
    for index, heading in enumerate(headings):
        end = headings[index + 1].start() if index + 1 < len(headings) else len(text)
        output.append(
            (
                text.count("\n", 0, heading.start()) + 1,
                text[heading.start():end].rstrip(),
            )
        )
    return output


def source_row(entry_id: str) -> int | None:
    match = re.match(r"kaikki_(?:aramaic|hebrew):([0-9]+):", entry_id)
    return int(match.group(1)) if match else None


def outcome_from_tail(text: str) -> str:
    tokens = [match.group(1) for match in OUTCOME_TOKEN.finditer(text)]
    for token in tokens:
        if token in FINAL_STATES:
            return token
    for token in tokens:
        if token in PARKED_STATES:
            return token
    return tokens[0] if tokens else ""


def segment_targets(
    segment: str,
    family_members: list[dict[str, Any]],
    entry_lookup: dict[str, tuple[str, dict[str, Any]]],
) -> set[str]:
    family_entry_ids = {member["entry_id"] for member in family_members}
    targets = {
        entry_id
        for entry_id in ENTRY_ID.findall(segment)
        if entry_id in family_entry_ids
    }
    if targets:
        return targets

    by_row = {
        row: member["entry_id"]
        for member in family_members
        if (row := source_row(member["entry_id"])) is not None
    }
    if any(
        marker in segment
        for marker in ("المدخل", "المدخلين", "الأسطر", "السطر")
    ):
        for number in WESTERN_NUMBER.findall(segment):
            row = int(number)
            if row in by_row:
                targets.add(by_row[row])
    return targets


def resolve_block_family(
    block: str,
    family_lookup: dict[str, dict[str, Any]],
    entry_lookup: dict[str, tuple[str, dict[str, Any]]],
    row_lookup: dict[int, set[str]],
) -> tuple[str | None, str]:
    heading = block.splitlines()[0]
    heading_family = FAMILY_ID.search(heading)
    if heading_family and heading_family.group(0) in family_lookup:
        return heading_family.group(0), "current-heading"

    candidates = {
        entry_lookup[entry_id][0]
        for entry_id in ENTRY_ID.findall(block)
        if entry_id in entry_lookup
    }
    for citation in SOURCE_REFERENCE.finditer(block):
        start = int(citation.group("start"))
        end = int(citation.group("end") or start)
        if end >= start and end - start <= 100:
            for row in range(start, end + 1):
                candidates.update(row_lookup.get(row, set()))
    if len(candidates) == 1:
        return next(iter(candidates)), "stable-entry-reconciled"
    if len(candidates) > 1:
        return None, "ambiguous-stale-heading"
    return None, "unmapped-stale-heading"


def build_report(population: dict[str, Any]) -> dict[str, Any]:
    validate_population(population)
    preregistration = read_json(PREREGISTRATION)
    thresholds = preregistration["execution_trigger"]["thresholds"]
    language_reports: dict[str, Any] = {}
    total_eligible = 0

    for language, reading_path in READINGS.items():
        family_list = population["languages"][language]["families"]
        family_lookup = {item["family_id"]: item for item in family_list}
        entry_lookup: dict[str, tuple[str, dict[str, Any]]] = {}
        row_lookup: dict[int, set[str]] = defaultdict(set)
        for family in family_list:
            for member in family["members"]:
                entry_id = member["entry_id"]
                entry_lookup[entry_id] = (family["family_id"], member)
                row = source_row(entry_id)
                if row is not None:
                    row_lookup[row].add(family["family_id"])

        text = reading_path.read_text(encoding="utf-8")
        dispositions: dict[str, dict[str, Any]] = {}
        represented: set[str] = set()
        reconciliation_counts: Counter[str] = Counter()
        ambiguous_blocks: list[dict[str, Any]] = []

        def record(
            entry_id: str,
            outcome: str,
            line: int,
            evidence: str,
            family_id: str,
        ) -> None:
            if outcome not in FINAL_STATES | PARKED_STATES:
                return
            dispositions[entry_id] = {
                "outcome": outcome,
                "final": outcome in FINAL_STATES,
                "family_id": family_id,
                "line": line,
                "evidence": evidence.strip()[:500],
            }

        for block_line, block in card_blocks(text):
            family_id, reconciliation = resolve_block_family(
                block, family_lookup, entry_lookup, row_lookup
            )
            reconciliation_counts[reconciliation] += 1
            if family_id is None:
                if len(ambiguous_blocks) < 100:
                    ambiguous_blocks.append(
                        {
                            "line": block_line,
                            "heading": block.splitlines()[0],
                            "reason": reconciliation,
                        }
                    )
                continue
            represented.add(family_id)
            family = family_lookup[family_id]
            members = family["members"]

            for match in MEMBER_LINE.finditer(block):
                entry_id = match.group("entry")
                if entry_id not in entry_lookup:
                    continue
                if entry_lookup[entry_id][0] != family_id:
                    continue
                result_tail = match.group("body").split("النتيجة:", 1)
                if len(result_tail) != 2:
                    continue
                outcome = outcome_from_tail(result_tail[1])
                record(
                    entry_id,
                    outcome,
                    block_line + block.count("\n", 0, match.start()),
                    match.group(0),
                    family_id,
                )

            for match in LIVE_FIELD.finditer(block):
                field_line = match.group(0)
                body = match.group("body")
                # A mixed live field can name a positive for some members and
                # leave another member explicitly unresolved. Process every
                # semicolon-delimited clause independently.
                inherited_outcome = ""
                for segment in re.split(r"[؛;]", body):
                    outcome = outcome_from_tail(segment)
                    explicit_nonissue = False
                    if outcome in FINAL_STATES | PARKED_STATES:
                        inherited_outcome = outcome
                    elif "غير صادر" in segment:
                        outcome = "OPEN-CANDIDATE"
                        explicit_nonissue = True
                    else:
                        outcome = inherited_outcome
                    if outcome not in FINAL_STATES | PARKED_STATES:
                        continue
                    targets = segment_targets(segment, members, entry_lookup)
                    # "غير صادر لسائر الأسرة" is a scope guard, not a
                    # revocation of the named singleton's verdict. A nonissue
                    # clause can override only a member it identifies.
                    if (
                        not targets
                        and len(members) == 1
                        and not explicit_nonissue
                    ):
                        targets = {members[0]["entry_id"]}
                    for entry_id in targets:
                        record(
                            entry_id,
                            outcome,
                            block_line + block.count("\n", 0, match.start()),
                            field_line,
                            family_id,
                        )

        eligible_family_ids: list[str] = []
        positive_family_ids: list[str] = []
        closure_family_ids: list[str] = []
        fully_disposed_excluded: list[str] = []
        one_member_short: list[dict[str, Any]] = []
        incomplete_family_queue: list[dict[str, Any]] = []
        incompleteness: Counter[str] = Counter()
        issued_member_outcomes: Counter[str] = Counter()

        for family_id in sorted(represented):
            family = family_lookup[family_id]
            members = family["members"]
            missing = []
            final_outcomes = []
            for member in members:
                disposition = dispositions.get(member["entry_id"])
                if disposition and disposition["final"]:
                    final_outcomes.append(disposition["outcome"])
                    issued_member_outcomes[disposition["outcome"]] += 1
                else:
                    missing.append(member)
                    state = (
                        disposition["outcome"] if disposition else "UNRECORDED"
                    )
                    incompleteness[state] += 1
            if not missing:
                original_outcomes = [
                    outcome
                    for outcome in final_outcomes
                    if outcome not in EXCLUDED_MEMBER_CLOSURES
                ]
                if not original_outcomes:
                    fully_disposed_excluded.append(family_id)
                    continue
                eligible_family_ids.append(family_id)
                if any(outcome in POSITIVE_VERDICTS for outcome in original_outcomes):
                    positive_family_ids.append(family_id)
                else:
                    closure_family_ids.append(family_id)
            else:
                missing_rows = []
                for member in missing:
                    disposition = dispositions.get(member["entry_id"])
                    missing_rows.append(
                        {
                            "entry_id": member["entry_id"],
                            "headword": member["headword"],
                            "pos": member["pos"],
                            "gloss": member["gloss"],
                            "current_state": (
                                disposition["outcome"]
                                if disposition
                                else "UNRECORDED"
                            ),
                            "reading_line": (
                                disposition["line"] if disposition else None
                            ),
                        }
                    )
                incomplete_family_queue.append(
                    {
                        "family_id": family_id,
                        "anchor_headword": family["anchor_headword"],
                        "member_count": family["member_count"],
                        "missing_member_count": len(missing_rows),
                        "missing_members": missing_rows,
                    }
                )
                if len(missing) == 1:
                    member = missing[0]
                    disposition = dispositions.get(member["entry_id"])
                    one_member_short.append(
                        {
                            "family_id": family_id,
                            "anchor_headword": family["anchor_headword"],
                            "member_count": family["member_count"],
                            "missing_entry_id": member["entry_id"],
                            "missing_headword": member["headword"],
                            "missing_pos": member["pos"],
                            "missing_gloss": member["gloss"],
                            "current_state": (
                                disposition["outcome"]
                                if disposition
                                else "UNRECORDED"
                            ),
                            "reading_line": (
                                disposition["line"] if disposition else None
                            ),
                        }
                    )

        one_member_short.sort(
            key=lambda item: (
                item["current_state"] == "UNRECORDED",
                item["family_id"],
            )
        )
        incomplete_family_queue.sort(
            key=lambda item: (
                item["missing_member_count"],
                item["family_id"],
            )
        )
        eligible = len(eligible_family_ids)
        total_eligible += eligible
        language_reports[language] = {
            "inventory_family_count": len(family_list),
            "represented_current_family_count": len(represented),
            "eligible_family_count": eligible,
            "positive_family_count": len(positive_family_ids),
            "closure_only_family_count": len(closure_family_ids),
            "fully_disposed_but_population_excluded_count": len(
                fully_disposed_excluded
            ),
            "one_member_short_count": len(one_member_short),
            "issued_member_dispositions": {
                "positive": sum(
                    count
                    for outcome, count in issued_member_outcomes.items()
                    if outcome in POSITIVE_VERDICTS
                ),
                "closures": sum(
                    count
                    for outcome, count in issued_member_outcomes.items()
                    if outcome in TERMINAL_CLOSURES
                ),
                "by_outcome": dict(sorted(issued_member_outcomes.items())),
            },
            "incomplete_members_by_state": dict(
                sorted(incompleteness.items())
            ),
            "block_reconciliation": dict(sorted(reconciliation_counts.items())),
            "eligible_family_ids": eligible_family_ids,
            "positive_family_ids": positive_family_ids,
            "closure_only_family_ids": closure_family_ids,
            "fully_disposed_but_population_excluded_ids": (
                fully_disposed_excluded
            ),
            "one_member_short": one_member_short,
            "incomplete_family_queue": incomplete_family_queue,
            "ambiguous_or_unmapped_blocks": ambiguous_blocks,
        }

    per_language_minimum_met = all(
        language_reports[language]["eligible_family_count"]
        >= thresholds["min_eligible_reviewed_families_per_language"]
        for language in READINGS
    )
    total_met = total_eligible >= thresholds["total_eligible_reviewed_families"]
    return {
        "schema_version": 1,
        "generated_by": "scripts/count_proof_eligible_families.py",
        "contract": {
            "definition": (
                "A family counts only when every inventory member has an "
                "issued verdict or recorded terminal closure."
            ),
            "family_positive_does_not_propagate_to_unnamed_members": True,
            "parked_states_are_not_final": sorted(PARKED_STATES),
            "reading_live_fields_only": True,
            "historical_appendices_do_not_revive_a_card": True,
            "proof_executed": False,
        },
        "inputs": {
            "preregistration": {
                "path": PREREGISTRATION.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(PREREGISTRATION),
                "version": preregistration["version"],
                "status": preregistration["status"],
            },
            "population": {
                "path": POPULATION.relative_to(ROOT).as_posix(),
                "sha256": sha256_file(POPULATION),
            },
            "readings": {
                language: {
                    "path": path.relative_to(ROOT).as_posix(),
                    "sha256": sha256_file(path),
                }
                for language, path in READINGS.items()
            },
        },
        "thresholds": thresholds,
        "summary": {
            "eligible_family_total": total_eligible,
            "required_total": thresholds["total_eligible_reviewed_families"],
            "required_per_language": thresholds[
                "min_eligible_reviewed_families_per_language"
            ],
            "total_threshold_met": total_met,
            "per_language_minimum_met": per_language_minimum_met,
            "trigger_threshold_met": total_met and per_language_minimum_met,
            "proof_executed": False,
        },
        "languages": language_reports,
    }


def mirror_payload(
    family_states: dict[str, Any], report: dict[str, Any]
) -> dict[str, Any]:
    output = json.loads(json.dumps(family_states, ensure_ascii=False))
    output["proof_counter"] = {
        "schema_version": 1,
        "generated_by": "scripts/count_proof_eligible_families.py",
        "report_path": REPORT.relative_to(ROOT).as_posix(),
        "report_sha256": sha256_bytes(stable_json(report).encode("utf-8")),
        "summary": report["summary"],
        "languages": {
            language: {
                "eligible_family_count": block["eligible_family_count"],
                "positive_family_count": block["positive_family_count"],
                "closure_only_family_count": block["closure_only_family_count"],
                "one_member_short_count": block["one_member_short_count"],
                "eligible_family_ids": block["eligible_family_ids"],
            }
            for language, block in report["languages"].items()
        },
    }
    return output


def print_summary(report: dict[str, Any]) -> None:
    for language in READINGS:
        row = report["languages"][language]
        dispositions = row["issued_member_dispositions"]
        print(
            f"{language}: eligible={row['eligible_family_count']}; "
            f"positive-members={dispositions['positive']}; "
            f"closure-members={dispositions['closures']}; "
            f"one-member-short={row['one_member_short_count']}"
        )
    summary = report["summary"]
    print(
        f"official eligible denominator: "
        f"{summary['eligible_family_total']} / {summary['required_total']}"
    )
    print(
        "trigger threshold met: "
        + ("yes" if summary["trigger_threshold_met"] else "no")
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--refresh-population", action="store_true")
    args = parser.parse_args()

    if args.check and args.refresh_population:
        parser.error("--check and --refresh-population are mutually exclusive")

    if args.refresh_population:
        population = population_from_database()
        atomic_write(POPULATION, stable_json(population))
        print(
            f"wrote {POPULATION.relative_to(ROOT)}: "
            + ", ".join(
                f"{language}={block['family_count']} families"
                for language, block in population["languages"].items()
            )
        )
    if not POPULATION.exists():
        raise FileNotFoundError(
            "data/proof-family-population.json is absent; use "
            "--refresh-population with the local inventory"
        )

    population = read_json(POPULATION)
    report = build_report(population)
    rendered_report = stable_json(report)
    family_states = read_json(FAMILY_STATES)
    mirrored = mirror_payload(family_states, report)
    rendered_states = (
        json.dumps(mirrored, ensure_ascii=False, indent=2, sort_keys=False) + "\n"
    )

    if args.check:
        failures = []
        if not REPORT.exists() or REPORT.read_text(encoding="utf-8") != rendered_report:
            failures.append("data/proof-eligible-families.json is stale")
        if FAMILY_STATES.read_text(encoding="utf-8") != rendered_states:
            failures.append("data/family-review-states.json proof mirror is stale")
        if failures:
            for failure in failures:
                print(f"STALE: {failure}")
            return 1
        print_summary(report)
        print("CLEAN: proof eligibility count and family-state mirror are current")
        return 0

    atomic_write(REPORT, rendered_report)
    atomic_write(FAMILY_STATES, rendered_states)
    print_summary(report)
    print(f"wrote {REPORT.relative_to(ROOT)}")
    print(f"mirrored count into {FAMILY_STATES.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
