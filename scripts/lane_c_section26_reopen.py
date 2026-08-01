#!/usr/bin/env python3
"""Apply section 26 to lane C's six Indo-European readings.

The source inventories and Arabic source table are read-only.  Writes are
limited to lane-C-owned readings, lane-C-prefixed data, and a lane-C audit.
No Git command, shared builder, shared script, or proof-line tool is invoked.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

import pyarrow.parquet as pq

from lane_c_section26_rules import named_donor, self_test as rules_self_test


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
COVERAGE = DATA / "lane_c_coverage.jsonl"
NAMES = DATA / "lane_c_names_inventory.jsonl"
MORPH_QUEUE = DATA / "lane_c_morphology_queue.jsonl"
AUDIT = ROOT / "05-audits" / "lane-c-2026-07-30-section26-reopening.md"
ARABIC_ROOTS = (
    ROOT
    / "Resources"
    / "arabic_roots_hf"
    / "train-00000-of-00001.parquet"
)
DATE = "2026-07-30"
READING_MARKER = "LANE-C-SECTION26-REOPENING-2026-07-30"

COVERAGE_FIELDS = (
    "member_id",
    "language",
    "form",
    "branch_meaning",
    "non_issuance_reason",
    "batch_number",
)
NAME_FIELDS = (
    "member_id",
    "language",
    "name",
    "branch_meaning",
    "root_status",
    "published_root_or_components",
    "arabic_root_candidates",
    "source",
    "statistical_denominator",
)
MORPH_FIELDS = (
    "language",
    "source_db",
    "total_form_records",
    "proper_name_forms_routed_to_names",
    "discovery_form_records",
    "already_recorded",
    "referral_eligible",
    "void_closure_prevented",
    "nonlexical_priority",
    "pending",
    "first_pending_member_id",
    "last_pending_member_id",
    "queue_order",
)

ENTRY_RE = re.compile(
    r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
    r"\d+:[^`\s\]]+"
)
CARD_RE = re.compile(
    r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^## |^<!-- /|\Z)"
)
FUNCTION_POS = {
    "article",
    "conj",
    "conjunction",
    "det",
    "determiner",
    "intj",
    "num",
    "numeral",
    "particle",
    "postp",
    "prep",
    "pron",
    "pronoun",
}
BAD_FORM_POS = {
    "abbrev",
    "character",
    "circumfix",
    "infix",
    "interfix",
    "letter",
    "phrase",
    "prefix",
    "punct",
    "romanization",
    "suffix",
    "symbol",
}
OPEN_VERDICTS = {
    "",
    "غير صادر",
    "لا حكم",
}


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


def nfc(value: str | None) -> str:
    return unicodedata.normalize("NFC", value or "")


def compact(value: str | None, limit: int | None = None) -> str:
    result = " ".join(nfc(value).replace("—", "،").split())
    if limit is not None and len(result) > limit:
        return result[: limit - 1].rstrip() + "…"
    return result


def chunks(values: list[str], size: int = 450) -> Iterable[list[str]]:
    for start in range(0, len(values), size):
        yield values[start : start + size]


def ro_connection(relative: str) -> sqlite3.Connection:
    path = (ROOT / relative).resolve()
    connection = sqlite3.connect(
        f"file:{path.as_posix()}?mode=ro&immutable=1",
        uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def source_ordinal(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else 10**18


def card_identity(card: str) -> str:
    branch = re.search(r"(?m)^- الكلمةُ في الفرع:.*$", card)
    if branch is None:
        return ""
    matches = ENTRY_RE.findall(branch.group(0))
    return nfc(matches[0]) if matches else ""


def card_verdict(card: str) -> str:
    match = re.search(r"(?m)^- الحكم \(استكشاف\):\s*(.+)$", card)
    return compact(match.group(1)).rstrip(".") if match else ""


def parse_cards(text: str) -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    for match in CARD_RE.finditer(text):
        card = match.group(0)
        entry_id = card_identity(card)
        if not entry_id:
            continue
        result.append(
            {
                "start": match.start(),
                "end": match.end(),
                "text": card,
                "entry_id": entry_id,
                "verdict": card_verdict(card),
            }
        )
    return result


def issued_verdict(verdict: str) -> bool:
    cleaned = compact(verdict).rstrip(".")
    if cleaned in OPEN_VERDICTS:
        return False
    if "موقوف" in cleaned or "لا NO-TRACE" in cleaned:
        return False
    return True


def load_metadata(
    connection: sqlite3.Connection,
    entry_ids: list[str],
) -> dict[str, dict[str, Any]]:
    result: dict[str, dict[str, Any]] = {}
    for id_chunk in chunks(entry_ids):
        marks = ",".join("?" for _ in id_chunk)
        rows = connection.execute(
            f"""
            SELECT entry_id, headword, romanization, pos, gloss, etymology,
                   form_of, alternative_of, form_targets_json,
                   alternative_targets_json, form_resolution_status,
                   licensed_candidate_count
            FROM entries
            WHERE entry_id IN ({marks})
            """,
            id_chunk,
        ).fetchall()
        for row in rows:
            result[nfc(row["entry_id"])] = dict(row)
    return result


def analyze_reading(
    language: Language,
) -> dict[str, Any]:
    path = READINGS / language.reading_file
    text = path.read_text(encoding="utf-8")
    if READING_MARKER in text:
        raise RuntimeError(f"section-26 marker already present: {path}")
    cards = parse_cards(text)
    loan_cards = [
        card for card in cards if card["verdict"].startswith("LOANWORD")
    ]
    connection = ro_connection(language.db_path)
    try:
        metadata = load_metadata(
            connection,
            [card["entry_id"] for card in loan_cards],
        )
    finally:
        connection.close()
    reopen: list[dict[str, Any]] = []
    valid: list[dict[str, Any]] = []
    for card in loan_cards:
        meta = metadata.get(card["entry_id"])
        donor = named_donor(
            language.key,
            meta["etymology"] if meta else "",
        )
        item = {**card, "meta": meta, "donor": donor}
        if donor:
            valid.append(item)
        else:
            reopen.append(item)
    return {
        "language": language,
        "path": path,
        "text": text,
        "cards": cards,
        "loan_cards": loan_cards,
        "valid_loans": valid,
        "reopened_loans": reopen,
    }


def remove_cards(text: str, entry_ids: set[str]) -> str:
    def replacement(match: re.Match[str]) -> str:
        card = match.group(0)
        if card_identity(card) not in entry_ids:
            return card
        return ""

    result = CARD_RE.sub(replacement, text)
    result = re.sub(r"\n{4,}", "\n\n\n", result)
    return nfc(result)


def reading_note(
    language: Language,
    reopened: int,
    valid: int,
    names: int,
    morph_pending: int,
) -> str:
    return nfc(
        f"""

