#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recovery_pipeline.network import compile_network, dump_network_json, network_report, rules_by_id


ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "scripts" / "recovery_pipeline" / "network-fixtures.json"


def check_fixtures() -> list[str]:
    expected = json.loads(FIXTURES.read_text(encoding="utf-8"))
    actual = rules_by_id(compile_network())
    failures: list[str] = []
    for row_id, fields in expected.items():
        rule = actual.get(row_id)
        if rule is None:
            failures.append(f"missing row {row_id}")
            continue
        for field, value in fields.items():
            got = list(getattr(rule, field)) if field == "scopes" else getattr(rule, field)
            if got != value:
                failures.append(f"{row_id}.{field}: expected {value!r}, got {got!r}")
    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description="Compile the frozen Markdown shift table without changing it.")
    parser.add_argument("--json", action="store_true", help="Print every compiled row as JSON.")
    parser.add_argument("--check", action="store_true", help="Require 44 rows and pass the ten manual fixtures.")
    args = parser.parse_args()
    rules = compile_network()
    if args.json:
        print(dump_network_json(rules))
    else:
        print(json.dumps(network_report(rules), ensure_ascii=False, indent=2))
    if args.check:
        failures = check_fixtures()
        if len(rules) != 44:
            failures.append(f"expected 44 operative rows, got {len(rules)}")
        if failures:
            for failure in failures:
                print(f"FAIL: {failure}")
            return 1
        print("network compiler: PASS (44 rows; 10 manual fixtures)")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())

