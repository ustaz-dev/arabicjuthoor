#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 38; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative ledger after OPEN-COMP-02620.
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

import harvest_ancient_greek_round37 as R37  # noqa: E402


R36, R35, R11 = R37.R36, R37.R35, R37.R11
READING, REPORT = R37.READING, R37.REPORT
DATE = "2026-08-27"
FIRST_COMPLETION, LAST_COMPLETION = 2621, 2720
EXPECTED_PREVIOUS = 2620
EXPECTED_POOL = 14_130
REMAINING_POOL = 14_030
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
EXPECTED_STRICT = Counter({2: 100})
EXPECTED_TOKENS = Counter({2: 98, 3: 2})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 100})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 97, "SOURCE-GAP": 3})
FIRST_MEMBER = "kaikki_ancient_greek:9091:en-εὐώδης-grc-adj-N77pCfvT"
LAST_MEMBER = "kaikki_ancient_greek:21289:en-γηθέω-grc-verb-zgrYhn9O"
EXPECTED_PRIOR_SURFACES = {
    "LANE-A-OPEN-COMP-02644": "δάος",
}
EXPECTED_SURFACE_GROUPS = {
    "οὐδός": 2,
    "ἰώδης": 2,
    "ἄγετε": 2,
}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:2f32bac160719cd706a1845d": 10,
    "ancient_greek:family:d2031d8b747384270481e00f": 2,
    "ancient_greek:family:b684a5a41aee2d52eb7eace1": 2,
    "ancient_greek:family:2dc4972e35a0b95db22aeec8": 2,
    "ancient_greek:family:fbf0223a55fb70079475010b": 2,
    "ancient_greek:family:8db93de5174b1d1a540afa57": 3,
    "ancient_greek:family:056c3c1a2f66ab234f036e0d": 2,
    "ancient_greek:family:05350ee3a58a849449db3381": 5,
    "ancient_greek:family:c2eceddc46460eae517f151b": 5,
    "ancient_greek:family:35a19f380c06d03f85ea6537": 2,
    "ancient_greek:family:3a1d62897c20a97cf23d67ee": 4,
    "ancient_greek:family:c9b2befab46c86bd9fd279ec": 2,
    "ancient_greek:family:b4573fba1ffbb0fa7d069b48": 2,
    "ancient_greek:family:768e34cda9160c6109d71235": 2,
}


