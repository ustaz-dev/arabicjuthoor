#!/usr/bin/env python3
"""Summarise the full-coverage sweep into a small committed record.

Why this exists
---------------
Full coverage means a recorded disposition for every member examined, and that record is
the denominator without which no yield figure means anything. But the raw sweep is about a
million lines and 350 MB, which no repository should carry and which GitHub refuses outright
above 100 MB per file.

So the raw lines stay outside git under `Data raw/coverage/`, and this builds the small file
that git does carry: per language and per reason, how many members were examined, plus a
SHA-256 of every raw file so the summary can always be proved against the lines it came from.

Usage:
  python scripts/build_coverage_summary.py
  python scripts/build_coverage_summary.py --check
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "coverage-summary.json"
# The lanes write here while running; the raw files are moved out of git afterwards.
SEARCH_DIRS = (
    ROOT / "04-cross-linguistic" / "data",
    ROOT / "Data raw" / "coverage",
)
PATTERN = "lane_*_coverage.jsonl"


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with path.open("rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def build() -> dict:
    by_language: dict[str, Counter] = defaultdict(Counter)
    totals = Counter()
    sources = []

    for directory in SEARCH_DIRS:
        if not directory.is_dir():
            continue
        for path in sorted(directory.glob(PATTERN)):
            lines = 0
            with path.open(encoding="utf-8") as fh:
                for line in fh:
                    if not line.strip():
                        continue
                    lines += 1
                    try:
                        rec = json.loads(line)
                    except json.JSONDecodeError:
                        by_language["(unparsed)"]["malformed-line"] += 1
                        totals["malformed-line"] += 1
                        continue
                    lang = rec.get("language") or rec.get("lang") or "(unnamed)"
                    reason = rec.get("non_issuance_reason") or rec.get("reason") or "(unstated)"
                    by_language[lang][str(reason)[:60]] += 1
                    totals[str(reason)[:60]] += 1
            sources.append({
                "file": str(path.relative_to(ROOT)).replace("\\", "/"),
                "lines": lines,
                "bytes": path.stat().st_size,
                "sha256": sha256(path),
            })

    return {
        "schema_version": "1.0",
        "generated_by": "scripts/build_coverage_summary.py",
        "note": (
            "Denominator of the full-coverage sweep. The raw lines live outside git; "
            "every figure here is provable against the fingerprinted files below."
        ),
        "members_examined_total": sum(totals.values()),
        "by_language": {
            lang: {
                "members_examined": sum(counter.values()),
                "by_reason": dict(counter.most_common()),
            }
            for lang, counter in sorted(
                by_language.items(), key=lambda kv: -sum(kv[1].values())
            )
        },
        "by_reason_total": dict(totals.most_common()),
        "sources": sources,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"

    if args.check:
        if not OUT.exists():
            print("MISSING: data/coverage-summary.json has not been built")
            return 1
        if OUT.read_text(encoding="utf-8") != rendered:
            print("STALE: coverage summary does not match the raw sweep files")
            return 1
        print(f"CLEAN: coverage summary matches, {payload['members_examined_total']:,} members")
        return 0

    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    print(f"members examined: {payload['members_examined_total']:,}")
    for lang, block in list(payload["by_language"].items())[:8]:
        print(f"   {lang:18} {block['members_examined']:>9,}")
    print(f"raw files fingerprinted: {len(payload['sources'])}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
