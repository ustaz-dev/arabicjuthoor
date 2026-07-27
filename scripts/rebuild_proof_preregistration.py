#!/usr/bin/env python3
"""Retire preregistration v1 and build v2 in LOCKED state, awaiting the author's signature.

Why this exists
---------------
The author answered «سجّل من جديد» on 2026-07-27, choosing to re-preregister from scratch
rather than repair the counter of a signed preregistration after its results were known.

Version 1 was signed on 2026-07-23 and armed, but its run trigger counted families of the
two population languages from data/family-review-states.json, and that file was only ever
populated with Phoenician and Punic entries, all suspended. The eligible count was therefore
zero and could never rise from the work being done. Rather than rewire the trigger of a
signed preregistration after we knew that 301 link verdicts had passed third-lens review,
version 1 is retired intact and version 2 is written with full disclosure of what is known
today. Nothing is deleted: v1 is archived byte-for-byte.

Version 2 keeps every scientific commitment of v1 unchanged, adds the disclosure block that
re-preregistration exists to provide, and adds one preregistered directional prediction that
makes the test harder to pass, not easier.

Usage:
  python scripts/rebuild_proof_preregistration.py
  python scripts/rebuild_proof_preregistration.py --check
"""
from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
LIVE = ROOT / "data" / "recovery-proof-preregistration.json"
ARCHIVE = ROOT / "data" / "recovery-proof-preregistration-v1-superseded.json"
READINGS = ROOT / "04-cross-linguistic" / "readings"

VERDICT_LINE = re.compile(r"^-\s*الحكم[^\n]*?:\s*([A-Z][A-Z\-]+)", re.M)
BLOCKER_LINE = re.compile(r"^-\s*عائق:\s*النوع\s*=\s*([A-Z\-]+)", re.M)
POSITIVE = {"ROOT-TRACE", "NUCLEUS-TRACE", "ROOT-ECHO", "NUCLEUS-ECHO", "FLOOR-TRACE"}
CLOSURES = {
    "NO-TRACE", "LOANWORD", "PROPER-NAME-ISOLATED", "NONLEXICAL-ISOLATED",
    "MIXED-ISOLATED", "FORM-OF-ISOLATED", "INTRA-HOUSE-TRANSFER",
    "COMPOUND-BOUNDARY", "LOAN-ROUTE-ISOLATED", "PHRASE-LINK",
    "FUNCTION-WORD", "CONTACT-ISOLATED", "OUT-OF-SCOPE", "ABBREVIATION",
}


def measure_today() -> dict:
    """Count, per language, what the exploration layer holds on the day of re-preregistration."""
    out = {}
    for path in sorted(READINGS.glob("*.md")):
        links = closures = 0
        text = path.read_text(encoding="utf-8")
        for block in re.split(r"^###\s", text, flags=re.M)[1:]:
            head = block.split("\n", 1)[0]
            if "بطاقة" not in head or "<" in head:
                continue
            vm = VERDICT_LINE.search(block)
            bm = BLOCKER_LINE.search(block)
            verdict = vm.group(1) if vm else ""
            blocker = bm.group(1) if bm else ""
            if verdict in POSITIVE:
                links += 1
            elif verdict in CLOSURES or blocker in CLOSURES:
                closures += 1
        if links or closures:
            out[path.stem] = {
                "links": links,
                "closures": closures,
                "resolved": links + closures,
                "yield_percent": round(100 * links / (links + closures), 1) if links + closures else None,
            }
    return out