<!-- {READING_MARKER}:{language.key} -->
## إنفاذ القسم 26: إعادة فتح ما منعه قانون الاكتشاف

- أُعيد {reopened} إغلاق قرض لم يحمل مانحًا مسمى ومسارًا منشورًا، ونُقل العضو إلى `lane_c_coverage.jsonl` بحكم غير صادر؛ وبقي {valid} إغلاق قرض يستوفي الشرط الجديد.
- الأعلام: سُجل {names} علمًا في `lane_c_names_inventory.jsonl` خارج البسط الإحصائي وداخل الاكتشاف شاهدًا على الأصل أو المكونات المنشورة.
- الصور الصرفية: صار {morph_pending} عضوًا ظاهرًا في طابور الصرف للمراجعة الذاتية أو الإحالة إلى أصل مكتوب ذي حكم صادر؛ لا إحالة في الفراغ.
- الأعداد والضمائر والأدوات لا تُستبعد من الاكتشاف، وتخضع لشرط المصدرين والصفوف الموقعة نفسه.
- خط البرهان مجمد؛ لم يُنشأ صف صوتي ولم تُستعمل أداة مشتركة.
"""
    )


def load_coverage() -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    with COVERAGE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            row = json.loads(line)
            if tuple(row.keys()) != COVERAGE_FIELDS:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number}: invalid field order"
                )
            entry_id = nfc(str(row["member_id"]))
            if entry_id in seen:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number}: duplicate {entry_id}"
                )
            seen.add(entry_id)
            rows.append(row)
    return rows


def revised_coverage(
    old_rows: list[dict[str, Any]],
    analyses: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Counter[str]]]:
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    rows: list[dict[str, Any]] = []
    seen: set[str] = set()
    for old in old_rows:
        row = dict(old)
        reason = compact(str(row["non_issuance_reason"]))
        language = str(row["language"])
        if "NONLEXICAL" in reason or "FUNCTION-WORD" in reason:
            row["non_issuance_reason"] = (
                "OPEN-CANDIDATE؛ SECTION26-NONLEXICAL-INCLUDED؛ "
                "قورن بالمعيار نفسه ولم يستبعد؛ الحكم غير صادر"
            )
            counters[language]["nonlexical_reopened"] += 1
        elif "LOANWORD" in reason or "CONTACT-ISOLATED" in reason:
            row["non_issuance_reason"] = (
                "OPEN-CANDIDATE؛ SECTION26-LOAN-LABEL-REOPENED؛ "
                "لا إغلاق في سجل التغطية؛ الحكم غير صادر"
            )
            counters[language]["coverage_loan_labels_reopened"] += 1
        entry_id = nfc(str(row["member_id"]))
        seen.add(entry_id)
        rows.append(row)

    for analysis in analyses:
        language: Language = analysis["language"]
        for item in analysis["reopened_loans"]:
            meta = item["meta"]
            if meta is None:
                raise RuntimeError(
                    f"missing source metadata for {item['entry_id']}"
                )
            entry_id = item["entry_id"]
            if entry_id in seen:
                raise RuntimeError(
                    f"reopened closure already in coverage: {entry_id}"
                )
            reason_state = (
                "OPEN-CANDIDATE"
                if int(meta["licensed_candidate_count"] or 0)
                else "OPEN-NO-LICENSED-CANDIDATE"
            )
            row = {
                "member_id": entry_id,
                "language": language.key,
                "form": nfc(meta["headword"]),
                "branch_meaning": (
                    nfc(meta["gloss"]) or "(غير مسجل في المصدر)"
                ),
                "non_issuance_reason": (
                    f"{reason_state}؛ SECTION26-LOAN-NO-NAMED-DONOR؛ "
                    "أعيدت المقارنة كسائر الكلمات؛ الحكم غير صادر"
                ),
                "batch_number": 0,
            }
            rows.append(row)
            seen.add(entry_id)
            counters[language.key]["loan_closures_reopened"] += 1
    return rows, counters


def load_classical_source_roots() -> set[str]:
    table = pq.read_table(
        ARABIC_ROOTS,
        columns=["root", "book_name"],
    )
    source_sets: dict[str, set[str]] = defaultdict(set)
    for row in table.to_pylist():
        root = nfc(row["root"])
        book = nfc(row["book_name"])
        if book in {
            "لسان العرب لابن منظور",
            "تاج العروس لمرتضى الزبيدي",
        }:
            source_sets[root].add(book)
    return {
        root
        for root, sources in source_sets.items()
        if sources
        == {
            "لسان العرب لابن منظور",
            "تاج العروس لمرتضى الزبيدي",
        }
    }


def root_evidence(row: sqlite3.Row) -> tuple[str, str]:
    form_targets = json.loads(row["form_targets_json"] or "[]")
    if row["form_of"] and form_targets:
        return "published-form-target", "، ".join(map(nfc, form_targets))
    alternative_targets = json.loads(
        row["alternative_targets_json"] or "[]"
    )
    if row["alternative_of"] and alternative_targets:
        return (
            "published-alternative-target",
            "، ".join(map(nfc, alternative_targets)),
        )

    etymology = compact(row["etymology"])
    if etymology:
        patterns = (
            r"\bBorrowed from\s+(.{1,280}?)(?=[.;]|$)",
            r"(?:^|[.;]\s+)From\s+(.{1,280}?)(?=[.;]|$)",
            r"\bDerived from\s+(.{1,280}?)(?=[.;]|$)",
            r"\b(?:from|From)\s+(.{1,180}?\+.{1,100}?)(?=[.;]|$)",
        )
        for pattern in patterns:
            match = re.search(pattern, etymology)
            if match:
                return "published-etymology", compact(match.group(1), 320)
        return "published-etymology", compact(etymology, 320)

    gloss = compact(row["gloss"])
    match = re.search(
        r"\b(?:abbreviation|acronym|diminutive|form|initialism|"
        r"transliteration|variant)\s+of\s+(.{1,240}?)(?=[.;]|$)",
        gloss,
        re.IGNORECASE,
    )
    if match:
        return "published-gloss-base", compact(match.group(1), 280)
    return "unresolved-source-gap", ""


def build_names_inventory(
    roots_with_two_sources: set[str],
) -> tuple[list[dict[str, Any]], dict[str, Counter[str]]]:
    output: list[dict[str, Any]] = []
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for language in LANGUAGES:
        connection = ro_connection(language.db_path)
        try:
            name_rows = connection.execute(
                """
                SELECT entry_id, headword, pos, gloss, etymology,
                       form_of, alternative_of, form_targets_json,
                       alternative_targets_json
                FROM entries
                WHERE language = ?
                  AND lower(pos) IN ('name', 'proper noun')
                """,
                (language.key,),
            ).fetchall()
            name_ids = [nfc(row["entry_id"]) for row in name_rows]
            candidates: dict[str, list[dict[str, Any]]] = defaultdict(list)
            for id_chunk in chunks(name_ids):
                marks = ",".join("?" for _ in id_chunk)
                candidate_rows = connection.execute(
                    f"""
                    SELECT entry_id, form, rule_ids_json
                    FROM candidates
                    WHERE entry_id IN ({marks})
                      AND kind = 'root'
                      AND status = 'licensed'
                      AND route_flag = 0
                    ORDER BY entry_id, form
                    """,
                    id_chunk,
                ).fetchall()
                for candidate in candidate_rows:
                    root = nfc(candidate["form"])
                    if root not in roots_with_two_sources:
                        continue
                    bucket = candidates[nfc(candidate["entry_id"])]
                    if len(bucket) >= 6:
                        continue
                    bucket.append(
                        {
                            "root": root,
                            "rule_ids": json.loads(
                                candidate["rule_ids_json"] or "[]"
                            ),
                            "sources": [
                                "لسان العرب لابن منظور",
                                "تاج العروس لمرتضى الزبيدي",
                            ],
                            "status": "discovery-candidate-not-verdict",
                        }
                    )
        finally:
            connection.close()

        for row in name_rows:
            entry_id = nfc(row["entry_id"])
            status, evidence = root_evidence(row)
            arabic_candidates = candidates.get(entry_id, [])
            output.append(
                {
                    "member_id": entry_id,
                    "language": language.key,
                    "name": nfc(row["headword"]),
                    "branch_meaning": (
                        nfc(row["gloss"]) or "(غير مسجل في المصدر)"
                    ),
                    "root_status": status,
                    "published_root_or_components": evidence,
                    "arabic_root_candidates": arabic_candidates,
                    "source": language.source_label,
                    "statistical_denominator": False,
                }
            )
            counters[language.key]["names"] += 1
            if status == "unresolved-source-gap":
                counters[language.key]["names_unresolved"] += 1
            else:
                counters[language.key]["names_root_recorded"] += 1
            if arabic_candidates:
                counters[language.key]["names_with_arabic_candidates"] += 1
    output.sort(
        key=lambda row: (
            next(
                index
                for index, language in enumerate(LANGUAGES)
                if language.key == row["language"]
            ),
            source_ordinal(str(row["member_id"])),
            str(row["member_id"]),
        )
    )
    return output, counters


def known_ids_by_language(
    analyses: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> dict[str, set[str]]:
    result: dict[str, set[str]] = defaultdict(set)
    for analysis in analyses:
        language: Language = analysis["language"]
        result[language.key].update(
            card["entry_id"]
            for card in analysis["cards"]
            if card not in analysis["reopened_loans"]
        )
    for row in coverage_rows:
        result[str(row["language"])].add(nfc(str(row["member_id"])))
    return result


def build_morph_queue(
    analyses: list[dict[str, Any]],
    coverage_rows: list[dict[str, Any]],
) -> tuple[list[dict[str, Any]], dict[str, Counter[str]]]:
    known = known_ids_by_language(analyses, coverage_rows)
    issued_ids: dict[str, set[str]] = defaultdict(set)
    for analysis in analyses:
        language: Language = analysis["language"]
        reopened = {
            item["entry_id"] for item in analysis["reopened_loans"]
        }
        for card in analysis["cards"]:
            if card["entry_id"] in reopened:
                continue
            if issued_verdict(card["verdict"]):
                issued_ids[language.key].add(card["entry_id"])

    rows: list[dict[str, Any]] = []
    counters: dict[str, Counter[str]] = defaultdict(Counter)
    for language in LANGUAGES:
        connection = ro_connection(language.db_path)
        try:
            base_rows = connection.execute(
                """
                SELECT entry_id, headword
                FROM entries
                WHERE language = ? AND form_of = 0
                """,
                (language.key,),
            ).fetchall()
            bases: dict[str, list[str]] = defaultdict(list)
            for base in base_rows:
                bases[nfc(base["headword"])].append(nfc(base["entry_id"]))

            form_rows = connection.execute(
                """
                SELECT entry_id, headword, pos, form_targets_json,
                       form_resolution_status
                FROM entries
                WHERE language = ? AND form_of = 1
                """,
                (language.key,),
            )
            total = 0
            name_forms = 0
            discovery_forms = 0
            already = 0
            referral = 0
            void = 0
            nonlexical = 0
            pending_keys: list[tuple[int, int, str]] = []
            for form in form_rows:
                total += 1
                entry_id = nfc(form["entry_id"])
                pos = nfc(form["pos"]).casefold()
                headword = nfc(form["headword"])
                if pos in {"name", "proper noun"}:
                    name_forms += 1
                    continue
                if pos in BAD_FORM_POS or not headword or headword.startswith("<"):
                    continue
                discovery_forms += 1
                if entry_id in known[language.key]:
                    already += 1
                    continue
                if pos in FUNCTION_POS:
                    nonlexical += 1
                targets = [
                    nfc(target)
                    for target in json.loads(
                        form["form_targets_json"] or "[]"
                    )
                ]
                unique_issued_base = False
                if form["form_resolution_status"] == "linked":
                    for target in targets:
                        base_ids = bases.get(target, [])
                        if (
                            len(base_ids) == 1
                            and base_ids[0] in issued_ids[language.key]
                        ):
                            unique_issued_base = True
                            break
                if unique_issued_base:
                    referral += 1
                else:
                    void += 1
                pending_keys.append(
                    (
                        0 if pos in FUNCTION_POS else 1,
                        source_ordinal(entry_id),
                        entry_id,
                    )
                )
        finally:
            connection.close()

        pending_keys.sort()
        row = {
            "language": language.key,
            "source_db": language.db_path,
            "total_form_records": total,
            "proper_name_forms_routed_to_names": name_forms,
            "discovery_form_records": discovery_forms,
            "already_recorded": already,
            "referral_eligible": referral,
            "void_closure_prevented": void,
            "nonlexical_priority": nonlexical,
            "pending": len(pending_keys),
            "first_pending_member_id": (
                pending_keys[0][2] if pending_keys else ""
            ),
            "last_pending_member_id": (
                pending_keys[-1][2] if pending_keys else ""
            ),
            "queue_order": (
                "function words and numerals first, then stable source order"
            ),
        }
        rows.append(row)
        counters[language.key].update(
            {
                "morph_total": total,
                "morph_name_forms": name_forms,
                "morph_discovery_forms": discovery_forms,
                "morph_already_recorded": already,
                "morph_referral_eligible": referral,
                "morph_void_prevented": void,
                "morph_nonlexical_priority": nonlexical,
                "morph_pending": len(pending_keys),
            }
        )
    return rows, counters


def jsonl_text(
    rows: list[dict[str, Any]],
    fields: tuple[str, ...],
) -> str:
    lines: list[str] = []
    for row in rows:
        if tuple(row.keys()) != fields:
            raise RuntimeError(
                f"invalid JSONL field order for {row.get('member_id')}"
            )
        lines.append(
            json.dumps(
                row,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


def aggregate_counters(
    *counter_maps: dict[str, Counter[str]],
) -> dict[str, Counter[str]]:
    result: dict[str, Counter[str]] = defaultdict(Counter)
    for counter_map in counter_maps:
        for language, counter in counter_map.items():
            result[language].update(counter)
    return result


def audit_text(
    analyses: list[dict[str, Any]],
    counters: dict[str, Counter[str]],
    coverage_rows: list[dict[str, Any]],
    name_rows: list[dict[str, Any]],
    morph_rows: list[dict[str, Any]],
    planned_sizes: dict[str, int],
) -> str:
    labels = {language.key: language.source_label for language in LANGUAGES}
    table_lines = [
        "| اللسان | قرض بلا مانح أعيد | قرض مستوفٍ بقي | وسوم قرض في التغطية أعيدت | غير معجمي أعيد | الأعلام | جذورها/مكوناتها مسجلة | فجوة مصدر | صور صرفية في الطابور | منع إغلاق في الفراغ | إحالة جائزة |",
        "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|",
    ]
    for analysis in analyses:
        key = analysis["language"].key
        count = counters[key]
        table_lines.append(
            f"| {labels[key]} | "
            f"{len(analysis['reopened_loans']):,} | "
            f"{len(analysis['valid_loans']):,} | "
            f"{count['coverage_loan_labels_reopened']:,} | "
            f"{count['nonlexical_reopened']:,} | "
            f"{count['names']:,} | "
            f"{count['names_root_recorded']:,} | "
            f"{count['names_unresolved']:,} | "
            f"{count['morph_pending']:,} | "
            f"{count['morph_void_prevented']:,} | "
            f"{count['morph_referral_eligible']:,} |"
        )

    total_reopened = sum(
        len(analysis["reopened_loans"]) for analysis in analyses
    )
    total_valid = sum(
        len(analysis["valid_loans"]) for analysis in analyses
    )
    total_names = len(name_rows)
    total_rooted = sum(
        counter["names_root_recorded"] for counter in counters.values()
    )
    total_unresolved = sum(
        counter["names_unresolved"] for counter in counters.values()
    )
    total_morph = sum(row["pending"] for row in morph_rows)
    total_void = sum(row["void_closure_prevented"] for row in morph_rows)
    total_referral = sum(row["referral_eligible"] for row in morph_rows)
    total_nonlex = sum(
        counter["nonlexical_reopened"] for counter in counters.values()
    )
    total_coverage_loan = sum(
        counter["coverage_loan_labels_reopened"]
        for counter in counters.values()
    )
    size_lines = "\n".join(
        f"- `{path}`: {size:,} بايت."
        for path, size in planned_sizes.items()
    )
    table = "\n".join(table_lines)
    return nfc(
        f"""# محضر المسار ج: إنفاذ القسم 26 وإعادة فتح ما خذّل الاكتشاف