def _configure_renderer() -> None:
    """Bind the stable renderer stack to the round-38 fixed window."""
    values = {
        "DATE": DATE,
        "FIRST_COMPLETION": FIRST_COMPLETION,
        "LAST_COMPLETION": LAST_COMPLETION,
        "EXPECTED_PREVIOUS": EXPECTED_PREVIOUS,
        "EXPECTED_POOL": EXPECTED_POOL,
        "REMAINING_POOL": REMAINING_POOL,
        "BATCH_SIZE": BATCH_SIZE,
        "CARD_COUNT": CARD_COUNT,
        "CHUNK_SIZE": CHUNK_SIZE,
        "EXPECTED_STRICT": EXPECTED_STRICT,
        "EXPECTED_TOKENS": EXPECTED_TOKENS,
        "EXPECTED_CATEGORIES": EXPECTED_CATEGORIES,
        "EXPECTED_VERDICTS": EXPECTED_VERDICTS,
        "FIRST_MEMBER": FIRST_MEMBER,
        "LAST_MEMBER": LAST_MEMBER,
        "EXPECTED_PRIOR_SURFACES": EXPECTED_PRIOR_SURFACES,
        "EXPECTED_SURFACE_GROUPS": EXPECTED_SURFACE_GROUPS,
        "EXPECTED_FAMILY_GROUPS": EXPECTED_FAMILY_GROUPS,
    }
    for name, value in values.items():
        setattr(R37, name, value)
    R37._configure_round36_renderer()


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    report = REPORT.read_text(encoding="utf-8")
    if "LANE-A DONE37 100 LANE-A-OPEN-COMP-02620" not in report:
        raise AssertionError("خاتمة DONE37 غير مثبتة")
    reading = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND37-CHUNK-50:END -->" not in reading:
        raise AssertionError("الجولة السابعة والثلاثون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND38-BATCH-1:START -->" in reading:
        raise AssertionError("بطاقات الجولة الثامنة والثلاثين موجودة")

    _configure_renderer()
    cards, records, meta = R36.render_all(allow_installed=True)
    adjusted_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        window_count = record["surface_window_count"]
        seen_before = record["completion_id"] in EXPECTED_PRIOR_SURFACES
        if seen_before:
            old_note = "الرسم سبق إتمامه إلى 02420"
            new_note = "الرسم سبق إتمامه إلى 02620"
            if window_count > 1:
                old_note += f" ومكرر في النافذة={window_count}"
                new_note += f" ومكرر في النافذة={window_count}"
        elif window_count == 1:
            old_note = "الرسم جديد إلى 02420"
            new_note = "الرسم جديد إلى 02620"
        else:
            old_note = new_note = f"الرسم مكرر في النافذة={window_count}"
        if card.count(old_note) != 1:
            raise AssertionError(f"تغير موضع فحص الرسم: {record['completion_id']}")
        card = card.replace(old_note, new_note, 1)
        card, size = R11.R6.compact_to_limit(card, record["completion_id"])
        record["bytes"] = size
        adjusted_cards.append(card)
    return adjusted_cards, records, meta


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
        f"<!-- LANE-A-GREEK-ROUND38-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة الثامنة والثلاثون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
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
    source_gaps = [record for record in records if record["verdict"] == "SOURCE-GAP"]
    gap_text = "؛ ".join(
        f"`{record['word']}` ({record['completion_id']})" for record in source_gaps
    )
    lines = [
        "",
        "<!-- LANE-A-GREEK-ROUND38-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الثامنة والثلاثون، إتمام الجرد المفتوح، الدفعة 1",
        "",
        f"- البطاقات: 50؛ المدى: `{first_batch[0]['completion_id']}` إلى `{first_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(first_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(first_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(first_batch, 'category')}.",
        "",
        f"## {DATE}، الجولة الثامنة والثلاثون، إتمام الجرد المفتوح، الدفعة 2",
        "",
        f"- البطاقات: 50؛ المدى: `{second_batch[0]['completion_id']}` إلى `{second_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(second_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(second_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(second_batch, 'category')}.",
        "",
        "## حصيلة الجولة الثامنة والثلاثين",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        f"- انتقال الرتل: أُخذت أول 100 بطاقة باقية من حوض `OPEN-CANDIDATE` بعد `02620`؛ كان الحوض {EXPECTED_POOL} عضوا وبقي بعد النافذة {meta['next_pool_remaining']} عضوا.",
        f"- فحص التكرار: معرّفات الأعضاء الفريدة={meta['unique_members']}؛ صورة سبق إتمامها={meta['prior_surface_rows']}؛ تكرار الرسم الزائد داخل النافذة={meta['surface_duplicate_rows']} في المجموعات {_groups_text(meta['surface_duplicate_groups'])}.",
        f"- فحص الأسرة: تكرار الصفوف الزائد={meta['family_duplicate_rows']} في المجموعات {_groups_text(meta['family_duplicate_groups'])}؛ حفظت الصفوف لأنها أعضاء مستقلة بمواضع مصدر مختلفة.",
        f"- الأحكام الكلية: {_distribution(records, 'verdict')}؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- ضبط الأرجل الثلاث: موجب مكتمل=0؛ حكم شريف مسمى السبب={meta['honourable_reasoned']}؛ حملت 97 بطاقة حكما مفتوحا لغياب مدار بشري محدود، وحملت 3 بطاقات `SOURCE-GAP` لغياب شاهد مصدري صالح.",
        f"- بوابة المصدر: بقيت بطاقات فجوة المصدر مفتوحة ولم يصنع غياب المصدر صلة: {gap_text}.",
        f"- الطبقتان: مجموع مرشحي الجذر={sum(record['roots'] for record in records)}؛ مجموع مرشحي النواة={sum(record['nuclei'] for record in records)}؛ خيارات الشاهد ذي المصدرين={sum(record['source_options'] for record in records)}؛ كل بطاقة قرأت الطبقتين معا.",
        f"- قاموس الإغلاق: استعمل {_distribution(records, 'closure')}، وكلها من القاموس المغلق المقرر؛ لم يولد وسم جديد.",
        "- أصناف النافذة: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(categories.items())) + ".",
        "- ضبط الهيكل الصارم: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(strict.items())) + "؛ صوامت `tokens_json`: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(tokens.items())) + ".",
        f"- حد الحجم: أكبر بطاقة {largest['bytes']} بايت، `{largest['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: اتصال المعرفات؛ مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ الأرجل؛ التكرار، من غير تشغيل git.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND38-REPORT:END -->",
        "",
        "LANE-A DONE38 100 LANE-A-OPEN-COMP-02720",
    ]
    report = "\n".join(lines)
    if "—" in report:
        raise AssertionError("شرطة طويلة في تقرير الجولة الثامنة والثلاثين")
    return report


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round38-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND37-CHUNK-50:END -->"
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
                lines += [f"<!-- LANE-A-GREEK-ROUND38-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND38-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R35.R34.R33.R30._anchored_patch(
                READING, "\n".join(lines), previous_anchor
            )
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        R35.R34.R33.R30._anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE37 100 LANE-A-OPEN-COMP-02620",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND38-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة الثامنة والثلاثون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND38-CHUNK-50:END -->", 1)[0]
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
            section.split(f"<!-- LANE-A-GREEK-ROUND38-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND38-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND38-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, records, meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND38-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    disposition_lines = len(re.findall(
        r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE
    ))
    previous_states = Counter(record["previous_state"] for record in records)
    verdicts = Counter(record["verdict"] for record in records)
    truncation_markers = len(re.findall(
        r"tokens truncated|chars truncated|lines truncated", section
    ))
    done = "LANE-A DONE38 100 LANE-A-OPEN-COMP-02720"
    report = REPORT.read_text(encoding="utf-8")
    report_marker = "<!-- LANE-A-GREEK-ROUND38-REPORT:START -->"
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
        or disposition_lines != CARD_COUNT
        or previous_states != Counter({"OPEN-CANDIDATE": CARD_COUNT})
        or verdicts != EXPECTED_VERDICTS
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
            f"repeats={repeat_lines} dispositions={disposition_lines} previous={previous_states} "
            f"verdicts={verdicts} truncation={truncation_markers} "
            f"report={exact_report} done={report.count(done)}"
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
        "disposition_lines": disposition_lines,
        "previous_states": dict(previous_states),
        "verdicts": dict(verdicts),
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
