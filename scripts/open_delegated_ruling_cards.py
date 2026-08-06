#!/usr/bin/env python3
"""Open the two delegated-ruling card populations in small, reversible batches.

The frozen nucleus index is read-only and pinned by SHA-256.  The output is an
overlay review ledger: no proposed nucleus is inserted into the frozen index,
no proposed-nucleus card receives a descent verdict, and no relation is made.
The SIB-07 scan likewise records every Aramaic samekh entry and only supersedes
the already complete sahra/month card in its original reading ledger.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sqlite3
import sys
import unicodedata
from collections import Counter, defaultdict
from itertools import combinations
from pathlib import Path
from typing import Any

import pyarrow.parquet as pq


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import build_proposed_nuclei_report as proposed_report  # noqa: E402
from recovery_pipeline.candidates import (  # noqa: E402
    ArabicInventory,
    CandidateHit,
    HAMZA,
    SlotOption,
    _combine,
    generate_hits,
    slot_options,
)
from recovery_pipeline.network import compile_network  # noqa: E402


DATE = "2026-08-06"
CORE = ROOT / "data" / "juthoor-core-levels.json"
NETWORK = ROOT / "04-cross-linguistic" / "shift-network-draft.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
ARABIC_ROOTS = ROOT / "Resources" / "arabic_roots_hf" / "train-00000-of-00001.parquet"
LAYER_2 = ROOT / "computational" / "data" / "layer_2_results_v2.jsonl"
CACHE = ROOT / "cache" / "delegated_rulings" / "proposed_opening_queue.json"
SAMEKH_CACHE = ROOT / "cache" / "delegated_rulings" / "samekh_opening_queue.json"
LEDGER = ROOT / "04-cross-linguistic" / "data" / "delegated_ruling_card_reviews.jsonl"
READING = ROOT / "04-cross-linguistic" / "exploration" / "delegated-ruling-card-openings.md"
AUDIT = ROOT / "05-audits" / "2026-08-06-delegated-rulings-card-opening.md"

EXPECTED_CORE_SHA256 = "98d31b01a811ea44706d2ecc82c6f0423014982d1ad65eed3ad39ace3715cfcb"
EXPECTED_SAMEKH = 245
EXPECTED_PROPOSED = 4393
EXPECTED_DECISION_NUCLEI = 223
EXPECTED_CARRYING = 3889
EXPECTED_WITHOUT = 504
REQUIRED_NOTE = "النواة من الطبقة المقترحة 2026-08-06، لا من الفهرس المجمَّد"
SOURCE_NAMES = ("لسان العرب لابن منظور", "تاج العروس لمرتضى الزبيدي")
LONG_DASHES = {"\u2013", "\u2014"}
TOKEN_RE = re.compile(r"[A-Za-z][A-Za-z'-]*")
STOP = {
    "a", "an", "and", "are", "as", "at", "be", "been", "being", "by",
    "for", "from", "had", "has", "have", "he", "her", "his", "in", "into",
    "is", "it", "its", "of", "on", "or", "that", "the", "their", "to",
    "was", "were", "which", "with", "without",
}


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def clean(value: object) -> str:
    text = re.sub(r"\s+", " ", nfc(value)).strip()
    return text.replace("\u2013", "-").replace("\u2014", "-")


def excerpt(value: object, limit: int = 360) -> str:
    text = clean(value)
    if len(text) <= limit:
        return text
    cut = text[: limit + 1].rsplit(" ", 1)[0].rstrip(" ،؛,;:")
    return cut + "..."


def normalize_arabic(value: object) -> str:
    text = re.sub(r"[^ء-ي]", "", nfc(value))
    return "".join(HAMZA.get(char, char) for char in text)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def assert_constitutional_inputs() -> tuple[str, str]:
    core_hash = sha256(CORE)
    if core_hash != EXPECTED_CORE_SHA256:
        raise RuntimeError(
            "تغيّر data/juthoor-core-levels.json؛ أوقفت الأداة قبل أي كتابة"
        )
    network_text = NETWORK.read_text(encoding="utf-8")
    required = "| SIB-07 | ش ↔ שׂ / ס | كلاهما (عربيّة/عبريّة/آراميّة) |"
    if required not in network_text:
        raise RuntimeError("رجل SIB-07 الآرامية غير نافذة في ملف الشبكة")
    return core_hash, sha256(NETWORK)


def ro_connection() -> sqlite3.Connection:
    con = sqlite3.connect(f"file:{DB.resolve().as_posix()}?mode=ro", uri=True)
    con.row_factory = sqlite3.Row
    return con


def source_line(entry_id: str) -> int:
    match = re.search(r":(\d+):", entry_id)
    return int(match.group(1)) if match else 10**12


def metadata_for(entry_ids: list[str]) -> dict[str, dict[str, Any]]:
    output: dict[str, dict[str, Any]] = {}
    con = ro_connection()
    try:
        for start in range(0, len(entry_ids), 700):
            group = entry_ids[start : start + 700]
            placeholders = ",".join("?" for _ in group)
            rows = con.execute(
                f"""
                SELECT e.entry_id, e.pos, e.etymology, e.loan_hint, e.form_of,
                       e.alternative_of, e.morphology_status, e.source_stratum,
                       fm.family_id
                FROM entries e
                LEFT JOIN family_members fm ON fm.entry_id=e.entry_id
                WHERE e.entry_id IN ({placeholders})
                """,
                group,
            ).fetchall()
            for row in rows:
                output[row["entry_id"]] = dict(row)
    finally:
        con.close()
    return output


def load_arabic_support() -> tuple[
    dict[str, str],
    dict[str, dict[str, str]],
    dict[str, str],
    dict[str, set[str]],
    dict[str, float],
]:
    table = pq.read_table(
        ARABIC_ROOTS, columns=["root", "definition", "book_name"]
    )
    english: dict[str, str] = {}
    quotes: dict[str, dict[str, str]] = defaultdict(dict)
    for row in table.to_pylist():
        root = normalize_arabic(row["root"])
        book = nfc(row["book_name"])
        definition = clean(row["definition"])
        if book == "المعجم العربي الإنجليزي":
            english[root] = definition
        elif book in SOURCE_NAMES:
            quotes[root][book] = definition

    axials: dict[str, str] = {}
    with LAYER_2.open(encoding="utf-8") as handle:
        for line in handle:
            if not line.strip():
                continue
            row = json.loads(line)
            root = normalize_arabic(row.get("tri_root"))
            if len(root) == 3:
                axials[root] = clean(row.get("jabal_axial"))

    token_sets: dict[str, set[str]] = {}
    frequency: Counter[str] = Counter()
    for root, definition in english.items():
        tokens = {
            token.casefold()
            for token in TOKEN_RE.findall(definition)
            if token.casefold() not in STOP
        }
        token_sets[root] = tokens
        frequency.update(tokens)
    size = max(len(token_sets), 1)
    idf = {
        token: math.log((size + 1) / (count + 1)) + 1.0
        for token, count in frequency.items()
    }
    return english, dict(quotes), axials, token_sets, idf


def semantic_score(gloss: str, root: str, token_sets: dict[str, set[str]], idf: dict[str, float]) -> float:
    left = {
        token.casefold()
        for token in TOKEN_RE.findall(gloss)
        if token.casefold() not in STOP
    }
    right = token_sets.get(root, set())
    common = left & right
    if not common:
        return 0.0
    numerator = sum(idf.get(token, 1.0) for token in common)
    left_weight = sum(idf.get(token, 1.0) for token in left)
    right_weight = sum(idf.get(token, 1.0) for token in right)
    return numerator / math.sqrt(max(left_weight * right_weight, 1.0))


def proposed_routes(card: proposed_report.Card, rules) -> dict[str, dict[str, Any]]:
    if len(card.tokens) < 2:
        return {}
    slots = tuple(slot_options(token, card.language, rules) for token in card.tokens)
    routes: dict[str, list[dict[str, Any]]] = defaultdict(list)
    for left, right in combinations(range(len(slots)), 2):
        if not slots[left] or not slots[right]:
            continue
        for combo, rule_ids, status in _combine((slots[left], slots[right])):
            if status != "licensed":
                continue
            form = "".join(HAMZA.get(option.arabic, option.arabic) for option in combo)
            if len(form) != 2:
                continue
            routes[form].append(
                {
                    "positions": f"{left + 1}-{right + 1}",
                    "rule_ids": list(rule_ids),
                    "path": " + ".join(option.path for option in combo),
                    "sound_rows_complete": all(option.rule_id for option in combo),
                    "route_evidence_required": any(option.route_flag for option in combo),
                }
            )
    selected: dict[str, dict[str, Any]] = {}
    for form, candidates in routes.items():
        candidates.sort(
            key=lambda item: (
                not item["sound_rows_complete"],
                item["route_evidence_required"],
                len(item["rule_ids"]),
                item["positions"],
                item["path"],
            )
        )
        selected[form] = candidates[0]
    return selected


def roots_by_pair(
    approved: set[str],
    english: dict[str, str],
    quotes: dict[str, dict[str, str]],
    axials: dict[str, str],
) -> dict[str, list[str]]:
    output: dict[str, set[str]] = defaultdict(set)
    for root in sorted(axials):
        if len(root) != 3 or root not in english:
            continue
        if any(book not in quotes.get(root, {}) for book in SOURCE_NAMES):
            continue
        for left, right in combinations(range(3), 2):
            pair = root[left] + root[right]
            if pair in approved:
                output[pair].add(root)
    return {pair: sorted(roots) for pair, roots in output.items()}


def full_root_candidates(card: proposed_report.Card, rules, inventory: ArabicInventory) -> list[dict[str, Any]]:
    hits, _ = generate_hits(card.tokens, card.language, rules, inventory)
    rows = []
    for hit in hits:
        if hit.kind != "root" or hit.status != "licensed":
            continue
        rows.append(
            {
                "root": hit.form,
                "reading": clean(hit.reading),
                "rule_ids": list(hit.rule_ids),
                "route_evidence_required": hit.route_flag,
            }
        )
    unique: dict[str, dict[str, Any]] = {}
    for row in rows:
        unique.setdefault(row["root"], row)
    return list(unique.values())[:8]


def prepare_proposed_queue(core_hash: str, network_hash: str, force: bool = False) -> dict[str, Any]:
    if CACHE.exists() and not force:
        payload = json.loads(CACHE.read_text(encoding="utf-8"))
        if (
            payload.get("pins", {}).get("core_sha256") == core_hash
            and payload.get("pins", {}).get("network_sha256") == network_hash
            and len(payload.get("records", [])) == EXPECTED_PROPOSED
        ):
            return payload

    cards = proposed_report.load_population()
    rules = compile_network()
    _, frozen = proposed_report.load_core()
    forms = {card.entry_id: proposed_report.proposed_forms(card, rules) for card in cards}
    witnesses: Counter[str] = Counter()
    for card_forms in forms.values():
        witnesses.update(form for form in card_forms if form not in frozen)
    approved = {form for form, count in witnesses.items() if count >= 40}
    if len(cards) != EXPECTED_PROPOSED or len(approved) != EXPECTED_DECISION_NUCLEI:
        raise RuntimeError(
            f"انجرف مجتمع القرار: cards={len(cards)} nuclei={len(approved)}"
        )

    english, quotes, axials, token_sets, idf = load_arabic_support()
    support = roots_by_pair(approved, english, quotes, axials)
    metadata = metadata_for([card.entry_id for card in cards])
    inventory = ArabicInventory.load(ROOT)
    records: list[dict[str, Any]] = []

    for rank, card in enumerate(cards, start=1):
        routes = proposed_routes(card, rules)
        card_forms = sorted(set(routes) & approved)
        meta = metadata.get(card.entry_id, {})
        roots = full_root_candidates(card, rules, inventory)
        shortlist: list[dict[str, Any]] = []
        for nucleus in card_forms:
            root_rows = []
            for root in support.get(nucleus, []):
                root_rows.append(
                    (
                        semantic_score(card.gloss, root, token_sets, idf),
                        root,
                    )
                )
            root_rows.sort(key=lambda item: (-item[0], item[1]))
            route = routes[nucleus]
            if root_rows:
                score, root = root_rows[0]
                shortlist.append(
                    {
                        "nucleus": nucleus,
                        "route": route,
                        "support_root": root,
                        "support_root_axial": axials.get(root, ""),
                        "semantic_retrieval_score": round(score, 6),
                        "semantic_score_is_verdict": False,
                        "named_lexica": list(SOURCE_NAMES),
                        "quoted_text": {
                            book: excerpt(quotes[root][book]) for book in SOURCE_NAMES
                        },
                        "english_support_excerpt": excerpt(english[root], 260),
                        "orbit_status": "REQUIRES-ORGANIC-NARRATION-FROM-QUOTED-LEXICA",
                    }
                )
            else:
                shortlist.append(
                    {
                        "nucleus": nucleus,
                        "route": route,
                        "support_root": None,
                        "semantic_retrieval_score": 0.0,
                        "semantic_score_is_verdict": False,
                        "named_lexica": [],
                        "quoted_text": {},
                        "orbit_status": "SOURCE-GAP; NO-TWO-LEXICON-ROOT-FAN",
                    }
                )
        shortlist.sort(
            key=lambda item: (
                -float(item["semantic_retrieval_score"]),
                item["nucleus"],
                str(item.get("support_root") or ""),
            )
        )
        shortlist = shortlist[:5]

        if card_forms:
            notes = [REQUIRED_NOTE]
            state = "READING-OPEN-NOT-A-VERDICT"
        else:
            notes = [
                "فُحصت ضمن مجتمع القرار، ولم تولّد نواة من الطبقة المقترحة المقرّة؛ لم يرفع القرار عنها عائقًا"
            ]
            state = "DECISION-POPULATION-READ; NO-APPROVED-PROPOSED-NUCLEUS"

        if meta.get("loan_hint"):
            direction = "BRANCH-LOAN-HINT; VERDICT-BLOCKED"
        elif any(item["route"]["route_evidence_required"] for item in shortlist):
            direction = "ROUTE-EVIDENCE-REQUIRED; VERDICT-BLOCKED"
        else:
            direction = "DIRECTION-UNDECIDED; NO-RELATION-ISSUED"
        morphology = (
            "FORM-OR-ALTERNATIVE; VERDICT-BLOCKED"
            if meta.get("form_of") or meta.get("alternative_of")
            else clean(meta.get("morphology_status") or "NOT-REVIEWED-FOR-VERDICT")
        )
        records.append(
            {
                "schema": "delegated-ruling-card-review-v1",
                "date": DATE,
                "lane": "proposed-nuclei",
                "rank": rank,
                "entry_id": card.entry_id,
                "family_id": meta.get("family_id"),
                "language": card.language,
                "headword": clean(card.headword),
                "romanization": clean(card.romanization),
                "pos": clean(meta.get("pos")),
                "branch_gloss": clean(card.gloss),
                "source": clean(card.source),
                "source_stratum": clean(meta.get("source_stratum")),
                "tokens": list(card.tokens),
                "approved_proposed_nuclei": card_forms,
                "candidate_shortlist": shortlist,
                "full_root_candidates": roots,
                "tri_root_precedence": "FULL-ROOT-FIRST" if roots else "NO-LICENSED-FULL-ROOT-FOUND",
                "morphology_filter": morphology,
                "direction_filter": direction,
                "review_state": state,
                "verdict_issued": False,
                "relation_created": False,
                "notes": notes,
            }
        )

    carrying = sum(bool(row["approved_proposed_nuclei"]) for row in records)
    if carrying != EXPECTED_CARRYING or len(records) - carrying != EXPECTED_WITHOUT:
        raise RuntimeError(
            f"انجرف حمل القرار: carrying={carrying} without={len(records) - carrying}"
        )
    payload = {
        "schema": "delegated-ruling-proposed-opening-queue-v1",
        "date": DATE,
        "pins": {"core_sha256": core_hash, "network_sha256": network_hash},
        "approved_nuclei": sorted(approved),
        "records": records,
    }
    CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = CACHE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(CACHE)
    return payload


def delegated_hits(tokens: tuple[str, ...], inventory: ArabicInventory, rules) -> list[CandidateHit]:
    slots = []
    for token in tokens:
        options = list(slot_options(token, "aramaic", rules))
        if token == "s":
            options.append(
                SlotOption(
                    "ش",
                    "licensed",
                    "SIB-07",
                    "cross-script",
                    "SIB-07: שׂ / ס ↔ ش",
                    False,
                )
            )
        slots.append(tuple(options))
    slot_tuple = tuple(slots)
    hits: list[CandidateHit] = []

    def add(kind: str, form: str, reading: str, positions: str, combo, rule_ids, status):
        hits.append(
            CandidateHit(
                kind=kind,
                form=form,
                reading=reading,
                positions=positions,
                status=status,
                rule_ids=rule_ids,
                path=" + ".join(item.path for item in combo),
                route_flag=any(item.route_flag for item in combo),
            )
        )

    if len(tokens) == 3:
        for combo, rule_ids, status in _combine(slot_tuple):
            form = "".join(item.arabic for item in combo)
            if form in inventory.roots:
                add("root", form, inventory.roots[form], "1-2-3", combo, rule_ids, status)
    for left, right in combinations(range(len(tokens)), 2):
        for combo, rule_ids, status in _combine((slot_tuple[left], slot_tuple[right])):
            form = "".join(item.arabic for item in combo)
            if form in inventory.nuclei:
                add(
                    "nucleus",
                    form,
                    inventory.nuclei[form],
                    f"{left + 1}-{right + 1}",
                    combo,
                    rule_ids,
                    status,
                )
    return hits


def samekh_records() -> list[dict[str, Any]]:
    rules = compile_network()
    inventory = ArabicInventory.load(ROOT)
    con = ro_connection()
    try:
        rows = con.execute(
            """
            SELECT e.entry_id, e.headword, e.romanization, e.pos, e.gloss,
                   e.tokens_json, e.etymology, e.loan_hint, e.form_of,
                   e.alternative_of, e.morphology_status, fm.family_id
            FROM entries e
            LEFT JOIN family_members fm ON fm.entry_id=e.entry_id
            WHERE e.language='aramaic' AND instr(e.headword, 'ס')>0
            """
        ).fetchall()
    finally:
        con.close()
    rows = sorted(rows, key=lambda row: (source_line(row["entry_id"]), row["entry_id"]))
    if len(rows) != EXPECTED_SAMEKH:
        raise RuntimeError(f"جرد السامخ {len(rows)} وليس {EXPECTED_SAMEKH}")

    output = []
    for rank, row in enumerate(rows, start=1):
        tokens = tuple(json.loads(row["tokens_json"]))
        after = delegated_hits(tokens, inventory, rules)
        new_hits = [
            hit
            for hit in after
            if "SIB-07" in hit.rule_ids
            and hit.status == "licensed"
        ]
        unique: dict[tuple[str, str, str], CandidateHit] = {}
        for hit in sorted(new_hits, key=lambda item: (item.kind, item.form, item.positions, item.rule_ids)):
            unique.setdefault((hit.kind, hit.form, hit.positions), hit)
        candidates = [
            {
                "kind": hit.kind,
                "form": hit.form,
                "reading": clean(hit.reading),
                "positions": hit.positions,
                "rule_ids": list(hit.rule_ids),
                "path": hit.path,
                "route_evidence_required": hit.route_flag,
            }
            for hit in unique.values()
        ]
        entry_id = row["entry_id"]
        state = "SIB07-OPEN-READING" if candidates else "SIB07-SCANNED-NO-NEW-INDEXED-CANDIDATE"
        record: dict[str, Any] = {
            "schema": "delegated-ruling-card-review-v1",
            "date": DATE,
            "lane": "aramaic-samekh-sib07",
            "rank": rank,
            "entry_id": entry_id,
            "family_id": row["family_id"],
            "language": "aramaic",
            "headword": clean(row["headword"]),
            "romanization": clean(row["romanization"]),
            "pos": clean(row["pos"]),
            "branch_gloss": clean(row["gloss"]),
            "tokens": list(tokens),
            "new_candidates": candidates,
            "morphology_filter": (
                "FORM-OR-ALTERNATIVE; VERDICT-BLOCKED"
                if row["form_of"] or row["alternative_of"]
                else clean(row["morphology_status"] or "NOT-REVIEWED-FOR-VERDICT")
            ),
            "direction_filter": (
                "BRANCH-LOAN-HINT; VERDICT-BLOCKED"
                if row["loan_hint"]
                else "NO-NAMED-DONOR-IN-SOURCE-FIELDS; ORGANIC-REVIEW-STILL-REQUIRED"
            ),
            "review_state": state,
            "verdict_issued": False,
            "relation_created": False,
            "notes": [
                "فُحصت بطاقة السامخ بعد إكمال الرجل الآرامية في SIB-07؛ الصف الصوتي يفتح القراءة ولا يصدر الصلة وحده"
            ],
        }
        if entry_id == "kaikki_aramaic:164:en-סהרא-arc-noun-nni0PqAO":
            month = next(
                (
                    item
                    for item in candidates
                    if item["kind"] == "root" and item["form"] == "شهر"
                ),
                None,
            )
            if month is None:
                raise RuntimeError("لم تنفتح بطاقة סהרא على الجذر شهر")
            record["review_state"] = "SIB07-SUPERSEDES-LAW-GAP; ROOT-TRACE"
            record["verdict_issued"] = True
            record["relation_created"] = True
            record["supersedes"] = "LAW-GAP in 04-cross-linguistic/readings/aramaic.md"
            record["selected_root"] = "شهر"
        output.append(record)
    return output


def prepare_samekh_queue(core_hash: str, network_hash: str) -> list[dict[str, Any]]:
    if SAMEKH_CACHE.exists():
        payload = json.loads(SAMEKH_CACHE.read_text(encoding="utf-8"))
        if (
            payload.get("pins", {}).get("core_sha256") == core_hash
            and payload.get("pins", {}).get("network_sha256") == network_hash
            and len(payload.get("records", [])) == EXPECTED_SAMEKH
        ):
            return payload["records"]
    records = samekh_records()
    payload = {
        "schema": "delegated-ruling-samekh-opening-queue-v1",
        "date": DATE,
        "pins": {"core_sha256": core_hash, "network_sha256": network_hash},
        "records": records,
    }
    SAMEKH_CACHE.parent.mkdir(parents=True, exist_ok=True)
    temporary = SAMEKH_CACHE.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    temporary.replace(SAMEKH_CACHE)
    return records


def load_ledger() -> list[dict[str, Any]]:
    if not LEDGER.exists():
        return []
    rows = []
    with LEDGER.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                rows.append(json.loads(line))
    keys = [(row["lane"], row["entry_id"]) for row in rows]
    if len(keys) != len(set(keys)):
        raise RuntimeError("تكرار في سجل بطاقات القرار")
    return rows


def write_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    with temporary.open("w", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n")
    temporary.replace(path)


def card_markdown(row: dict[str, Any]) -> str:
    display = row.get("headword") or row.get("romanization") or row["entry_id"]
    lines = [
        f"### بطاقة القرار: `{row['entry_id']}`، {display}",
        f"- اللسان: `{row['language']}`؛ الطبقة: `{row['lane']}`؛ الرتبة: {row['rank']}.",
        f"- معنى الفرع: «{row.get('branch_gloss') or 'غير مسجل'}».",
        f"- حالة القراءة: `{row['review_state']}`.",
    ]
    if row["lane"] == "proposed-nuclei":
        forms = "، ".join(f"`{item}`" for item in row["approved_proposed_nuclei"]) or "لا واحدة"
        lines.append(f"- النوى المقرّة التي حملتها البطاقة: {forms}.")
        lines.append(f"- أولوية الثلاثي التام: `{row['tri_root_precedence']}`.")
        if row["full_root_candidates"]:
            roots = "، ".join(f"`{item['root']}`" for item in row["full_root_candidates"])
            lines.append(f"- الجذور التامة المتاحة قبل النواة: {roots}.")
        if row["candidate_shortlist"]:
            top = row["candidate_shortlist"][0]
            route = top["route"]
            lines.append(
                f"- أعلى مرشح قراءة لا حكم: النواة `{top['nucleus']}`؛ شاهد المادة "
                f"`{top.get('support_root') or 'فجوة مصدر'}`؛ الدرجة الاسترجاعية "
                f"{top['semantic_retrieval_score']:.6f}."
            )
            lines.append(
                f"- مسار الصوت المرشح: `{route['path']}`؛ الصفوف "
                f"{('، '.join(route['rule_ids']) or 'غير مكتملة التسمية')}؛ "
                f"اكتمال الصف لكل صامت=`{str(route['sound_rows_complete']).lower()}`."
            )
            if top.get("support_root"):
                for book in SOURCE_NAMES:
                    lines.append(f"- {book}: «{top['quoted_text'][book]}»")
                lines.append(
                    f"- المدار: `{top['orbit_status']}`؛ لا تُحوّل درجة الاسترجاع إلى مدار."
                )
        lines.append(f"- مصفاة الصرف: `{row['morphology_filter']}`.")
        lines.append(f"- مصفاة الاتجاه: `{row['direction_filter']}`.")
        lines.append("- الحكم: لم يصدر حكم نسب، ولم تُنشأ صلة.")
    else:
        candidates = row.get("new_candidates", [])
        shown = "، ".join(
            f"`{item['kind']}:{item['form']}` ({'+'.join(item['rule_ids'])})"
            for item in candidates[:8]
        ) or "لا مرشح مفهرس جديد"
        lines.append(f"- ما فتحه SIB-07: {shown}.")
        lines.append(f"- مصفاة الصرف: `{row['morphology_filter']}`.")
        lines.append(f"- مصفاة الاتجاه: `{row['direction_filter']}`.")
        if row.get("selected_root") == "شهر":
            lines.append("- البطاقة الناسخة: `סהרא` «القمر» تقابل `شهر` بالجذر التام، وحكمها `ROOT-TRACE` موثق في سجل الآرامية.")
        else:
            lines.append("- الحكم: لا حكم آلي؛ بقيت القراءة العضوية وشروطها مستقلة.")
    for note in row.get("notes", []):
        lines.append(f"- ملاحظات: {note}.")
    return "\n".join(lines)


def render_reading(rows: list[dict[str, Any]]) -> str:
    counts = Counter(row["lane"] for row in rows)
    carrying = sum(
        bool(row.get("approved_proposed_nuclei"))
        for row in rows
        if row["lane"] == "proposed-nuclei"
    )
    blocks = "\n\n".join(card_markdown(row) for row in rows)
    return (
        "# فتح بطاقات القرارين المفوّضين في 2026-08-06\n\n"
        "هذه طبقة مراجعة قابلة للعزل. لا تعدّل الفهرس المجمّد، ولا تجعل النواة المقترحة حكم نسب أو صلة.\n\n"
        f"- بطاقات السامخ المسجلة: {counts['aramaic-samekh-sib07']} من {EXPECTED_SAMEKH}.\n"
        f"- بطاقات مجتمع النوى المسجلة: {counts['proposed-nuclei']} من {EXPECTED_PROPOSED}.\n"
        f"- البطاقات المسجلة التي تحمل نواة مقرّة: {carrying}.\n\n"
        f"{blocks}\n"
    )


def render_audit(rows: list[dict[str, Any]], core_hash: str, network_hash: str) -> str:
    samekh = [row for row in rows if row["lane"] == "aramaic-samekh-sib07"]
    proposed = [row for row in rows if row["lane"] == "proposed-nuclei"]
    carrying = sum(bool(row["approved_proposed_nuclei"]) for row in proposed)
    opened_samekh = sum(bool(row.get("new_candidates")) for row in samekh)
    month = sum(row.get("selected_root") == "شهر" for row in samekh)
    by_language = Counter(row["language"] for row in proposed)
    language_rows = "\n".join(
        f"| {language} | {count} |" for language, count in sorted(by_language.items())
    ) or "| لا شيء | 0 |"
    return f"""# محضر فتح بطاقات القرارين المفوّضين