التاريخ: {DATE}

## السلطة

القسم 26 من `_inbox/recovery-pipeline-brief-for-codex.md` ناسخ لكل ما
يخالفه، والمحضر التشخيصي المقروء هو
`05-audits/2026-07-30-diagnosis-rules-that-suppress-discovery.md`.
لم يُشغّل Git، ولا باني مشترك، ولا خط البرهان، ولم يُعدّل ملف مشترك.

## ما تغير

1. استُبدل قارض السلسلة النصية بشرط مانح مسمى ومسار منشور. أزيلت بطاقات
   الإغلاق غير المستوفية من ملفات القراءة وعادت هوياتها إلى
   `lane_c_coverage.jsonl` بأحكام غير صادرة.
2. رُفعت أوصاف `NONLEXICAL-ISOLATED` و`FUNCTION-WORD` من التغطية؛
   الأعداد والضمائر والأدوات في الاكتشاف كسائر الكلمات.
3. سُجل كل علم مصدره في `lane_c_names_inventory.jsonl` خارج المقام
   الإحصائي. لا يُسمى مقابل عربي فيه إلا إذا حمل صفوف الجرد الموقعة
   وشاهدَي لسان العرب وتاج العروس؛ وهو مرشح اكتشاف لا حكم.
4. أُبطل استبعاد الصور الصرفية من تعريف الجرد. يسجل
   `lane_c_morphology_queue.jsonl` موضع الطابور المقيس من قواعد المصدر:
   لا تعد إحالة جائزة إلا إذا كان الهدف واحدًا مكتوبًا وله حكم صادر،
   وما عدا ذلك منع إغلاقه في الفراغ. لا تُنسخ مئات آلاف الصور بطاقات
   نثرية إلى `old-latin.md`.
