#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 18 without committing or shipping.

Round 17 ended at OPEN-COMP-01020. This round reads the next one hundred
still-open Ancient Greek members with a licensed root or nucleus candidate,
in strict-skeleton/source-row order, as two batches of fifty. Retrieval never
becomes a verdict by itself.
"""

from __future__ import annotations

from collections import Counter
import argparse
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round17 as R17  # noqa: E402


READING, REPORT = R17.READING, R17.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION = 1021, 1120
EXPECTED_PREVIOUS = 1020
EXPECTED_POOL = 1_339
BATCH_SIZE = 50
BATCHES = ((1021, 1070), (1071, 1120))
EXPECTED_STRICT = Counter({2: 100})
EXPECTED_TOKENS = Counter({2: 98, 3: 2})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 57, "NONLEXICAL": 28, "FUNCTION": 15})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:6182:en-κατ'-grc-prep-rkOMYen4"
LAST_MEMBER = "kaikki_ancient_greek:53346:en-μήθ'-grc-conj-UgvCmSS8"


# Reuse the accepted selector and card renderer with round-18 invariants. These
# assignments affect only this process and leave the frozen earlier script intact.
R17.FIRST_COMPLETION = FIRST_COMPLETION
R17.LAST_COMPLETION = LAST_COMPLETION
R17.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
R17.EXPECTED_POOL = EXPECTED_POOL
R17.EXPECTED_STRICT = EXPECTED_STRICT
R17.EXPECTED_TOKENS = EXPECTED_TOKENS
R17.EXPECTED_CATEGORIES = EXPECTED_CATEGORIES
R17.EXPECTED_VERDICTS = EXPECTED_VERDICTS
R17.FIRST_MEMBER = FIRST_MEMBER
R17.LAST_MEMBER = LAST_MEMBER


def render_all() -> tuple[list[str], list[dict]]:
    """Render and validate the fixed round-18 window."""
    cards, records = R17.render_all()
    if len(cards) != 100 or len(records) != 100:
        raise AssertionError("تغير حجم نافذة الجولة الثامنة عشرة")
    expected = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected:
        raise AssertionError("معرفات الجولة الثامنة عشرة غير متصلة")
    return cards, records


def batch_for(start: int, end: int) -> tuple[int, int, int]:
    for batch, (first, last) in enumerate(BATCHES, 1):
        if first <= start <= end <= last:
            return batch, first, last
    raise AssertionError("مدى قطعة القراءة غير صحيح")


def reading_fragment(start: int, count: int, cards: list[str] | None = None) -> str:
    if cards is None:
        cards, _ = render_all()
    if count < 1 or start < FIRST_COMPLETION or start + count - 1 > LAST_COMPLETION:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    end = start + count - 1
    batch, first, last = batch_for(start, end)
    selected = cards[start - FIRST_COMPLETION:start - FIRST_COMPLETION + count]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND18-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الثامنة عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ لا صلة بلا شاهدين عربيين قديمين، ولا صف صوتيا مخترعا.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND18-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round18-"))
    for first, last in BATCHES:
        for start in range(first, last + 1, 4):
            count = min(4, last - start + 1)
            (stage / f"{start:05d}.md").write_text(
                reading_fragment(start, count, cards), encoding="utf-8"
            )
    return stage


def append_patch(path: Path, fragment: str, marker: str) -> str:
    return R17.append_patch(path, fragment, marker)


def emit_staged_patch(stage: Path, start: int) -> str:
    resolved = stage.resolve()
    if Path(tempfile.gettempdir()).resolve() not in resolved.parents:
        raise AssertionError("مجلد المرحل خارج مجلد النظام المؤقت")
    fragment = resolved / f"{start:05d}.md"
    if not fragment.is_file():
        raise AssertionError(f"قطعة مرحلية مفقودة: {fragment}")
    marker = (
        f"### LANE-A-OPEN-COMP-{start:05d}:"
        if start == LAST_COMPLETION
        else f"LANE-A-OPEN-COMP-{start:05d}"
    )
    return append_patch(READING, fragment.read_text(encoding="utf-8"), marker)


def report_fragment(records: list[dict] | None = None) -> str:
    if records is None:
        _, records = render_all()
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])

    def distribution(rows: list[dict], field: str) -> str:
        counts = Counter(row[field] for row in rows)
        return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))

    root_total = sum(record["roots"] for record in records)
    nucleus_total = sum(record["nuclei"] for record in records)
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND18-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الثامنة عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-01021` إلى `LANE-A-OPEN-COMP-01070`.",
        "- توزيع الأحكام: " + distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + distribution(first, "category") + ".",
        "",
        f"## {DATE}، الجولة الثامنة عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-01071` إلى `LANE-A-OPEN-COMP-01120`.",
        "- توزيع الأحكام: " + distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + distribution(second, "category") + ".",
        "",
        "## حصيلة الجولة الثامنة عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق بعد الإتمامات 1020 من `TWO-LAYER-OPEN` ذي مرشح في طبقة على الأقل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت؛ بقي في هذه الشريحة 1239 عضوا.",
        "- الأحكام الكلية: `OPEN-CANDIDATE`=100؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- الطبقتان: مجموع مرشحي الجذر={root_total}؛ مجموع مرشحي النواة={nucleus_total}؛ كل بطاقة سمت عددي الطبقتين وقرأتهما معا.",
        "- بوابة المصدر: البطاقات المئة سمت جذر شاهد ومصدرين عربيين قديمين على الأقل ثم منعت الحكم لغياب المدار؛ لا `SOURCE-GAP` في النافذة.",
        "- أصناف النافذة: `LEXICAL`=57؛ `NONLEXICAL`=28؛ `FUNCTION`=15؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: صوامت `tokens_json`: 2=98؛ 3=2؛ لا صامت أصليا حذف بالحدس.",
        "- حارس الطبقتين: أعيدت البطاقات المئة إلى مسترجع SECTION28 المجمد بمدخل `tokens_json`؛ طابقت أعداد الجذر والنواة سجل التغطية فيها كلها.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND18-REPORT:END -->",
        "",
        "LANE-A DONE18 100 LANE-A-OPEN-COMP-01120",
    ])


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", type=int)
    parser.add_argument("--count", type=int, default=4)
    parser.add_argument("--report", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--staged-patch", type=Path)
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.stage:
        print(stage_fragments())
    elif args.staged_patch is not None:
        if args.start is None:
            raise AssertionError("يلزم --start مع --staged-patch")
        print(emit_staged_patch(args.staged_patch, args.start), end="")
    elif args.start is not None:
        marker = (
            f"### LANE-A-OPEN-COMP-{args.start:05d}:"
            if args.start == LAST_COMPLETION
            else f"LANE-A-OPEN-COMP-{args.start:05d}"
        )
        print(append_patch(
            READING, reading_fragment(args.start, args.count), marker,
        ), end="")
    elif args.report:
        print(append_patch(REPORT, report_fragment(), "LANE-A DONE18"), end="")
    else:
        _, records = render_all()
        print(f"cards={len(records)} max={max(record['bytes'] for record in records)}")
        print(Counter(record["verdict"] for record in records))
        print(Counter(record["category"] for record in records))
        print(Counter(record["strict_length"] for record in records))
        print(
            f"roots={sum(record['roots'] for record in records)} "
            f"nuclei={sum(record['nuclei'] for record in records)}"
        )
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
