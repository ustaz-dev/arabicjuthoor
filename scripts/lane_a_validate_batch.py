#!/usr/bin/env python3
"""Read-only validator for lane A discovery batches.

The validator never rewrites a reading.  Its default scope is card blocks
appended after the measured 2026-07-29 lane A baseline.  It counts judgments
by a composite identity made from the family ID and the explicitly judged
Kaikki member IDs, not by Markdown headings.
"""

from __future__ import annotations

import argparse
import bisect
import hashlib
import json
import re
import sys
import unicodedata
from dataclasses import dataclass
from functools import cached_property
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"

FILES = {
    "aramaic": READINGS / "aramaic.md",
    "hebrew": READINGS / "hebrew.md",
}

# Measured before lane A began adding cards on 2026-07-29.  The complete-file
# hashes identify that baseline exactly.  Appended cards are selected by their
# header line, so historical cards remain outside the default validation scope.
BASELINE = {
    "aramaic": {
        "last_line": 86232,
        "sha256": "453d8f5f7ecf5f5b28bf1872bcf8c1b1dd5a00634601da244a5a9de1dd039d33",
    },
    "hebrew": {
        "last_line": 32153,
        "sha256": "1fcabd1866f1a8c4ea8e1727b2b23d281e4ff2617e44c2c202fbf595634772e8",
    },
}

POSITIVE_VERDICTS = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}

