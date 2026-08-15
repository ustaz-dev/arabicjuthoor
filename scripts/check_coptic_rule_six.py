#!/usr/bin/env python3
"""Check Coptic script integrity and the superseding full-Arabic comparison law."""
from __future__ import annotations

import json
import re
import sqlite3
import sys
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READING = ROOT / "04-cross-linguistic" / "readings" / "coptic.md"
POLICY = ROOT / "data" / "unicode-language-boundaries.json"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
NON_COPTIC_RESERVE = ROOT / "data" / "non-coptic-borrowings-in-coptic.json"
DEMOTIC_PAIRS = (
    ("COPTIC CAPITAL LETTER SHEI", "Ϣ", "ϣ"),
    ("COPTIC CAPITAL LETTER FEI", "Ϥ", "ϥ"),
    ("COPTIC CAPITAL LETTER KHEI", "Ϧ", "ϧ"),
    ("COPTIC CAPITAL LETTER HORI", "Ϩ", "ϩ"),
    ("COPTIC CAPITAL LETTER GANGIA", "Ϫ", "ϫ"),
    ("COPTIC CAPITAL LETTER SHIMA", "Ϭ", "ϭ"),
    ("COPTIC CAPITAL LETTER DEI", "Ϯ", "ϯ"),
)
DIRECT_DONOR_LABELS = (
    "arabisches Lehnwort",
    "hebräisches Lehnwort",
    "aramäisches Lehnwort",
    "syriakisches Lehnwort",
    "aus dem Syrischen",
)
GREEK = re.compile(r"[\u0370-\u03e1\u03f0-\u03ff\u1f00-\u1fff]")
UNCERTAINTY = re.compile(r"\?|\bvgl\.|mißverstanden|uncertain|compare", re.I)


def fail(message: str) -> None:
    raise SystemExit(f"Coptic rule six: FAIL - {message}")


def section(text: str, heading: str) -> str:
    try:
        start = text.index(heading) + len(heading)
    except ValueError:
        fail(f"missing section {heading}")
    end = text.find("\n### ", start)
    if end < 0:
        end = len(text)
    return text[start:end]


def source_ids(body: str) -> list[str]:
    return re.findall(r"`(C\d+)`", body)


def card_verdicts(text: str) -> list[str]:
    starts = list(re.finditer(r"^### بطاقة:.*$", text, re.MULTILINE))
    verdicts: list[str] = []
    for index, start in enumerate(starts):
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        card = text[start.start() : end]
        match = re.search(r"^- الحكم \(استكشاف\):\s*(.+)$", card, re.MULTILINE)
        if not match:
            fail(f"card lacks a verdict: {start.group(0)}")
        verdicts.append(match.group(1))
    return verdicts


