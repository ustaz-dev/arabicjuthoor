#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 36; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative ledger after OPEN-COMP-02420.
The fixed window takes the first one hundred still-unused OPEN-CANDIDATE
members in strict-skeleton-length then source-row order. Every card reads
both retrieval layers, keeps retrieval separate from judgment, and uses
only the repository's closed closure vocabulary.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_ancient_greek_round35 as R35  # noqa: E402


R17, R11 = R35.R17, R35.R11
READING, REPORT = R35.READING, R35.REPORT
DATE = "2026-08-26"
FIRST_COMPLETION, LAST_COMPLETION = 2421, 2520
EXPECTED_PREVIOUS = 2420
EXPECTED_POOL = 14_330
REMAINING_POOL = 14_230
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
EXPECTED_STRICT = Counter({2: 51, 1: 49})
EXPECTED_TOKENS = Counter({2: 97, 3: 3})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 100})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:998:en-εἷς-grc-num-dpLDrTVA"
LAST_MEMBER = "kaikki_ancient_greek:2085:en-δίκη-grc-noun-Hm4GuDeq"
EXPECTED_PRIOR_SURFACES = {
    "LANE-A-OPEN-COMP-02431": "ἕως",
    "LANE-A-OPEN-COMP-02432": "ἕως",
    "LANE-A-OPEN-COMP-02455": "ὀξέα",
}
EXPECTED_SURFACE_GROUPS = {
    "ὅς": 3,
    "ἑός": 2,
    "ὡς": 3,
    "ἕως": 2,
    "ὀξύ": 2,
    "ὄψ": 2,
}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:f242506e2e553faab95efb2d": 3,
    "ancient_greek:family:96a6566adab590f19777febe": 4,
    "ancient_greek:family:f2de7ee165ed45ab77d9775d": 2,
    "ancient_greek:family:0b36959d0d53ec58baba9586": 2,
    "ancient_greek:family:af2087a9ccc3399d50a90d6b": 3,
    "ancient_greek:family:8e0f3a21072585283f309af9": 4,
    "ancient_greek:family:45d6390237146dd28e1fc5a7": 2,
    "ancient_greek:family:582c1adb4abc96e46584ce3d": 2,
    "ancient_greek:family:ffa58b7d0e6964a13367b195": 5,
    "ancient_greek:family:337369ee2bf8d97397ad6c3e": 4,
    "ancient_greek:family:65e91fc109de05d3a9e9d0ab": 2,
    "ancient_greek:family:101861295ae489da356b97f3": 3,
}
_ORIGINAL_PREVIOUS_WORDS = R35._previous_words


def inventory_items() -> list[tuple[str, R11.InventoryItem]]:
    """Return the fixed first-one-hundred continuation of OPEN-CANDIDATE."""
    R17.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    used = R17.completed_members()
    coverage = R11.coverage_rows()
    tail: list[tuple[int, int, object, str]] = []
    pool: list[tuple[int, int, object, str]] = []
    con = R11.open_connection()
    try:
        rows = con.execute(
            """
            SELECT rowid AS source_rowid, entry_id, headword, romanization,
                   pos, gloss, etymology, source_stratum, selected_input,
                   skeleton, tokens_json, form_of, alternative_of,
                   form_targets_json, alternative_targets_json,
                   processing_status
            FROM entries WHERE language='ancient_greek' ORDER BY rowid
            """
        ).fetchall()
        for row in rows:
            member_id = R11.nfc(row["entry_id"])
            if member_id in used or member_id not in coverage:
                continue
            previous = R11.nfc(coverage[member_id].get("non_issuance_reason"))
            record = (
                len(R11.R2.branch_skeleton(R11.nfc(row["headword"]))),
                int(row["source_rowid"]),
                row,
                previous,
            )
            counts = R11.ZERO_LAYERS.search(previous)
            if counts is not None and counts.groups() != ("0", "0"):
                tail.append(record)
            elif previous == "OPEN-CANDIDATE":
                pool.append(record)

        tail.sort(key=lambda record: (record[0], record[1]))
        pool.sort(key=lambda record: (record[0], record[1]))
        if tail:
            raise AssertionError(f"عاد حوض TWO-LAYER-OPEN بعد استنفاده: {len(tail)}")
        if len(pool) != EXPECTED_POOL:
            raise AssertionError(f"تغير حوض OPEN-CANDIDATE: {len(pool)}")

        items: list[tuple[str, R11.InventoryItem]] = []
        for _strict, _rowid, row, previous in pool[:CARD_COUNT]:
            families = con.execute(
                """
                SELECT f.family_id, f.member_count, f.lemma_count
                FROM family_members fm JOIN families f ON f.family_id=fm.family_id
                WHERE fm.entry_id=? ORDER BY f.family_id
                """,
                (row["entry_id"],),
            ).fetchall()
            if len(families) != 1:
                raise AssertionError(f"عضو الجرد لا يحمل أسرة واحدة: {row['entry_id']}")
            items.append(("OPEN-CANDIDATE", R35._inventory_item(row, previous, families[0])))
    finally:
        con.close()

    members = [item for _subpool, item in items]
    if len(members) != CARD_COUNT or len({item.member_id for item in members}) != CARD_COUNT:
        raise AssertionError("تغير عد نافذة الجولة السادسة والثلاثين أو تكرر عضو")
    if members[0].member_id != FIRST_MEMBER or members[-1].member_id != LAST_MEMBER:
        raise AssertionError("تغير حدا نافذة الجولة السادسة والثلاثين")
    strict = Counter(len(R11.R2.branch_skeleton(item.word)) for item in members)
    tokens = Counter(len(item.tokens) for item in members)
    categories = Counter(R11.item_category(item) for item in members)
    if strict != EXPECTED_STRICT:
        raise AssertionError(f"تغير توزيع الهيكل الصارم: {strict}")
    if tokens != EXPECTED_TOKENS:
        raise AssertionError(f"تغير توزيع صوامت الجرد: {tokens}")
    if categories != EXPECTED_CATEGORIES:
        raise AssertionError(f"تغير توزيع أصناف الجرد: {categories}")
    return items