TERMINAL_CLOSURES = {
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

PARKED_STATES = {
    "SOURCE-GAP",
    "TOOL-GAP",
    "MORPHOLOGY-GAP",
    "LAW-GAP",
    "OPEN-CANDIDATE",
}

# These labels are the independent historical works recognized by the Arabic
# fan tool.  The modern Arabic-English fallback is deliberately not accepted
# as one of the two old sources required for an issued link.
OLD_ARABIC_SOURCES = {
    "lisan": "لسان العرب",
    "taj": "تاج العروس",
    "sihah": "صحاح العربية",
    "muhkam": "المحكم والمحيط الأعظم",
    "ayn": "كتاب العين",
    "asas": "أساس البلاغة",
    "mufradat": "المفردات في غريب القرآن",
    "misbah": "المصباح المنير",
    "muhit": "المحيط",
}

HEADER_RE = re.compile(
    r"^### (?:بطاقة|مراجعة عضوية|إعادةُ توسيم).*$",
    re.MULTILINE,
)
FAMILY_RE = re.compile(r"(?:aramaic|hebrew):family:[0-9a-f]+")
ENTRY_RE = re.compile(r"kaikki_(?:aramaic|hebrew):[^`\s،؛\]\)\.]+")
VERDICT_RE = re.compile(r"^- الحكم[^\n]*?:\s*(?P<body>.*)$", re.MULTILINE)
BLOCKER_RE = re.compile(
    r"^- عائق:\s*النوع=(?P<state>[A-Z][A-Z\-]+)(?P<body>.*)$",
    re.MULTILINE,
)
ORBIT_RE = re.compile(r"^- المدار:\s*(?P<body>.*)$", re.MULTILINE)
OLDEST_FORM_RE = re.compile(
    r"^- أقدمُ صورةٍ مستعادة:\s*(?P<body>.*)$",
    re.MULTILINE,
)
DESTINY_REVIEW_RE = re.compile(
    r"^- مراجعة المصير:\s*(?P<body>.*)$",
    re.MULTILINE,
)
TERMINAL_REOPEN_RE = re.compile(
    r"^- مراجعة إغلاق نهائي:\s*(?P<body>.*)$",
    re.MULTILINE,
)
MEMBER_LINE_RE = re.compile(
    r"^- العضو:\s*`(?P<entry>kaikki_(?:aramaic|hebrew):[^`]+)`",
    re.MULTILINE,
)
OUTCOME_TOKEN_RE = re.compile(r"\b([A-Z][A-Z\-]+)\b")


@dataclass(frozen=True)
class Card:
    language: str
    path: Path
    start_line: int
    heading: str
    text: str

    @cached_property
    def family_id(self) -> str:
        match = FAMILY_RE.search(self.heading)
        return match.group(0) if match else ""

    @cached_property
    def verdict_line(self) -> str:
        match = VERDICT_RE.search(self.text)
        return match.group("body").strip() if match else ""

    @cached_property
    def blocker_state(self) -> str:
        match = BLOCKER_RE.search(self.text)
        return match.group("state") if match else ""

    @cached_property
    def blocker_line(self) -> str:
        match = BLOCKER_RE.search(self.text)
        return match.group(0).strip() if match else ""

    @cached_property
    def orbit(self) -> str:
        match = ORBIT_RE.search(self.text)
        return match.group("body").strip() if match else ""

    @cached_property
    def oldest_form(self) -> str:
        match = OLDEST_FORM_RE.search(self.text)
        return match.group("body").strip() if match else ""

    @cached_property
    def destiny_review(self) -> str:
        match = DESTINY_REVIEW_RE.search(self.text)
        return match.group("body").strip() if match else ""

    @cached_property
    def terminal_reopen_review(self) -> str:
        match = TERMINAL_REOPEN_RE.search(self.text)
        return match.group("body").strip() if match else ""

    @cached_property
    def is_member_review(self) -> bool:
        return self.heading.startswith("### مراجعة عضوية:")

    @cached_property
    def documents_pending_reopen(self) -> bool:
        review = self.destiny_review
        return (
            self.is_member_review
            and bool(review)
            and "السابق" in review
            and "محفوظ" in review
        )

    @cached_property
    def documents_terminal_reopen(self) -> bool:
        # A terminal closure is stronger than a parked candidate.  Reopening it
        # therefore needs its own explicit field, naming the former closure,
        # the reason it was overturned, its evidence, and third-lens review.
        review = self.terminal_reopen_review
        return (
            self.is_member_review
            and all(
                token in review
                for token in (
                    "السابق=",
                    "سبب النقض=",
                    "السند=",
                    "المراجعة الثالثة=",
                )
            )
        )

    @cached_property
    def outcome(self) -> str:
        token = OUTCOME_TOKEN_RE.match(self.verdict_line)
        if token and token.group(1) in POSITIVE_VERDICTS | TERMINAL_CLOSURES:
            return token.group(1)
        if self.blocker_state in TERMINAL_CLOSURES:
            return self.blocker_state
        return ""

    @cached_property
    def verdict_member_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(ENTRY_RE.findall(self.verdict_line))))

    @cached_property
    def blocker_member_ids(self) -> tuple[str, ...]:
        return tuple(sorted(set(ENTRY_RE.findall(self.blocker_line))))

    @cached_property
    def member_ids(self) -> tuple[str, ...]:
        # The live verdict is authoritative.  The blocker is the second live
        # field used by closure cards.  Explicit member rows are a fallback for
        # multi-member structural closures.  Do not scan the whole card, since
        # recovery notes may mention neighboring members that are not judged.
        members = list(self.verdict_member_ids)
        if not members:
            members = list(self.blocker_member_ids)
        if not members:
            members = MEMBER_LINE_RE.findall(self.text)
        return tuple(sorted(set(members)))

    @cached_property
    def identity(self) -> str:
        if not self.family_id:
            return ""
        if self.member_ids:
            return self.family_id + "|" + "|".join(self.member_ids)
        return self.family_id + "|UNSCOPED"

    @cached_property
    def source_ids(self) -> tuple[str, ...]:
        return tuple(
            source_id
            for source_id, label in OLD_ARABIC_SOURCES.items()
            if label in self.text
        )

    @cached_property
    def source_excerpt_ids(self) -> tuple[str, ...]:
        return tuple(
            source_id
            for source_id, label in OLD_ARABIC_SOURCES.items()
            if re.search(
                rf"^\s{{2,}}-\s+[^\n]*{re.escape(label)}[^\n]*:\s*«",
                self.text,
                re.MULTILINE,
            )
        )

    @cached_property
    def outcome_kind(self) -> str:
        if self.outcome in POSITIVE_VERDICTS:
            return "positive"
        if self.outcome in TERMINAL_CLOSURES:
            return "closure"
        return "pending"


