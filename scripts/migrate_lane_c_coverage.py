#!/usr/bin/env python3
"""Compact Lane C non-verdict cards into one machine coverage row per member.

This is a lane-local migration.  It never invokes Git, a shared builder, or
the proof line.  Positive and final-closure RECOVERY-v2 cards remain byte-for-
byte in their reading files.  Only cards whose direct verdict is explicitly
not issued are removed and represented in lane_c_coverage.jsonl.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import sys
import unicodedata
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path
from typing import Iterable, TextIO


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
DATA = ROOT / "04-cross-linguistic" / "data"
AUDITS = ROOT / "05-audits"
COVERAGE = DATA / "lane_c_coverage.jsonl"
AUDIT = AUDITS / "2026-07-30-lane-c-coverage-compaction.md"

LANGUAGES = (
    ("ancient_greek", "اليونانية القديمة", "ancient-greek.md"),
    ("latin", "اللاتينية القديمة", "old-latin.md"),
    ("persian", "الفارسية", "persian.md"),
    ("gothic", "القوطية", "gothic.md"),
    ("old_norse", "النوردية القديمة", "old-norse.md"),
    ("welsh", "الويلزية", "welsh.md"),
)

REQUIRED_ROW_FIELDS = (
    "member_id",
    "language",
    "form",
    "branch_meaning",
    "non_issuance_reason",
    "batch_number",
)

ENTRY_RE = re.compile(
    r"(?:kaikki_[^:`\s]+(?::\d{4}_\d{2}_\d{2})?|kaikki_[^:`\s]+):"
    r"\d+:[^`\s\]]+"
)
FIELD_RE = re.compile(r"(?m)^- ([^:\n]+):\s*(.*)$")
BATCH_RE = re.compile(r"(?:الدفعة|batch)\s*([0-9]+)", re.IGNORECASE)
TOP_LEVEL_COMMENT_RE = re.compile(
    r"^<!-- (?:/"
    r"|LANE-C"
    r"|RECOVERY-PROTOCOL"
    r"|RADIATION-FIELDS"
    r"|TRACK-"
    r"|FAR-BRANCH"
    r"|WEEK-DAY"
    r"|THIRD-LENS"
    r"|GOTHIC-HUMAN"
    r"|GOTHIC-GIBLA)"
)

POSITIVE_VERDICTS = (
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
)
CLOSURE_VERDICTS = ("LOANWORD", "NO-TRACE")
NON_VERDICT_MARKERS = (
    "غير صادر",
    "لا حكم",
    "موقوف",
    "لا توقيع",
)


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def clean_value(value: str) -> str:
    return " ".join(nfc(value).strip().split())


def field_values(block: str, label: str) -> list[str]:
    return [
        clean_value(value)
        for name, value in FIELD_RE.findall(block)
        if clean_value(name) == label
    ]


def last_field(block: str, label: str) -> str:
    values = field_values(block, label)
    return values[-1] if values else ""


def is_template(block: str) -> bool:
    heading = block.splitlines()[0] if block.splitlines() else ""
    protocol = last_field(block, "إصدارُ البروتوكول")
    return (
        "<الكلمة" in heading
        or "<معناها" in heading
        or "<" in protocol
    )


def classify_card(block: str) -> str:
    """Return template, open, positive, closure, or ambiguous."""

    if is_template(block):
        return "template"
    verdict = last_field(block, "الحكم (استكشاف)")
    state = last_field(block, "حالةُ الإغلاق")
    if any(marker in verdict for marker in NON_VERDICT_MARKERS):
        return "open"
    if any(marker in verdict for marker in POSITIVE_VERDICTS):
        return "positive"
    if any(marker in verdict for marker in CLOSURE_VERDICTS):
        return "closure"
    heading = block.splitlines()[0] if block.splitlines() else ""
    if "مرشح موقوف" in heading:
        return "open"
    if not verdict and (
        state.startswith("OPEN")
        or state.endswith("-GAP")
        or state in {"TOOL-GAP", "LAW-GAP", "SOURCE-GAP", "MORPHOLOGY-GAP"}
    ):
        return "open"
    return "ambiguous"


def strip_citation(value: str) -> str:
    value = clean_value(value)
    value = re.sub(r"\s*\[[^\[\]]*]\.?$", "", value)
    return value.strip()


def extract_form(block: str) -> str:
    value = last_field(block, "الكلمةُ في الفرع")
    if value:
        value = re.sub(r"\s*\[[^\[\]]*]\.?$", "", value).strip()
        return value or "(غير مسجل في البطاقة)"
    heading = block.splitlines()[0].partition(":")[2].strip()
    heading = re.sub(r"\s*\([^()]*\)\s*$", "", heading)
    heading = re.sub(r"^`[^`]+`،\s*", "", heading)
    return clean_value(heading) or "(غير مسجل في البطاقة)"


def extract_meaning(block: str) -> str:
    value = last_field(block, "المعنى من قاموس الفرع")
    if not value:
        return "(غير مسجل في البطاقة)"
    match = re.search(r"«(.*)»(?:\s*\[[^\[\]]*])?\.?$", value)
    if match:
        return clean_value(match.group(1))
    return strip_citation(value).strip("«»") or "(غير مسجل في البطاقة)"


def extract_reason(block: str) -> str:
    verdict = last_field(block, "الحكم (استكشاف)")
    state = last_field(block, "حالةُ الإغلاق")
    obstacle = last_field(block, "عائق")
    parts: list[str] = []
    if state:
        parts.append(state.rstrip("."))
    if obstacle and obstacle not in parts:
        parts.append(obstacle.rstrip("."))
    detailed_verdict = verdict.rstrip(".")
    if detailed_verdict and detailed_verdict not in {"غير صادر", "لا حكم"}:
        parts.append(detailed_verdict)
    if not parts:
        parts.append("الحكم غير صادر في البطاقة")
    return "؛ ".join(dict.fromkeys(parts))


def extract_member_id(block: str, language: str) -> tuple[str, bool]:
    branch = last_field(block, "الكلمةُ في الفرع")
    matches = list(dict.fromkeys(ENTRY_RE.findall(branch)))
    if not matches:
        matches = list(dict.fromkeys(ENTRY_RE.findall(block)))
    if matches:
        return matches[0], False

    branch_ticks = re.findall(r"`([^`\n]+)`", branch)
    for token in reversed(branch_ticks):
        if ":" in token and ("en-" in token or token.startswith(language + ":")):
            return clean_value(token), False

    heading = block.splitlines()[0] if block.splitlines() else ""
    digest_source = "\n".join(
        (
            language,
            heading,
            extract_form(block),
            extract_meaning(block),
        )
    )
    digest = hashlib.sha256(nfc(digest_source).encode("utf-8")).hexdigest()[:24]
    return f"lane-c:{language}:legacy:{digest}", True


def batch_number(section_heading: str, card_heading: str) -> int:
    for source in (section_heading, card_heading):
        match = BATCH_RE.search(source)
        if match:
            return int(match.group(1))
    # Historical Lane C material predating the explicitly numbered standing
    # queue is assigned batch 0 rather than inventing a historical number.
    return 0


@dataclass
class FileStats:
    language: str
    language_ar: str
    filename: str
    before_bytes: int
    after_bytes: int = 0
    open_cards_removed: int = 0
    superseded_open_cards: int = 0
    coverage_rows: int = 0
    positive_cards: int = 0
    closure_cards: int = 0
    templates: int = 0
    synthetic_ids: int = 0
    missing_forms: int = 0
    missing_meanings: int = 0
    identities_before: set[str] = field(default_factory=set)
    retained_identities: set[str] = field(default_factory=set)
    ambiguous: list[str] = field(default_factory=list)

    @property
    def full_cards_remaining(self) -> int:
        return self.positive_cards + self.closure_cards


@dataclass
class ScanResult:
    stats: FileStats
    rows: list[dict[str, object]]
    open_ids: set[str]


def write_or_count_card(
    block_lines: list[str],
    section_heading: str,
    language: str,
    stats: FileStats,
    rows: list[dict[str, object]],
    open_ids: set[str],
    output: TextIO | None,
) -> None:
    block = "".join(block_lines)
    kind = classify_card(block)
    if kind == "template":
        stats.templates += 1
        if output is not None:
            output.write(block)
        return

    member_id, synthetic = extract_member_id(block, language)
    stats.identities_before.add(member_id)
    if synthetic:
        stats.synthetic_ids += 1

    if kind == "open":
        form = extract_form(block)
        meaning = extract_meaning(block)
        if form == "(غير مسجل في البطاقة)":
            stats.missing_forms += 1
        if meaning == "(غير مسجل في البطاقة)":
            stats.missing_meanings += 1
        row = {
            "member_id": member_id,
            "language": language,
            "form": form,
            "branch_meaning": meaning,
            "non_issuance_reason": extract_reason(block),
            "batch_number": batch_number(
                section_heading,
                block_lines[0].rstrip("\r\n"),
            ),
        }
        rows.append(row)
        open_ids.add(member_id)
        stats.open_cards_removed += 1
        return

    if kind == "positive":
        stats.positive_cards += 1
        stats.retained_identities.add(member_id)
    elif kind == "closure":
        stats.closure_cards += 1
        stats.retained_identities.add(member_id)
    else:
        heading = block_lines[0].rstrip("\r\n")
        verdict = last_field(block, "الحكم (استكشاف)") or "(مفقود)"
        state = last_field(block, "حالةُ الإغلاق") or "(مفقود)"
        stats.ambiguous.append(
            f"{heading} | الحالة={state} | الحكم={verdict}"
        )
    if output is not None:
        output.write(block)


def scan_file(
    language: str,
    language_ar: str,
    filename: str,
    output_path: Path | None = None,
) -> ScanResult:
    path = READINGS / filename
    stats = FileStats(
        language=language,
        language_ar=language_ar,
        filename=filename,
        before_bytes=path.stat().st_size,
    )
    rows: list[dict[str, object]] = []
    open_ids: set[str] = set()
    output: TextIO | None = None
    if output_path is not None:
        output = output_path.open("w", encoding="utf-8", newline="\n")

    section_heading = ""
    card_lines: list[str] | None = None
    try:
        with path.open("r", encoding="utf-8", newline=None) as source:
            for line in source:
                is_boundary = bool(
                    re.match(r"^#{1,6} ", line)
                    or TOP_LEVEL_COMMENT_RE.match(line)
                )
                if card_lines is not None and is_boundary:
                    write_or_count_card(
                        card_lines,
                        section_heading,
                        language,
                        stats,
                        rows,
                        open_ids,
                        output,
                    )
                    card_lines = None

                if line.startswith("## "):
                    section_heading = line.rstrip("\r\n")

                if line.startswith("### بطاقة:"):
                    card_lines = [line]
                elif card_lines is not None:
                    card_lines.append(line)
                elif output is not None:
                    output.write(line)

            if card_lines is not None:
                write_or_count_card(
                    card_lines,
                    section_heading,
                    language,
                    stats,
                    rows,
                    open_ids,
                    output,
                )
    finally:
        if output is not None:
            output.close()

    unsuperseded_rows = [
        row
        for row in rows
        if str(row["member_id"]) not in stats.retained_identities
    ]
    stats.superseded_open_cards = len(rows) - len(unsuperseded_rows)
    rows = unsuperseded_rows
    open_ids = {str(row["member_id"]) for row in rows}
    stats.coverage_rows = len(rows)
    if output_path is not None:
        stats.after_bytes = output_path.stat().st_size
    return ScanResult(stats=stats, rows=rows, open_ids=open_ids)


def scan_all() -> list[ScanResult]:
    return [
        scan_file(language, language_ar, filename)
        for language, language_ar, filename in LANGUAGES
    ]


def validate_preflight(results: list[ScanResult]) -> None:
    problems: list[str] = []
    all_open: dict[str, str] = {}
    for result in results:
        stats = result.stats
        if stats.ambiguous:
            preview = "\n    ".join(stats.ambiguous[:12])
            problems.append(
                f"{stats.filename}: {len(stats.ambiguous)} ambiguous cards:\n"
                f"    {preview}"
            )
        if (
            stats.open_cards_removed
            != stats.coverage_rows + stats.superseded_open_cards
        ):
            problems.append(
                f"{stats.filename}: removed={stats.open_cards_removed}, "
                f"rows={stats.coverage_rows}, "
                f"superseded={stats.superseded_open_cards}"
            )
        for row in result.rows:
            member_id = str(row["member_id"])
            prior = all_open.get(member_id)
            if prior is not None:
                problems.append(
                    f"duplicate open member id: {member_id} "
                    f"({prior}, {stats.filename})"
                )
            else:
                all_open[member_id] = stats.filename
            if tuple(row.keys()) != REQUIRED_ROW_FIELDS:
                problems.append(
                    f"{stats.filename}: invalid row fields for {member_id}"
                )
            if not isinstance(row["batch_number"], int):
                problems.append(
                    f"{stats.filename}: non-integer batch for {member_id}"
                )
    if problems:
        raise RuntimeError("\n".join(problems[:80]))


def compact_number(value: int) -> str:
    return f"{value:,}"


def size_label(value: int) -> str:
    return f"{value:,} بايت ({value / 1_000_000:.3f} MB)"


def audit_text(results: list[ScanResult], coverage_bytes: int) -> str:
    rows = []
    for result in results:
        stats = result.stats
        before_registered = len(stats.identities_before)
        after_registered = len(stats.retained_identities | result.open_ids)
        rows.append(
            "| "
            + " | ".join(
                (
                    stats.filename,
                    size_label(stats.before_bytes),
                    size_label(stats.after_bytes),
                    compact_number(stats.coverage_rows),
                    compact_number(stats.superseded_open_cards),
                    compact_number(stats.full_cards_remaining),
                    compact_number(stats.positive_cards),
                    compact_number(stats.closure_cards),
                    compact_number(before_registered),
                    compact_number(after_registered),
                )
            )
            + " |"
        )

    total_moved = sum(result.stats.coverage_rows for result in results)
    total_full = sum(result.stats.full_cards_remaining for result in results)
    total_positive = sum(result.stats.positive_cards for result in results)
    total_closure = sum(result.stats.closure_cards for result in results)
    before_members = set().union(
        *(result.stats.identities_before for result in results)
    )
    after_members = set().union(
        *(
            result.stats.retained_identities | result.open_ids
            for result in results
        )
    )
    synthetic = sum(result.stats.synthetic_ids for result in results)
    missing_forms = sum(result.stats.missing_forms for result in results)
    missing_meanings = sum(result.stats.missing_meanings for result in results)
    if before_members != after_members:
        raise RuntimeError(
            "registered member identity set changed while building audit"
        )

    return nfc(
        f"""# محضر ضغط تغطية المسار ج

