#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 12 without committing or shipping.

Round 11 ended at OPEN-COMP-00433.  This round takes the next one hundred
still-open members whose frozen root and nucleus layers both returned zero,
ordered by strict branch-skeleton length and then the pinned inventory row.
Cards remain append-only and are split into two batches of fifty.
"""

from __future__ import annotations

from collections import Counter
import argparse
import json
import re
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round11 as R11  # noqa: E402


READING = R11.READING
REPORT = R11.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION, BATCH_SIZE = 434, 533, 50
EXPECTED_PREVIOUS = 433
EXPECTED_POOL = 387
EXPECTED_STRICT_LENGTHS = Counter({0: 51, 1: 49})
EXPECTED_TOKEN_LENGTHS = Counter({1: 100})
EXPECTED_CATEGORIES = Counter({"NONLEXICAL": 62, "LEXICAL": 22, "FUNCTION": 16})
FIRST_MEMBER = "kaikki_ancient_greek:9499:en-ἁ--grc-prefix-5mnjcAFS"
LAST_MEMBER = "kaikki_ancient_greek:41735:en--κα-grc-suffix-LsHEQk-U"


def completed_before_round12() -> set[str]:
    text = READING.read_text(encoding="utf-8")
    used: set[str] = set()
    numbers: list[int] = []
    starts = list(re.finditer(
        r"^### LANE-A-OPEN-COMP-(?P<number>\d{5}):[^\n]*$",
        text,
        re.MULTILINE,
    ))
    for index, match in enumerate(starts):
        number = int(match.group("number"))
        if number > EXPECTED_PREVIOUS:
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        member = re.search(
            r"- مرجع بطاقة الجرد: `[^`]+`؛ العضو(?: الفردي)? `([^`]+)`",
            block,
        )
        if member is None:
            raise AssertionError(f"بطاقة إتمام بلا عضو: {number}")
        numbers.append(number)
        used.add(member.group(1))
    if numbers != list(range(1, EXPECTED_PREVIOUS + 1)):
        raise AssertionError("تغير اتصال معرفات الإتمام السابقة")
    if len(used) != EXPECTED_PREVIOUS:
        raise AssertionError(
            f"تغير مقام الإتمام السابق: {len(used)} لا {EXPECTED_PREVIOUS}"
        )
    return used


def inventory_items() -> list[R11.InventoryItem]:
    used = completed_before_round12()
    coverage = R11.coverage_rows()
    eligible: list[tuple[int, int, R11.InventoryItem]] = []
    connection = R11.open_connection()
    try:
        for member_id, state in coverage.items():
            if member_id in used:
                continue
            previous = R11.nfc(state.get("non_issuance_reason"))
            counts = R11.ZERO_LAYERS.search(previous)
            if counts is None or counts.groups() != ("0", "0"):
                continue
            row = connection.execute(
                """
                SELECT rowid AS source_rowid, entry_id, headword, romanization,
                       pos, gloss, etymology, source_stratum, selected_input,
                       skeleton, tokens_json, form_of, alternative_of,
                       form_targets_json, alternative_targets_json,
                       processing_status
                FROM entries WHERE entry_id=?
                """,
                (member_id,),
            ).fetchone()
            if row is None:
                raise AssertionError(f"عضو التغطية غائب من الجرد: {member_id}")
            families = connection.execute(
                """
                SELECT f.family_id, f.member_count, f.lemma_count
                FROM family_members fm
                JOIN families f ON f.family_id=fm.family_id
                WHERE fm.entry_id=? ORDER BY f.family_id
                """,
                (member_id,),
            ).fetchall()
            if len(families) != 1:
                raise AssertionError(
                    f"عضو الجرد لا يحمل أسرة واحدة: {member_id} ({len(families)})"
                )
            tokens = tuple(
                R11.nfc(token) for token in json.loads(row["tokens_json"] or "[]")
            )
            form_targets = tuple(
                R11.nfc(target)
                for target in json.loads(row["form_targets_json"] or "[]")
            )
            alternative_targets = tuple(
                R11.nfc(target)
                for target in json.loads(row["alternative_targets_json"] or "[]")
            )
            family = families[0]
            item = R11.InventoryItem(
                family_id=R11.nfc(family["family_id"]),
                family_members=int(family["member_count"]),
                family_lemmas=int(family["lemma_count"]),
                member_id=member_id,
                word=R11.nfc(row["headword"]),
                read=R11.nfc(row["romanization"]),
                pos=R11.nfc(row["pos"]),
                meaning=R11.nfc(row["gloss"]),
                etym=R11.nfc(row["etymology"]),
                source_stratum=R11.nfc(row["source_stratum"]),
                selected_input=R11.nfc(row["selected_input"]),
                skeleton=R11.nfc(row["skeleton"]),
                tokens=tokens,
                form_of=bool(row["form_of"]),
                alternative_of=bool(row["alternative_of"]),
                form_targets=form_targets,
                alternative_targets=alternative_targets,
                processing_status=R11.nfc(row["processing_status"]),
                previous_state=previous,
                source_rowid=int(row["source_rowid"]),
            )
            strict_length = len(R11.R2.branch_skeleton(item.word))
            eligible.append((strict_length, item.source_rowid, item))
    finally:
        connection.close()
    eligible.sort(key=lambda record: (record[0], record[1]))
    if len(eligible) != EXPECTED_POOL:
        raise AssertionError(
            f"تغير مقام الجرد ذي الطبقتين الصفريتين: {len(eligible)}"
        )
    selected = [record[2] for record in eligible[:100]]
    if (selected[0].member_id, selected[-1].member_id) != (
        FIRST_MEMBER,
        LAST_MEMBER,
    ):
        raise AssertionError("تغير طرفا نافذة الجولة الثانية عشرة")
    if len({item.member_id for item in selected}) != 100:
        raise AssertionError("تكرر عضو في نافذة الجولة الثانية عشرة")
    strict_lengths = Counter(
        len(R11.R2.branch_skeleton(item.word)) for item in selected
    )
    if strict_lengths != EXPECTED_STRICT_LENGTHS:
        raise AssertionError(f"تغير توزيع الهيكل الصارم: {strict_lengths}")
    token_lengths = Counter(len(item.tokens) for item in selected)
    if token_lengths != EXPECTED_TOKEN_LENGTHS:
        raise AssertionError(f"تغير توزيع صوامت الجرد: {token_lengths}")
    categories = Counter(R11.item_category(item) for item in selected)
    if categories != EXPECTED_CATEGORIES:
        raise AssertionError(f"تغير توزيع أصناف الجرد: {categories}")
    return selected


def inventory_card(number: int, item: R11.InventoryItem) -> tuple[str, dict]:
    rendered, record = R11.inventory_card(number, item)
    old = "أول الباقي بعد `00333`"
    if rendered.count(old) != 1:
        raise AssertionError(f"تغير سطر معيار الانتخاب في {number}")
    rendered = rendered.replace(old, "أول الباقي بعد `00433`")
    record = dict(record)
    record["bytes"] = len(rendered.encode("utf-8"))
    if record["bytes"] > R11.R2.MAX_CARD_BYTES:
        raise AssertionError(
            f"تجاوزت البطاقة {record['completion_id']} حد الحجم: {record['bytes']}"
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
        raise AssertionError("معرفات الجولة الثانية عشرة غير متصلة")
    if Counter(record["verdict"] for record in records) != Counter(
        {"TOOL-GAP": 100}
    ):
        raise AssertionError("تغيرت أحكام الجولة الثانية عشرة")
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
            f"<!-- LANE-A-GREEK-ROUND12-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الثانية عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قُرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ اختيرت هذه النافذة لأنهما صفريان معًا، وسميت فجوة الأداة ومطلوبها من غير NO-TRACE.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND12-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round12-"))
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
    return R11.R8.emit_append_patch(
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
        "<!-- LANE-A-GREEK-ROUND12-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الثانية عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00434` إلى `LANE-A-OPEN-COMP-00483`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(first) + ".",
        "",
        f"## {DATE}، الجولة الثانية عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00484` إلى `LANE-A-OPEN-COMP-00533`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(second) + ".",
        "",
        "## حصيلة الجولة الثانية عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق من `TWO-LAYER-OPEN` بعد الإتمامات الـ433، بشرط صفر مرشحي الجذر وصفر مرشحي النواة؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        "- الأحكام الكلية: `TOOL-GAP`=100؛ لم يحول صفر الأداة إلى `NO-TRACE` ولم يختر مرشحا من خارجها.",
        "- أصناف النافذة: `NONLEXICAL`=62؛ `LEXICAL`=22؛ `FUNCTION`=16؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: الهيكل الصارم 0=51 و1=49؛ صوامت الجرد المثبتة=1 في البطاقات كلها؛ لا صامت أصلي حُذف بالحدس.",
        "- المطلوب المكتوب: كل بطاقة تسمي التحليل أو الرومنة أو قاعدة الإغلاق الموقعة اللازمة قبل أي حكم؛ لا صلة موجبة جديدة.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والصنف والصوامت الكاملة وحكمي الطبقتين والمصدر والعائق وعدستي المراجعة.",
        "- فحص انضباط النواة: 28 ملاحظة موروثة بلا زيادة؛ لم تضف الجولة حكم جذر أو نواة موجبًا.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ طزاجة سجل الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND12-REPORT:END -->",
        "",
        "LANE-A DONE12 100 LANE-A-OPEN-COMP-00533",
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
        print(R11.R8.emit_append_patch(
            READING,
            reading_fragment(args.start, args.count),
            marker,
        ), end="")
    elif args.report:
        print(R11.R8.emit_append_patch(
            REPORT,
            report_fragment(),
            "LANE-A DONE12",
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