def _configure_round35_renderer() -> None:
    """Bind the stable round-35 renderer to the round-36 fixed window."""
    R35.R16.DATE = DATE
    R35.FIRST_COMPLETION = FIRST_COMPLETION
    R35.LAST_COMPLETION = LAST_COMPLETION
    R35.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    R35.TAIL_COUNT = 0
    R35.NEXT_POOL_COUNT = CARD_COUNT
    R35.EXPECTED_TAIL_POOL = 0
    R35.EXPECTED_NEXT_POOL = EXPECTED_POOL
    R35.REMAINING_NEXT_POOL = REMAINING_POOL
    R35.CARD_COUNT = CARD_COUNT
    R35.EXPECTED_STRICT = EXPECTED_STRICT
    R35.EXPECTED_TOKENS = EXPECTED_TOKENS
    R35.EXPECTED_CATEGORIES = EXPECTED_CATEGORIES
    R35.EXPECTED_VERDICTS = EXPECTED_VERDICTS
    R35.EXPECTED_SURFACE_GROUPS = EXPECTED_SURFACE_GROUPS
    R35.EXPECTED_FAMILY_GROUPS = EXPECTED_FAMILY_GROUPS
    R35.inventory_items = inventory_items


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    if "LANE-A DONE35 100 LANE-A-OPEN-COMP-02420" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE35 غير مثبتة")
    reading = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND35-CHUNK-50:END -->" not in reading:
        raise AssertionError("الجولة الخامسة والثلاثون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND36-BATCH-1:START -->" in reading:
        raise AssertionError("بطاقات الجولة السادسة والثلاثين موجودة")
    _configure_round35_renderer()
    prior_words = _ORIGINAL_PREVIOUS_WORDS()
    R35._previous_words = lambda: set()
    try:
        cards, records, meta = R35.render_all(allow_installed=True)
    finally:
        R35._previous_words = _ORIGINAL_PREVIOUS_WORDS

    prior_rows = {
        record["completion_id"]: record["word"]
        for record in records
        if record["word"] in prior_words
    }
    if prior_rows != EXPECTED_PRIOR_SURFACES:
        raise AssertionError(f"تغيرت صور الإتمامات السابقة في النافذة: {prior_rows!r}")

    adjusted_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        window_count = record["surface_window_count"]
        old_surface_note = (
            "الرسم جديد إلى 02320"
            if window_count == 1 else
            f"الرسم مكرر في النافذة={window_count}"
        )
        seen_before = record["completion_id"] in prior_rows
        if seen_before:
            new_surface_note = "الرسم سبق إتمامه إلى 02420"
            if window_count > 1:
                new_surface_note += f" ومكرر في النافذة={window_count}"
        elif window_count == 1:
            new_surface_note = "الرسم جديد إلى 02420"
        else:
            new_surface_note = old_surface_note
        if card.count(old_surface_note) != 1:
            raise AssertionError(f"تغير موضع فحص الرسم: {record['completion_id']}")
        card = card.replace(old_surface_note, new_surface_note, 1)
        card, size = R11.R6.compact_to_limit(card, record["completion_id"])
        record["bytes"] = size
        record["surface_seen_before"] = seen_before
        adjusted_cards.append(card)
    cards = adjusted_cards
    meta["prior_surface_rows"] = len(prior_rows)
    return cards, records, meta


def _distribution(rows: list[dict], field: str) -> str:
    counts = Counter(row[field] for row in rows)
    return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))


