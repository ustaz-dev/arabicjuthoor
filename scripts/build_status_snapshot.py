#!/usr/bin/env python3
"""Build the small live-status snapshot that the public dashboard reads.

Every number on status.html comes from this file, and this file is computed from the
repository's own data. No figure on the dashboard is ever typed by hand, so the site
cannot silently drift away from the work, which is what happened before 2026-07-25.

The snapshot is deliberately small (a few kilobytes) so the page loads instantly
instead of pulling the multi-megabyte ledger into the browser.

Usage:
  python scripts/build_status_snapshot.py
  python scripts/build_status_snapshot.py --check   # CI: rebuild and compare
"""
from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / "data" / "status-snapshot.json"

READINGS = ROOT / "04-cross-linguistic" / "readings"
LEDGER = ROOT / "data" / "recovery-ledger.json"
PROOF = ROOT / "data" / "recovery-proof-preregistration.json"
FAMILY_STATES = ROOT / "data" / "family-review-states.json"
CORE_LEVELS = ROOT / "data" / "juthoor-core-levels.json"
LOANS = ROOT / "data" / "recovery-loan-registry.json"

CARD_HEADING = re.compile(r"^###\s.*بطاقة", re.M)

# Display names for the reading files, English and Arabic.
LANGUAGE_NAMES = {
    "aramaic": ("Aramaic", "الآراميّة"),
    "egyptian": ("Egyptian", "المصريّة القديمة"),
    "coptic": ("Coptic", "القبطيّة"),
    "hebrew": ("Hebrew", "العبريّة"),
    "old-latin": ("Old Latin", "اللاتينيّة القديمة"),
    "phoenician-punic-scout": ("Phoenician scout", "مسحُ الفينيقيّة"),
    "akkadian": ("Akkadian", "الأكّاديّة"),
    "ancient-greek": ("Ancient Greek", "اليونانيّة القديمة"),
    "welsh": ("Welsh", "الويلزيّة"),
    "punic": ("Punic", "البونيقيّة"),
    "old-norse": ("Old Norse", "النورديّة القديمة"),
    "persian": ("Persian", "الفارسيّة"),
    "gothic": ("Gothic", "القوطيّة"),
}

# Files that are working notes rather than a language reading.
SKIP_READINGS = {"README", "nucleus-echoes-week17"}


def read_json(path: Path) -> dict:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def language_rows() -> list[dict]:
    rows = []
    for path in sorted(READINGS.glob("*.md")):
        stem = path.stem
        if stem in SKIP_READINGS:
            continue
        text = path.read_text(encoding="utf-8")
        cards = len(CARD_HEADING.findall(text))
        if not cards:
            continue
        en, ar = LANGUAGE_NAMES.get(stem, (stem.replace("-", " ").title(), stem))
        rows.append({"key": stem, "en": en, "ar": ar, "cards": cards})
    rows.sort(key=lambda r: -r["cards"])
    return rows


def ledger_rows() -> dict:
    ledger = read_json(LEDGER)
    suspended = ledger.get("suspended", [])
    blockers = Counter(
        (item.get("blocker_type") or "UNLABELLED") for item in suspended
    )
    # Which reading file each suspended card belongs to, so the backlog is visible per language.
    per_file = Counter(
        Path(str(item.get("file", ""))).name for item in suspended
    )
    total = ledger.get("cards_total", 0)
    return {
        "cards_total": total,
        "suspended": len(suspended),
        "released": max(total - len(suspended), 0),
        "blockers": [
            {"name": name, "count": count} for name, count in blockers.most_common()
        ],
        "backlog_by_file": [
            {"file": name, "count": count} for name, count in per_file.most_common(12)
        ],
    }


def proof_rows() -> dict:
    pre = read_json(PROOF)
    trigger = pre.get("execution_trigger", {}) or {}
    thresholds = trigger.get("thresholds", trigger)
    states = read_json(FAMILY_STATES)
    families = states.get("families", {}) or {}
    status_counts = Counter(
        (value.get("status") if isinstance(value, dict) else str(value))
        for value in families.values()
    )
    # A family counts toward the trigger only when its review is complete and it is not suspended.
    eligible = sum(
        1
        for value in families.values()
        if isinstance(value, dict) and value.get("status") in {"reviewed", "eligible"}
    )
    per_language = Counter(key.split(":")[0] for key in families)
    return {
        "signed": bool(pre.get("execution_authorized")),
        "frozen_commit": (pre.get("frozen_git_commit") or "")[:7],
        "required_total": thresholds.get("total_eligible_reviewed_families"),
        "required_per_language": thresholds.get(
            "min_eligible_reviewed_families_per_language"
        ),
        "families_tracked": len(families),
        "eligible_now": eligible,
        "status_counts": [
            {"name": str(name), "count": count}
            for name, count in status_counts.most_common()
        ],
        "languages_tracked": [
            {"name": name, "count": count} for name, count in per_language.most_common()
        ],
    }


def frozen_rows() -> dict:
    levels = read_json(CORE_LEVELS).get("levels", {}) or {}
    out = {}
    for name, block in levels.items():
        if isinstance(block, dict):
            for field in ("count", "total", "entries"):
                if isinstance(block.get(field), int):
                    out[name] = block[field]
                    break
            else:
                items = block.get("items") or block.get("records")
                if isinstance(items, list):
                    out[name] = len(items)
    loans = read_json(LOANS)
    loan_items = loans.get("entries") or []
    out["loanwords_registered"] = loans.get("entries_total") or (
        len(loan_items) if isinstance(loan_items, list) else 0
    )
    return out


def build() -> dict:
    languages = language_rows()
    return {
        "schema_version": "1.0",
        "generated_by": "scripts/build_status_snapshot.py",
        "note": (
            "Every figure here is computed from repository data. "
            "Nothing on the dashboard is hand-typed."
        ),
        "exploration": {
            "languages_open": len(languages),
            "cards_total": sum(row["cards"] for row in languages),
            "by_language": languages,
        },
        "pipeline": ledger_rows(),
        "proof": proof_rows(),
        "frozen": frozen_rows(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true", help="verify the committed snapshot is current")
    args = parser.parse_args()

    payload = build()
    rendered = json.dumps(payload, ensure_ascii=False, indent=1) + "\n"

    if args.check:
        if not OUT.exists():
            print("MISSING: data/status-snapshot.json has not been built")
            return 1
        if OUT.read_text(encoding="utf-8") != rendered:
            print("STALE: data/status-snapshot.json does not match the repository data")
            return 1
        print("CLEAN: status snapshot matches repository data")
        return 0

    OUT.write_text(rendered, encoding="utf-8", newline="\n")
    exploration = payload["exploration"]
    pipeline = payload["pipeline"]
    print(f"languages open:   {exploration['languages_open']}")
    print(f"cards written:    {exploration['cards_total']}")
    print(f"ledger cards:     {pipeline['cards_total']}")
    print(f"suspended:        {pipeline['suspended']}")
    print(f"released:         {pipeline['released']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