def main() -> None:
    text = READING.read_text(encoding="utf-8")
    policy = json.loads(POLICY.read_text(encoding="utf-8"))
    boundary = next(
        row for row in policy["boundaries"]
        if row["id"] == "legacy-coptic-inside-greek-and-coptic-block"
    )
    listed = boundary["letters"]
    policy_pairs = {
        (row["name"], row["capital"], row["small"])
        for row in listed
    }
    expected_policy_pairs = {
        (name.removeprefix("COPTIC CAPITAL LETTER "), capital, small)
        for name, capital, small in DEMOTIC_PAIRS
    }
    if policy_pairs != expected_policy_pairs:
        fail("Unicode policy does not list the seven Demotic-derived pairs exactly")

    for name, capital, small in DEMOTIC_PAIRS:
        if GREEK.search(capital) or GREEK.search(small):
            fail(f"Demotic-derived letter entered Greek detector: {name}")
        if unicodedata.name(capital) != name:
            fail(f"Unicode name mismatch for {capital}")
        if not unicodedata.name(small).startswith("COPTIC SMALL LETTER"):
            fail(f"Unicode name mismatch for {small}")
        if capital not in text or small not in text:
            fail(f"reading does not preserve both cases of {name}")

    sys.path.insert(0, str(ROOT / "scripts"))
    import apply_coptic_greek_loan_isolation as isolation

    isolation.assert_demotic_letters_are_not_greek()
    for _, capital, small in DEMOTIC_PAIRS:
        if isolation.GREEK.search(capital) or isolation.GREEK.search(small):
            fail("active loan detector disagrees with Unicode policy")

    direct_body = section(text, "### سجل أعضاء الانتقال السامي المباشر في CCL")
    via_greek_body = section(text, "### سجل أعضاء الانتقال السامي عبر اليونانية")
    direct_list = source_ids(direct_body)
    via_greek_list = source_ids(via_greek_body)
    direct_ids = set(direct_list)
    via_greek_ids = set(via_greek_list)
    if len(direct_ids) != 19:
        fail(f"direct Semitic ledger is not exactly 19 unique members: {len(direct_ids)}")
    if len(via_greek_ids) != 45:
        fail(f"Semitic-via-Greek ledger is not exactly 45 unique members: {len(via_greek_ids)}")
    if direct_ids & via_greek_ids:
        fail(f"Semitic ledgers overlap: {sorted(direct_ids & via_greek_ids)}")
    tagged_ids = direct_ids | via_greek_ids
    if len(tagged_ids) != 64:
        fail(f"expected 64 tagged source members, found {len(tagged_ids)}")

    uri = f"file:{DB.resolve().as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    try:
        rows = connection.execute(
            """
            SELECT source_entry_id, etymology, loan_hint
            FROM entries
            WHERE language = 'coptic'
            """
        ).fetchall()
    finally:
        connection.close()
    inventory = {row["source_entry_id"]: row for row in rows}

    direct_from_source = {
        row["source_entry_id"]
        for row in rows
        if any(label.lower() in (row["etymology"] or "").lower() for label in DIRECT_DONOR_LABELS)
    }
    if direct_from_source != direct_ids:
        fail(
            "named direct Semitic source and ledger differ: "
            f"missing={sorted(direct_from_source - direct_ids)}, "
            f"extra={sorted(direct_ids - direct_from_source)}"
        )
    missing_members = sorted(tagged_ids - inventory.keys())
    if missing_members:
        fail(f"tagged members absent from source: {missing_members}")
    not_hinted = sorted(member for member in tagged_ids if not inventory[member]["loan_hint"])
    if not_hinted:
        fail(f"tagged members lack source loan route: {not_hinted}")
    via_without_greek = sorted(
        member for member in via_greek_ids
        if not GREEK.search(inventory[member]["etymology"] or "")
    )
    if via_without_greek:
        fail(f"via-Greek members lack Greek route in source: {via_without_greek}")

    greek_rows = [row for row in rows if GREEK.search(row["etymology"] or "")]
    greek_hinted = [row for row in greek_rows if row["loan_hint"]]
    greek_unhinted = [row for row in greek_rows if not row["loan_hint"]]
    unqualified_unhinted = [
        row["source_entry_id"] for row in greek_unhinted
        if not UNCERTAINTY.search(row["etymology"] or "")
    ]
    if unqualified_unhinted:
        fail(f"apparently definite Greek routes remain ordinary: {unqualified_unhinted}")

    required_policy_text = (
        "كل صورة قبطية، وكل صورة لهجية في CCL، والصورة اليونانية التي يسميها CCL، قوبلت بالعربية",
        "«ما يقولُه قاموسُ الفرعِ عن الأصل» خبر محفوظ",
        "المقام هو **3,301** كاملًا",
        "الحروف `Ϣ Ϥ Ϧ Ϩ Ϫ Ϭ Ϯ` ليست قرينة قرض بحال",
    )
    missing_text = [item for item in required_policy_text if item not in text]
    if missing_text:
        fail(f"reading lacks hard rule-six statements: {missing_text}")

    if not NON_COPTIC_RESERVE.exists():
        fail("missing CCL published-origin register for the reopened loan queue")
    reserve = json.loads(NON_COPTIC_RESERVE.read_text(encoding="utf-8"))
    reserve_rows = reserve.get("rows") or []
    counts = reserve.get("counts") or {}
    expected_origins = {
        "ancient-greek": 3280,
        "arabic": 11,
        "aramaic": 2,
        "hamitic-libyan": 1,
        "hebrew": 3,
        "persian": 3,
        "syriac": 1,
    }
    if len(reserve_rows) != 3301:
        fail(f"reopened published-origin register is not 3301 cards: {len(reserve_rows)}")
    if counts.get("by_published_origin") != expected_origins:
        fail(f"reopened origin report changed: {counts.get('by_published_origin')}")
    if counts.get("named_semitic_loan_closures") != 17:
        fail("named Semitic closures in the reopened queue are not exactly 17")
    if counts.get("arabic_reexaminations") != 3284:
        fail("Arabic reexaminations in the reopened queue are not exactly 3284")
    if counts.get("coptic_denominator") != 3301:
        fail("full Coptic denominator of the reopened loan queue is not 3301")
    if counts.get("excluded_by_published_origin") != 0:
        fail("a published origin still excludes a card from the denominator")
    greek_reserve = [row for row in reserve_rows if row.get("origin_code") == "ancient-greek"]
    if len(greek_reserve) != 3280 or any(
        not row.get("arabic_comparison_performed")
        or row.get("closure_in_coptic") not in {"OPEN-CANDIDATE", "ROOT-TRACE"}
        for row in greek_reserve
    ):
        fail("Greek-published material was not compared with Arabic in Coptic")
    semitic_codes = {"arabic", "aramaic", "hebrew", "syriac"}
    named_semitic = [row for row in reserve_rows if row.get("origin_code") in semitic_codes]
    if len(named_semitic) != 17 or any(
        row.get("closure_in_coptic") != "LOANWORD" for row in named_semitic
    ):
        fail("named Semitic donor material lacks LOANWORD closure")
    if any(not row.get("counted_in_coptic_denominator") for row in reserve_rows):
        fail("a published origin removed a card from the full denominator")
    if any(
        row.get("counted_link_in_coptic")
        != (row.get("closure_in_coptic") == "ROOT-TRACE")
        for row in reserve_rows
    ):
        fail("Coptic link count and ROOT-TRACE closures disagree")
    if text.count("LOAN-HARVEST-REREVIEW:LOAN-REOPEN-COPTIC-") != 3301:
        fail("the reading does not contain 3301 append-only supersession markers")
    if text.count("ARABIC-ROOT-SENSE-REREVIEW:LH-COPTIC-") != 3284:
        fail("the reading does not contain 3284 Arabic-reexamination supersession markers")

    print(
        "Coptic rule six: CLEAN "
        f"({len(rows)} source members; {len(greek_rows)} Greek-script etymologies, "
        f"{len(greek_hinted)} published source routes; no origin exclusions; "
        f"64 historical Semitic-source members preserved; {len(greek_unhinted)} "
        "uncertain/comparative Greek mentions recorded in the source; reopened queue: "
        "3284 compared with Arabic, 17 named-Semitic closures, denominator 3301; "
        "7 Demotic letter pairs preserved)"
    )


if __name__ == "__main__":
    main()
