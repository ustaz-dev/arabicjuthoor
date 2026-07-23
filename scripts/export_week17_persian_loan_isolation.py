#!/usr/bin/env python3
"""Build a member-level Persian Arabic-loan isolation register.

This is retrieval only.  It reads the author-approved pinned Kaikki snapshot
and the isolated Week 17 family inventory.  It never writes a linguistic
verdict, a review state, the shared ledger, or proof data.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import re
import sqlite3
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_DB = ROOT / "cache" / "recovery_pipeline" / "week17-day1-inventory.sqlite"
DEFAULT_SOURCE = ROOT / "Resources" / "persian" / "kaikki.org-dictionary-Persian.jsonl"
DEFAULT_OUTPUT = ROOT / "cache" / "recovery_pipeline" / "week17-day2-persian-loans.json"

DIRECT_TEMPLATES = {
    "bor", "bor+", "borrowed", "ubor", "unadapted borrowing",
}
DERIVED_TEMPLATES = {"der", "der+", "derived", "uder"}
CALQUE_TEMPLATES = {"cal", "calque", "clq", "pclq", "semantic loan"}
PSEUDO_TEMPLATES = {"pl", "pseudo-loan", "pseudoloan"}
MIXED_TEMPLATES = {"af", "com", "compound", "surface analysis", "surf"}
TREE_TEMPLATES = {"etymon", "ety"}

TEXT_PATTERNS = (
    ("direct-borrowing", re.compile(
        r"(?:borrowed|borrowing|loanword|from)\s+(?:ultimately\s+)?from\s+arabic\b"
        r"|\bborrowed\s+from\s+arabic\b|\bfrom\s+arabic\b",
        re.IGNORECASE,
    )),
    ("calque-or-semantic-loan", re.compile(
        r"\b(?:partial\s+)?calque\s+of\s+arabic\b|\bsemantic loan from arabic\b",
        re.IGNORECASE,
    )),
    ("pseudo-loan", re.compile(r"\bpseudo-arab(?:ism|ic)\b", re.IGNORECASE)),
    ("mediated-borrowing", re.compile(r"\bthrough arabic\b", re.IGNORECASE)),
)


def source_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def mentions_arabic(template: dict[str, Any]) -> bool:
    args = template.get("args") or {}
    expansion = str(template.get("expansion") or "")
    serialized = json.dumps(args, ensure_ascii=False).casefold()
    return (
        any(str(value).casefold() == "ar" for value in args.values())
        or "ar:" in serialized
        or "arabic" in expansion.casefold()
    )


def classify_row(row: dict[str, Any]) -> list[dict[str, str]]:
    """Return only explicit Arabic source routes, never cognate mentions."""
    evidence: list[dict[str, str]] = []
    etymology = str(row.get("etymology_text") or "")
    for route_class, pattern in TEXT_PATTERNS:
        if pattern.search(etymology):
            evidence.append({
                "class": route_class,
                "source": "etymology_text",
                "text": etymology[:1200],
            })
    for template in row.get("etymology_templates") or []:
        if not isinstance(template, dict) or not mentions_arabic(template):
            continue
        name = str(template.get("name") or "").casefold()
        args = template.get("args") or {}
        serialized = json.dumps(args, ensure_ascii=False).casefold()
        if name in DIRECT_TEMPLATES:
            route_class = "direct-borrowing"
        elif name in DERIVED_TEMPLATES:
            route_class = "arabic-derived"
        elif name in CALQUE_TEMPLATES:
            route_class = "calque-or-semantic-loan"
        elif name in PSEUDO_TEMPLATES:
            route_class = "pseudo-loan"
        elif name in MIXED_TEMPLATES:
            route_class = "arabic-component"
        elif name in TREE_TEMPLATES and ":bor" in serialized:
            route_class = "direct-borrowing"
        else:
            # root/cog/ncog/noncog and loose comparisons do not prove a route.
            continue
        evidence.append({
            "class": route_class,
            "source": f"template:{name}",
            "text": str(template.get("expansion") or "")[:1200],
        })
    unique: dict[tuple[str, str, str], dict[str, str]] = {}
    for item in evidence:
        unique[(item["class"], item["source"], item["text"])] = item
    return [unique[key] for key in sorted(unique)]


def check_classifier_contract() -> None:
    """Guard the boundary between source routes and cognate comparisons."""
    borrowed = classify_row({
        "etymology_text": "Borrowed from Arabic كِتَاب.",
        "etymology_templates": [],
    })
    compared = classify_row({
        "etymology_text": "",
        "etymology_templates": [{
            "name": "cog",
            "args": {"1": "ar", "2": "كَهَنَ"},
            "expansion": "cognate with Arabic كَهَنَ",
        }],
    })
    if not borrowed or {item["class"] for item in borrowed} != {"direct-borrowing"}:
        raise ValueError("Classifier no longer recognizes an explicit Arabic borrowing")
    if compared:
        raise ValueError("Classifier promoted a cognate comparison to a borrowing route")


def line_entry_map(connection: sqlite3.Connection) -> dict[int, dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT e.entry_id, e.headword, e.romanization, e.pos, e.gloss,
               fm.family_id, f.anchor_headword, fm.role
        FROM entries AS e
        JOIN family_members AS fm ON fm.entry_id=e.entry_id
        JOIN families AS f ON f.family_id=fm.family_id
        WHERE e.language='persian'
        ORDER BY e.entry_id
        """
    )
    result: dict[int, dict[str, Any]] = {}
    for entry_id, headword, romanization, pos, gloss, family_id, anchor, role in rows:
        parts = entry_id.split(":", 2)
        if len(parts) != 3 or not parts[1].isdigit():
            raise ValueError(f"Persian entry lacks pinned line number: {entry_id}")
        result[int(parts[1])] = {
            "entry_id": entry_id,
            "headword": headword,
            "romanization": romanization,
            "pos": pos,
            "gloss": gloss,
            "family_id": family_id,
            "family_anchor": anchor,
            "family_role": role,
        }
    return result