def _groups_text(groups: dict[str, int]) -> str:
    if not groups:
        return "0"
    return "؛ ".join(f"`{key}`={value}" for key, value in groups.items())


def batch_header(batch: int, records: list[dict]) -> list[str]:
    first, last = records[0]["completion_id"], records[-1]["completion_id"]
    return [
        f"<!-- LANE-A-GREEK-ROUND36-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة السادسة والثلاثون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
        "",
        f"- المواصلة متصلة من `{first}` إلى `{last}`؛ 50 بطاقة؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        f"- توزيع الأحواض: {_distribution(records, 'subpool')}.",
        "- فُحص تكرار معرّف العضو والرسم والأسرة في الذاكرة وفي النافذة؛ لم يسقط صف مستقل لمجرد اتحاد الرسم أو الأسرة.",
        "- لا موجب إلا بأرجل الصوت والحدث والمعنى كاملة؛ وما لم يكتمل حمل حكما شريفا مسمى السبب من قاموس الإغلاق المغلق.",
        "",
    ]


def report_addition(records: list[dict], meta: dict) -> str:
    first_batch, second_batch = records[:BATCH_SIZE], records[BATCH_SIZE:]
    categories = Counter(record["category"] for record in records)
    strict = Counter(record["strict_length"] for record in records)
    tokens = Counter(record["token_length"] for record in records)
    largest = max(records, key=lambda record: record["bytes"])
    lines = [
        "",
        "<!-- LANE-A-GREEK-ROUND36-REPORT:START -->",
        "",
        f"## {DATE}، الجولة السادسة والثلاثون، إتمام الجرد المفتوح، الدفعة 1",
        "",
        f"- البطاقات: 50؛ المدى: `{first_batch[0]['completion_id']}` إلى `{first_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(first_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(first_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(first_batch, 'category')}.",
        "",
        f"## {DATE}، الجولة السادسة والثلاثون، إتمام الجرد المفتوح، الدفعة 2",
        "",
        f"- البطاقات: 50؛ المدى: `{second_batch[0]['completion_id']}` إلى `{second_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(second_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(second_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(second_batch, 'category')}.",
        "",
        "## حصيلة الجولة السادسة والثلاثين",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        f"- انتقال الرتل: أُخذت أول 100 بطاقة باقية من حوض `OPEN-CANDIDATE` بعد `02420`؛ كان الحوض {EXPECTED_POOL} عضوا وبقي بعد النافذة {meta['next_pool_remaining']} عضوا.",
        f"- فحص التكرار: معرّفات الأعضاء الفريدة={meta['unique_members']}؛ صورة سبق إتمامها={meta['prior_surface_rows']}؛ تكرار الرسم الزائد داخل النافذة={meta['surface_duplicate_rows']} في المجموعات {_groups_text(meta['surface_duplicate_groups'])}.",
        f"- فحص الأسرة: تكرار الصفوف الزائد={meta['family_duplicate_rows']} في المجموعات {_groups_text(meta['family_duplicate_groups'])}؛ حفظت الصفوف لأنها أعضاء مستقلة بمواضع مصدر مختلفة.",
        f"- الأحكام الكلية: {_distribution(records, 'verdict')}؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- ضبط الأرجل الثلاث: موجب مكتمل=0؛ حكم شريف مسمى السبب={meta['honourable_reasoned']}؛ حملت البطاقات كلها حكما مفتوحا لغياب مدار بشري محدود.",
        "- بوابة المصدر: `SOURCE-GAP`=0؛ حملت كل بطاقة شاهدا مصدريا صالحا، ولم يصنع الاسترجاع وحده صلة.",
        f"- الطبقتان: مجموع مرشحي الجذر={sum(record['roots'] for record in records)}؛ مجموع مرشحي النواة={sum(record['nuclei'] for record in records)}؛ خيارات الشاهد ذي المصدرين={sum(record['source_options'] for record in records)}؛ كل بطاقة قرأت الطبقتين معا.",
        f"- قاموس الإغلاق: استعمل {_distribution(records, 'closure')}، وهو من القاموس المغلق المقرر؛ لم يولد وسم جديد.",
        "- أصناف النافذة: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(categories.items())) + ".",
        "- ضبط الهيكل الصارم: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(strict.items())) + "؛ صوامت `tokens_json`: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(tokens.items())) + ".",
        f"- حد الحجم: أكبر بطاقة {largest['bytes']} بايت، `{largest['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: اتصال المعرفات؛ مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ الأرجل؛ التكرار، من غير تشغيل git.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND36-REPORT:END -->",
        "",
        "LANE-A DONE36 100 LANE-A-OPEN-COMP-02520",
    ]
    report = "\n".join(lines)
    if "—" in report:
        raise AssertionError("شرطة طويلة في تقرير الجولة السادسة والثلاثين")
    return report


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round36-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND35-CHUNK-50:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, CHUNK_SIZE):
            chunk_number += 1
            lines: list[str] = []
            if offset == 0:
                lines += batch_header(batch, batch_records)
            for card in batch_cards[offset:offset + CHUNK_SIZE]:
                lines += [card, ""]
            if offset + CHUNK_SIZE == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND36-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND36-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R35.R34.R33.R30._anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        R35.R34.R33.R30._anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE35 100 LANE-A-OPEN-COMP-02420",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND36-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة السادسة والثلاثون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND36-CHUNK-50:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    global_ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", reading, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND36-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND36-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND36-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, records, meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND36-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(r"^- عائق: النوع=OPEN-CANDIDATE؛", section, re.MULTILINE))
    previous_states = Counter(record["previous_state"] for record in records)
    truncation_markers = len(re.findall(
        r"tokens truncated|chars truncated|lines truncated", section
    ))
    done = "LANE-A DONE36 100 LANE-A-OPEN-COMP-02520"
    report = REPORT.read_text(encoding="utf-8")
    report_marker = "<!-- LANE-A-GREEK-ROUND36-REPORT:START -->"
    report_start = report.find(report_marker)
    report_end = report.find(done, report_start)
    installed_report = (
        report[report_start:report_end + len(done)]
        if report_start >= 0 and report_end >= 0 else ""
    )
    exact_report = installed_report.rstrip() == report_addition(records, meta).strip()
    if (
        ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1))
        or global_ids != list(range(1, LAST_COMPLETION + 1))
        or batch_counts != [BATCH_SIZE, BATCH_SIZE]
        or len(cards) != CARD_COUNT
        or exact_cards != CARD_COUNT
        or len(markers) != 50
        or max_bytes > 5_120
        or repeat_lines != CARD_COUNT
        or leg_lines != CARD_COUNT
        or previous_states != Counter({"OPEN-CANDIDATE": CARD_COUNT})
        or truncation_markers
        or "—" in section
        or re.search(r"[۰-۹]", section)
        or not exact_report
        or report.count(done) != 1
        or report.count(report_marker) != 1
    ):
        raise AssertionError(
            f"فشل التحقق: ids={len(ids)} global={len(global_ids)} batches={batch_counts} "
            f"cards={len(cards)} exact={exact_cards} chunks={len(markers)} max={max_bytes} "
            f"repeats={repeat_lines} legs={leg_lines} previous={previous_states} "
            f"truncation={truncation_markers} report={exact_report} done={report.count(done)}"
        )
    return {
        "cards": len(cards),
        "batches": batch_counts,
        "chunks": len(markers),
        "first": ids[0],
        "last": ids[-1],
        "max_bytes": max_bytes,
        "exact_generated_cards": exact_cards,
        "duplicate_audit_lines": repeat_lines,
        "three_leg_disposition_lines": leg_lines,
        "previous_states": dict(previous_states),
        "remaining_pool": meta["next_pool_remaining"],
        "truncation_markers": truncation_markers,
        "exact_generated_report": exact_report,
        "done": done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    parser.add_argument("--records", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2))
        return 0
    if args.stage:
        print(stage_patches())
        return 0
    _cards, records, meta = render_all()
    print(json.dumps({
        **meta,
        "cards": len(records),
        "subpools": dict(Counter(record["subpool"] for record in records)),
        "closures": dict(Counter(record["closure"] for record in records)),
        "categories": dict(Counter(record["category"] for record in records)),
        "max_bytes": max(record["bytes"] for record in records),
        "last": records[-1]["completion_id"],
    }, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