التاريخ: 2026-07-30

## القرار البنيوي

أعيد تمثيل العضو الذي لا يحمل حكمًا صادرًا بسطر آلي واحد في
`04-cross-linguistic/data/lane_c_coverage.jsonl`. بقيت بطاقة
`RECOVERY-v2` كاملة في ملف القراءة لكل صلة موجبة ولكل إغلاق نهائي.
لم يُشغّل Git، ولا باني مشترك، ولا خط البرهان.

يحمل كل سطر الحقول الستة الآتية فقط: `member_id`، `language`، `form`،
`branch_meaning`، `non_issuance_reason`، `batch_number`. الرقم `0` يعني
مادة تاريخية سبقت ترقيم دفعات الطابور الدائم ولم يُخترع لها رقم قديم.

## القياس قبل التحويل وبعده

| الملف | الحجم قبل | الحجم بعد | المنقول إلى JSONL | نسخ بلا حكم أزيلت لأن للعضو حكمًا نافذًا | البطاقات الكاملة الباقية | الصلات | الإغلاقات | الأعضاء قبل | الأعضاء بعد |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|
{os.linesep.join(rows)}
| **المجموع** | — | — | **{compact_number(total_moved)}** | **{compact_number(sum(result.stats.superseded_open_cards for result in results))}** | **{compact_number(total_full)}** | **{compact_number(total_positive)}** | **{compact_number(total_closure)}** | **{compact_number(len(before_members))}** | **{compact_number(len(after_members))}** |