def post_filter_queue(
    connection: sqlite3.Connection,
    excluded: set[str],
) -> list[dict[str, Any]]:
    """Rank the best not-explicitly-isolated member of every surviving family."""
    connection.execute("CREATE TEMP TABLE excluded_arabic_route(entry_id TEXT PRIMARY KEY)")
    connection.executemany(
        "INSERT INTO excluded_arabic_route VALUES (?)",
        [(entry_id,) for entry_id in sorted(excluded)],
    )
    rows = connection.execute(
        """
        WITH candidate_strength AS (
          SELECT c.entry_id,
                 MAX(CASE WHEN c.kind='root' AND c.status='licensed'
                               AND c.route_flag=0 THEN 1 ELSE 0 END) AS full_root,
                 MIN(CASE WHEN c.status='licensed' AND c.route_flag=0
                          THEN json_array_length(c.rule_ids_json) END) AS rule_count
          FROM candidates AS c GROUP BY c.entry_id
        ), eligible AS (
          SELECT fm.family_id, e.entry_id, e.headword, e.romanization, e.pos, e.gloss,
                 COALESCE(cs.full_root,0) AS full_root, cs.rule_count,
                 ROW_NUMBER() OVER (
                   PARTITION BY fm.family_id
                   ORDER BY COALESCE(cs.full_root,0) DESC,
                            CASE WHEN cs.rule_count IS NULL THEN 999 ELSE cs.rule_count END,
                            LENGTH(TRIM(e.gloss)) DESC, e.entry_id
                 ) AS member_rank
          FROM family_members AS fm
          JOIN entries AS e ON e.entry_id=fm.entry_id
          LEFT JOIN candidate_strength AS cs ON cs.entry_id=e.entry_id
          LEFT JOIN excluded_arabic_route AS x ON x.entry_id=e.entry_id
          WHERE e.language='persian' AND x.entry_id IS NULL
            AND fm.role NOT IN ('form','nonlexical') AND e.form_of=0
            AND e.loan_hint=0
            AND e.pos NOT IN (
              'name','character','symbol','punct','suffix','prefix','affix',
              'infix','circumfix','interfix','combining_form'
            )
        )
        SELECT f.family_id, f.anchor_headword, f.member_count,
               e.entry_id, e.headword, e.romanization, e.pos, e.gloss,
               e.full_root, e.rule_count,
               (SELECT COUNT(*) FROM family_members fm2
                JOIN excluded_arabic_route x2 ON x2.entry_id=fm2.entry_id
                WHERE fm2.family_id=f.family_id) AS isolated_member_count
        FROM eligible AS e JOIN families AS f ON f.family_id=e.family_id
        WHERE e.member_rank=1
        ORDER BY e.full_root DESC,
                 CASE WHEN e.rule_count IS NULL THEN 999 ELSE e.rule_count END,
                 LENGTH(TRIM(e.gloss)) DESC, e.entry_id
        """
    )
    fields = (
        "family_id", "family_anchor", "family_member_count", "member_entry_id",
        "member_headword", "member_romanization", "member_pos", "member_gloss",
        "licensed_full_root", "licensed_rule_count", "isolated_member_count",
    )
    return [dict(zip(fields, row)) for row in rows]


