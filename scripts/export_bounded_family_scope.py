#!/usr/bin/env python3
"""Export the bounded Phoenician/Punic family scope without linguistic verdicts."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recovery_pipeline.families import require_current_family_metadata
from recovery_pipeline.inventory import DEFAULT_DB, connect


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_OUTPUT = ROOT / "data" / "phoenician-punic-family-scope.json"
LANGUAGES = ("phoenician", "punic")


def source_disposition(nonlexical_count: int, strata: list[str]) -> str:
    if nonlexical_count:
        return "nonlexical-isolated"
    if "reconstruction" in strata:
        return "reconstruction-isolated"
    if strata == ["proper-name"]:
        return "proper-name-isolated"
    if "proper-name" in strata:
        return "mixed-source-strata-review"
    return "lexical-review-required"


def build_payload(db_path: Path) -> dict:
    connection = connect(db_path, create=False)
    try:
        require_current_family_metadata(connection, LANGUAGES)
        languages: dict[str, dict] = {}
        for language in LANGUAGES:
            source = connection.execute(
                "SELECT source_id, path, size_bytes, entries_seen FROM sources WHERE language=?",
                (language,),
            ).fetchone()
            if source is None:
                raise RuntimeError(f"Missing pinned source record for {language}")
            families = []
            family_rows = connection.execute(
                "SELECT family_id, anchor_headword, construction, member_count, lemma_count, "
                "form_count, nonlexical_count FROM families WHERE language=? ORDER BY family_id",
                (language,),
            ).fetchall()
            for row in family_rows:
                (
                    family_id,
                    anchor_headword,
                    construction,
                    member_count,
                    lemma_count,
                    form_count,
                    nonlexical_count,
                ) = row
                members = connection.execute(
                    "SELECT e.entry_id, e.headword, e.romanization, e.pos, e.gloss, "
                    "e.source_stratum, fm.role, fm.link_types_json "
                    "FROM family_members fm JOIN entries e ON e.entry_id=fm.entry_id "
                    "WHERE fm.family_id=? ORDER BY e.entry_id",
                    (family_id,),
                ).fetchall()
                member_payload = [
                    {
                        "entry_id": member[0],
                        "headword": member[1],
                        "romanization": member[2],
                        "pos": member[3],
                        "gloss": member[4],
                        "source_stratum": member[5],
                        "family_role": member[6],
                        "link_types": json.loads(member[7]),
                    }
                    for member in members
                ]
                strata = sorted({member["source_stratum"] for member in member_payload})
                families.append(
                    {
                        "family_id": family_id,
                        "anchor_headword": anchor_headword,
                        "construction": construction,
                        "member_count": member_count,
                        "lemma_count": lemma_count,
                        "form_count": form_count,
                        "nonlexical_count": nonlexical_count,
                        "source_strata": strata,
                        "scope_disposition": source_disposition(nonlexical_count, strata),
                        "members": member_payload,
                    }
                )
            languages[language] = {
                "source_id": source[0],
                "source_path": source[1],
                "source_size_bytes": source[2],
                "source_entries_seen": source[3],
                "family_count": len(families),
                "families": families,
            }
        return {
            "version": 1,
            "generated_from": "scripts/export_bounded_family_scope.py",
            "scope": "استطلاع Kaikki محدود؛ لا يمثل معجم الفينيقية أو البونيقية التاريخي كاملًا.",
            "linguistic_verdicts": False,
            "disposition_contract": {
                "nonlexical-isolated": "حرف أو عنصر غير معجمي؛ يعزل من أحكام النسب.",
                "proper-name-isolated": "علم محض؛ يعزل من أحكام المعجم العام.",
                "reconstruction-isolated": "صورة معاد بناؤها؛ تعزل حتى يثبت شاهدها المنشور.",
                "mixed-source-strata-review": "أسرة تجمع أكثر من طبقة مصدر؛ تحتاج فصلًا يدويًا.",
                "lexical-review-required": "أسرة معجمية تدخل بطاقة RECOVERY-v2 ولا يحمل هذا السجل حكمها.",
            },
            "languages": languages,
        }
    finally:
        connection.close()


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload = build_payload(args.db)
    rendered = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if args.check:
        if not args.output.exists():
            print(f"FAIL: missing bounded family scope export: {args.output}")
            return 1
        if args.output.read_text(encoding="utf-8") != rendered:
            print(f"FAIL: stale bounded family scope export: {args.output}")
            return 1
        print(
            "bounded family scope: CLEAN ("
            + ", ".join(
                f"{language}={payload['languages'][language]['family_count']}"
                for language in LANGUAGES
            )
            + ")"
        )
        return 0
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(rendered, encoding="utf-8")
    print(f"wrote {args.output}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
