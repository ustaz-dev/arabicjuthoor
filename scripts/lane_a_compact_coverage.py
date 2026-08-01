#!/usr/bin/env python3
"""Compact Lane A Hebrew/Aramaic pending cards into one JSONL registry.

Positive judgments and terminal closures remain byte-for-byte inside the
readings.  A card or member review with no positive judgment and no terminal
closure is removed.  Every inventory member without either outcome receives
exactly one row in ``04-cross-linguistic/data/lane_a_coverage.jsonl``.

The command is a dry run unless ``--apply`` is supplied.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
READINGS = ROOT / "04-cross-linguistic" / "readings"
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDIT = (
    ROOT
    / "05-audits"
    / "lane-a-2026-07-30-hebrew-aramaic-coverage-compaction.md"
)

LANGUAGES = ("hebrew", "aramaic")
READING_PATHS = {
    language: READINGS / f"{language}.md" for language in LANGUAGES
}

POSITIVE_OUTCOMES = {
    "ROOT-TRACE",
    "NUCLEUS-TRACE",
    "ROOT-ECHO",
    "NUCLEUS-ECHO",
    "FLOOR-TRACE",
}

TERMINAL_CLOSURES = {
    "NO-TRACE",
    "CLOSED-NO-TRACE",
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
    "REFERRED",
    "READY",
}

OUTCOME_ALTERNATION = "(?:" + "|".join(
    re.escape(value)
    for value in sorted(
        POSITIVE_OUTCOMES | TERMINAL_CLOSURES,
        key=len,
        reverse=True,
    )
) + ")"

PARKED_ALTERNATION = "(?:" + "|".join(
    re.escape(value)
    for value in sorted(PARKED_STATES, key=len, reverse=True)
) + ")"

FIELD_OUTCOME_RE = re.compile(
    r"^\s*-\s*(?:الحكم[^:]*|حالةُ الإغلاق|الحسم|المصير|حالة الأسرة)"
    rf"\s*:\s*`?(?P<outcome>{OUTCOME_ALTERNATION})",
    re.MULTILINE,
)

MEMBER_OUTCOME_RE = re.compile(
    rf"(?:^|[؛|])\s*النتيجة\s*:\s*`?"
    rf"(?P<outcome>{OUTCOME_ALTERNATION})",
    re.MULTILINE,
)

PARKED_RESULT_RE = re.compile(
    rf"(?:^|[؛|])\s*النتيجة\s*:\s*`?"
    rf"(?P<state>{PARKED_ALTERNATION})"
)

BOUNDARY_RE = re.compile(
    r"^(?P<section>## (?!#).*)$"
    r"|^(?P<card>### (?P<kind>بطاقة|مراجعة عضوية):.*)$"
    r"|^(?P<marker><!-- .*:(?:START|END) -->)\s*$",
    re.MULTILINE,
)

SOURCE_LINE_RE = {
    language: re.compile(rf"kaikki_{language}:(\d+):")
    for language in LANGUAGES
}

REQUIRED_ROW_KEYS = {
    "member_id",
    "language",
    "orthography",
    "branch_meaning",
    "nonissuance_reason",
    "batch_number",
}


@dataclass(frozen=True)
class CardBlock:
    start: int
    end: int
    heading: str
    kind: str
    section: str
    section_number: int
    text: str

    @property
    def has_outcome(self) -> bool:
        return bool(
            FIELD_OUTCOME_RE.search(self.text)
            or MEMBER_OUTCOME_RE.search(self.text)
        )


@dataclass
class LanguageResult:
    language: str
    original_text: str
    compacted_text: str
    inventory: dict[str, dict[str, Any]]
    terminal_members: set[str]
    pending_members: set[str]
    registered_before: set[str]
    metadata: dict[str, tuple[str, str]]
    cards_before: int
    cards_removed: int
    cards_retained: int
    retained_protocol_cards: int
    retained_legacy_reviews: int
    markers_before: int
    markers_after: int

    @property
    def before_bytes(self) -> int:
        return len(self.original_text.encode("utf-8"))

    @property
    def after_bytes(self) -> int:
        return len(self.compacted_text.encode("utf-8"))


def one_line(value: Any) -> str:
    return " ".join(str(value or "").replace("\x00", "").split())


def load_inventory() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    dict[str, dict[int, str]],
]:
    inventory = {language: {} for language in LANGUAGES}
    by_source_line = {language: {} for language in LANGUAGES}
    connection = sqlite3.connect(DB)
    connection.row_factory = sqlite3.Row
    try:
        for language in LANGUAGES:
            for row in connection.execute(
                """
                SELECT entry_id,headword,gloss
                FROM entries
                WHERE language=?
                ORDER BY
                  CAST(
                    substr(entry_id,instr(entry_id,':')+1)
                    AS INTEGER
                  ),
                  entry_id
                """,
                (language,),
            ):
                entry = dict(row)
                entry_id = str(entry["entry_id"])
                source_line = int(entry_id.split(":", 2)[1])
                if source_line in by_source_line[language]:
                    raise ValueError(
                        f"سطر مصدر مكرر في {language}: {source_line}"
                    )
                inventory[language][entry_id] = entry
                by_source_line[language][source_line] = entry_id
    finally:
        connection.close()
    return inventory, by_source_line


def parse_card_blocks(text: str) -> list[CardBlock]:
    boundaries = list(BOUNDARY_RE.finditer(text))
    blocks: list[CardBlock] = []
    current_section = "unsectioned"
    section_number = 0
    for index, match in enumerate(boundaries):
        if match.group("section"):
            current_section = match.group("section")[3:].strip()
            section_number += 1
            continue
        if not match.group("card"):
            continue
        end = (
            boundaries[index + 1].start()
            if index + 1 < len(boundaries)
            else len(text)
        )
        blocks.append(
            CardBlock(
                start=match.start(),
                end=end,
                heading=match.group("card"),
                kind=match.group("kind"),
                section=current_section,
                section_number=section_number,
                text=text[match.start() : end],
            )
        )
    return blocks


def canonical_batch_number(
    language: str,
    section: str,
    section_number: int,
) -> str:
    batch_match = re.search(
        r"(?:الدفعة|دفعة)\s+([0-9]+[A-Za-z0-9]*)",
        section,
    )
    batch = batch_match.group(1).upper() if batch_match else ""
    if language == "hebrew" and "التغطية العبرية التوراتية" in section:
        return f"hebrew-biblical-{int(batch):03d}" if batch else (
            f"hebrew-biblical-section-{section_number:03d}"
        )
    if language == "hebrew" and "التغطية العبرية العامة" in section:
        return f"hebrew-inventory-{int(batch):03d}" if batch else (
            f"hebrew-inventory-section-{section_number:03d}"
        )
    if language == "aramaic" and "التغطية الآرامية العامة" in section:
        return f"aramaic-inventory-{int(batch):03d}" if batch else (
            f"aramaic-inventory-section-{section_number:03d}"
        )
    if language == "aramaic" and "دفعة الجرد الآرامية أ" in section:
        return f"aramaic-discovery-{batch}" if batch else (
            f"aramaic-discovery-section-{section_number:03d}"
        )
    if batch:
        return f"{language}-batch-{batch}"
    return f"{language}-legacy-{section_number:03d}"


def ids_on_line(
    language: str,
    line: str,
    by_source_line: dict[int, str],
) -> list[str]:
    result: list[str] = []
    for raw_source_line in SOURCE_LINE_RE[language].findall(line):
        entry_id = by_source_line.get(int(raw_source_line))
        if entry_id and entry_id not in result:
            result.append(entry_id)
    return result


def pending_reason(line: str) -> str:
    state_match = re.search(
        rf"(?:النوع=|النتيجة\s*:\s*`?)(?P<state>{PARKED_ALTERNATION})",
        line,
    )
    state = state_match.group("state") if state_match else "غير صادر"

    reason_match = re.search(r"السبب=(?P<reason>.*?)(?:[.]?$)", line)
    if reason_match:
        reason = reason_match.group("reason").strip(" ؛.")
        return f"{state}: {one_line(reason)}"

    requirement_match = re.search(
        r"يتطلب=(?P<reason>.*?)(?:؛\s*(?:العضو|الأعضاء)=|[.]?$)",
        line,
    )
    if requirement_match:
        reason = requirement_match.group("reason").strip(" ؛.")
        return f"{state}: {one_line(reason)}"

    result_match = PARKED_RESULT_RE.search(line)
    if result_match:
        tail = line[result_match.end() :].lstrip(" `؛:،.")
        tail = re.split(
            r"(?:الخطوة الصفر=|السطح المباشر=|المروحة الكاملة=)",
            tail,
            maxsplit=1,
        )[0]
        reason = one_line(tail).strip(" ؛.")
        return f"{state}: {reason or 'لم تكتمل شروط الإصدار'}"

    return f"{state}: لم يصدر حكم موجب ولا إغلاق نهائي"


def subject_lines(block: CardBlock) -> list[str]:
    return [
        line
        for line in block.text.splitlines()
        if line.lstrip().startswith(("- العضو:", "- عائق:", "- الحكم"))
    ]


def outcome_ids_from_block(
    language: str,
    block: CardBlock,
    by_source_line: dict[int, str],
) -> set[str]:
    result: set[str] = set()
    for line in block.text.splitlines():
        if FIELD_OUTCOME_RE.search(line) or MEMBER_OUTCOME_RE.search(line):
            result.update(ids_on_line(language, line, by_source_line))
    return result


def compact_language(
    language: str,
    inventory: dict[str, dict[str, Any]],
    by_source_line: dict[int, str],
    existing_rows: dict[str, dict[str, Any]],
) -> LanguageResult:
    path = READING_PATHS[language]
    original_text = path.read_text(encoding="utf-8")
    blocks = parse_card_blocks(original_text)

    terminal_members: set[str] = set()
    registered_before: set[str] = set()
    metadata: dict[str, tuple[str, str]] = {}
    removed_blocks: list[CardBlock] = []
    retained_protocol_cards = 0
    retained_legacy_reviews = 0

    for block in blocks:
        batch_number = canonical_batch_number(
            language,
            block.section,
            block.section_number,
        )
        terminal_members.update(
            outcome_ids_from_block(language, block, by_source_line)
        )
        explicit_subject_ids: set[str] = set()
        for line in subject_lines(block):
            line_ids = ids_on_line(language, line, by_source_line)
            explicit_subject_ids.update(line_ids)
            if not (
                FIELD_OUTCOME_RE.search(line)
                or MEMBER_OUTCOME_RE.search(line)
            ):
                reason = pending_reason(line)
                for entry_id in line_ids:
                    metadata[entry_id] = (reason, batch_number)
        registered_before.update(explicit_subject_ids)

        if block.has_outcome:
            if "RECOVERY-v2" in block.text:
                retained_protocol_cards += 1
            else:
                retained_legacy_reviews += 1
        else:
            removed_blocks.append(block)

    terminal_members.intersection_update(inventory)
    pending_members = set(inventory) - terminal_members
    registered_before.update(terminal_members)

    for entry_id, row in existing_rows.items():
        if entry_id in pending_members:
            # Once a member has been migrated, its row is the canonical
            # compact record.  Preserve it exactly on later validation runs
            # even when a retained mixed card also mentions that member.
            metadata[entry_id] = (
                one_line(row.get("nonissuance_reason")),
                one_line(row.get("batch_number")),
            )
            registered_before.add(entry_id)

    missing_before = set(inventory) - registered_before
    if missing_before:
        sample = ", ".join(sorted(missing_before)[:5])
        raise ValueError(
            f"{language}: أعضاء غير مسجلين قبل التحويل: "
            f"{len(missing_before)}؛ عينة={sample}"
        )

    missing_metadata = pending_members - set(metadata)
    if missing_metadata:
        sample = ", ".join(sorted(missing_metadata)[:5])
        raise ValueError(
            f"{language}: أعضاء بلا سبب/دفعة: "
            f"{len(missing_metadata)}؛ عينة={sample}"
        )

    pieces: list[str] = []
    cursor = 0
    for block in removed_blocks:
        pieces.append(original_text[cursor : block.start])
        cursor = block.end
    pieces.append(original_text[cursor:])
    compacted_text = "".join(pieces)

    remaining_blocks = parse_card_blocks(compacted_text)
    pending_blocks = [
        block for block in remaining_blocks if not block.has_outcome
    ]
    if pending_blocks:
        raise ValueError(
            f"{language}: بقيت بطاقات بلا حكم بعد التحويل: "
            f"{len(pending_blocks)}"
        )

    marker_pattern = re.compile(r"^<!-- .*:(?:START|END) -->\s*$", re.MULTILINE)
    markers_before = len(marker_pattern.findall(original_text))
    markers_after = len(marker_pattern.findall(compacted_text))
    if markers_before != markers_after:
        raise ValueError(
            f"{language}: تغير عدد علامات الدفعات "
            f"{markers_before} -> {markers_after}"
        )

    return LanguageResult(
        language=language,
        original_text=original_text,
        compacted_text=compacted_text,
        inventory=inventory,
        terminal_members=terminal_members,
        pending_members=pending_members,
        registered_before=registered_before,
        metadata=metadata,
        cards_before=len(blocks),
        cards_removed=len(removed_blocks),
        cards_retained=len(remaining_blocks),
        retained_protocol_cards=retained_protocol_cards,
        retained_legacy_reviews=retained_legacy_reviews,
        markers_before=markers_before,
        markers_after=markers_after,
    )


def load_existing_rows() -> tuple[
    dict[str, dict[str, dict[str, Any]]],
    list[dict[str, Any]],
]:
    by_language = {language: {} for language in LANGUAGES}
    other_rows: list[dict[str, Any]] = []
    if not COVERAGE.exists():
        return by_language, other_rows

    for line_number, raw_line in enumerate(
        COVERAGE.read_text(encoding="utf-8").splitlines(),
        1,
    ):
        if not raw_line.strip():
            continue
        row = json.loads(raw_line)
        member_id = str(row.get("member_id", ""))
        language = str(row.get("language", ""))
        if not member_id:
            raise ValueError(f"سطر تغطية بلا member_id: {line_number}")
        if language in by_language:
            if member_id in by_language[language]:
                raise ValueError(f"معرف مكرر في التغطية: {member_id}")
            by_language[language][member_id] = row
        else:
            other_rows.append(row)
    return by_language, other_rows


def build_rows(
    results: dict[str, LanguageResult],
    other_rows: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = list(other_rows)
    for language in LANGUAGES:
        result = results[language]
        for entry_id in sorted(
            result.pending_members,
            key=lambda value: (int(value.split(":", 2)[1]), value),
        ):
            entry = result.inventory[entry_id]
            reason, batch_number = result.metadata[entry_id]
            rows.append(
                {
                    "member_id": entry_id,
                    "language": language,
                    "orthography": one_line(entry["headword"]),
                    "branch_meaning": one_line(entry["gloss"]),
                    "nonissuance_reason": reason,
                    "batch_number": batch_number,
                }
            )
    return rows


def render_jsonl(rows: list[dict[str, Any]]) -> str:
    seen: set[str] = set()
    lines: list[str] = []
    for row in rows:
        if set(row) != REQUIRED_ROW_KEYS:
            raise ValueError(
                f"حقول تغطية غير مطابقة في {row.get('member_id', '<missing>')}"
            )
        member_id = str(row["member_id"])
        if member_id in seen:
            raise ValueError(f"معرف تغطية مكرر: {member_id}")
        seen.add(member_id)
        lines.append(
            json.dumps(
                row,
                ensure_ascii=False,
                separators=(",", ":"),
            )
        )
    return "\n".join(lines) + ("\n" if lines else "")


def validate_final_registration(
    results: dict[str, LanguageResult],
    rows: list[dict[str, Any]],
) -> None:
    coverage_by_language = {language: set() for language in LANGUAGES}
    for row in rows:
        language = str(row["language"])
        if language in coverage_by_language:
            coverage_by_language[language].add(str(row["member_id"]))

    for language, result in results.items():
        coverage_ids = coverage_by_language[language]
        overlap = result.terminal_members.intersection(coverage_ids)
        if overlap:
            sample = ", ".join(sorted(overlap)[:5])
            raise ValueError(
                f"{language}: أعضاء محكومون في سجل بلا حكم: {sample}"
            )
        registered_after = result.terminal_members | coverage_ids
        expected = set(result.inventory)
        if registered_after != expected:
            missing = expected - registered_after
            extra = registered_after - expected
            raise ValueError(
                f"{language}: فشل حفظ المقام؛ "
                f"ناقص={len(missing)} زائد={len(extra)}"
            )
        if len(result.registered_before) != len(registered_after):
            raise ValueError(
                f"{language}: تغير مجموع المسجلين "
                f"{len(result.registered_before)} -> {len(registered_after)}"
            )


def atomic_stage(path: Path, text: str) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, raw_temp_path = tempfile.mkstemp(
        prefix=f".{path.name}.",
        suffix=".tmp",
        dir=path.parent,
    )
    temp_path = Path(raw_temp_path)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
            handle.flush()
            os.fsync(handle.fileno())
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise
    return temp_path


def format_bytes(value: int) -> str:
    return f"{value:,}"


def render_audit(
    results: dict[str, LanguageResult],
    coverage_bytes_before: int,
    coverage_bytes_after: int,
    coverage_rows: int,
) -> str:
    hebrew = results["hebrew"]
    aramaic = results["aramaic"]
    total_before = sum(
        len(result.registered_before) for result in results.values()
    )
    total_after = sum(
        len(result.terminal_members) + len(result.pending_members)
        for result in results.values()
    )
    return "\n".join(
        [
            "# محضر ضغط تغطية المسار أ: العبرية والآرامية",
            "",
            "- التاريخ: 2026-07-30.",
            "- القاعدة البنيوية: الحكم الموجب أو الإغلاق النهائي يبقى "
            "بطاقة كاملة؛ غير المحكوم يسجل سطر JSONL واحدًا.",
            "- لم يشغل Git ولا أداة مشتركة.",
            "",
            "## الأحجام قبل وبعد",
            "",
            "| الملف | قبل (بايت) | بعد (بايت) | الفرق |",
            "|---|---:|---:|---:|",
            f"| `04-cross-linguistic/readings/hebrew.md` | "
            f"{format_bytes(hebrew.before_bytes)} | "
            f"{format_bytes(hebrew.after_bytes)} | "
            f"-{format_bytes(hebrew.before_bytes - hebrew.after_bytes)} |",
            f"| `04-cross-linguistic/readings/aramaic.md` | "
            f"{format_bytes(aramaic.before_bytes)} | "
            f"{format_bytes(aramaic.after_bytes)} | "
            f"-{format_bytes(aramaic.before_bytes - aramaic.after_bytes)} |",
            f"| `04-cross-linguistic/data/lane_a_coverage.jsonl` | "
            f"{format_bytes(coverage_bytes_before)} | "
            f"{format_bytes(coverage_bytes_after)} | "
            f"+{format_bytes(coverage_bytes_after - coverage_bytes_before)} |",
            "",
            "## المنقول والباقي",
            "",
            "| اللسان | أعضاء نقلوا إلى JSONL | بطاقات نثرية حذفت | "
            "كتل أحكام/إغلاقات بقيت كاملة | منها RECOVERY-v2 | "
            "مراجعات حكم قديمة محفوظة |",
            "|---|---:|---:|---:|---:|---:|",
            f"| العبرية | {len(hebrew.pending_members)} | "
            f"{hebrew.cards_removed} | {hebrew.cards_retained} | "
            f"{hebrew.retained_protocol_cards} | "
            f"{hebrew.retained_legacy_reviews} |",
            f"| الآرامية | {len(aramaic.pending_members)} | "
            f"{aramaic.cards_removed} | {aramaic.cards_retained} | "
            f"{aramaic.retained_protocol_cards} | "
            f"{aramaic.retained_legacy_reviews} |",
            f"| المجموع | {coverage_rows} | "
            f"{hebrew.cards_removed + aramaic.cards_removed} | "
            f"{hebrew.cards_retained + aramaic.cards_retained} | "
            f"{hebrew.retained_protocol_cards + aramaic.retained_protocol_cards} | "
            f"{hebrew.retained_legacy_reviews + aramaic.retained_legacy_reviews} |",
            "",
            "البطاقة المختلطة التي تحمل حكمًا لعضو وتترك عضوًا آخر "
            "مفتوحًا بقيت كاملة، وسجل العضو المفتوح في JSONL.",
            "",
            "## ثبات المقام",
            "",
            "| اللسان | المسجل قبل | ذوو حكم/إغلاق بعد | "
            "سجلات بلا حكم بعد | المسجل بعد | النقص |",
            "|---|---:|---:|---:|---:|---:|",
            f"| العبرية | {len(hebrew.registered_before)} | "
            f"{len(hebrew.terminal_members)} | "
            f"{len(hebrew.pending_members)} | "
            f"{len(hebrew.terminal_members) + len(hebrew.pending_members)} | 0 |",
            f"| الآرامية | {len(aramaic.registered_before)} | "
            f"{len(aramaic.terminal_members)} | "
            f"{len(aramaic.pending_members)} | "
            f"{len(aramaic.terminal_members) + len(aramaic.pending_members)} | 0 |",
            f"| المجموع | {total_before} | "
            f"{len(hebrew.terminal_members) + len(aramaic.terminal_members)} | "
            f"{coverage_rows} | {total_after} | 0 |",
            "",
            "النتيجة: مجموع الأعضاء المسجلة لم ينقص عضوًا واحدًا. "
            "كل سطر JSONL صالح، معرفه فريد، ويحمل الحقول الستة "
            "المطلوبة.",
            "",
        ]
    )


def metrics(
    results: dict[str, LanguageResult],
    coverage_bytes_before: int,
    coverage_text: str,
    rows: list[dict[str, Any]],
) -> dict[str, Any]:
    return {
        "coverage_file": str(COVERAGE.relative_to(ROOT)),
        "coverage_bytes_before": coverage_bytes_before,
        "coverage_bytes_after": len(coverage_text.encode("utf-8")),
        "coverage_rows": len(
            [row for row in rows if row["language"] in LANGUAGES]
        ),
        "languages": {
            language: {
                "reading_bytes_before": result.before_bytes,
                "reading_bytes_after": result.after_bytes,
                "cards_before": result.cards_before,
                "cards_moved": result.cards_removed,
                "full_cards_retained": result.cards_retained,
                "retained_recovery_v2": result.retained_protocol_cards,
                "retained_legacy_outcome_reviews": (
                    result.retained_legacy_reviews
                ),
                "members_moved_to_jsonl": len(result.pending_members),
                "members_with_positive_or_closure": len(
                    result.terminal_members
                ),
                "registered_before": len(result.registered_before),
                "registered_after": (
                    len(result.terminal_members)
                    + len(result.pending_members)
                ),
                "registration_loss": 0,
            }
            for language, result in results.items()
        },
    }


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--apply",
        action="store_true",
        help="Atomically replace the readings and write the JSONL/audit.",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    inventory, by_source_line = load_inventory()
    existing_by_language, other_rows = load_existing_rows()
    coverage_bytes_before = COVERAGE.stat().st_size if COVERAGE.exists() else 0

    results = {
        language: compact_language(
            language,
            inventory[language],
            by_source_line[language],
            existing_by_language[language],
        )
        for language in LANGUAGES
    }
    rows = build_rows(results, other_rows)
    coverage_text = render_jsonl(rows)

    # Parse every produced line again before any file replacement.
    reparsed = [
        json.loads(line)
        for line in coverage_text.splitlines()
        if line.strip()
    ]
    if reparsed != rows:
        raise ValueError("فشل اختبار إعادة قراءة JSONL")
    validate_final_registration(results, rows)

    coverage_rows = len(
        [row for row in rows if row["language"] in LANGUAGES]
    )
    audit_text = render_audit(
        results,
        coverage_bytes_before,
        len(coverage_text.encode("utf-8")),
        coverage_rows,
    )

    result_metrics = metrics(
        results,
        coverage_bytes_before,
        coverage_text,
        rows,
    )
    result_metrics["mode"] = "apply" if args.apply else "dry-run"

    if args.apply:
        staged: dict[Path, Path] = {}
        try:
            for path, text in (
                (READING_PATHS["hebrew"], results["hebrew"].compacted_text),
                (READING_PATHS["aramaic"], results["aramaic"].compacted_text),
                (COVERAGE, coverage_text),
                (AUDIT, audit_text),
            ):
                staged[path] = atomic_stage(path, text)
            for path, temp_path in staged.items():
                os.replace(temp_path, path)
        finally:
            for temp_path in staged.values():
                temp_path.unlink(missing_ok=True)

    print(json.dumps(result_metrics, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