def build_payload(db: Path, source: Path) -> dict[str, Any]:
    check_classifier_contract()
    connection = sqlite3.connect(db)
    try:
        line_map = line_entry_map(connection)
        isolated: list[dict[str, Any]] = []
        with source.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, start=1):
                row = json.loads(line)
                evidence = classify_row(row)
                if not evidence:
                    continue
                member = line_map.get(line_number)
                if member is None:
                    raise ValueError(f"Pinned Persian line is absent from inventory: {line_number}")
                isolated.append({
                    **member,
                    "line_number": line_number,
                    "route_classes": sorted({item["class"] for item in evidence}),
                    "evidence": evidence,
                    "member_level_only": True,
                })
        isolated.sort(key=lambda item: item["entry_id"])
        excluded = {item["entry_id"] for item in isolated}
        families: dict[str, dict[str, Any]] = {}
        for item in isolated:
            family = families.setdefault(item["family_id"], {
                "family_id": item["family_id"],
                "family_anchor": item["family_anchor"],
                "isolated_member_ids": [],
                "route_classes": set(),
            })
            family["isolated_member_ids"].append(item["entry_id"])
            family["route_classes"].update(item["route_classes"])
        family_rows = []
        for family in families.values():
            family_rows.append({
                **family,
                "isolated_member_ids": sorted(family["isolated_member_ids"]),
                "route_classes": sorted(family["route_classes"]),
                "whole_family_isolation_forbidden": True,
            })
        family_rows.sort(key=lambda item: item["family_id"])
        queue = post_filter_queue(connection, excluded)
        leaked = excluded.intersection(item["member_entry_id"] for item in queue)
        if leaked:
            raise ValueError(
                "Explicit Arabic-route members leaked into the post-filter queue: "
                f"{sorted(leaked)[:5]}"
            )
    finally:
        connection.close()
    return {
        "schema": "week17-persian-arabic-route-isolation-v1",
        "source": str(source.relative_to(ROOT)).replace("\\", "/"),
        "source_sha256": source_sha256(source),
        "contract": {
            "retrieval_only": True,
            "verdicts_written": False,
            "family_is_display_not_verdict": True,
            "comparison_mentions_are_not_routes": True,
            "post_filter_queue_is_not_a_native_verdict": True,
        },
        "isolated_members": isolated,
        "families_with_explicit_arabic_route": family_rows,
        "post_filter_review_queue": queue,
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Build the Week 17 member-level Persian Arabic-route register."
    )
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--source", type=Path, default=DEFAULT_SOURCE)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_payload(args.db.resolve(), args.source.resolve())
    encoded = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    output = args.output.resolve()
    if args.check:
        if not output.exists() or output.read_text(encoding="utf-8") != encoded:
            raise ValueError("Persian Arabic-route isolation register is missing or stale")
        print(json.dumps({
            "check": "passed",
            "isolated_members": len(payload["isolated_members"]),
            "families": len(payload["families_with_explicit_arabic_route"]),
            "queue": len(payload["post_filter_review_queue"]),
        }, ensure_ascii=False))
        return 0
    output.parent.mkdir(parents=True, exist_ok=True)
    temporary = output.with_suffix(output.suffix + ".tmp")
    temporary.write_text(encoded, encoding="utf-8")
    temporary.replace(output)
    print(json.dumps({
        "output": str(output),
        "isolated_members": len(payload["isolated_members"]),
        "families": len(payload["families_with_explicit_arabic_route"]),
        "queue": len(payload["post_filter_review_queue"]),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
