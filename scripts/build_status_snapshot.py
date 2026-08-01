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

# scripts/count_links.py is the single definition of a link.  The dashboard
# imports it rather than reimplementing the rule, because two implementations
# that must agree is exactly the defect that made the public counter understate
# itself by half.
sys.path.insert(0, str(Path(__file__).resolve().parent))
import count_links  # noqa: E402
OUT = ROOT / "data" / "status-snapshot.json"

READINGS = ROOT / "04-cross-linguistic" / "readings"
LEDGER = ROOT / "data" / "recovery-ledger.json"
PROOF = ROOT / "data" / "recovery-proof-preregistration.json"
PROOF_ELIGIBILITY = ROOT / "data" / "proof-eligible-families.json"
FAMILY_STATES = ROOT / "data" / "family-review-states.json"
CORE_LEVELS = ROOT / "data" / "juthoor-core-levels.json"
LOANS = ROOT / "data" / "recovery-loan-registry.json"

# The issued-verdict line of a card.  It is anchored to the live field so a
# historical appendix that preserves an earlier verdict cannot revive it in
# the public counter.
# The verdict is written under six different field names across the campaigns.
# Counting only "- الحكم" hid 640 Aramaic and 384 Hebrew verdicts from the public
# dashboard, so the site understated itself.  scripts/count_links.py is the single
# definition of a link; this pattern mirrors it.
VERDICT_LINE = re.compile(
    r"^-\s*(?:الحكم|الحسم|حكمُ? طبقة النواة|حكمُ? طبقة الجذر|نتيجةُ? طبقة النواة)"
    r"[^\n]*?:\s*\*{0,2}([A-Z][A-Z\-]+)",
    re.M,
)

# Verdicts that assert a link to the Arabic tongue, as opposed to closures
# (loanword, proper name, non-lexical) which end a card without asserting one.
POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}

# Terminal outcomes that resolve a card without asserting a link.  Newer
# campaign cards sometimes carry the terminal outcome in the authoritative
# blocker field while keeping "غير صادر" in the verdict field.  The counter
# must therefore read both live fields, once per card.
CLOSURE_VERDICTS = {
    "NO-TRACE",
    "LOANWORD",
    "PROPER-NAME-ISOLATED",
    "NONLEXICAL-ISOLATED",
    "MIXED-ISOLATED",
    "FORM-OF-ISOLATED",
    "INTRA-HOUSE-TRANSFER",
    "COMPOUND-BOUNDARY",
    "LOAN-ROUTE-ISOLATED",
    "PHRASE-LINK",
    "FUNCTION-WORD",
    "CONTACT-ISOLATED",
    "OUT-OF-SCOPE",
    "ABBREVIATION",
}

BLOCKER_LINE = re.compile(r"^- عائق:\s*النوع=([A-Z\-]+)", re.M)

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


def reading_cards(text: str) -> list[str]:
    """Return real card blocks, using the same boundary law as the ledger."""
    blocks = re.split(r"(?=^### )", text, flags=re.M)
    cards = []
    for block in blocks:
        # Six heading forms carry verdicts: بطاقة, إعادة قراءة بطبقتين, عين النواة,
        # مراجعة عضوية, بطاقة حسم, إعادةُ توسيم.  Restricting to two of them was
        # the second half of the undercount; any heading is now admitted and the
        # verdict field decides, exactly as scripts/count_links.py does.
        if not block.startswith("### "):
            continue
        heading = block.split("\n", 1)[0]
        if "<" in heading:
            continue
        cards.append(block)
    return cards


def live_verdict(card: str) -> str:
    match = VERDICT_LINE.search(card)
    return match.group(1) if match else ""


def live_blocker(card: str) -> str:
    match = BLOCKER_LINE.search(card)
    return match.group(1) if match else ""