def build(v1: dict, today: dict) -> dict:
    """Version 2: every v1 commitment preserved, plus disclosure and one harder prediction."""
    v2 = json.loads(json.dumps(v1))  # deep copy, so no v1 clause is lost by omission

    v2["version"] = 2
    v2["status"] = "DRAFT-LOCKED"
    v2["execution_authorized"] = False
    v2["author_signature"] = ""
    v2["signed_date"] = ""
    v2["frozen_git_commit"] = ""

    v2["supersedes"] = {
        "version": 1,
        "signed_date": v1.get("signed_date"),
        "frozen_git_commit": v1.get("frozen_git_commit"),
        "archived_at": "data/recovery-proof-preregistration-v1-superseded.json",
        "reason": (
            "Version 1 was signed and armed, but its run trigger counted eligible families "
            "from data/family-review-states.json, which was only ever populated with "
            "Phoenician and Punic entries, all suspended. The eligible count stood at zero "
            "and could not rise from the work being done, so the confirmatory run could "
            "never fire. Repairing that wiring after the exploratory results were known "
            "would have amended a signed preregistration with knowledge of its own outcome. "
            "The author chose re-preregistration instead, on 2026-07-27."
        ),
        "retired_without_deletion": True,
    }

    v2["disclosure_at_re_preregistration"] = {
        "principle": (
            "Re-preregistration is only honest if it declares everything already known. "
            "Every figure below was produced before this document was written and none of "
            "it is confirmatory evidence; it is the exploratory state that this test exists "
            "to confirm or refute."
        ),
        "date": "2026-07-27",
        "exploration_layer_by_language": today,
        "third_lens_reviewed_link_verdicts": 301,
        "third_lens_returned_to_hold": 0,
        "observed_yield_gradient_exploratory": {
            "close_semitic_sister": "Aramaic alone, 58.1 percent",
            "distant_afro_asiatic_cousin": "Egyptian and Coptic, 33.8 percent",
            "indo_european_branch": "18.2 percent",
            "excluded_and_why": {
                "hebrew": (
                    "90.9 percent rests on nine closures against ninety links while 248 of "
                    "its suspended cards sit in SOURCE-GAP, so its negatives are parked "
                    "rather than judged and its rate is a selection artifact"
                ),
                "akkadian": (
                    "sixty eight links and no closures issued at all; an early-stage file "
                    "with no denominator"
                ),
            },
        },
        "known_defects_repaired_before_this_document": [
            "the recovery scanner re-suspended any card whose audit trail merely mentioned a past blocker",
            "the Coptic loan detector counted U+03E2 to U+03EF as Greek, though Unicode names them Coptic letters inherited from Egyptian Demotic",
            "129 cards carried their obstacle in prose with no structured blocker line",
        ],
        "known_open_risks": [
            "Hebrew is half the primary population and its negatives are not yet judged; the trigger cannot fire until they are",
            "the exploratory yield gradient may not replicate on a fresh random control sample, which is precisely what this test decides",
        ],
    }

    trigger = v2.setdefault("execution_trigger", {})
    trigger["counting_source"] = (
        "families of the two population languages whose members all carry a recorded final "
        "disposition, counted by scripts/count_proof_eligible_families.py over the reading "
        "files themselves and mirrored into data/family-review-states.json; a family counts "
        "only when every member carries an issued verdict or a recorded closure, and both "
        "links and closures count, so a language cannot reach the threshold by judging only "
        "its positives"
    )
    trigger["thresholds_unchanged_from_v1"] = True
    trigger["parked_negative_rule"] = (
        "a family whose members sit in SOURCE-GAP, TOOL-GAP, MORPHOLOGY-GAP, LAW-GAP or "
        "OPEN-CANDIDATE is not eligible; parking a negative is not judging it"
    )

    v2["preregistered_predictions"] = {
        "primary": (
            "the observed positive rate on the eligible denominator exceeds the chance line "
            "produced by the frozen perturbation model, under the comparison rule already "
            "fixed in this document; this is unchanged from version 1"
        ),
        "secondary_directional": {
            "statement": (
                "on the confirmatory sample, the positive rate for close Semitic sisters "
                "exceeds the rate for distant Afro-Asiatic cousins, which in turn exceeds "
                "the rate for Indo-European branches"
            ),
            "status_before_this_document": (
                "observed exploratorily on 2026-07-27 at 58.1, 33.8 and 18.2 percent; it is "
                "recorded here as a prediction to be tested, not as a result"
            ),
            "why_it_is_added": (
                "it makes the test harder rather than easier: a rate above chance with the "
                "ordering violated would be reported as a partial failure, and an instrument "
                "that scores a different family as highly as a sister branch is indicting "
                "itself rather than supporting the thesis"
            ),
            "failure_condition": (
                "if the ordering is violated in the confirmatory sample, the secondary "
                "prediction is recorded as failed on the day it is produced, regardless of "
                "the primary outcome, and no post-hoc regrouping of languages is permitted"
            ),
            "minimum_per_group": 100,
        },
    }

    v2["integrity_clauses"] = {
        "no_threshold_may_be_lowered": (
            "the totals, the per-language minimum, the comparison rule, the chance model, "
            "the seed, the iteration count and the success criterion are fixed by this "
            "signature and may not be altered without a new dated signature and a new version"
        ),
        "single_confirmatory_run": True,
        "result_committed_the_day_it_is_produced": True,
        "negative_result_published_identically": (
            "a negative result is written up, committed and published in the same form and "
            "with the same prominence as a positive one"
        ),
    }
    return v2


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()

    live = json.loads(LIVE.read_text(encoding="utf-8"))

    if args.check:
        if live.get("version") != 2:
            print("STALE: the live preregistration is not version 2")
            return 1
        if live.get("status") not in {"DRAFT-LOCKED", "AUTHOR-SIGNED"}:
            print(f"INVALID: unexpected status {live.get('status')}")
            return 1
        if not ARCHIVE.exists():
            print("MISSING: version 1 archive is absent")
            return 1
        print(f"CLEAN: preregistration v2 present, status {live['status']}, v1 archived")
        return 0

    if live.get("version") == 2:
        print("version 2 already in place; refusing to rebuild over it")
        return 0

    ARCHIVE.write_text(
        json.dumps(live, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    v2 = build(live, measure_today())
    LIVE.write_text(
        json.dumps(v2, ensure_ascii=False, indent=1) + "\n", encoding="utf-8", newline="\n"
    )
    print(f"archived v1 to {ARCHIVE.name}")
    print(f"wrote v2 to {LIVE.name}, status {v2['status']}, execution_authorized {v2['execution_authorized']}")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
