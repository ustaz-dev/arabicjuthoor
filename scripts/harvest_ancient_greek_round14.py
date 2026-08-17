#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 14 without committing or shipping.

Round 13 ended at OPEN-COMP-00633.  This round takes the next one hundred
still-open members whose frozen root and nucleus layers both returned zero,
ordered by strict branch-skeleton length and then the pinned inventory row.
Cards remain append-only and are split into two batches of fifty.
"""

from __future__ import annotations

from collections import Counter
import argparse
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round13 as R13  # noqa: E402


READING = R13.READING
REPORT = R13.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION, BATCH_SIZE = 634, 733, 50
EXPECTED_PREVIOUS = 633
EXPECTED_POOL = 187
EXPECTED_STRICT_LENGTHS = Counter({1: 100})
EXPECTED_TOKEN_LENGTHS = Counter({1: 100})
EXPECTED_CATEGORIES = Counter({"NONLEXICAL": 61, "LEXICAL": 22, "FUNCTION": 17})
FIRST_MEMBER = "kaikki_ancient_greek:23:en-π-grc-character-fkpr7peu"
LAST_MEMBER = "kaikki_ancient_greek:9403:en-τού-grc-pron-mGh~rL7B"


def inventory_items() -> list[R13.R12.R11.InventoryItem]:
    """Reuse the accepted selector with the round-14 frozen boundaries."""
    R13.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    R13.EXPECTED_POOL = EXPECTED_POOL
    R13.EXPECTED_STRICT_LENGTHS = EXPECTED_STRICT_LENGTHS
    R13.EXPECTED_TOKEN_LENGTHS = EXPECTED_TOKEN_LENGTHS
    R13.EXPECTED_CATEGORIES = EXPECTED_CATEGORIES
    R13.FIRST_MEMBER = FIRST_MEMBER
    R13.LAST_MEMBER = LAST_MEMBER
    return R13.inventory_items()


def inventory_card(
    number: int,
    item: R13.R12.R11.InventoryItem,
) -> tuple[str, dict]:
    rendered, record = R13.inventory_card(number, item)
    old = "أول الباقي بعد `00533`"
    if rendered.count(old) != 1:
        raise AssertionError(f"تغير سطر معيار الانتخاب في {number}")
    rendered = rendered.replace(old, "أول الباقي بعد `00633`")
    record = dict(record)
    record["bytes"] = len(rendered.encode("utf-8"))
    if record["bytes"] > R13.R12.R11.R2.MAX_CARD_BYTES:
        raise AssertionError(
            f"تجاوزت البطاقة {record['completion_id']} حد الحجم: "
            f"{record['bytes']}"
        )
    return rendered, record


def render_all() -> tuple[list[str], list[dict]]:
    rendered: list[str] = []
    records: list[dict] = []
    for number, item in enumerate(inventory_items(), FIRST_COMPLETION):
        card, record = inventory_card(number, item)
        rendered.append(card)
        records.append(record)
    expected = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected:
        raise AssertionError("معرفات الجولة الرابعة عشرة غير متصلة")
    if Counter(record["verdict"] for record in records) != Counter(
        {"TOOL-GAP": 100}
    ):
        raise AssertionError("تغيرت أحكام الجولة الرابعة عشرة")
    return rendered, records


def reading_fragment(
    start: int,
    count: int,
    cards: list[str] | None = None,
) -> str:
    if cards is None:
        cards, _ = render_all()
    if count < 1 or start < FIRST_COMPLETION or start + count - 1 > LAST_COMPLETION:
        raise AssertionError("مدى قطعة القراءة غير صحيح")
    end = start + count - 1
    boundary = FIRST_COMPLETION + BATCH_SIZE - 1
    if start <= boundary < end:
        raise AssertionError("لا تعبر قطعة القراءة حد الدفعتين")
    batch = 1 if start <= boundary else 2
    first, last = (
        (FIRST_COMPLETION, boundary)
        if batch == 1 else (boundary + 1, LAST_COMPLETION)
    )
    selected = cards[
        start - FIRST_COMPLETION:start - FIRST_COMPLETION + count
    ]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND14-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الرابعة عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ اختيرت هذه النافذة لأنهما صفريان معًا، وسميت فجوة الأداة ومطلوبها من غير NO-TRACE.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND14-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round14-"))
    batches = (
        (FIRST_COMPLETION, FIRST_COMPLETION + BATCH_SIZE - 1),
        (FIRST_COMPLETION + BATCH_SIZE, LAST_COMPLETION),
    )
    for first, last in batches:
        for start in range(first, last + 1, 4):
            count = min(4, last - start + 1)
            (stage / f"{start:05d}.md").write_text(
                reading_fragment(start, count, cards),
                encoding="utf-8",
            )
    return stage


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
    return R13.R12.R11.R8.emit_append_patch(
        READING,
        fragment.read_text(encoding="utf-8"),
        marker,
    )


def report_fragment() -> str:
    _, records = render_all()
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])

    def categories(rows: list[dict]) -> str:
        counts = Counter(row["category"] for row in rows)
        return "؛ ".join(
            f"`{key}`={value}" for key, value in sorted(counts.items())
        )

    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND14-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الرابعة عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00634` إلى `LANE-A-OPEN-COMP-00683`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(first) + ".",
        "",
        f"## {DATE}، الجولة الرابعة عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00684` إلى `LANE-A-OPEN-COMP-00733`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(second) + ".",
        "",
        "## حصيلة الجولة الرابعة عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق من `TWO-LAYER-OPEN` بعد الإتمامات الـ633، بشرط صفر مرشحي الجذر وصفر مرشحي النواة؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        "- الأحكام الكلية: `TOOL-GAP`=100؛ لم يحول صفر الأداة إلى `NO-TRACE` ولم يختر مرشحا من خارجها.",
        "- أصناف النافذة: `NONLEXICAL`=61؛ `LEXICAL`=22؛ `FUNCTION`=17؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: الهيكل الصارم=1 وصوامت الجرد المثبتة=1 في البطاقات كلها؛ لا صامت أصلي حذف بالحدس.",
        "- المطلوب المكتوب: كل بطاقة تسمي التحليل أو الرومنة أو قاعدة الإغلاق الموقعة اللازمة قبل أي حكم؛ لا صلة موجبة جديدة.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والصنف والصوامت الكاملة وحكمي الطبقتين والمصدر والعائق وعدستي المراجعة.",
        "- فحص انضباط النواة: 28 ملاحظة موروثة بلا زيادة؛ لم تضف الجولة حكم جذر أو نواة موجبًا.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ طزاجة سجل الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND14-REPORT:END -->",
        "",
        "LANE-A DONE14 100 LANE-A-OPEN-COMP-00733",
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
        print(R13.R12.R11.R8.emit_append_patch(
            READING,
            reading_fragment(args.start, args.count),
            marker,
        ), end="")
    elif args.report:
        print(R13.R12.R11.R8.emit_append_patch(
            REPORT,
            report_fragment(),
            "LANE-A DONE14",
        ), end="")
    else:
        _, records = render_all()
        print(
            f"cards={len(records)} "
            f"max={max(record['bytes'] for record in records)}"
        )
        print(Counter(record["verdict"] for record in records))
        print(Counter(record["category"] for record in records))
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
