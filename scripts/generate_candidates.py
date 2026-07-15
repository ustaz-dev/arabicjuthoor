#!/usr/bin/env python3
"""Sound-first candidate retrieval through the industrial recovery pipeline.

This command retrieves frozen Arabic roots and nuclei. It distinguishes a
licensed path from a manual condition and from a scope gap. It never emits a
linguistic verdict.
"""
from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from recovery_pipeline.candidates import ArabicInventory, generate_hits
from recovery_pipeline.network import compile_network, rules_by_id
from recovery_pipeline.normalization import available_profiles, detect_language, load_profile, normalize


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("skeleton")
    parser.add_argument("--language", choices=["auto", *available_profiles()], default="auto")
    parser.add_argument("--max", type=int, default=30)
    parser.add_argument("--json", action="store_true")
    parser.add_argument("--allow-unknown", action="store_true", help="Diagnostic only; strict is the default.")
    parser.add_argument("--strict", action="store_true", help="Compatibility flag; strict is already the default.")
    args = parser.parse_args()

    language = detect_language(args.skeleton) if args.language == "auto" else args.language
    profile = load_profile(language)
    try:
        normalized = normalize(args.skeleton, profile, strict=not args.allow_unknown)
    except ValueError as error:
        print(f"FAIL: {error}")
        return 2
    rules = compile_network()
    hits, unmapped = generate_hits(normalized.tokens, language, rules, ArabicInventory.load())
    relevant = []
    indexed = rules_by_id(rules)
    for row_id in profile.get("relevant_branch_rules", []):
        rule = indexed.get(row_id)
        if rule:
            relevant.append({"row_id": row_id, "automation": rule.automation, "condition": rule.note})

    payload = {
        "language": language,
        "input": args.skeleton,
        "folded": normalized.folded,
        "tokens": normalized.tokens,
        "unknown": normalized.unknown,
        "ambiguities": normalized.ambiguities,
        "unmapped_tokens": unmapped,
        "manual_branch_rules": relevant,
        "candidate_count": len(hits),
        "candidates": [asdict(hit) for hit in hits[: args.max]],
        "truncated": max(0, len(hits) - args.max),
    }
    if args.json:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
    else:
        print(f"اللغة: {language} | الهيكل: {normalized.skeleton} | المرشحات: {len(hits)}")
        if normalized.ambiguities:
            print("مواضع تحتاج مراجعة: " + "؛ ".join(normalized.ambiguities))
        if relevant:
            print("صفوف فرعية يدوية لا يطبقها المحرك: " + ", ".join(row["row_id"] for row in relevant))
        for hit in hits[: args.max]:
            rules_text = ",".join(hit.rule_ids) or "ANCHOR"
            route_text = " [route-required]" if hit.route_flag else ""
            print(f"  [{hit.status}] {hit.kind} {hit.form} ({hit.positions}) [{rules_text}]{route_text} «{hit.reading}»")
        if payload["truncated"]:
            print(f"  ... و{payload['truncated']} مرشح آخر")
        if unmapped:
            print("FAIL: رموز مطبعة بلا مرساة عربية: " + ", ".join(unmapped))
    return 2 if unmapped else 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