5. عُدّل `lane_c_standing_queue.py` ليقرأ الصورة نفسها تحفظًا، ويقدّم
   الأعداد والضمائر والأدوات، ولا يغلق قرضًا إلا بالقارض الجديد.

## القياس

{table}

المحصلة: أُعيد {total_reopened:,} إغلاق قرض بلا مانح مسمى، وأعيدت
{total_coverage_loan:,} وسمات قرض تاريخية كانت مختبئة في سجل التغطية،
وبقي {total_valid:,} إغلاق قرض بمانح مسمى. وأعيدت {total_nonlex:,}
حالات غير معجمية مسماة صراحة.

جرد الأعلام: {total_names:,} علمًا؛ سُجل أصل أو مكونات منشورة لـ
{total_rooted:,} وبقيت {total_unresolved:,} فجوة مصدر ظاهرة بلا اختلاق.

طابور الصور الصرفية: {total_morph:,} صورة غير مسجلة سابقًا؛ منع شرط
القسم 26 إغلاق {total_void:,} منها في الفراغ، ووجد {total_referral:,}
فقط قابلة للإحالة من حيث وجود هدف واحد ذي حكم صادر. القابلية للإحالة
ليست حكم صلة، ولا تنشئ صفًا صوتيًا.

## حفظ التغطية والحجم

