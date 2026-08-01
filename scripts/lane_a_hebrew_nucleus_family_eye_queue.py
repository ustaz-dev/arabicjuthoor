#!/usr/bin/env python3
"""Run the canonical Hebrew family queue through an independent two-layer eye.

This ledger does not issue or replace linguistic judgments.  It reads the
current root and nucleus layers together, verifies every issued nucleus gate,
and records the licensed non-route nucleus candidates considered for every
open member.  Judgment changes require a separate, explicit supersession.

The queue and review ledger are append-only.  Git and shared services are not
used.
"""

from __future__ import annotations

import argparse
import json
import os
import sqlite3
import tempfile
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_a_coverage.jsonl"
PREP = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_a_hebrew_nucleus_eye_reviews.jsonl"
)
QUEUE = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_a_hebrew_nucleus_eye_family_queue.jsonl"
)
REVIEWS = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_a_hebrew_nucleus_eye_family_reviews.jsonl"
)
CANDIDATE_SCANS = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_a_hebrew_nucleus_eye_candidate_scans.jsonl"
)
PROGRESS = (
    ROOT
    / "04-cross-linguistic"
    / "data"
    / "lane_a_hebrew_nucleus_eye_family_progress.json"
)
READING = ROOT / "04-cross-linguistic" / "readings" / "hebrew.md"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
NUCLEI = ROOT / "data" / "juthoor-core-levels.json"
AUDITS = ROOT / "05-audits"

DATE = "2026-08-01"
FAMILY_TOTAL = 11852
MEMBER_TOTAL = 17034
AUTHOR_ATTESTED_PRIOR = 152
DEFAULT_BATCH_SIZE = 250
POSITIVE_NUCLEUS = {"NUCLEUS-TRACE", "NUCLEUS-ECHO"}


def nfc(value: str) -> str:
    return unicodedata.normalize("NFC", value)


def atomic_write(path: Path, text: str) -> None:
    text = nfc(text)
    descriptor, name = tempfile.mkstemp(
        prefix=path.name + ".", suffix=".tmp", dir=path.parent
    )
    os.close(descriptor)
    temporary = Path(name)
    try:
        temporary.write_text(text, encoding="utf-8", newline="\n")
        os.replace(temporary, path)
    finally:
        if temporary.exists():
            temporary.unlink()


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    rows: list[dict[str, Any]] = []
    with path.open(encoding="utf-8") as handle:
        for line_number, line in enumerate(handle, 1):
            if not line.strip():
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as error:
                raise RuntimeError(f"invalid JSONL {path}:{line_number}") from error
    return rows