def counted_outcomes(card: str) -> list[str]:
    """Every outcome this card asserts.

    The positive half is delegated to scripts/count_links.py so there is one
    implementation of "what counts as a link", not two that have to be kept in
    agreement.  A card read under the two-layer rule can assert a root-level
    link and a nucleus-level link at once, in two separate fields, and both are
    real claims, so positives come back as a set.  A card asserting none of them
    falls back to a single closure, read from the verdict field or from the
    authoritative blocker field.
    """
    positives = count_links.scan_card(count_links.bare(card))
    if positives:
        return sorted(positives)
    verdict = live_verdict(card)
    if verdict in CLOSURE_VERDICTS:
        return [verdict]
    blocker = live_blocker(card)
    if blocker in CLOSURE_VERDICTS:
        return [blocker]
    return []


def language_rows() -> list[dict]:
    rows = []
    for path in sorted(READINGS.glob("*.md")):
        stem = path.stem
        if stem in SKIP_READINGS:
            continue
        text = path.read_text(encoding="utf-8")
        card_blocks = reading_cards(text)
        cards = len(card_blocks)
        if not cards:
            continue
        verdicts = Counter(
            outcome for card in card_blocks for outcome in counted_outcomes(card)
        )
        links = sum(
            count for name, count in verdicts.items() if name in POSITIVE_VERDICTS
        )
        en, ar = LANGUAGE_NAMES.get(stem, (stem.replace("-", " ").title(), stem))
        rows.append({"key": stem, "en": en, "ar": ar, "cards": cards, "links": links})
    rows.sort(key=lambda r: -r["cards"])
    return rows


def verdict_totals() -> dict:
    """Issued verdicts across every reading file, split into links and closures."""
    counts: Counter = Counter()
    for path in READINGS.glob("*.md"):
        if path.stem in SKIP_READINGS:
            continue
        cards = reading_cards(path.read_text(encoding="utf-8"))
        counts.update(
            outcome for card in cards for outcome in counted_outcomes(card)
        )
    links = sum(c for name, c in counts.items() if name in POSITIVE_VERDICTS)
    closures = sum(c for name, c in counts.items() if name in CLOSURE_VERDICTS)
    return {
        "links_to_arabic": links,
        "closures": closures,
        "by_verdict": [
            {
                "name": name,
                "count": count,
                "link": name in POSITIVE_VERDICTS,
            }
            for name, count in counts.most_common()
        ],
    }


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
    eligibility = read_json(PROOF_ELIGIBILITY)
    summary = eligibility.get("summary", {}) or {}
    language_blocks = eligibility.get("languages", {}) or {}
    by_language = []
    for language in pre.get("population", {}).get("languages", []):
        block = language_blocks.get(language, {}) or {}
        by_language.append(
            {
                "name": language,
                "eligible": block.get("eligible_family_count", 0),
                "represented": block.get(
                    "represented_current_family_count", 0
                ),
                "positive_families": block.get("positive_family_count", 0),
                "closure_only_families": block.get(
                    "closure_only_family_count", 0
                ),
                "one_member_short": block.get("one_member_short_count", 0),
            }
        )
    return {
        "signed": bool(pre.get("execution_authorized")),
        "registration_status": pre.get("status", ""),
        "frozen_commit": (pre.get("frozen_git_commit") or "")[:7],
        "required_total": thresholds.get("total_eligible_reviewed_families"),
        "required_per_language": thresholds.get(
            "min_eligible_reviewed_families_per_language"
        ),
        "families_tracked": sum(row["represented"] for row in by_language),
        "eligible_now": summary.get("eligible_family_total", 0),
        "trigger_threshold_met": summary.get("trigger_threshold_met", False),
        "proof_executed": summary.get("proof_executed", False),
        "by_language": by_language,
        "counting_law": (
            "A family counts only when every inventory member carries an "
            "issued verdict or recorded terminal closure."
        ),
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
        "verdicts": verdict_totals(),
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
    verdicts = payload["verdicts"]
    print(f"languages open:   {exploration['languages_open']}")
    print(f"cards written:    {exploration['cards_total']}")
    print(f"links to Arabic:  {verdicts['links_to_arabic']}")
    print(f"closures:         {verdicts['closures']}")
    print(f"ledger cards:     {pipeline['cards_total']}")
    print(f"suspended:        {pipeline['suspended']}")
    print(f"released:         {pipeline['released']}")
    print(f"wrote {OUT.relative_to(ROOT)}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
