#!/usr/bin/env python3
"""Check the hard Coptic rule-six boundary without changing project data."""
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
        "الأصل اليوناني المسمّى قرض طرف ثالث خارج الوراثة",
        "المصدر السامي المسمّى يحفظ بوسم `SEMITIC-SOURCE-TRANSMISSION` خارج بسط الوراثة",
        "الحروف `Ϣ Ϥ Ϧ Ϩ Ϫ Ϭ Ϯ` ليست قرينة قرض بحال",
        "لا يدخل أي من `65` في بسط الإرث المشترك",
        "`64` عضوًا بوسم `SEMITIC-SOURCE-TRANSMISSION`",
        "`3,208` أعضاء من طرف ثالث إلى القبطية",
        "`80` عادت إلى الحكم العادي",
        "`3,237` بطاقة من طرف ثالث إلى القبطية",
    )
    missing_text = [item for item in required_policy_text if item not in text]
    if missing_text:
        fail(f"reading lacks hard rule-six statements: {missing_text}")

    verdicts = card_verdicts(text)
    loan_cards = sum(verdict.startswith("LOANWORD") for verdict in verdicts)
    if loan_cards != 3303:
        fail(f"expected 3303 isolated live loan cards, found {loan_cards}")
    if 65 + 3237 + 1 != loan_cards:
        fail("live direction partition does not equal isolated loan-card count")

    print(
        "Coptic rule six: CLEAN "
        f"({len(rows)} source members; {len(greek_rows)} Greek-script etymologies, "
        f"{len(greek_hinted)} source loan routes; 3208 third-party exclusions; "
        f"64 Semitic-source members outside inheritance; {len(greek_unhinted)} "
        "uncertain/comparative Greek mentions reopened; 7 Demotic letter pairs preserved)"
    )


if __name__ == "__main__":
    main()
