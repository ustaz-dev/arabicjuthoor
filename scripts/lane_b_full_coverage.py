#!/usr/bin/env python3
"""Complete lane B's Egyptian and Coptic snapshot denominator.

This lane-local tool is deliberately read-only with respect to the shared
inventory database.  It writes only lane B's two owned reading files and
lane-b-* audit records.  It never rebuilds a shared artifact and never issues
an automated positive linguistic verdict.
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sqlite3
import sys
import tempfile
from bisect import bisect_right
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


ROOT = Path(__file__).resolve().parents[1]
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
AUDITS = ROOT / "05-audits"
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_b_coverage.jsonl"
DATE = "2026-07-30"
BATCH_SIZE = 1000
PROTOCOL = "RECOVERY-v2 (2026-07-14)"
PUBLICATION_CARD_FIELDS = (
    "- إصدارُ البروتوكول:",
    "- الكلمةُ في الفرع:",
    "- أقدمُ صورةٍ مستعادة:",
    "- الخطوةُ صفر (التعرية بصرف الفرع):",
    "- درجةُ المقارنة:",
    "- مسحُ المعاني العربيّة:",
    "- المقابلُ من اللسان:",
    "- مسارُ الصوت:",
    "- المعنى من قاموس الفرع:",
    "- المدار:",
    "- المصفاة:",
    "- فصلُ المتجانسات والاقتراض:",
    "- مؤشر اليتم:",
    "- إشعاع الأسرة في الفرع:",
    "- إشعاع الأسرة في العربية:",
    "- جسورُ الاسترداد المفحوصة:",
    "- حالةُ الإغلاق:",
    "- الحكم (استكشاف):",
    "- ملاحظات:",
)
COVERAGE_FIELDS = (
    "member_id",
    "language",
    "script",
    "branch_gloss",
    "non_issuance_reason",
    "batch",
)
GAP_PATTERN = re.compile(
    r"\b(?:OPEN-CANDIDATE|TOOL-GAP|LAW-GAP|SOURCE-GAP|"
    r"MORPHOLOGY-GAP|REFERRED)\b"
)
POSITIVE_PATTERN = re.compile(
    r"\b(?:ROOT-TRACE|ROOT-ECHO|NUCLEUS-TRACE|NUCLEUS-ECHO|"
    r"FLOOR-TRACE)\b"
)
FINAL_PATTERN = re.compile(r"\b(?:LOANWORD|NO-TRACE)\b")


@dataclass(frozen=True)
class LanguageSpec:
    language: str
    arabic_name: str
    source_label: str
    reading: Path
    marker_pattern: re.Pattern[str]


SPECS = (
    LanguageSpec(
        language="egyptian",
        arabic_name="المصرية القديمة",
        source_label="AED v1.0",
        reading=ROOT / "04-cross-linguistic" / "readings" / "egyptian.md",
        marker_pattern=re.compile(
            r"<!-- lane-b-week2-full-coverage:egyptian:(\d+) -->"
        ),
    ),
    LanguageSpec(
        language="coptic",
        arabic_name="القبطية",
        source_label="Comprehensive Coptic Lexicon 1.2",
        reading=ROOT / "04-cross-linguistic" / "readings" / "coptic.md",
        marker_pattern=re.compile(
            r"<!-- lane-b-week2-full-coverage:coptic:(C\d+) -->"
        ),
    ),
)


def compact(value: object, limit: int = 900) -> str:
    text = " ".join(str(value or "").replace("`", "ˋ").split())
    if len(text) <= limit:
        return text
    return text[: limit - 28].rstrip() + " … [مختصر عرضيًا في البطاقة]"


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp_name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temp_name, path)
    finally:
        if os.path.exists(temp_name):
            os.unlink(temp_name)


def connect() -> sqlite3.Connection:
    uri = f"file:{DB.as_posix()}?mode=ro"
    connection = sqlite3.connect(uri, uri=True)
    connection.row_factory = sqlite3.Row
    return connection


def inventory_rows(connection: sqlite3.Connection, language: str) -> list[sqlite3.Row]:
    order = (
        "CAST(e.source_entry_id AS INTEGER)"
        if language == "egyptian"
        else "CAST(SUBSTR(e.source_entry_id, 2) AS INTEGER)"
    )
    return connection.execute(
        f"""
        SELECT
            e.entry_id,
            e.source_entry_id,
            e.headword,
            e.romanization,
            e.pos,
            e.gloss,
            e.etymology,
            e.loan_hint,
            e.form_of,
            e.alternative_of,
            e.selected_input,
            e.skeleton,
            e.processing_status,
            e.morphology_status,
            e.candidate_count,
            e.licensed_candidate_count,
            e.scope_gap_count,
            fm.family_id,
            fm.role,
            f.member_count,
            f.lemma_count,
            f.candidate_bearing_member_count,
            (
                SELECT COUNT(DISTINCT e2.gloss)
                FROM family_members fm2
                JOIN entries e2 ON e2.entry_id = fm2.entry_id
                WHERE fm2.family_id = fm.family_id AND e2.gloss <> ''
            ) AS family_gloss_count
        FROM entries e
        LEFT JOIN family_members fm ON fm.entry_id = e.entry_id
        LEFT JOIN families f ON f.family_id = fm.family_id
        WHERE e.language = ?
        ORDER BY {order}, e.entry_id
        """,
        (language,),
    ).fetchall()


def source_metadata(connection: sqlite3.Connection, language: str) -> sqlite3.Row:
    row = connection.execute(
        """
        SELECT language, source_id, path, size_bytes, mtime_ns,
               coverage_complete, entries_seen
        FROM sources
        WHERE language = ?
        """,
        (language,),
    ).fetchone()
    if row is None:
        raise RuntimeError(f"Shared inventory has no source row for {language}")
    source_path = ROOT / row["path"]
    stat = source_path.stat()
    if stat.st_size != row["size_bytes"] or stat.st_mtime_ns != row["mtime_ns"]:
        raise RuntimeError(
            f"Pinned source changed since the read-only inventory was built: {source_path}"
        )
    if not row["coverage_complete"]:
        raise RuntimeError(f"Shared inventory coverage is not complete for {language}")
    return row


def marker_ids(spec: LanguageSpec, text: str) -> list[str]:
    ids = spec.marker_pattern.findall(text)
    if len(ids) != len(set(ids)):
        duplicates = sorted(
            item for item, count in Counter(ids).items() if count > 1
        )
        raise RuntimeError(
            f"Duplicate full-coverage markers in {spec.reading}: {duplicates[:10]}"
        )
    return ids


def card_outcome(block: str) -> str:
    """Classify the live outcome line of one prose card."""
    verdict_match = re.search(
        r"^- الحكم \(استكشاف\):(.*)$", block, re.MULTILINE
    )
    state_match = re.search(
        r"^- حالةُ الإغلاق:(.*)$", block, re.MULTILINE
    )
    verdict = verdict_match.group(1).strip() if verdict_match else ""
    state = state_match.group(1).strip() if state_match else ""
    if "غير صادر" in verdict or GAP_PATTERN.search(state):
        return "unissued"
    if FINAL_PATTERN.search(verdict) or "CLOSED-NO-TRACE" in state:
        return "final"
    if POSITIVE_PATTERN.search(verdict):
        return "positive"
    return "unissued" if verdict else "other"


def strip_unissued_cards(text: str) -> tuple[str, Counter[str]]:
    """Remove prose cards without a live verdict while preserving section ends."""
    fence_positions = [
        match.start() for match in re.finditer(r"(?m)^```", text)
    ]
    boundary = re.compile(
        r"(?m)^### بطاقة:|^#{1,3} (?!بطاقة:)|^<!-- /[^>]+ -->"
    )
    starts = list(boundary.finditer(text))
    pieces: list[str] = []
    cursor = 0
    counts: Counter[str] = Counter()
    for index, match in enumerate(starts):
        if not match.group(0).startswith("### بطاقة:"):
            continue
        if bisect_right(fence_positions, match.start()) % 2:
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        if card_outcome(block) != "unissued":
            continue
        pieces.append(text[cursor:match.start()])
        cursor = end
        counts["cards"] += 1
        if "lane-b-week2-full-coverage:" in block[:900]:
            counts["generated_cards"] += 1
        else:
            counts["legacy_cards"] += 1
    pieces.append(text[cursor:])
    compacted = "".join(pieces)
    compacted = re.sub(r"\n{4,}", "\n\n\n", compacted)
    return compacted, counts


def closure_kind(row: sqlite3.Row, language: str) -> str:
    if bool(row["loan_hint"]):
        return "LOANWORD"
    pos = compact(row["pos"]).casefold()
    if language == "egyptian" and pos.startswith("entity_name"):
        return "PROPER-NAME-ISOLATED"
    normalized = pos.replace("-", "_").replace(" ", "_")
    if normalized in {"character", "symbol", "punct", "punctuation"}:
        return "NONLEXICAL-ISOLATED"
    return ""


def disposition(row: sqlite3.Row, language: str) -> tuple[str, str]:
    closure = closure_kind(row, language)
    if closure == "LOANWORD":
        return closure, "المصدر يسمّي مسار نقل لهذا العضو؛ عُزل عن حكم النسب."
    if closure == "PROPER-NAME-ISOLATED":
        return closure, "العضو عَلَم مسمّى في جزء الكلام المنشور؛ عُزل عن الحكم المعجمي."
    if closure == "NONLEXICAL-ISOLATED":
        return closure, "العضو علامة غير معجمية في جزء الكلام المنشور؛ عُزل عن المقارنة."
    if bool(row["form_of"]) and not bool(row["alternative_of"]):
        return (
            "MORPHOLOGY-GAP",
            "العضو صورة صرفية محيلة؛ يلزم ربطها بلمتها المنشورة قبل حكم مستقل.",
        )
    if row["processing_status"] == "blocked-normalization":
        return (
            "LAW-GAP",
            "التطبيع المثبت لم يستوعب رسم العضو؛ لا يُنشأ صف صوتي جديد آليًا.",
        )
    if not compact(row["skeleton"]):
        return (
            "SOURCE-GAP",
            "لم تُستعد من الرسم بنية صامتية صالحة؛ يلزم سلف أو تحليل منشور مسمى.",
        )
    if row["morphology_status"] == "morphology-review-required":
        return (
            "MORPHOLOGY-GAP",
            "البنية أطول من أن تُعرّى بلا تحليل صرفي منشور للعضو.",
        )
    if int(row["candidate_count"] or 0) and not compact(row["etymology"]):
        return (
            "SOURCE-GAP",
            "ظهر مرشح صوتي، لكن المصدر التاريخي الفردي ومروحة المعنى لم يكتملَا.",
        )
    if int(row["candidate_count"] or 0):
        return (
            "OPEN-CANDIDATE",
            "ظهر مرشح صوتي، وبقي مسح مروحة المعنى بالعدستين قبل أي حكم.",
        )
    return (
        "OPEN-CANDIDATE",
        "الجرد المجمّد لم يولّد جسرًا؛ يبقى العضو مفتوحًا بلا سالب مصطنع.",
    )


def needs_prose_card(row: sqlite3.Row, language: str) -> bool:
    """Automated lane-B output is full prose only for a final issued closure."""
    blocker, _ = disposition(row, language)
    return blocker == "LOANWORD"


def coverage_record(
    row: sqlite3.Row,
    spec: LanguageSpec,
    batch_number: int,
) -> dict[str, object]:
    blocker, reason = disposition(row, spec.language)
    return {
        "member_id": str(row["entry_id"]),
        "language": spec.language,
        "script": compact(row["headword"]) or "بلا رسم",
        "branch_gloss": compact(row["gloss"]) or "بلا شرح منشور",
        "non_issuance_reason": f"{blocker}: {reason}",
        "batch": batch_number,
    }


def load_coverage() -> list[dict[str, object]]:
    if not COVERAGE.exists():
        return []
    records: list[dict[str, object]] = []
    seen: set[str] = set()
    with COVERAGE.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, start=1):
            if not line.strip():
                continue
            record = json.loads(line)
            if tuple(record) != COVERAGE_FIELDS:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number} has fields {tuple(record)}, "
                    f"expected {COVERAGE_FIELDS}"
                )
            member_id = str(record["member_id"])
            if member_id in seen:
                raise RuntimeError(
                    f"{COVERAGE}:{line_number} duplicates {member_id}"
                )
            seen.add(member_id)
            records.append(record)
    return records


def write_coverage(records: Iterable[dict[str, object]]) -> None:
    lines = [
        json.dumps(
            {field: record[field] for field in COVERAGE_FIELDS},
            ensure_ascii=False,
            separators=(",", ":"),
        )
        for record in records
    ]
    atomic_write(COVERAGE, "\n".join(lines) + ("\n" if lines else ""))


def coverage_ids(
    records: Iterable[dict[str, object]], language: str
) -> set[str]:
    return {
        str(record["member_id"])
        for record in records
        if record["language"] == language
    }


def outcome_counts(rows: Iterable[sqlite3.Row], language: str) -> Counter[str]:
    counter: Counter[str] = Counter()
    for row in rows:
        blocker, _ = disposition(row, language)
        counter[blocker] += 1
    return counter


def closure_total(counter: Counter[str]) -> int:
    return counter["LOANWORD"]


def closure_text(counter: Counter[str]) -> str:
    return f"{closure_total(counter)} (LOANWORD={counter['LOANWORD']})"


def unresolved_text(counter: Counter[str]) -> str:
    unresolved = sum(
        counter[name]
        for name in (
            "OPEN-CANDIDATE",
            "SOURCE-GAP",
            "LAW-GAP",
            "MORPHOLOGY-GAP",
            "PROPER-NAME-ISOLATED",
            "NONLEXICAL-ISOLATED",
        )
    )
    return (
        f"{unresolved} "
        f"(OPEN-CANDIDATE={counter['OPEN-CANDIDATE']}، "
        f"SOURCE-GAP={counter['SOURCE-GAP']}، "
        f"LAW-GAP={counter['LAW-GAP']}، "
        f"MORPHOLOGY-GAP={counter['MORPHOLOGY-GAP']}، "
        f"PROPER-NAME-ISOLATED={counter['PROPER-NAME-ISOLATED']}، "
        f"NONLEXICAL-ISOLATED={counter['NONLEXICAL-ISOLATED']})"
    )


def repair_existing_closure_block(
    block: str, row: sqlite3.Row, language: str
) -> str:
    closure = closure_kind(row, language)
    if closure not in {
        "LOANWORD",
        "PROPER-NAME-ISOLATED",
        "NONLEXICAL-ISOLATED",
    }:
        return block
    if closure == "LOANWORD":
        requirement = "المصدر يسمّي مسار نقل لهذا العضو؛ عُزل عن حكم النسب."
        verdict = "LOANWORD؛ عزل مسار النقل، لا حكم نسب."
    elif closure == "PROPER-NAME-ISOLATED":
        requirement = (
            "العضو عَلَم مسمّى في جزء الكلام المنشور؛ عُزل عن الحكم المعجمي."
        )
        verdict = (
            "غير صادر؛ أُغلق العضو بوصفه عَلَمًا مسمّى، لا بوصفه صلةً معجمية."
        )
    else:
        requirement = (
            "العضو علامة غير معجمية في جزء الكلام المنشور؛ عُزل عن المقارنة."
        )
        verdict = (
            "غير صادر؛ أُغلق العضو بوصفه علامةً غير معجمية، لا صلةً لغوية."
        )
    replacements = {
        r"^- عائق:.*$": f"- عائق: النوع={closure}؛ يتطلب={requirement}",
        r"^- حالةُ الإغلاق:.*$": f"- حالةُ الإغلاق: READY؛ {closure}.",
        r"^- الحكم \(استكشاف\):.*$": f"- الحكم (استكشاف): {verdict}",
    }
    for pattern, replacement in replacements.items():
        block, count = re.subn(
            pattern, replacement, block, count=1, flags=re.MULTILINE
        )
        if count != 1:
            raise RuntimeError(
                f"Could not repair {pattern!r} for {row['entry_id']}"
            )
    return block


def card_block_counter(
    spec: LanguageSpec, text: str, expected_ids: set[str]
) -> Counter[str]:
    id_pattern = r"\d+" if spec.language == "egyptian" else r"C\d+"
    card_pattern = re.compile(
        rf"^### بطاقة:[^\n]*\n"
        rf"<!-- lane-b-week2-full-coverage:{spec.language}:"
        rf"(?P<id>{id_pattern}) -->\n"
        rf"(?P<body>.*?)(?=^### بطاقة:|^<!-- /lane-b|^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    counter: Counter[str] = Counter()
    found: set[str] = set()
    for match in card_pattern.finditer(text):
        source_id = match.group("id")
        if source_id not in expected_ids:
            continue
        found.add(source_id)
        blocker = re.search(
            r"^- عائق: النوع=([^؛\n]+)", match.group("body"), re.MULTILINE
        )
        if blocker is None:
            raise RuntimeError(
                f"Coverage card {spec.language}:{source_id} lacks blocker type"
            )
        counter[blocker.group(1).strip()] += 1
    if found != expected_ids:
        missing = sorted(expected_ids - found)
        raise RuntimeError(
            f"Could not count repaired coverage cards for {spec.language}: "
            f"{missing[:10]}"
        )
    return counter


def repair_initial_slice(
    spec: LanguageSpec, rows_by_id: dict[str, sqlite3.Row]
) -> tuple[list[str], Counter[str]]:
    text = spec.reading.read_text(encoding="utf-8")
    initial_header = (
        "## ملحق المسار ب: المقام المصري ذو التغطية الكاملة، الأسبوع الثاني"
        if spec.language == "egyptian"
        else "## ملحق المسار ب: المقام القبطي ذو التغطية الكاملة، الأسبوع الثاني"
    )
    start = text.find(initial_header)
    close = text.find(
        f"<!-- /lane-b-week2-full-coverage-{spec.language} -->", start
    )
    if start < 0 or close < 0:
        return [], Counter()
    section = text[start:close]
    ids = marker_ids(spec, section)
    if not ids:
        return [], Counter()
    card_pattern = re.compile(
        rf"^### بطاقة:[^\n]*\n"
        rf"<!-- lane-b-week2-full-coverage:{spec.language}:"
        rf"(?P<id>{r'\d+' if spec.language == 'egyptian' else r'C\d+'}) -->\n"
        rf".*?(?=^### بطاقة:|^<!-- /lane-b-week2-full-coverage|^## |\Z)",
        re.MULTILINE | re.DOTALL,
    )
    found: list[str] = []

    def replace(match: re.Match[str]) -> str:
        source_id = match.group("id")
        row = rows_by_id.get(source_id)
        if row is None:
            raise RuntimeError(
                f"Coverage marker {source_id} has no pinned inventory row"
            )
        found.append(source_id)
        return repair_existing_closure_block(match.group(0), row, spec.language)

    repaired = card_pattern.sub(replace, section)
    if set(found) != set(ids):
        missing = sorted(set(ids) - set(found))
        raise RuntimeError(
            f"Could not locate full card blocks for {spec.language}: {missing[:10]}"
        )
    counter = card_block_counter(spec, repaired, set(ids))
    new_summary = (
        f"- النتيجة المحلية للشريحة: الصلات الموجبة=0 من {len(ids)}؛ "
        f"الإغلاقات={closure_text(counter)}؛ "
        f"الأحكام غير الصادرة={unresolved_text(counter)}."
    )
    repaired, count = re.subn(
        r"^- النتيجة المحلية للشريحة:.*$",
        new_summary,
        repaired,
        count=1,
        flags=re.MULTILINE,
    )
    if count != 1:
        raise RuntimeError(
            f"Could not update initial summary for {spec.language}"
        )
    new_text = text[:start] + repaired + text[close:]
    if new_text != text:
        atomic_write(spec.reading, new_text)
    return ids, counter


def source_reference(row: sqlite3.Row, spec: LanguageSpec) -> str:
    etymology = compact(row["etymology"])
    if etymology:
        return f"{etymology} [{spec.source_label}، ˋ{row['source_entry_id']}ˋ]"
    return (
        f"لا صورة أقدم منشورة في الحقل الفردي "
        f"[{spec.source_label}، ˋ{row['source_entry_id']}ˋ]"
    )


def filter_line(row: sqlite3.Row, spec: LanguageSpec) -> str:
    etymology = compact(row["etymology"])
    if bool(row["loan_hint"]):
        origin = etymology or "وسم ˋforeignˋ أو إحالة قرض صريحة في بنية المصدر"
        base = f"يعزل مسارًا: {origin}"
    else:
        base = (
            f"لا وسم قرض صريح لهذا العضو؛ "
            f"الأصل المنشور «{etymology or 'لا تأثيل فردي في الحقل'}»؛ "
            "غياب الوسم لا يثبت الأصالة"
        )
    if spec.language == "coptic":
        base += (
            "؛ U+03E2–U+03EF حروف قبطية أصيلة موروثة من الديموطيقية "
            "ولم تُحسب يونانية"
        )
    return base + "."


def semantic_lines(
    row: sqlite3.Row, spec: LanguageSpec, blocker: str
) -> tuple[str, str, str, str]:
    candidates = int(row["candidate_count"] or 0)
    licensed = int(row["licensed_candidate_count"] or 0)
    scope_gap = int(row["scope_gap_count"] or 0)
    if blocker in {
        "LOANWORD",
        "PROPER-NAME-ISOLATED",
        "NONLEXICAL-ISOLATED",
    }:
        reason = {
            "LOANWORD": "عزل مسار النقل",
            "PROPER-NAME-ISOLATED": "عزل العَلَم",
            "NONLEXICAL-ISOLATED": "عزل العلامة غير المعجمية",
        }[blocker]
        return (
            f"غير منطبق بعد {reason}؛ لا تصنع المروحة العربية حكم نسب.",
            f"لا مقابل عربي محكوم بعد {reason}.",
            f"{reason} هو النافذ؛ لم تُحوّل صوامت العضو إلى صف نسب.",
            f"لا مدار معجمي بعد {reason}؛ الإغلاق تصنيفي لا صلة دلالية.",
        )
    if candidates:
        scan = (
            f"ولّد الجرد المجمّد {candidates} مسارًا مرشحًا "
            f"(مرخّص={licensed}، فجوة نطاق={scope_gap})، "
            "لكن لم تكتمل مروحة المعاني في لسان العرب لابن منظور "
            "وتاج العروس لمرتضى الزبيدي لهذا العضو بعينه؛ لا صلة موجبة ولا سالب."
        )
        counterpart = (
            f"{candidates} مرشحًا آليًا محفوظًا في الجرد؛ "
            "لم يُعيّن جذر أو نواة حاكمة قبل المسح الدلالي."
        )
        sound = (
            f"الجرد يحصي مرخّص={licensed} وفجوة نطاق={scope_gap}؛ "
            "هذه مخرجات استرداد لا صفوف حكم، ولم يُضف صف صوتي غير موقّع."
        )
    else:
        scan = (
            "لم يولّد الجرد المجمّد مرشحًا صوتيًا صالحًا لمسح مروحة "
            "لسان العرب لابن منظور وتاج العروس لمرتضى الزبيدي؛ "
            "لا صلة موجبة ولا ˋNO-TRACEˋ."
        )
        counterpart = "لا مقابل حاكم ولّده الجرد المجمّد."
        sound = "غير صادر؛ لا صف مخترع ولا صف صوتي جديد."
    orbit = (
        f"غير صادر؛ جوار الفرع «{compact(row['gloss']) or 'بلا شرح إنجليزي'}» "
        "لم يلتق بجوار عربي مسند في خطوة واحدة مسماة."
    )
    return scan, counterpart, sound, orbit


def closure_and_verdict(blocker: str, reason: str) -> tuple[str, str]:
    if blocker == "LOANWORD":
        return "READY؛ LOANWORD.", "LOANWORD؛ عزل مسار النقل، لا حكم نسب."
    if blocker == "PROPER-NAME-ISOLATED":
        return (
            "READY؛ PROPER-NAME-ISOLATED.",
            "غير صادر؛ أُغلق العضو بوصفه عَلَمًا مسمّى، لا صلةً معجمية.",
        )
    if blocker == "NONLEXICAL-ISOLATED":
        return (
            "READY؛ NONLEXICAL-ISOLATED.",
            "غير صادر؛ أُغلق العضو بوصفه علامة غير معجمية.",
        )
    return blocker + ".", f"غير صادر؛ {reason}"


def card(
    row: sqlite3.Row,
    spec: LanguageSpec,
    source_position: int,
    source_total: int,
) -> str:
    blocker, reason = disposition(row, spec.language)
    scan, counterpart, sound, orbit = semantic_lines(row, spec, blocker)
    closure, verdict = closure_and_verdict(blocker, reason)
    headword = compact(row["headword"]) or "بلا رسم"
    gloss = compact(row["gloss"]) or "بلا شرح إنجليزي"
    romanization = compact(row["romanization"]) or "بلا رومنة منشورة"
    pos = compact(row["pos"]) or "بلا نوع منشور"
    selected = compact(row["selected_input"]) or "غير معيّن"
    skeleton = compact(row["skeleton"]) or "غير مستعاد"
    family_id = compact(row["family_id"]) or "بلا أسرة في الجرد"
    role = compact(row["role"]) or "غير معيّن"
    members = int(row["member_count"] or 1)
    lemmas = int(row["lemma_count"] or 1)
    glosses = int(row["family_gloss_count"] or 0)
    candidate_members = int(row["candidate_bearing_member_count"] or 0)
    orphan = "نعم" if members == 1 else "لا"
    source_entry = row["entry_id"]
    source_id = row["source_entry_id"]
    return "\n".join(
        [
            (
                f"### بطاقة: ˋ{headword}ˋ «{gloss}» — "
                f"جرد اللقطة {source_position}/{source_total}"
            ),
            (
                f"<!-- lane-b-week2-full-coverage:"
                f"{spec.language}:{source_id} -->"
            ),
            f"- عائق: النوع={blocker}؛ يتطلب={reason}",
            f"- إصدارُ البروتوكول: {PROTOCOL}",
            (
                f"- الكلمةُ في الفرع: ˋ{headword}ˋ؛ {romanization}؛ {pos}؛ "
                f"العضو ˋ{source_entry}ˋ في الأسرة ˋ{family_id}ˋ."
            ),
            f"- أقدمُ صورةٍ مستعادة: {source_reference(row, spec)}.",
            (
                f"- الخطوةُ صفر (التعرية بصرف الفرع): حُفظ مدخل ˋ{selected}ˋ "
                f"بلا نزع تخميني؛ اللب الصامتي ˋ{skeleton}ˋ."
            ),
            (
                "- درجةُ المقارنة: الجذر الكامل أولًا، ثم الأجوف، ثم النواة؛ "
                "لم يتجاوز الحكم أدنى درجة نافذة."
            ),
            f"- مسحُ المعاني العربيّة: {scan}",
            f"- المقابلُ من اللسان: {counterpart}",
            f"- مسارُ الصوت: {sound}",
            (
                f"- المعنى من قاموس الفرع: «{gloss}» "
                f"[{spec.source_label}، ˋ{source_id}ˋ]."
            ),
            f"- المدار: {orbit}",
            f"- المصفاة: {filter_line(row, spec)}",
            (
                f"- فصلُ المتجانسات والاقتراض: الحكم للعضو ˋ{source_entry}ˋ "
                f"وحده داخل الأسرة ˋ{family_id}ˋ؛ لا يرث حكم جار."
            ),
            (
                f"- مؤشر اليتم: يتيم في فرعه={orphan}؛ حجم الأسرة={members}؛ "
                f"دور العضو=ˋ{role}ˋ؛ حق النقض العضوي محفوظ."
            ),
            (
                f"- إشعاع الأسرة في الفرع: الأعضاء في اللقطة={members}؛ "
                f"اللمم={lemmas}؛ سلاسل المعنى المنشورة={glosses}؛ "
                "هذا وصف للجرد لا توريث للحكم."
            ),
            (
                f"- إشعاع الأسرة في العربية: أعضاء الأسرة ذوو مرشح آلي="
                f"{candidate_members}؛ لا يثبت هذا إشعاعًا دلاليًا "
                "ولا يورث العضو حكمًا."
            ),
            (
                "- جسورُ الاسترداد المفحوصة: الرسم؛ الهيكل؛ الجذر؛ الأجوف؛ "
                "النواة؛ المروحة؛ الصرف؛ القرض؛ المدار."
            ),
            f"- حالةُ الإغلاق: {closure}",
            f"- الحكم (استكشاف): {verdict}",
            (
                f"- ملاحظات: موضع العضو في اللقطة المثبتة "
                f"{source_position}/{source_total}؛ بطاقة مقام كاملة؛ "
                "لا تدخل خط البرهان المجمّد."
            ),
            "",
        ]
    )


def validate_rendered_card(rendered: str, member_id: str) -> None:
    heading = rendered.splitlines()[0] if rendered else ""
    if not heading.startswith("### بطاقة:"):
        raise RuntimeError(
            f"Generated publication card {member_id} has a noncanonical heading"
        )
    missing = [field for field in PUBLICATION_CARD_FIELDS if field not in rendered]
    if missing:
        raise RuntimeError(
            f"Generated publication card {member_id} lacks fields: {missing}"
        )


def audit_text(
    spec: LanguageSpec,
    batch_number: int,
    batch_rows: list[sqlite3.Row],
    positions: dict[str, int],
    source_total: int,
    covered_after: int,
    counter: Counter[str],
    *,
    existing_slice: bool = False,
) -> str:
    first = batch_rows[0]
    last = batch_rows[-1]
    remaining = source_total - covered_after
    qualifier = (
        "دفعة قائمة أصلحت إغلاقات الأعلام والعلامات فيها"
        if existing_slice
        else "دفعة استكمال مرتبة بمعرف المصدر"
    )
    return "\n".join(
        [
            (
                f"# المسار ب: {spec.arabic_name}، التغطية الكاملة، "
                f"الدفعة {batch_number:03d}"
            ),
            "",
            f"- الحالة: LOCAL-NO-PROOF؛ {qualifier}.",
            f"- اللقطة المثبتة: {spec.source_label}.",
            (
                f"- بدأَت الدفعة من ˋ{first['entry_id']}ˋ "
                f"(موضع اللقطة {positions[first['source_entry_id']]}/{source_total}) "
                f"وانتهت عند ˋ{last['entry_id']}ˋ "
                f"(موضع اللقطة {positions[last['source_entry_id']]}/{source_total})؛ "
                f"بقي في الجرد بعدَها {remaining}."
            ),
            f"- عدد الأعضاء المفحوصة في الدفعة: {len(batch_rows)}.",
            f"- التغطية المتراكمة بعد الدفعة: {covered_after}/{source_total}.",
            "- الصلات الموجبة: 0.",
            f"- الإغلاقات: {closure_text(counter)}.",
            f"- الأحكام غير الصادرة: {unresolved_text(counter)}.",
            (
                "- معيار التخزين: الحكم الموجب أو الإغلاق النهائي وحده "
                "بطاقة RECOVERY-v2 كاملة؛ غير الصادر سطر JSONL واحد "
                "بمصيره وسببه، ولا سالب مصطنع ولا صف صوتي جديد."
            ),
            (
                "- بوابة المصدرين: لم تصدر في هذه الدفعة صلة موجبة؛ "
                "لذلك لم تُنسب مادة إلى مصدرين عربيين قديمين بلا فحص."
            ),
            (
                "- مصفاة القبطية: التصنيف اعتمد وسم المصدر الصريح وحده؛ "
                "U+03E2–U+03EF لم تُحسب حروفًا يونانية."
                if spec.language == "coptic"
                else "- مصفاة المصرية: عُزلت القروض والأعلام على مستوى العضو."
            ),
            "",
            "## الرقمان المفصولان",
            "",
            "- الصلات الموجبة: 0.",
            f"- الإغلاقات: {closure_total(counter)}.",
            "",
            "## الملفات المكتوب فيها",
            "",
            f"- ˋ{spec.reading.relative_to(ROOT).as_posix()}ˋ",
            f"- ˋ{COVERAGE.relative_to(ROOT).as_posix()}ˋ",
            (
                f"- ˋ05-audits/lane-b-{DATE}-{spec.language}-"
                f"full-coverage-batch-{batch_number:03d}.mdˋ"
            ),
            "",
        ]
    )


def write_audit(
    spec: LanguageSpec,
    batch_number: int,
    batch_rows: list[sqlite3.Row],
    positions: dict[str, int],
    source_total: int,
    covered_after: int,
    counter: Counter[str],
    *,
    existing_slice: bool = False,
) -> None:
    path = (
        AUDITS
        / f"lane-b-{DATE}-{spec.language}-full-coverage-"
        f"batch-{batch_number:03d}.md"
    )
    atomic_write(
        path,
        audit_text(
            spec,
            batch_number,
            batch_rows,
            positions,
            source_total,
            covered_after,
            counter,
            existing_slice=existing_slice,
        ),
    )


def append_batch(
    spec: LanguageSpec,
    batch_number: int,
    batch_rows: list[sqlite3.Row],
    positions: dict[str, int],
    source_total: int,
    covered_after: int,
    coverage_records: list[dict[str, object]],
) -> Counter[str]:
    counter = outcome_counts(batch_rows, spec.language)
    first = batch_rows[0]
    last = batch_rows[-1]
    remaining = source_total - covered_after
    header = [
        (
            f"## استكمال المسار ب: المقام الكامل في {spec.arabic_name} "
            f"— الدفعة {batch_number:03d}"
        ),
        "",
        (
            f"<!-- lane-b-full-coverage-batch:"
            f"{spec.language}:{batch_number:03d} -->"
        ),
        (
            f"- نطاق الدفعة: من ˋ{first['entry_id']}ˋ "
            f"(موضع {positions[first['source_entry_id']]}/{source_total}) "
            f"إلى ˋ{last['entry_id']}ˋ "
            f"(موضع {positions[last['source_entry_id']]}/{source_total})."
        ),
        f"- عدد الأعضاء: {len(batch_rows)}؛ الباقي بعد الدفعة: {remaining}.",
        (
            f"- النتيجة المحلية: الصلات الموجبة=0؛ "
            f"الإغلاقات={closure_text(counter)}؛ "
            f"الأحكام غير الصادرة={unresolved_text(counter)}."
        ),
        (
            "- المصير مسجل على مستوى العضو: الحكم أو الإغلاق النهائي في "
            "بطاقة RECOVERY-v2 كاملة، وغير الصادر في "
            "ˋ04-cross-linguistic/data/lane_b_coverage.jsonlˋ؛ "
            "لا توريث داخل الأسرة ولا مساس بخط البرهان المجمّد."
        ),
        "",
    ]
    prose_rows = [
        row for row in batch_rows if needs_prose_card(row, spec.language)
    ]
    machine_rows = [
        row for row in batch_rows if not needs_prose_card(row, spec.language)
    ]
    existing_ids = {str(record["member_id"]) for record in coverage_records}
    for row in machine_rows:
        if str(row["entry_id"]) in existing_ids:
            raise RuntimeError(
                f"Coverage JSONL already contains {row['entry_id']}"
            )
        coverage_records.append(coverage_record(row, spec, batch_number))
        existing_ids.add(str(row["entry_id"]))
    write_coverage(coverage_records)
    rendered_cards = [
        card(row, spec, positions[row["source_entry_id"]], source_total)
        for row in prose_rows
    ]
    for row, rendered in zip(prose_rows, rendered_cards, strict=True):
        validate_rendered_card(rendered, str(row["entry_id"]))
    body = header + rendered_cards
    body.extend(
        [
            (
                f"<!-- /lane-b-full-coverage-batch:"
                f"{spec.language}:{batch_number:03d} -->"
            ),
            "",
        ]
    )
    with spec.reading.open("a", encoding="utf-8", newline="\n") as handle:
        if spec.reading.stat().st_size:
            handle.write("\n")
        handle.write("\n".join(body))
        handle.flush()
        os.fsync(handle.fileno())
    return counter


def batch_numbers(spec: LanguageSpec, text: str) -> dict[str, int]:
    id_pattern = r"\d+" if spec.language == "egyptian" else r"C\d+"
    events = re.compile(
        rf"<!-- lane-b-full-coverage-batch:{spec.language}:(?P<batch>\d+) -->"
        rf"|<!-- lane-b-week2-full-coverage:{spec.language}:"
        rf"(?P<source>{id_pattern}) -->"
    )
    current_batch = 1
    mapping: dict[str, int] = {}
    for match in events.finditer(text):
        if match.group("batch"):
            current_batch = int(match.group("batch"))
            continue
        source_id = str(match.group("source"))
        if source_id in mapping:
            raise RuntimeError(
                f"Duplicate coverage member while reading batches: "
                f"{spec.language}:{source_id}"
            )
        mapping[source_id] = current_batch
    return mapping


def add_storage_policy(text: str) -> str:
    marker = "## سياسةُ تخزينِ التغطية"
    if marker in text:
        return text
    anchor = "## بطاقةُ القراءةِ الموحَّدة"
    offset = text.find(anchor)
    if offset < 0:
        raise RuntimeError("Could not locate the unified-card section")
    policy = "\n".join(
        [
            "## سياسةُ تخزينِ التغطية",
            "",
            (
                "- العضو ذو الحكم الموجب أو الإغلاق النهائي وحده يبقى "
                "بطاقة `RECOVERY-v2` كاملة في ملف القراءة."
            ),
            (
                "- العضو الذي لم يصدر له حكم يسجل سطرًا واحدًا في "
                "[`../data/lane_b_coverage.jsonl`](../data/lane_b_coverage.jsonl) "
                "بمعرّفه ولسانه ورسمه ومعنى الفرع وسبب عدم الإصدار ورقم الدفعة."
            ),
            (
                "- السطر الآلي مصير مسجل في مقام التغطية، وليس حكم صلة "
                "ولا إغلاقًا سلبيًا."
            ),
            "",
        ]
    )
    return text[:offset] + policy + "\n" + text[offset:]


def rewrite_storage_summaries(
    spec: LanguageSpec,
    text: str,
    rows_by_source: dict[str, sqlite3.Row],
    batches: dict[str, int],
) -> str:
    grouped: dict[int, list[sqlite3.Row]] = {}
    for source_id, batch_number in batches.items():
        grouped.setdefault(batch_number, []).append(rows_by_source[source_id])

    if 1 in grouped:
        counter = outcome_counts(grouped[1], spec.language)
        line = (
            f"- النتيجة المحلية للشريحة: الصلات الموجبة=0؛ "
            f"الإغلاقات النهائية={closure_text(counter)}؛ "
            f"المصائر غير الصادرة={unresolved_text(counter)}، "
            "وموضعها سجل JSONL الآلي."
        )
        text, count = re.subn(
            r"^- النتيجة المحلية للشريحة:.*$",
            line,
            text,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RuntimeError(
                f"Could not update initial storage summary for {spec.language}"
            )

    for batch_number, batch_rows in sorted(grouped.items()):
        if batch_number == 1:
            continue
        start_token = (
            f"<!-- lane-b-full-coverage-batch:"
            f"{spec.language}:{batch_number:03d} -->"
        )
        end_token = (
            f"<!-- /lane-b-full-coverage-batch:"
            f"{spec.language}:{batch_number:03d} -->"
        )
        start = text.find(start_token)
        end = text.find(end_token, start)
        if start < 0 or end < 0:
            raise RuntimeError(
                f"Could not locate batch {spec.language}:{batch_number:03d}"
            )
        segment = text[start:end]
        counter = outcome_counts(batch_rows, spec.language)
        line = (
            f"- النتيجة المحلية: الصلات الموجبة=0؛ "
            f"الإغلاقات النهائية={closure_text(counter)}؛ "
            f"المصائر غير الصادرة={unresolved_text(counter)} في سجل JSONL."
        )
        segment, count = re.subn(
            r"^- النتيجة المحلية:.*$",
            line,
            segment,
            count=1,
            flags=re.MULTILINE,
        )
        if count != 1:
            raise RuntimeError(
                f"Could not update batch summary "
                f"{spec.language}:{batch_number:03d}"
            )
        old_storage = (
            "- هذه دفعة مقام كاملة على مستوى العضو؛ لا توريث داخل الأسرة، "
            "ولا مساس بخط البرهان المجمّد."
        )
        new_storage = (
            "- المصير مسجل على مستوى العضو بين البطاقة الكاملة وسجل JSONL؛ "
            "لا توريث داخل الأسرة ولا مساس بخط البرهان المجمّد."
        )
        segment = segment.replace(old_storage, new_storage)
        text = text[:start] + segment + text[end:]
    text = text.replace(
        "هذه شريحة جديدة متصلة الحكم، وفيها بطاقة لكل عضو فُحص.",
        (
            "هذه شريحة جديدة متصلة المصير؛ لكل عضو حكم كامل أو سطر تغطية "
            "آلي بحسب سياسة التخزين."
        ),
    )
    return text


def migration_report_text(
    rows: list[dict[str, object]],
    jsonl_size: int,
) -> str:
    lines = [
        "# محضر نقل بطاقات التغطية غير الصادرة إلى JSONL",
        "",
        "- التاريخ: 2026-07-30.",
        (
            "- القاعدة: الحكم الموجب أو الإغلاق النهائي يبقى بطاقة "
            "RECOVERY-v2 كاملة؛ غير الصادر يسجل مرة واحدة على مستوى العضو "
            "في `04-cross-linguistic/data/lane_b_coverage.jsonl`."
        ),
        "",
        (
            "| اللسان | حجم القراءة قبل | حجم القراءة بعد | بطاقات غير صادرة "
            "نُقلت | بطاقات كاملة بقيت | أعضاء التغطية قبل | أعضاء التغطية بعد |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for row in rows:
        lines.append(
            f"| {row['arabic_name']} | {row['before_bytes']:,} بايت "
            f"({row['before_mib']:.3f} MiB) | {row['after_bytes']:,} بايت "
            f"({row['after_mib']:.3f} MiB) | {row['moved_cards']:,} | "
            f"{row['remaining_cards']:,} | {row['registered_before']:,} | "
            f"{row['registered_after']:,} |"
        )
    total_before = sum(int(row["registered_before"]) for row in rows)
    total_after = sum(int(row["registered_after"]) for row in rows)
    moved = sum(int(row["moved_cards"]) for row in rows)
    unique_machine = sum(int(row["coverage_rows"]) for row in rows)
    lines.extend(
        [
            "",
            "## تحقق المقام",
            "",
            f"- مجموع بطاقات «غير صادر» المنقولة من ملفي القراءة: {moved:,}.",
            (
                f"- السطور الآلية الفريدة على مستوى العضو: "
                f"{unique_machine:,}. البطاقات التاريخية المكررة اندمجت "
                "في مصير العضو الواحد ولم تُنشئ سطورًا مكررة."
            ),
            (
                f"- مجموع أعضاء التغطية المسجلين قبل النقل: "
                f"{total_before:,}؛ بعده: {total_after:,}."
            ),
            (
                "- النتيجة: لم ينقص مجموع الأعضاء المسجلة عضوًا واحدًا."
                if total_before == total_after
                else "- النتيجة: فشل ثبات المقام."
            ),
            (
                f"- حجم `lane_b_coverage.jsonl` بعد النقل: "
                f"{jsonl_size:,} بايت."
            ),
            "",
            "## الحقول الآلية",
            "",
            (
                "- `member_id`، `language`، `script`، `branch_gloss`، "
                "`non_issuance_reason`، `batch`."
            ),
            "",
        ]
    )
    return "\n".join(lines)


def migrate_existing_coverage(
    all_rows: dict[str, list[sqlite3.Row]],
) -> dict[str, object]:
    existing_records = load_coverage()
    retained_records = [
        record
        for record in existing_records
        if record["language"] not in {spec.language for spec in SPECS}
    ]
    pending_texts: dict[str, str] = {}
    batch_maps: dict[str, dict[str, int]] = {}
    before_sizes: dict[str, int] = {}
    moved_counts: dict[str, Counter[str]] = {}

    for spec in SPECS:
        text = spec.reading.read_text(encoding="utf-8")
        before_sizes[spec.language] = spec.reading.stat().st_size
        rows = all_rows[spec.language]
        rows_by_source = {str(row["source_entry_id"]): row for row in rows}
        batches = batch_numbers(spec, text)
        inventory_ids = set(rows_by_source)
        if set(batches) != inventory_ids:
            missing = sorted(inventory_ids - set(batches))
            extra = sorted(set(batches) - inventory_ids)
            raise RuntimeError(
                f"Cannot migrate {spec.language}; marker mismatch "
                f"missing={missing[:10]} extra={extra[:10]}"
            )
        batch_maps[spec.language] = batches
        for row in rows:
            if not needs_prose_card(row, spec.language):
                retained_records.append(
                    coverage_record(
                        row,
                        spec,
                        batches[str(row["source_entry_id"])],
                    )
                )
        stripped, counts = strip_unissued_cards(text)
        moved_counts[spec.language] = counts
        stripped = add_storage_policy(stripped)
        stripped = rewrite_storage_summaries(
            spec, stripped, rows_by_source, batches
        )
        pending_texts[spec.language] = stripped

    member_ids = [str(record["member_id"]) for record in retained_records]
    duplicates = [
        member_id
        for member_id, count in Counter(member_ids).items()
        if count > 1
    ]
    if duplicates:
        raise RuntimeError(
            f"Duplicate JSONL member ids after migration: {duplicates[:10]}"
        )

    for spec in SPECS:
        atomic_write(spec.reading, pending_texts[spec.language])
    write_coverage(retained_records)

    report_rows: list[dict[str, object]] = []
    for spec in SPECS:
        rows = all_rows[spec.language]
        text = pending_texts[spec.language]
        full_ids = set(marker_ids(spec, text))
        machine_ids = coverage_ids(retained_records, spec.language)
        inventory_entry_ids = {str(row["entry_id"]) for row in rows}
        full_entry_ids = {
            str(row["entry_id"])
            for row in rows
            if str(row["source_entry_id"]) in full_ids
        }
        if full_entry_ids & machine_ids:
            raise RuntimeError(
                f"Coverage overlap after migration for {spec.language}"
            )
        registered_after = len(full_entry_ids | machine_ids)
        if full_entry_ids | machine_ids != inventory_entry_ids:
            missing = sorted(inventory_entry_ids - (full_entry_ids | machine_ids))
            raise RuntimeError(
                f"Coverage loss after migration for {spec.language}: "
                f"{missing[:10]}"
            )
        after_size = spec.reading.stat().st_size
        report_rows.append(
            {
                "language": spec.language,
                "arabic_name": spec.arabic_name,
                "before_bytes": before_sizes[spec.language],
                "before_mib": before_sizes[spec.language] / (1024 * 1024),
                "after_bytes": after_size,
                "after_mib": after_size / (1024 * 1024),
                "moved_cards": moved_counts[spec.language]["cards"],
                "generated_cards_moved": moved_counts[spec.language][
                    "generated_cards"
                ],
                "legacy_cards_moved": moved_counts[spec.language][
                    "legacy_cards"
                ],
                "remaining_cards": len(
                    re.findall(r"(?m)^### بطاقة:", text)
                )
                - 1,
                "coverage_rows": len(machine_ids),
                "full_coverage_cards": len(full_entry_ids),
                "registered_before": len(rows),
                "registered_after": registered_after,
            }
        )

    for spec in SPECS:
        rows = all_rows[spec.language]
        positions = {
            str(row["source_entry_id"]): index
            for index, row in enumerate(rows, start=1)
        }
        grouped: dict[int, list[sqlite3.Row]] = {}
        for row in rows:
            grouped.setdefault(
                batch_maps[spec.language][str(row["source_entry_id"])], []
            ).append(row)
        covered_after = 0
        for batch_number, batch_rows in sorted(grouped.items()):
            covered_after += len(batch_rows)
            write_audit(
                spec,
                batch_number,
                batch_rows,
                positions,
                len(rows),
                covered_after,
                outcome_counts(batch_rows, spec.language),
                existing_slice=batch_number == 1,
            )

    report_path = (
        AUDITS / f"lane-b-{DATE}-coverage-storage-migration.md"
    )
    atomic_write(
        report_path,
        migration_report_text(
            report_rows,
            COVERAGE.stat().st_size,
        ),
    )
    return {
        "report": str(report_path.relative_to(ROOT)),
        "coverage_file": str(COVERAGE.relative_to(ROOT)),
        "languages": report_rows,
    }


def verify_language(
    spec: LanguageSpec,
    rows: list[sqlite3.Row],
    coverage_records: list[dict[str, object]],
) -> dict[str, object]:
    text = spec.reading.read_text(encoding="utf-8")
    full_source_ids = set(marker_ids(spec, text))
    rows_by_source = {str(row["source_entry_id"]): row for row in rows}
    rows_by_entry = {str(row["entry_id"]): row for row in rows}
    machine_entry_ids = coverage_ids(coverage_records, spec.language)
    full_entry_ids = {
        str(row["entry_id"])
        for source_id, row in rows_by_source.items()
        if source_id in full_source_ids
    }
    inventory_entry_ids = set(rows_by_entry)
    missing = sorted(
        inventory_entry_ids - (full_entry_ids | machine_entry_ids)
    )
    extra = sorted(
        (full_entry_ids | machine_entry_ids) - inventory_entry_ids
    )
    overlap = sorted(full_entry_ids & machine_entry_ids)
    expected_full = {
        str(row["entry_id"])
        for row in rows
        if needs_prose_card(row, spec.language)
    }
    wrong_storage = sorted(
        (full_entry_ids ^ expected_full)
        | (machine_entry_ids ^ (inventory_entry_ids - expected_full))
    )
    required_fields = PUBLICATION_CARD_FIELDS
    field_failures = Counter()
    card_pattern = re.compile(
        rf"^### بطاقة:[^\n]*\n"
        rf"<!-- lane-b-week2-full-coverage:{spec.language}:"
        rf"(?P<id>{r'\d+' if spec.language == 'egyptian' else r'C\d+'}) -->\n"
        rf"(?P<body>.*?)(?=^### بطاقة:|^<!-- /lane-b|^## |\Z)",
        flags=re.MULTILINE | re.DOTALL,
    )
    checked_blocks = 0
    positive_verdicts = 0
    negative_verdicts = 0
    unissued_generated: list[str] = []
    for match in card_pattern.finditer(text):
        checked_blocks += 1
        block = match.group(0)
        for field in required_fields:
            if field not in block:
                field_failures[field] += 1
        verdict = re.search(
            r"^- الحكم \(استكشاف\):(.*)$", block, re.MULTILINE
        )
        verdict_text = verdict.group(1) if verdict else ""
        positive_verdicts += bool(POSITIVE_PATTERN.search(verdict_text))
        negative_verdicts += "NO-TRACE" in verdict_text
        if card_outcome(block) == "unissued":
            unissued_generated.append(match.group("id"))
    if spec.language == "coptic":
        coptic_rule_failures = sum(
            "U+03E2–U+03EF حروف قبطية أصيلة" not in match.group(0)
            for match in card_pattern.finditer(text)
        )
    else:
        coptic_rule_failures = 0
    stripped, remaining_unissued = strip_unissued_cards(text)
    if stripped != text:
        prose_unissued = remaining_unissued["cards"]
    else:
        prose_unissued = 0
    return {
        "language": spec.language,
        "inventory": len(inventory_entry_ids),
        "full_cards": len(full_entry_ids),
        "coverage_rows": len(machine_entry_ids),
        "registered": len(full_entry_ids | machine_entry_ids),
        "missing": missing,
        "extra": extra,
        "overlap": overlap,
        "wrong_storage": wrong_storage,
        "checked_blocks": checked_blocks,
        "field_failures": dict(field_failures),
        "coptic_rule_failures": coptic_rule_failures,
        "positive_verdicts": positive_verdicts,
        "negative_verdicts": negative_verdicts,
        "unissued_generated": unissued_generated,
        "prose_unissued": prose_unissued,
    }


def final_audit(
    results: list[dict[str, object]],
    all_rows: dict[str, list[sqlite3.Row]],
) -> None:
    lines = [
        "# المسار ب: ختم جرد المصرية والقبطية بالتغطية الكاملة",
        "",
        "- الحالة: LOCAL-NO-PROOF؛ خط البرهان مجمّد.",
        (
            "- بدأ الجرد من أول عضو غير مغطى في كل لقطة، وانتهى عند آخر "
            "عضو فيها؛ بقي في الجرد بعد الختم 0."
        ),
        "",
        (
            "| اللسان | أعضاء اللقطة | بطاقات كاملة | سطور JSONL | "
            "المسجل | الباقي | إغلاقات نهائية |"
        ),
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    total_closures = 0
    for result in results:
        language = str(result["language"])
        spec = next(item for item in SPECS if item.language == language)
        counter = outcome_counts(all_rows[language], language)
        closures = closure_total(counter)
        total_closures += closures
        lines.append(
            f"| {spec.arabic_name} | {result['inventory']} | "
            f"{result['full_cards']} | {result['coverage_rows']} | "
            f"{result['registered']} | {len(result['missing'])} | {closures} |"
        )
    lines.extend(
        [
            "",
            "## الرقمان المفصولان",
            "",
            "- الصلات الموجبة في شريحة التغطية الكاملة: 0.",
            f"- الإغلاقات في شريحة التغطية الكاملة: {total_closures}.",
            "",
            "## تحقق القالب",
            "",
            (
                "- كل معرف في اللقطتين له مصير واحد فقط: بطاقة كاملة أو "
                "سطر JSONL، بلا تداخل."
            ),
            (
                "- كل بطاقة باقية تحمل حكمًا موجبًا أو إغلاقًا نهائيًا؛ "
                "لا بطاقة نثرية لحكم غير صادر."
            ),
            (
                "- كل سطر آلي يحمل معرف العضو واللسان والرسم ومعنى الفرع "
                "وسبب عدم الإصدار ورقم الدفعة."
            ),
            (
                "- لم يُنشأ NO-TRACE آلي، ولم يُخترع صف صوتي، ولم تُحتسب "
                "U+03E2–U+03EF يونانية."
            ),
            "",
            "## الملفات المكتوب فيها",
            "",
            "- ˋ04-cross-linguistic/readings/egyptian.mdˋ",
            "- ˋ04-cross-linguistic/readings/coptic.mdˋ",
            "- ˋ04-cross-linguistic/data/lane_b_coverage.jsonlˋ",
            "- محاضر ˋ05-audits/lane-b-*ˋ الخاصة بهذه الدفعات.",
            "- ˋscripts/lane_b_full_coverage.pyˋ",
            "",
        ]
    )
    atomic_write(
        AUDITS / f"lane-b-{DATE}-egyptian-coptic-full-coverage-final.md",
        "\n".join(lines),
    )


def run_plan(connection: sqlite3.Connection) -> dict[str, object]:
    payload: dict[str, object] = {"database": str(DB), "languages": {}}
    coverage_records = load_coverage()
    for spec in SPECS:
        metadata = source_metadata(connection, spec.language)
        rows = inventory_rows(connection, spec.language)
        text = spec.reading.read_text(encoding="utf-8")
        full_source_ids = set(marker_ids(spec, text))
        covered = {
            str(row["entry_id"])
            for row in rows
            if str(row["source_entry_id"]) in full_source_ids
        }
        covered |= coverage_ids(coverage_records, spec.language)
        payload["languages"][spec.language] = {
            "source_id": metadata["source_id"],
            "inventory": len(rows),
            "source_entries_seen": metadata["entries_seen"],
            "covered": len(covered),
            "remaining": len(rows) - len(covered),
        }
    return payload


def run_apply(connection: sqlite3.Connection) -> dict[str, object]:
    all_rows: dict[str, list[sqlite3.Row]] = {}
    for spec in SPECS:
        metadata = source_metadata(connection, spec.language)
        rows = inventory_rows(connection, spec.language)
        if len(rows) != metadata["entries_seen"]:
            raise RuntimeError(
                f"Inventory/source mismatch for {spec.language}: "
                f"{len(rows)} != {metadata['entries_seen']}"
            )
        all_rows[spec.language] = rows

    coverage_records = load_coverage()
    progress: dict[str, object] = {}
    for spec in SPECS:
        rows = all_rows[spec.language]
        positions = {
            str(row["source_entry_id"]): index
            for index, row in enumerate(rows, start=1)
        }
        text = spec.reading.read_text(encoding="utf-8")
        full_source_ids = set(marker_ids(spec, text))
        covered = {
            str(row["entry_id"])
            for row in rows
            if str(row["source_entry_id"]) in full_source_ids
        }
        covered |= coverage_ids(coverage_records, spec.language)
        remaining = [
            row for row in rows if str(row["entry_id"]) not in covered
        ]
        prior_batches = [
            int(value)
            for value in re.findall(
                rf"<!-- lane-b-full-coverage-batch:"
                rf"{spec.language}:(\d+) -->",
                text,
            )
        ]
        batch_number = max(prior_batches, default=1) + 1
        while remaining:
            batch_rows = remaining[:BATCH_SIZE]
            covered_after = len(covered) + len(batch_rows)
            counter = append_batch(
                spec,
                batch_number,
                batch_rows,
                positions,
                len(rows),
                covered_after,
                coverage_records,
            )
            for row in batch_rows:
                covered.add(str(row["entry_id"]))
            write_audit(
                spec,
                batch_number,
                batch_rows,
                positions,
                len(rows),
                len(covered),
                counter,
            )
            print(
                json.dumps(
                    {
                        "language": spec.language,
                        "batch": batch_number,
                        "start": batch_rows[0]["entry_id"],
                        "end": batch_rows[-1]["entry_id"],
                        "links": 0,
                        "closures": closure_total(counter),
                        "remaining": len(rows) - len(covered),
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
            remaining = remaining[BATCH_SIZE:]
            batch_number += 1
        progress[spec.language] = {
            "inventory": len(rows),
            "covered": len(covered),
            "remaining": len(rows) - len(covered),
        }

    coverage_records = load_coverage()
    results = [
        verify_language(
            spec,
            all_rows[spec.language],
            coverage_records,
        )
        for spec in SPECS
    ]
    failures = [
        result
        for result in results
        if result["missing"]
        or result["extra"]
        or result["overlap"]
        or result["wrong_storage"]
        or result["field_failures"]
        or result["coptic_rule_failures"]
        or result["negative_verdicts"]
        or result["unissued_generated"]
        or result["prose_unissued"]
        or result["registered"] != result["inventory"]
    ]
    if failures:
        raise RuntimeError(
            "Final full-coverage verification failed: "
            + json.dumps(failures, ensure_ascii=False)
        )
    final_audit(results, all_rows)
    return {"progress": progress, "verification": results}


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "command",
        choices=("plan", "migrate", "apply", "verify"),
        nargs="?",
        default="plan",
    )
    args = parser.parse_args()
    connection = connect()
    try:
        if args.command == "plan":
            payload = run_plan(connection)
        elif args.command == "migrate":
            all_rows = {
                spec.language: inventory_rows(connection, spec.language)
                for spec in SPECS
            }
            payload = migrate_existing_coverage(all_rows)
        elif args.command == "apply":
            payload = run_apply(connection)
        else:
            all_rows = {
                spec.language: inventory_rows(connection, spec.language)
                for spec in SPECS
            }
            coverage_records = load_coverage()
            payload = {
                "verification": [
                    verify_language(
                        spec,
                        all_rows[spec.language],
                        coverage_records,
                    )
                    for spec in SPECS
                ]
            }
    finally:
        connection.close()
    print(json.dumps(payload, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