حجم ملف التغطية الناتج: {size_label(coverage_bytes)}.

## تحقق حفظ المقام

- عدد أسطر التغطية يساوي عدد الأعضاء المنقولين: {compact_number(total_moved)}.
- عدد الهويات المسجلة قبل التحويل: {compact_number(len(before_members))}.
- عدد الهويات المسجلة بعد التحويل: {compact_number(len(after_members))}.
- الفرق: صفر. لم ينقص مجموع الأعضاء المسجلة عضوًا واحدًا.
- الهويات المحلية الاصطناعية للبطاقات التاريخية التي لم تحمل معرف مصدر صريح: {compact_number(synthetic)}؛ وهي ثابتة مشتقة من اللسان والعنوان والرسم والمعنى.
- الرسوم غير المسجلة في البطاقات المنقولة: {compact_number(missing_forms)}؛ معاني الفرع غير المسجلة: {compact_number(missing_meanings)}.
- بقيت الصلات والإغلاقات في مواضعها داخل ملفات القراءة، ولم تتحول إلى أسطر تغطية.
"""
    )


def print_summary(results: Iterable[ScanResult]) -> None:
    total_open = 0
    total_full = 0
    for result in results:
        stats = result.stats
        total_open += stats.coverage_rows
        total_full += stats.full_cards_remaining
        print(
            "\t".join(
                (
                    stats.filename,
                    f"bytes={stats.before_bytes}",
                    f"move={stats.coverage_rows}",
                    f"superseded_open={stats.superseded_open_cards}",
                    f"positive={stats.positive_cards}",
                    f"closures={stats.closure_cards}",
                    f"full={stats.full_cards_remaining}",
                    f"templates={stats.templates}",
                    f"synthetic={stats.synthetic_ids}",
                    f"missing_form={stats.missing_forms}",
                    f"missing_meaning={stats.missing_meanings}",
                    f"ambiguous={len(stats.ambiguous)}",
                )
            )
        )
    print(f"TOTAL\tmove={total_open}\tfull={total_full}")


def apply_migration(results: list[ScanResult]) -> None:
    if COVERAGE.exists() and COVERAGE.stat().st_size:
        raise RuntimeError(f"refusing to overwrite existing {COVERAGE}")
    if AUDIT.exists():
        raise RuntimeError(f"refusing to overwrite existing {AUDIT}")

    temp_readings: list[tuple[Path, Path, ScanResult]] = []
    coverage_tmp = COVERAGE.with_name(COVERAGE.name + ".lane-c-migration.tmp")
    audit_tmp = AUDIT.with_name(AUDIT.name + ".lane-c-migration.tmp")
    if coverage_tmp.exists() or audit_tmp.exists():
        raise RuntimeError("stale Lane C migration temporary file exists")

    try:
        rewritten_results: list[ScanResult] = []
        for language, language_ar, filename in LANGUAGES:
            destination = READINGS / filename
            temporary = destination.with_name(
                destination.name + ".lane-c-migration.tmp"
            )
            if temporary.exists():
                raise RuntimeError(f"stale migration temporary file: {temporary}")
            rewritten = scan_file(
                language,
                language_ar,
                filename,
                output_path=temporary,
            )
            rewritten_results.append(rewritten)
            temp_readings.append((destination, temporary, rewritten))

        validate_preflight(rewritten_results)
        old_rows = [row for result in results for row in result.rows]
        new_rows = [row for result in rewritten_results for row in result.rows]
        if old_rows != new_rows:
            raise RuntimeError("rewrite scan changed coverage rows")

        with coverage_tmp.open("w", encoding="utf-8", newline="\n") as handle:
            for row in new_rows:
                handle.write(
                    json.dumps(
                        row,
                        ensure_ascii=False,
                        separators=(",", ":"),
                    )
                    + "\n"
                )

        coverage_ids: set[str] = set()
        with coverage_tmp.open("r", encoding="utf-8") as handle:
            for line_number, line in enumerate(handle, 1):
                row = json.loads(line)
                if tuple(row.keys()) != REQUIRED_ROW_FIELDS:
                    raise RuntimeError(
                        f"coverage line {line_number}: field mismatch"
                    )
                member_id = row["member_id"]
                if member_id in coverage_ids:
                    raise RuntimeError(
                        f"coverage line {line_number}: duplicate {member_id}"
                    )
                coverage_ids.add(member_id)
        if len(coverage_ids) != len(new_rows):
            raise RuntimeError("coverage JSONL count mismatch")

        for destination, temporary, _ in temp_readings:
            temporary.replace(destination)
        coverage_tmp.replace(COVERAGE)

        # Re-scan the committed reading files: no non-verdict card may remain.
        verified = scan_all()
        if any(result.stats.open_cards_removed for result in verified):
            raise RuntimeError("non-verdict card remained after rewrite")
        for before, after in zip(rewritten_results, verified):
            after.stats.before_bytes = before.stats.before_bytes
            after.stats.after_bytes = (READINGS / after.stats.filename).stat().st_size
            after.stats.open_cards_removed = before.stats.open_cards_removed
            after.stats.superseded_open_cards = before.stats.superseded_open_cards
            after.stats.coverage_rows = before.stats.coverage_rows
            after.stats.synthetic_ids = before.stats.synthetic_ids
            after.stats.missing_forms = before.stats.missing_forms
            after.stats.missing_meanings = before.stats.missing_meanings
            after.stats.identities_before = before.stats.identities_before
            after.open_ids = before.open_ids

        report = audit_text(verified, COVERAGE.stat().st_size)
        with audit_tmp.open("w", encoding="utf-8", newline="\n") as handle:
            handle.write(report.rstrip() + "\n")
        audit_tmp.replace(AUDIT)
    finally:
        for _, temporary, _ in temp_readings:
            if temporary.exists():
                temporary.unlink()
        if coverage_tmp.exists():
            coverage_tmp.unlink()
        if audit_tmp.exists():
            audit_tmp.unlink()


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="write compacted readings, coverage JSONL, and audit",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    results = scan_all()
    print_summary(results)
    validate_preflight(results)
    if args.apply:
        apply_migration(results)
        print(f"WROTE\t{COVERAGE}")
        print(f"WROTE\t{AUDIT}")
    else:
        print("DRY-RUN\tno files changed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