def read_cards(language: str, path: Path) -> tuple[str, list[Card]]:
    text = unicodedata.normalize("NFC", path.read_text(encoding="utf-8"))
    matches = list(HEADER_RE.finditer(text))
    newline_offsets = [match.start() for match in re.finditer("\n", text)]
    cards: list[Card] = []
    for index, match in enumerate(matches):
        end = matches[index + 1].start() if index + 1 < len(matches) else len(text)
        heading = match.group(0)
        if "<" in heading:
            continue
        start_line = bisect.bisect_left(newline_offsets, match.start()) + 1
        cards.append(
            Card(
                language=language,
                path=path,
                start_line=start_line,
                heading=heading,
                text=text[match.start() : end],
            )
        )
    return text, cards


def baseline_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def identity_sets(cards: list[Card]) -> dict[str, set[str]]:
    # Append-only readings can revisit the same judgment identity.  The last
    # live card wins for that identity; counting every historical card would
    # turn revisions into new discoveries.
    latest: dict[str, str] = {}
    for card in cards:
        if card.identity:
            latest[card.identity] = card.outcome_kind
    result = {"positive": set(), "closure": set(), "pending": set()}
    for identity, kind in latest.items():
        result[kind].add(identity)
    return result


def latest_cards_by_identity(cards: list[Card]) -> dict[str, Card]:
    latest: dict[str, Card] = {}
    for card in cards:
        if card.identity:
            latest[card.identity] = card
    return latest


def explicit_orbit_complete(orbit: str) -> bool:
    if not orbit:
        return False
    folded = orbit.replace("ُ", "").replace("ِ", "").replace("َ", "")
    branch = "جوار المعنى في الفرع" in folded or "جوار الفرع" in folded
    arabic = "جوار المعنى في العربية" in folded or "جوار العربية" in folded
    meeting = (
        "موضع الالتقاء" in folded
        or "التقيا" in folded
        or "تلتقي" in folded
        or "يلتقي" in folded
    )
    return branch and arabic and meeting


def has_published_old_hebrew_anchor(card: Card) -> bool:
    """Require an old witness or an explicit inherited proto-form.

    A modern quotation is useful for the gloss but cannot truthfully be
    labelled the oldest restored form.  The accepted strings below are
    retrieval anchors already present in the approved local Hebrew source and
    its temporal-witness export; they do not add a new source.
    """

    old = card.oldest_form
    if not old:
        return False
    old_markers = (
        "Tanach",
        "Tanakh",
        "Hebrew Bible",
        "Bible",
        "Genesis",
        "Exodus",
        "Leviticus",
        "Numbers",
        "Deuteronomy",
        "Mishnah",
        "Mishnaic",
        "Talmud",
        "Tosefta",
        "Midrash",
    )
    if any(marker in old for marker in old_markers):
        return True
    return "From Proto-Semitic" in card.text or "Proto-Semitic *" in card.text