**التاريخ:** {DATE}. **الفهرس المجمّد:** قراءة فقط.

## التقدم

| المسار | المنجز | المقام | الباقي |
|---|---:|---:|---:|
| سامخ الآرامية | {len(samekh)} | {EXPECTED_SAMEKH} | {EXPECTED_SAMEKH - len(samekh)} |
| النوى المقترحة | {len(proposed)} | {EXPECTED_PROPOSED} | {EXPECTED_PROPOSED - len(proposed)} |

- بطاقات السامخ ذات مرشح جديد عبر SIB-07: {opened_samekh}.
- بطاقة `סהרא` الناسخة للجذر `شهر`: {month}.
- بطاقات النوى المنجزة التي حملت واحدة من النوى 223: {carrying}.
- بطاقات مجتمع القرار المنجزة التي لم تحمل واحدة منها: {len(proposed) - carrying}.

## توزيع بطاقات النوى المنجزة

| اللسان | البطاقات |
|---|---:|
{language_rows}

## الحراس

- تجزئة `data/juthoor-core-levels.json`: `{core_hash}`، وهي التجزئة المثبتة قبل التنفيذ.
- تجزئة شبكة الصوت: `{network_hash}`.
- وسم البطاقة المفتوحة بالنواة المقترحة: «{REQUIRED_NOTE}».
- درجات التشابه ترتيب قراءة فقط، ولا تصدر حكمًا.
- الجذر الثلاثي التام مقدم متى كان متاحًا.
- لا حكم نسب ولا صلة في مسار النوى المقترحة.
"""


def write_views(rows: list[dict[str, Any]], core_hash: str, network_hash: str) -> None:
    reading = render_reading(rows)
    audit = render_audit(rows, core_hash, network_hash)
    for path, text in ((READING, reading), (AUDIT, audit)):
        if any(dash in text for dash in LONG_DASHES):
            raise RuntimeError(f"تسربت شرطة طويلة إلى {path}")
        path.parent.mkdir(parents=True, exist_ok=True)
        temporary = path.with_suffix(path.suffix + ".tmp")
        temporary.write_text(text, encoding="utf-8", newline="\n")
        temporary.replace(path)


def validate_complete(rows: list[dict[str, Any]]) -> None:
    samekh = [row for row in rows if row["lane"] == "aramaic-samekh-sib07"]
    proposed = [row for row in rows if row["lane"] == "proposed-nuclei"]
    if len(samekh) > EXPECTED_SAMEKH or len(proposed) > EXPECTED_PROPOSED:
        raise RuntimeError("تجاوز سجل القرار مقام المجتمع")
    for row in proposed:
        if row["approved_proposed_nuclei"] and REQUIRED_NOTE not in row.get("notes", []):
            raise RuntimeError(f"بطاقة بلا وسم القرار: {row['entry_id']}")
        if row.get("verdict_issued") or row.get("relation_created"):
            raise RuntimeError(f"تسرب حكم أو صلة من طبقة النوى: {row['entry_id']}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--lane", choices=("samekh", "proposed"), required=True)
    parser.add_argument("--batch-size", type=int, default=250)
    parser.add_argument("--force-prepare", action="store_true")
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("batch size must be positive")
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    core_hash, network_hash = assert_constitutional_inputs()
    current = load_ledger()
    lane_name = "aramaic-samekh-sib07" if args.lane == "samekh" else "proposed-nuclei"
    completed = {
        row["entry_id"] for row in current if row["lane"] == lane_name
    }
    if args.lane == "samekh":
        population = prepare_samekh_queue(core_hash, network_hash)
    else:
        population = prepare_proposed_queue(
            core_hash, network_hash, force=args.force_prepare
        )["records"]
    pending = [row for row in population if row["entry_id"] not in completed]
    addition = pending[: args.batch_size]
    if addition:
        current.extend(addition)
        current.sort(
            key=lambda row: (
                0 if row["lane"] == "aramaic-samekh-sib07" else 1,
                int(row["rank"]),
                row["entry_id"],
            )
        )
        validate_complete(current)
        write_jsonl(LEDGER, current)
        write_views(current, core_hash, network_hash)
    else:
        validate_complete(current)
        write_views(current, core_hash, network_hash)

    after = sum(row["lane"] == lane_name for row in current)
    remaining = len(population) - after
    print(
        json.dumps(
            {
                "lane": args.lane,
                "written": len(addition),
                "completed": after,
                "total": len(population),
                "remaining": remaining,
                "core_sha256": core_hash,
            },
            ensure_ascii=False,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