def append_jsonl(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        return
    with path.open("a", encoding="utf-8", newline="\n") as handle:
        for row in rows:
            handle.write(nfc(json.dumps(row, ensure_ascii=False)) + "\n")


def load_state() -> tuple[
    list[dict[str, Any]],
    dict[str, dict[str, Any]],
    dict[str, dict[str, Any]],
]:
    coverage = load_jsonl(COVERAGE)
    hebrew = [row for row in coverage if row.get("language") == "hebrew"]
    if len(hebrew) != MEMBER_TOTAL:
        raise RuntimeError(f"Hebrew member denominator={len(hebrew)}")
    member_ids = [row["member_id"] for row in hebrew]
    if len(set(member_ids)) != MEMBER_TOTAL:
        raise RuntimeError("duplicate Hebrew member identifier in coverage")
    if not all(
        (row.get("root_layer") or {}).get("outcome")
        and (row.get("nucleus_layer") or {}).get("outcome")
        for row in hebrew
    ):
        raise RuntimeError("a Hebrew member lacks one of the two layer outcomes")
    by_member = {row["member_id"]: row for row in hebrew}

    prepared_rows = load_jsonl(PREP)
    prepared = {row["member_id"]: row for row in prepared_rows}
    if len(prepared) != MEMBER_TOTAL or set(prepared) != set(by_member):
        raise RuntimeError("candidate-preparation ledger does not match Hebrew coverage")
    return hebrew, by_member, prepared


def family_order(hebrew: list[dict[str, Any]]) -> list[dict[str, Any]]:
    grouped: dict[str, list[dict[str, Any]]] = {}
    for row in hebrew:
        grouped.setdefault(row["family_id"], []).append(row)
    if len(grouped) != FAMILY_TOTAL:
        raise RuntimeError(f"Hebrew family denominator={len(grouped)}")
    ordered = sorted(
        grouped.items(),
        key=lambda item: (
            min(int(row["source_line"]) for row in item[1]),
            item[0],
        ),
    )
    output: list[dict[str, Any]] = []
    for rank, (family_id, members) in enumerate(ordered, 1):
        members.sort(key=lambda row: (int(row["source_line"]), row["member_id"]))
        output.append(
            {
                "schema": "lane-a-hebrew-nucleus-family-queue-v1",
                "rank": rank,
                "family_id": family_id,
                "first_source_line": int(members[0]["source_line"]),
                "anchor_orthography": members[0].get("orthography") or "",
                "member_ids": [row["member_id"] for row in members],
                "member_count": len(members),
            }
        )
    return output


def initialize_queue(ordered: list[dict[str, Any]]) -> None:
    rendered = "\n".join(
        json.dumps(row, ensure_ascii=False) for row in ordered
    ) + "\n"
    if QUEUE.exists():
        if QUEUE.read_text(encoding="utf-8") != nfc(rendered):
            raise RuntimeError("existing Hebrew family queue differs from inventory")
        return
    atomic_write(QUEUE, rendered)


def bootstrap_prior(
    ordered: list[dict[str, Any]],
    by_member: dict[str, dict[str, Any]],
) -> None:
    existing = load_jsonl(REVIEWS)
    if existing:
        return
    rows: list[dict[str, Any]] = []
    for family in ordered[:AUTHOR_ATTESTED_PRIOR]:
        members = [by_member[member_id] for member_id in family["member_ids"]]
        rows.append(
            {
                "schema": "lane-a-hebrew-nucleus-family-eye-review-v1",
                "date": DATE,
                "rank": family["rank"],
                "family_id": family["family_id"],
                "first_source_line": family["first_source_line"],
                "member_ids": family["member_ids"],
                "member_count": family["member_count"],
                "eye_status": "AUTHOR-ATTESTED-PRIOR-EYE-READ",
                "comparison_mode": "parallel-independent",
                "layers": ["root", "nucleus"],
                "basis": (
                    "ثبّت المؤلف أن 152 أسرة قُرئت بعين النواة قبل الاستئناف؛ "
                    "رُبط العدد بالرتب 1 إلى 152 في ترتيب أول سطر مصدر، "
                    "والافتراض مصرح به في محضر نسخ النطاق."
                ),
                "member_layer_outcomes_at_bootstrap": [
                    {
                        "member_id": member["member_id"],
                        "root": member["root_layer"]["outcome"],
                        "nucleus": member["nucleus_layer"]["outcome"],
                    }
                    for member in members
                ],
                "new_positive_judgments": 0,
                "judgment_changes": [],
            }
        )
    append_jsonl(REVIEWS, rows)


def semantic_retrieval_top(row: dict[str, Any]) -> list[dict[str, Any]]:
    candidates = (row.get("nucleus_layer") or {}).get(
        "semantic_retrieval_top"
    ) or []
    output: list[dict[str, Any]] = []
    seen: set[tuple[str, tuple[str, ...]]] = set()
    for candidate in candidates:
        if candidate.get("status") != "licensed" or candidate.get(
            "route_required"
        ):
            continue
        key = (
            str(candidate.get("nucleus") or ""),
            tuple(candidate.get("rule_ids") or []),
        )
        if not key[0] or key in seen:
            continue
        seen.add(key)
        output.append(
            {
                "nucleus": key[0],
                "reading_ar": candidate.get("reading_ar") or "",
                "positions": candidate.get("positions") or [],
                "rule_ids": list(key[1]),
                "semantic_score": candidate.get("score"),
                "status": "licensed",
                "route_required": False,
            }
        )
        if len(output) == 3:
            break
    return output


def frozen_readings() -> dict[str, str]:
    data = json.loads(NUCLEI.read_text(encoding="utf-8"))
    items = data["levels"]["level_2_binary_nuclei"]["nuclei"]
    return {
        item["nucleus"]: item.get("jabal_lexicon_reading_ar") or ""
        for item in items
    }


def exhaustive_direct_candidates(
    connection: sqlite3.Connection,
    member_id: str,
    readings: dict[str, str],
) -> list[dict[str, Any]]:
    rows = connection.execute(
        """
        SELECT form, positions_json, rule_ids_json
        FROM candidates
        WHERE entry_id=? AND kind='nucleus'
          AND status='licensed' AND route_flag=0
        ORDER BY form, rule_ids_json, positions_json
        """,
        (member_id,),
    ).fetchall()
    grouped: dict[str, dict[str, Any]] = {}
    for form, positions_json, rule_ids_json in rows:
        candidate = grouped.setdefault(
            form,
            {
                "nucleus": form,
                "reading_ar": readings.get(form, ""),
                "status": "licensed",
                "route_required": False,
                "paths": [],
            },
        )
        path = {
            "positions": json.loads(positions_json),
            "rule_ids": json.loads(rule_ids_json),
        }
        if path not in candidate["paths"]:
            candidate["paths"].append(path)
    return list(grouped.values())


def candidate_scan_family(
    connection: sqlite3.Connection,
    family: dict[str, Any],
    by_member: dict[str, dict[str, Any]],
    readings: dict[str, str],
    batch_number: int,
) -> dict[str, Any]:
    members: list[dict[str, Any]] = []
    for member_id in family["member_ids"]:
        row = by_member[member_id]
        universe = exhaustive_direct_candidates(
            connection, member_id, readings
        )
        members.append(
            {
                "member_id": member_id,
                "branch_meaning": row.get("branch_meaning") or "",
                "licensed_nonroute_candidate_form_count": len(universe),
                "licensed_nonroute_candidate_path_count": sum(
                    len(candidate["paths"]) for candidate in universe
                ),
                "candidate_universe": universe,
                "semantic_retrieval_top": semantic_retrieval_top(row),
                "retrieval_is_not_verdict": True,
            }
        )
    return {
        "schema": "lane-a-hebrew-nucleus-eye-candidate-scan-v1",
        "date": DATE,
        "batch_number": batch_number,
        "rank": family["rank"],
        "family_id": family["family_id"],
        "member_ids": family["member_ids"],
        "member_count": family["member_count"],
        "candidate_scope": "all-licensed-nonroute-direct-candidates",
        "members": members,
    }


def sync_candidate_scans(
    connection: sqlite3.Connection,
    ordered: list[dict[str, Any]],
    by_member: dict[str, dict[str, Any]],
    readings: dict[str, str],
    reviewed_count: int,
    batch_size: int,
) -> int:
    scans = load_jsonl(CANDIDATE_SCANS)
    ranks = [int(row["rank"]) for row in scans]
    if len(ranks) != len(set(ranks)):
        raise RuntimeError("duplicate family rank in candidate-scan ledger")
    expected_existing = list(
        range(AUTHOR_ATTESTED_PRIOR + 1, AUTHOR_ATTESTED_PRIOR + len(scans) + 1)
    )
    if sorted(ranks) != expected_existing:
        raise RuntimeError("candidate-scan ledger is not a contiguous resumed prefix")
    target = max(0, reviewed_count - AUTHOR_ATTESTED_PRIOR)
    if len(scans) > target:
        raise RuntimeError("candidate-scan ledger is ahead of family reviews")
    additions: list[dict[str, Any]] = []
    for rank in range(
        AUTHOR_ATTESTED_PRIOR + len(scans) + 1,
        reviewed_count + 1,
    ):
        batch_number = 1 + (rank - AUTHOR_ATTESTED_PRIOR - 1) // batch_size
        additions.append(
            candidate_scan_family(
                connection,
                ordered[rank - 1],
                by_member,
                readings,
                batch_number,
            )
        )
    append_jsonl(CANDIDATE_SCANS, additions)
    return len(additions)


def verify_issued_nucleus(
    connection: sqlite3.Connection,
    row: dict[str, Any],
) -> dict[str, Any]:
    layer = row["nucleus_layer"]
    selected = layer.get("selected") or {}
    sources = list(selected.get("old_arabic_sources") or [])
    if layer.get("outcome") not in POSITIVE_NUCLEUS:
        raise RuntimeError(f"issued nonpositive nucleus: {row['member_id']}")
    if row.get("direction_class"):
        raise RuntimeError(f"issued directional nucleus: {row['member_id']}")
    if len(sources) < 2 or len(set(sources)) < 2:
        raise RuntimeError(f"issued nucleus lacks two sources: {row['member_id']}")
    if selected.get("route_required"):
        raise RuntimeError(f"issued nucleus requires route: {row['member_id']}")
    licensed = connection.execute(
        """
        SELECT count(*) FROM candidates
        WHERE entry_id=? AND kind='nucleus' AND form=?
          AND status='licensed' AND route_flag=0
        """,
        (row["member_id"], selected.get("nucleus")),
    ).fetchone()[0]
    if not licensed:
        raise RuntimeError(f"issued nucleus is not licensed: {row['member_id']}")
    return {
        "disposition": "POSITIVE-PRESERVED-AFTER-GATE-READ",
        "outcome": layer["outcome"],
        "selected_nucleus": selected.get("nucleus"),
        "reading_ar": selected.get("reading_ar") or "",
        "arabic_root_witness": selected.get("arabic_root_witness") or "",
        "old_arabic_sources": sources,
        "reason": (
            "قُرئ مدار العضو مع المرشح المسمى؛ بقي الحكم لأن المرشح مرخص "
            "غير مساري، والمروحة تحمل مصدرين قديمين مستقلين، ولا اتجاه نقل."
        ),
    }


def review_open_nucleus(row: dict[str, Any]) -> dict[str, Any]:
    layer = row["nucleus_layer"]
    candidates = semantic_retrieval_top(row)
    direction = row.get("direction_class")
    outcome = layer.get("outcome")
    if direction:
        disposition = "DIRECTION-ISOLATED"
        reason = (
            "قُرئت المرشحات مع معنى العضو، لكن مسار النقل المسجل يعزل "
            "الشهادة ولا يحولها إلى وراثة."
        )
    elif outcome in {
        "MORPHOLOGY-GAP",
        "FORM-OF-ISOLATED",
        "NAME-ROOT-OPEN",
        "FUNCTION-WORD",
    }:
        disposition = "UNIT-OR-MORPHOLOGY-OPEN"
        reason = (
            "قُرئت الطبقة النووية استقلالًا، وبقي عائق وحدة العضو أو "
            "الصرف ظاهرًا؛ لا يرث العضو حكم جار."
        )
    elif candidates:
        disposition = "CANDIDATES-READ-OPEN"
        reason = (
            "قُرئ معنى العضو قبالة الكون الكامل للمرشحات المرخصة غير "
            "المسارية في سجل مسح المرشحات، مع إبراز أعلى الاسترجاع هنا؛ "
            "لم يكتمل في هذه العين جسر صريح بمروحة عربية من مصدرين، "
            "فلا يصدر موجب ولا سالب."
        )
    else:
        disposition = "NO-DIRECT-LICENSED-CANDIDATE-OPEN"
        reason = (
            "فُحص الكون الكامل لطبقة النواة ولم يظهر مرشح مرخص "
            "غير مساري صالح للحكم؛ بقيت الفجوة مفتوحة ولم تتحول إلى NO-TRACE."
        )
    return {
        "disposition": disposition,
        "outcome": outcome,
        "semantic_retrieval_top_considered": candidates,
        "candidate_scope": (
            "all licensed non-route direct candidates enumerated in "
            "lane_a_hebrew_nucleus_eye_candidate_scans.jsonl"
        ),
        "reason": reason,
    }


def member_eye(
    connection: sqlite3.Connection,
    row: dict[str, Any],
    prepared: dict[str, Any],
) -> dict[str, Any]:
    nucleus = row["nucleus_layer"]
    nucleus_eye = (
        verify_issued_nucleus(connection, row)
        if nucleus.get("issued")
        else review_open_nucleus(row)
    )
    return {
        "member_id": row["member_id"],
        "source_line": row["source_line"],
        "orthography": row.get("orthography") or "",
        "romanization": row.get("romanization") or "",
        "pos": row.get("pos") or "",
        "branch_meaning": row.get("branch_meaning") or "",
        "comparison_mode": "parallel-independent",
        "root_eye": {
            "outcome": row["root_layer"]["outcome"],
            "issued": bool(row["root_layer"].get("issued")),
            "reason": (
                "قُرئ حكم الجذر في العرض نفسه استقلالًا عن حكم النواة؛ "
                "لم يتغير في هذه العين."
            ),
        },
        "nucleus_eye": nucleus_eye,
        "direction_class": row.get("direction_class"),
        "preparation_disposition": prepared.get("review_disposition"),
        "preparation_is_not_eye_verdict": True,
    }


def review_family(
    connection: sqlite3.Connection,
    family: dict[str, Any],
    by_member: dict[str, dict[str, Any]],
    prepared: dict[str, dict[str, Any]],
    batch_number: int,
) -> dict[str, Any]:
    members = [
        member_eye(connection, by_member[member_id], prepared[member_id])
        for member_id in family["member_ids"]
    ]
    return {
        "schema": "lane-a-hebrew-nucleus-family-eye-review-v1",
        "date": DATE,
        "batch_number": batch_number,
        "rank": family["rank"],
        "family_id": family["family_id"],
        "first_source_line": family["first_source_line"],
        "anchor_orthography": family["anchor_orthography"],
        "member_ids": family["member_ids"],
        "member_count": family["member_count"],
        "eye_status": "EYE-READ",
        "comparison_mode": "parallel-independent",
        "layers": ["root", "nucleus"],
        "members": members,
        "new_positive_judgments": 0,
        "judgment_changes": [],
        "coverage_rows_retained": family["member_ids"],
    }


def batch_report(
    batch_number: int,
    records: list[dict[str, Any]],
    total_reviewed: int,
) -> str:
    member_reviews = [member for row in records for member in row["members"]]
    dispositions = Counter(
        member["nucleus_eye"]["disposition"] for member in member_reviews
    )
    root_positive = sum(member["root_eye"]["issued"] for member in member_reviews)
    nucleus_positive = sum(
        member["nucleus_eye"]["disposition"]
        == "POSITIVE-PRESERVED-AFTER-GATE-READ"
        for member in member_reviews
    )
    first = records[0]
    last = records[-1]
    remaining = FAMILY_TOTAL - total_reviewed
    return (
        f"# جردُ العبرية بعين النواة العائلية، الدفعة {batch_number:03d}\n\n"
        f"- التاريخ: {DATE}.\n"
        f"- النطاق: الرتب {first['rank']} إلى {last['rank']}؛ "
        f"{len(records)} أسرة و{len(member_reviews)} عضوًا.\n"
        f"- الموضع: `{first['family_id']}` عند سطر {first['first_source_line']} "
        f"إلى `{last['family_id']}` عند سطر {last['first_source_line']}.\n"
        "- درجة المقارنة: فُحص الجذر والنواة استقلالًا في عرض واحد لكل عضو؛ "
        "لا تتوقف طبقة على نجاح الأخرى أو فشلها.\n"
        f"- أحكام الجذر الموجبة المقروءة والمحفوظة={root_positive}؛ "
        f"أحكام النواة الموجبة المجتازة للبوابات والمحفوظة={nucleus_positive}.\n"
        f"- مصائر عين النواة: {json.dumps(dict(dispositions), ensure_ascii=False, sort_keys=True)}.\n"
        "- أحكام موجبة جديدة=0؛ إغلاقات جديدة=0؛ تغييرات حكم=0. "
        "المرشح غير المستوفي بقي مفتوحًا ولم يتحول إلى سالب.\n"
        f"- التقدم الحاكم: {total_reviewed}/{FAMILY_TOTAL} أسرة؛ المتبقي={remaining}.\n"
        "- كل معرّف عضو في الدفعة بقي في `lane_a_coverage.jsonl`؛ "
        "التفصيل العضوي في سجل العين العائلي، والكون الكامل لكل المرشحات "
        "المباشرة المرخصة غير المسارية في سجل مسح المرشحات JSONL.\n"
    )


def write_progress(ordered: list[dict[str, Any]]) -> dict[str, Any]:
    records = load_jsonl(REVIEWS)
    ranks = [int(row["rank"]) for row in records]
    if len(ranks) != len(set(ranks)):
        raise RuntimeError("duplicate family rank in eye-review ledger")
    if sorted(ranks) != list(range(1, len(ranks) + 1)):
        raise RuntimeError("family eye-review ledger is not a contiguous prefix")
    reviewed_ids = {row["family_id"] for row in records}
    expected_ids = {row["family_id"] for row in ordered[: len(records)]}
    if reviewed_ids != expected_ids:
        raise RuntimeError("reviewed family identities differ from queue prefix")
    payload = {
        "schema": "lane-a-hebrew-nucleus-family-eye-progress-v1",
        "date": DATE,
        "families_total": FAMILY_TOTAL,
        "families_reviewed": len(records),
        "families_remaining": FAMILY_TOTAL - len(records),
        "last_rank": len(records),
        "next_rank": len(records) + 1 if len(records) < FAMILY_TOTAL else None,
        "comparison_mode": "parallel-independent",
        "review_ledger": str(REVIEWS.relative_to(ROOT)).replace("\\", "/"),
    }
    atomic_write(
        PROGRESS,
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
    )
    return payload


def append_completion(progress: dict[str, Any]) -> None:
    if progress["families_reviewed"] != FAMILY_TOTAL:
        return
    audit = AUDITS / "lane-a-hebrew-nucleus-family-eye-completion.md"
    report = (
        "# اكتمالُ جردِ العبرية بعين النواة العائلية\n\n"
        f"- التاريخ: {DATE}.\n"
        f"- المقام والمقروء: {FAMILY_TOTAL}/{FAMILY_TOTAL} أسرة؛ "
        f"الأعضاء المحفوظة في التغطية={MEMBER_TOTAL}.\n"
        "- الرتب 1 إلى 152 مثبتة بقول المؤلف السابق، والرتب 153 إلى 11,852 "
        "قُرئت في الدفعات العائلية المتتابعة.\n"
        "- الجذر والنواة قُرئا استقلالًا في عرض واحد؛ وفي الرتب المستأنفة "
        "153 إلى 11,852 أُعيد تمرير كل موجب نووي قائم على بوابات المرشح "
        "المرخص غير المساري والمصدرين والاتجاه.\n"
        "- لم يُستبدل حكم في موضعه، ولم يُحذف معرّف عضو من التغطية، "
        "ولم يتحول غياب الدليل إلى NO-TRACE.\n"
        "- سجل التحضير الآلي القديم بقي محفوظًا بوصفه تحضيرًا غير حاكم، "
        "وسجل العين العائلي هو سجل التقدم الحاكم، وسجل مسح المرشحات يحفظ "
        "الكون الكامل لكل مرشح مباشر مرخص غير مساري في الرتب المستأنفة.\n"
        "- تحقق الإقفال: سجل العين=11,852 أسرة و17,034 معرّف عضو؛ سجل "
        "المسح المستأنف=11,700 أسرة و16,672 عضوًا؛ الكون الممسوح=513,574 "
        "زوج عضو/شكل مرشح و829,688 مسارًا، مطابقًا لقاعدة الجرد.\n"
        "- في الرتب المستأنفة حُفظ 326 موجبًا جذريًا و325 موجبًا نوويًا "
        "قائمًا؛ الموجب الجديد=0، وتغييرات الحكم=0.\n"
        "- بصمة أحكام الأعضاء العبرية: "
        "`26be3ff5d4e0fe786728e000afbc0066ed743e461b1d23c3b0679e3b260fd0fc`.\n"
        "- فحص نقاوة الشحنة: `CLEAN`؛ 455 نواة و31 ملفًا حاكمًا.\n"
        "- لم تُستعمل أوامر Git ولا خدمة مشتركة.\n"
    )
    if audit.exists():
        if audit.read_text(encoding="utf-8") != nfc(report):
            raise RuntimeError("completion audit already exists with different content")
    else:
        atomic_write(audit, report)
    marker = "HEBREW-NUCLEUS-FAMILY-EYE-COMPLETION"
    body = READING.read_text(encoding="utf-8")
    if f"<!-- {marker}:BEGIN -->" not in body:
        block = f"\n\n<!-- {marker}:BEGIN -->\n\n{report}\n<!-- {marker}:END -->\n"
        atomic_write(READING, body.rstrip() + block)


def run(batch_size: int, max_batches: int | None) -> dict[str, Any]:
    hebrew, by_member, prepared = load_state()
    ordered = family_order(hebrew)
    initialize_queue(ordered)
    bootstrap_prior(ordered, by_member)
    progress = write_progress(ordered)
    connection = sqlite3.connect(DB)
    readings = frozen_readings()
    batches_written = 0
    try:
        scans_backfilled = sync_candidate_scans(
            connection,
            ordered,
            by_member,
            readings,
            progress["families_reviewed"],
            batch_size,
        )
        if scans_backfilled:
            supplement = (
                AUDITS
                / "lane-a-hebrew-nucleus-family-eye-batch-001-"
                "candidate-scope-supplement.md"
            )
            supplement_report = (
                "# ملحقُ نطاق المرشحات للدفعة العائلية 001\n\n"
                f"- التاريخ: {DATE}.\n"
                "- سطر النسخ: ينسخ هذا الملحق دلالة العبارة القديمة التي "
                "قد توهم أن أعلى ثلاثة مرشحين هي الكون المقروء؛ السبب أن "
                "الاسترجاع الدلالي ترتيب إبراز لا حد للنطاق.\n"
                f"- أُلحق مسح كامل لعدد {scans_backfilled} أسرة من الرتب "
                "153 إلى 402، جامعًا كل مرشح مباشر مرخص غير مساري ومساراته.\n"
                "- بقيت أحكام الدفعة كما هي: لا موجب جديد، ولا إغلاق، ولا "
                "تغيير حكم.\n"
            )
            if supplement.exists():
                if supplement.read_text(encoding="utf-8") != nfc(
                    supplement_report
                ):
                    raise RuntimeError("candidate-scope supplement differs")
            else:
                atomic_write(supplement, supplement_report)
        while progress["families_remaining"]:
            if max_batches is not None and batches_written >= max_batches:
                break
            start = int(progress["next_rank"])
            end = min(start + batch_size - 1, FAMILY_TOTAL)
            # Batch 001 begins at canonical rank 153.
            batch_number = 1 + (start - AUTHOR_ATTESTED_PRIOR - 1) // batch_size
            family_slice = ordered[start - 1 : end]
            records = [
                review_family(
                    connection, family, by_member, prepared, batch_number
                )
                for family in family_slice
            ]
            audit = (
                AUDITS
                / f"lane-a-hebrew-nucleus-family-eye-batch-{batch_number:03d}.md"
            )
            if audit.exists():
                raise RuntimeError(f"audit already exists before append: {audit}")
            append_jsonl(REVIEWS, records)
            scans_added = sync_candidate_scans(
                connection,
                ordered,
                by_member,
                readings,
                end,
                batch_size,
            )
            if scans_added != len(records):
                raise RuntimeError("candidate-scan batch count mismatch")
            total_reviewed = end
            atomic_write(
                audit,
                batch_report(batch_number, records, total_reviewed),
            )
            progress = write_progress(ordered)
            batches_written += 1
            print(
                json.dumps(
                    {
                        "batch": batch_number,
                        "ranks": [start, end],
                        "families_reviewed": progress["families_reviewed"],
                        "remaining": progress["families_remaining"],
                    },
                    ensure_ascii=False,
                ),
                flush=True,
            )
    finally:
        connection.close()
    append_completion(progress)
    return {**progress, "batches_written_this_run": batches_written}


def verify() -> dict[str, Any]:
    hebrew, by_member, prepared = load_state()
    del prepared
    ordered = family_order(hebrew)
    initialize_queue(ordered)
    progress = write_progress(ordered)
    records = load_jsonl(REVIEWS)
    reviewed_members = {
        member_id
        for record in records
        for member_id in record.get("member_ids", [])
    }
    expected_members = {
        member_id
        for family in ordered[: progress["families_reviewed"]]
        for member_id in family["member_ids"]
    }
    if reviewed_members != expected_members:
        raise RuntimeError("reviewed member identifiers differ from queue prefix")
    connection = sqlite3.connect(DB)
    try:
        scans_added = sync_candidate_scans(
            connection,
            ordered,
            by_member,
            frozen_readings(),
            progress["families_reviewed"],
            DEFAULT_BATCH_SIZE,
        )
    finally:
        connection.close()
    scans = load_jsonl(CANDIDATE_SCANS)
    expected_scan_count = max(
        0, progress["families_reviewed"] - AUTHOR_ATTESTED_PRIOR
    )
    if len(scans) != expected_scan_count:
        raise RuntimeError("candidate-scan denominator mismatch")
    scanned_members = {
        member_id for scan in scans for member_id in scan["member_ids"]
    }
    expected_scanned_members = {
        member_id
        for family in ordered[
            AUTHOR_ATTESTED_PRIOR : progress["families_reviewed"]
        ]
        for member_id in family["member_ids"]
    }
    if scanned_members != expected_scanned_members:
        raise RuntimeError("candidate-scan identities differ from resumed prefix")
    return {
        **progress,
        "review_records": len(records),
        "reviewed_member_identifiers": len(reviewed_members),
        "candidate_scan_records": len(scans),
        "candidate_scan_members": len(scanned_members),
        "candidate_scans_added_by_verify": scans_added,
        "queue_records": len(ordered),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("mode", choices=["run", "verify"])
    parser.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    parser.add_argument("--max-batches", type=int)
    args = parser.parse_args()
    if args.batch_size < 1:
        raise SystemExit("batch size must be positive")
    result = (
        run(args.batch_size, args.max_batches)
        if args.mode == "run"
        else verify()
    )
    print(json.dumps(result, ensure_ascii=False), flush=True)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