def validate_card(card: Card, baseline_sets: dict[str, set[str]]) -> list[str]:
    issues: list[str] = []
    label = f"{card.path.name}:{card.start_line}"

    if not card.family_id:
        issues.append(f"{label}: لا معرّف أسرة في رأس البطاقة")
    if not card.blocker_line:
        issues.append(f"{label}: لا سطر عائق حي منظم")
    if not card.verdict_line:
        issues.append(f"{label}: لا سطر حكم حي")
    if not card.orbit:
        issues.append(f"{label}: لا سطر مدار")
    if not card.member_ids:
        issues.append(f"{label}: لا معرّف عضو محكوم، فلا دلتا قابلة لإعادة العد")

    if card.outcome_kind == "positive":
        if not card.verdict_member_ids:
            issues.append(
                f"{label}: الحكم الموجب لا يسمّي معرّف العضو في سطر الحكم"
            )
        if len(card.source_ids) < 2:
            named = ",".join(card.source_ids) if card.source_ids else "صفر"
            issues.append(
                f"{label}: صلة موجبة بلا مصدرين عربيين قديمين مستقلين "
                f"(المسمى={named})"
            )
        if len(card.source_excerpt_ids) < 2:
            named = (
                ",".join(card.source_excerpt_ids)
                if card.source_excerpt_ids
                else "صفر"
            )
            issues.append(
                f"{label}: الصلة لا تعرض مقتطفين فعليين من مصدرين قديمين "
                f"مستقلين (المعروض={named})"
            )
        if not explicit_orbit_complete(card.orbit):
            issues.append(
                f"{label}: المدار لا يسمي جوار الفرع وجوار العربية وموضع الالتقاء"
            )
        if card.language == "hebrew" and not has_published_old_hebrew_anchor(card):
            issues.append(
                f"{label}: الصلة العبرية لا تحمل شاهدًا قديمًا منشورًا ولا "
                "تصريح inheritance من صورة سامية أم"
            )
        if (
            card.language == "hebrew"
            and re.search(r"\b(?:19|20)\d{2}\b", card.oldest_form)
            and "قديم" in card.oldest_form
        ):
            issues.append(
                f"{label}: مثال حديث وُصف خطأ بأنه أقدم صورة أو شاهد قديم"
            )
        orbit_lower = card.orbit.lower()
        if (
            "موضع الالتقاء" in card.orbit
            and "حقل التأثيل" in card.orbit
            and "cognate" in orbit_lower
        ):
            issues.append(
                f"{label}: موضع الالتقاء يعيد قرينة cognate الاشتقاقية "
                "ولا يثبت التقاء جواري المعنى للحس"
            )
        blocker_targets_same_member = (
            not card.blocker_member_ids
            or not card.verdict_member_ids
            or bool(
                set(card.blocker_member_ids).intersection(card.verdict_member_ids)
            )
        )
        if card.blocker_state in PARKED_STATES and blocker_targets_same_member:
            issues.append(
                f"{label}: تناقض حي، حكم موجب مع عائق راقد {card.blocker_state}"
            )
        if "غير صادر" in card.verdict_line:
            issues.append(f"{label}: سطر الحكم يجمع حكمًا موجبًا وعبارة غير صادر")

    if card.outcome_kind == "closure":
        token = OUTCOME_TOKEN_RE.match(card.verdict_line)
        verdict_token = token.group(1) if token else ""
        if (
            verdict_token in POSITIVE_VERDICTS
            and card.blocker_state in TERMINAL_CLOSURES
        ):
            issues.append(
                f"{label}: تناقض حي، حكم موجب مع إغلاق {card.blocker_state}"
            )

    if card.identity:
        old_kind = next(
            (
                kind
                for kind in ("positive", "closure", "pending")
                if card.identity in baseline_sets[kind]
            ),
            "",
        )
        if old_kind == card.outcome_kind and card.outcome_kind != "pending":
            issues.append(
                f"{label}: المصير ليس جديدًا، الهوية نفسها موجودة في خط الأساس "
                f"بوصفها {old_kind}"
            )
        elif (
            old_kind == "pending"
            and card.outcome_kind in {"positive", "closure"}
            and card.documents_pending_reopen
        ):
            pass
        elif (
            old_kind == "closure"
            and card.outcome_kind == "positive"
            and card.documents_terminal_reopen
        ):
            pass
        elif old_kind and old_kind != card.outcome_kind:
            issues.append(
                f"{label}: تغيّر مصير هوية قائمة من {old_kind} إلى "
                f"{card.outcome_kind}، ويحتاج وسم المراجعة المناسب صريحًا"
            )

    return issues