- عدد أسطر `lane_c_coverage.jsonl` بعد العلاج: {len(coverage_rows):,}؛
  الهويات فريدة والحقول الستة محفوظة.
- الأعلام خارج البسط الإحصائي بنص الحقل نفسه.
- بقيت ملفات القراءة تحت حد GitHub؛ الصور غير المحكومة تبقى في طابور
  المصدر، وعند فحصها يكتب لها سطر التغطية الآلي لا بطاقة نثرية.
{size_lines}

## موضع الطابور

الجرد المعجمي المستقل السابق فرغ، لكن إغلاق الصور بوصفها غير مستقلة
أُلغي. موضع الاستئناف الدقيق، أول هوية وآخر هوية وعدد الباقي في كل
لسان، مكتوب في `lane_c_morphology_queue.jsonl`. ترتيب الاستئناف:
الأعداد والضمائر والأدوات أولًا، ثم ترتيب المصدر الثابت. لا هدف عددي؛
الباقي المقيس هو الطابور.

الرقمان المفصولان في هذه المعالجة: **0 صلة موجبة جديدة؛ 0 إغلاق جديد**.
وأعيد فتح {total_reopened + total_coverage_loan:,} إغلاقًا أو وسم
إغلاق سابقًا.

الملفات المكتوبة: ملفات القراءة الستة؛
`04-cross-linguistic/data/lane_c_coverage.jsonl`؛
`04-cross-linguistic/data/lane_c_names_inventory.jsonl`؛
`04-cross-linguistic/data/lane_c_morphology_queue.jsonl`؛
`scripts/lane_c_section26_rules.py`؛
`scripts/lane_c_section26_reopen.py`؛
`scripts/lane_c_standing_queue.py`؛ وهذا المحضر.
"""
    )


def prepare() -> dict[str, Any]:
    rules_self_test()
    analyses = [analyze_reading(language) for language in LANGUAGES]
    old_coverage = load_coverage()
    coverage_rows, coverage_counts = revised_coverage(
        old_coverage,
        analyses,
    )
    roots = load_classical_source_roots()
    name_rows, name_counts = build_names_inventory(roots)
    morph_rows, morph_counts = build_morph_queue(
        analyses,
        coverage_rows,
    )
    counters = aggregate_counters(
        coverage_counts,
        name_counts,
        morph_counts,
    )

    names_per_language = Counter(
        str(row["language"]) for row in name_rows
    )
    morph_per_language = {
        str(row["language"]): int(row["pending"]) for row in morph_rows
    }
    reading_outputs: dict[Path, str] = {}
    for analysis in analyses:
        language: Language = analysis["language"]
        reopened_ids = {
            item["entry_id"] for item in analysis["reopened_loans"]
        }
        text = remove_cards(analysis["text"], reopened_ids)
        text += reading_note(
            language,
            len(reopened_ids),
            len(analysis["valid_loans"]),
            names_per_language[language.key],
            morph_per_language[language.key],
        )
        reading_outputs[analysis["path"]] = text

    coverage_text = jsonl_text(coverage_rows, COVERAGE_FIELDS)
    names_text = jsonl_text(name_rows, NAME_FIELDS)
    morph_text = jsonl_text(morph_rows, MORPH_FIELDS)
    planned_sizes: dict[str, int] = {
        path.relative_to(ROOT).as_posix(): len(text.encode("utf-8"))
        for path, text in reading_outputs.items()
    }
    planned_sizes[COVERAGE.relative_to(ROOT).as_posix()] = len(
        coverage_text.encode("utf-8")
    )
    planned_sizes[NAMES.relative_to(ROOT).as_posix()] = len(
        names_text.encode("utf-8")
    )
    planned_sizes[MORPH_QUEUE.relative_to(ROOT).as_posix()] = len(
        morph_text.encode("utf-8")
    )
    audit = audit_text(
        analyses,
        counters,
        coverage_rows,
        name_rows,
        morph_rows,
        planned_sizes,
    )
    return {
        "analyses": analyses,
        "coverage_rows": coverage_rows,
        "name_rows": name_rows,
        "morph_rows": morph_rows,
        "reading_outputs": reading_outputs,
        "coverage_text": coverage_text,
        "names_text": names_text,
        "morph_text": morph_text,
        "audit_text": audit,
        "planned_sizes": planned_sizes,
    }


def atomic_write(path: Path, text: str) -> None:
    temporary = path.with_name(path.name + ".lane-c-section26.tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        handle.write(text)
    os.replace(temporary, path)


def validate_prepared(output: dict[str, Any]) -> None:
    coverage_ids = [
        nfc(str(row["member_id"])) for row in output["coverage_rows"]
    ]
    if len(coverage_ids) != len(set(coverage_ids)):
        raise RuntimeError("duplicate coverage identities after preparation")
    if len(output["morph_rows"]) != len(LANGUAGES):
        raise RuntimeError("morphology queue lacks a language")
    if any(
        tuple(row.keys()) != NAME_FIELDS for row in output["name_rows"]
    ):
        raise RuntimeError("invalid names inventory fields")
    for analysis in output["analyses"]:
        path = analysis["path"]
        text = output["reading_outputs"][path]
        remaining_invalid: list[str] = []
        connection = ro_connection(analysis["language"].db_path)
        try:
            cards = parse_cards(text)
            loan_cards = [
                card
                for card in cards
                if card["verdict"].startswith("LOANWORD")
            ]
            metadata = load_metadata(
                connection,
                [card["entry_id"] for card in loan_cards],
            )
            for card in loan_cards:
                meta = metadata.get(card["entry_id"])
                if not meta or not named_donor(
                    analysis["language"].key,
                    meta["etymology"],
                ):
                    remaining_invalid.append(card["entry_id"])
        finally:
            connection.close()
        if remaining_invalid:
            raise RuntimeError(
                f"{path}: invalid loan closures remain: "
                f"{remaining_invalid[:5]}"
            )
        if len(text.encode("utf-8")) >= 100_000_000:
            raise RuntimeError(f"{path}: exceeds 100 MB after treatment")


def print_plan(output: dict[str, Any]) -> None:
    for analysis in output["analyses"]:
        language: Language = analysis["language"]
        morph = next(
            row
            for row in output["morph_rows"]
            if row["language"] == language.key
        )
        names = sum(
            row["language"] == language.key
            for row in output["name_rows"]
        )
        print(
            f"{language.key}"
            f"\treopen_loans={len(analysis['reopened_loans'])}"
            f"\tvalid_loans={len(analysis['valid_loans'])}"
            f"\tnames={names}"
            f"\tmorph_pending={morph['pending']}"
            f"\tvoid_prevented={morph['void_closure_prevented']}"
        )
    print(
        f"coverage_rows={len(output['coverage_rows'])}"
        f"\tnames_rows={len(output['name_rows'])}"
        f"\tmorph_languages={len(output['morph_rows'])}"
    )
    for path, size in output["planned_sizes"].items():
        print(f"SIZE\t{size}\t{path}")


def apply(output: dict[str, Any]) -> None:
    if AUDIT.exists():
        raise RuntimeError(f"audit already exists: {AUDIT}")
    for path, text in output["reading_outputs"].items():
        atomic_write(path, text)
    atomic_write(COVERAGE, output["coverage_text"])
    atomic_write(NAMES, output["names_text"])
    atomic_write(MORPH_QUEUE, output["morph_text"])
    atomic_write(AUDIT, output["audit_text"])


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    output = prepare()
    validate_prepared(output)
    print_plan(output)
    if args.apply:
        apply(output)
        print("APPLIED\tsection26")
    else:
        print("PLAN-ONLY\tno files written")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
