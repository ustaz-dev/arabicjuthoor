#!/usr/bin/env python3
"""Run the section-26 priority pass over inflected function words.

This is a bounded queue stage, not a numerical yield target: it exhausts the
entire first-priority class (numerals, pronouns, and function words) in each of
lane C's six source inventories, then records the exact morphology remainder.
"""

from __future__ import annotations

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

import lane_c_section26_reopen as section26
import lane_c_standing_queue as queue
import lane_c_ie_week2_coverage as week2


if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


ROOT = Path(__file__).resolve().parents[1]
AUDIT = ROOT / "05-audits" / "lane-c-2026-07-30-section26-reopening.md"
PASS_MARKER = "<!-- LANE-C-SECTION26-FUNCTION-FORM-PASS-2026-07-30 -->"


def current_analyses() -> list[dict[str, Any]]:
    result: list[dict[str, Any]] = []
    language_by_key = {
        language.key: language for language in section26.LANGUAGES
    }
    for queue_language in week2.LANGUAGES:
        language = language_by_key[queue_language.key]
        path = section26.READINGS / language.reading_file
        text = path.read_text(encoding="utf-8")
        result.append(
            {
                "language": language,
                "path": path,
                "text": text,
                "cards": section26.parse_cards(text),
                "reopened_loans": [],
            }
        )
    return result


def refresh_morphology_queue() -> list[dict[str, Any]]:
    coverage = section26.load_coverage()
    rows, _ = section26.build_morph_queue(
        current_analyses(),
        coverage,
    )
    section26.atomic_write(
        section26.MORPH_QUEUE,
        section26.jsonl_text(rows, section26.MORPH_FIELDS),
    )
    return rows


def append_progress_audit(
    reports: list[dict[str, Any]],
    morph_rows: list[dict[str, Any]],
) -> None:
    old = AUDIT.read_text(encoding="utf-8")
    if PASS_MARKER in old:
        raise RuntimeError("function-form pass already recorded")
    remaining = {
        str(row["language"]): row for row in morph_rows
    }
    table = [
        "| اللسان | أعضاء الأولوية | بطاقات كاملة | أسطر تغطية | صلات | إغلاقات | الباقي الصرفي |",
        "|---|---:|---:|---:|---:|---:|---:|",
    ]
    for report in reports:
        counts = report["counts"]
        table.append(
            f"| {report['label']} | {counts['members']:,} | "
            f"{counts['cards']:,} | {counts['open']:,} | "
            f"{counts['positive']:,} | {counts['closures']:,} | "
            f"{remaining[report['key']]['pending']:,} |"
        )
    totals = Counter()
    for report in reports:
        totals.update(report["counts"])
    total_remaining = sum(int(row["pending"]) for row in morph_rows)
    positions = "\n".join(
        f"- {report['label']}: بدأ من {report['first']} وانتهى عند "
        f"{report['last']}؛ بقي بعد طبقة الأولوية "
        f"{remaining[report['key']]['pending']:,}."
        for report in reports
    )
    addition = section26.nfc(
        f"""

{PASS_MARKER}
## استئناف الطابور: طبقة الأعداد والضمائر والأدوات المصرفة

نُفذت طبقة الأولوية كاملة، لا بلوغًا لهدف عددي. قورنت كل صورة بالمعيار
نفسه؛ لم تغلق صورة بالإحالة، وكل عضو لم يحمل حكمًا أخذ سطره الآلي في
`lane_c_coverage.jsonl`. لم يُنشأ صف صوتي ولم يُخفف شرط المصدرين.

{chr(10).join(table)}

سطر الموضع لكل لسان:

{positions}

بعد الطبقة صار الباقي الصرفي المقيس {total_remaining:,}. موضعه الأول
والأخير في كل لسان محدثان في `lane_c_morphology_queue.jsonl`.

الرقمان المفصولان: **{totals['positive']:,} صلة موجبة؛
{totals['closures']:,} إغلاقًا**.
"""
    )
    with AUDIT.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write(addition)


def run() -> list[dict[str, Any]]:
    if PASS_MARKER in AUDIT.read_text(encoding="utf-8"):
        raise RuntimeError("function-form pass already applied")
    week2.POSITIVE_ALLOWLIST.update(queue.POSITIVE_ALLOWLIST)
    definitions = queue.discovery.load_arabic_english_definitions()
    source_counts = queue.discovery.load_classical_source_counts()
    scorer = queue.SemanticScorer(definitions)
    known_coverage_ids = queue.coverage_entry_ids()
    morph_before = {
        str(row["language"]): row
        for row in (
            json.loads(line)
            for line in section26.MORPH_QUEUE.read_text(
                encoding="utf-8"
            ).splitlines()
            if line.strip()
        )
    }
    reports: list[dict[str, Any]] = []

    for language in week2.LANGUAGES:
        path = queue.READINGS / language.reading_file
        used_ids = (
            queue.used_entry_ids(path)
            | queue.coverage_entry_ids(language.key)
        )
        connection = week2.ro_connection(language.db_path)
        try:
            pending = queue.queue_members(
                connection,
                language,
                used_ids,
                function_forms_only=True,
            )
            prior_batches = path.read_text(encoding="utf-8").count(
                f"<!-- {queue.MARKER_PREFIX}:{language.key}:"
            )
            complete_before = len(used_ids)
            aggregate = Counter(
                {
                    "members": 0,
                    "cards": 0,
                    "positive": 0,
                    "closures": 0,
                    "open": 0,
                }
            )
            processed = 0
            for member_chunk in queue.chunks(pending, 500):
                queue.attach_auxiliary_data(
                    connection,
                    member_chunk,
                    source_counts,
                    scorer,
                )
                batch_number = prior_batches + 1
                counts = queue.append_reading_batch(
                    language,
                    member_chunk,
                    batch_number,
                    complete_before + processed,
                    int(morph_before[language.key]["pending"])
                    - processed
                    - len(member_chunk),
                    known_coverage_ids,
                )
                aggregate.update(counts)
                processed += len(member_chunk)
                prior_batches += 1
                print(
                    f"{language.key}\tbatch={batch_number}"
                    f"\tmembers={counts['members']}"
                    f"\tcoverage={counts['open']}"
                    f"\tpositive={counts['positive']}"
                    f"\tclosures={counts['closures']}",
                    flush=True,
                )
        finally:
            connection.close()
        reports.append(
            {
                "key": language.key,
                "label": language.source_label,
                "first": (
                    f"{queue.display_member(pending[0])} "
                    f"(`{pending[0]['entry_id']}`)"
                    if pending
                    else "EMPTY"
                ),
                "last": (
                    f"{queue.display_member(pending[-1])} "
                    f"(`{pending[-1]['entry_id']}`)"
                    if pending
                    else "EMPTY"
                ),
                "counts": dict(aggregate),
            }
        )

    morph_rows = refresh_morphology_queue()
    append_progress_audit(reports, morph_rows)
    return reports


def main() -> int:
    reports = run()
    totals = Counter()
    for report in reports:
        totals.update(report["counts"])
    print(
        "FUNCTION-PASS-COMPLETE"
        f"\tmembers={totals['members']}"
        f"\tcoverage={totals['open']}"
        f"\tpositive={totals['positive']}"
        f"\tclosures={totals['closures']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