def summarize(
    language: str,
    all_cards: list[Card],
    selected: list[Card],
    baseline_cards: list[Card],
) -> dict:
    baseline_sets = identity_sets(baseline_cards)
    selected_sets = identity_sets(selected)
    new_positives = selected_sets["positive"] - (
        baseline_sets["positive"] | baseline_sets["closure"]
    )
    new_closures = selected_sets["closure"] - (
        baseline_sets["positive"] | baseline_sets["closure"]
    )
    selected_latest = latest_cards_by_identity(selected)
    positive_distribution: dict[str, int] = {}
    closure_distribution: dict[str, int] = {}
    for identity in sorted(new_positives):
        outcome = selected_latest[identity].outcome
        positive_distribution[outcome] = positive_distribution.get(outcome, 0) + 1
    for identity in sorted(new_closures):
        outcome = selected_latest[identity].outcome
        closure_distribution[outcome] = closure_distribution.get(outcome, 0) + 1
    issues = [
        issue
        for card in selected
        for issue in validate_card(card, baseline_sets)
    ]
    return {
        "language": language,
        "all_card_blocks": len(all_cards),
        "all_unique_families": len(
            {card.family_id for card in all_cards if card.family_id}
        ),
        "baseline_card_blocks": len(baseline_cards),
        "baseline_unique_families": len(
            {card.family_id for card in baseline_cards if card.family_id}
        ),
        "baseline_positive_identities": len(baseline_sets["positive"]),
        "baseline_closure_identities": len(baseline_sets["closure"]),
        "baseline_pending_identities": len(baseline_sets["pending"]),
        "baseline_unscoped_positive_identities": sum(
            identity.endswith("|UNSCOPED")
            for identity in baseline_sets["positive"]
        ),
        "baseline_unscoped_closure_identities": sum(
            identity.endswith("|UNSCOPED")
            for identity in baseline_sets["closure"]
        ),
        "selected_card_blocks": len(selected),
        "selected_positive_identities": len(selected_sets["positive"]),
        "selected_closure_identities": len(selected_sets["closure"]),
        "selected_pending_identities": len(selected_sets["pending"]),
        "new_positive_identities": len(new_positives),
        "new_closure_identities": len(new_closures),
        "new_positive_distribution": positive_distribution,
        "new_closure_distribution": closure_distribution,
        "issues": issues,
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Validate lane A Aramaic and Hebrew discovery cards."
    )
    parser.add_argument(
        "--scope",
        choices=("new", "baseline", "all"),
        default="new",
        help="Card scope to validate. Default: cards appended after the baseline.",
    )
    parser.add_argument(
        "--language",
        choices=("aramaic", "hebrew", "both"),
        default="both",
    )
    parser.add_argument("--json", action="store_true", help="Print JSON.")
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Return exit code 1 when a selected card has a validation issue.",
    )
    return parser.parse_args()


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    args = parse_args()
    languages = FILES if args.language == "both" else {args.language: FILES[args.language]}
    summaries = []

    for language, path in languages.items():
        text, all_cards = read_cards(language, path)
        cutoff = BASELINE[language]["last_line"]
        baseline_cards = [card for card in all_cards if card.start_line <= cutoff]
        new_cards = [card for card in all_cards if card.start_line > cutoff]
        if args.scope == "new":
            selected = new_cards
        elif args.scope == "baseline":
            selected = baseline_cards
        else:
            selected = all_cards
        summary = summarize(language, all_cards, selected, baseline_cards)
        summary["baseline_complete_file_hash_matches"] = (
            baseline_hash(text) == BASELINE[language]["sha256"]
        )
        summary["baseline_last_line"] = cutoff
        summaries.append(summary)

    result = {
        "scope": args.scope,
        "positive_definition": sorted(POSITIVE_VERDICTS),
        "closure_definition": sorted(TERMINAL_CLOSURES),
        "languages": summaries,
        "new_positive_identities": sum(
            item["new_positive_identities"] for item in summaries
        ),
        "new_closure_identities": sum(
            item["new_closure_identities"] for item in summaries
        ),
        "issues": sum(len(item["issues"]) for item in summaries),
    }

    if args.json:
        print(json.dumps(result, ensure_ascii=False, indent=2))
    else:
        print(f"scope={result['scope']}")
        for item in summaries:
            print(
                f"{item['language']}: cards={item['all_card_blocks']}; "
                f"families={item['all_unique_families']}; "
                f"baseline-positive-identities="
                f"{item['baseline_positive_identities']}; "
                f"baseline-closure-identities="
                f"{item['baseline_closure_identities']}; "
                f"baseline-unscoped-positive="
                f"{item['baseline_unscoped_positive_identities']}; "
                f"baseline-unscoped-closure="
                f"{item['baseline_unscoped_closure_identities']}; "
                f"selected={item['selected_card_blocks']}; "
                f"new-positive={item['new_positive_identities']}; "
                f"new-closure={item['new_closure_identities']}; "
                f"issues={len(item['issues'])}"
            )
            for issue in item["issues"]:
                print(f"ISSUE: {issue}")
        print(f"new-positive-identities={result['new_positive_identities']}")
        print(f"new-closure-identities={result['new_closure_identities']}")
        print(f"issues={result['issues']}")

    return 1 if args.strict and result["issues"] else 0


if __name__ == "__main__":
    sys.exit(main())
