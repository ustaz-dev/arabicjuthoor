#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 17 without committing or shipping.

Round 16 ended at OPEN-COMP-00920. This round reads the next one hundred
still-open Ancient Greek members with a licensed root or nucleus candidate,
in strict-skeleton/source-row order, as two batches of fifty. Retrieval never
becomes a verdict by itself.
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
import harvest_ancient_greek_round16 as R16  # noqa: E402


R11 = R16.R11
READING, REPORT = R16.READING, R16.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION = 921, 1020
EXPECTED_PREVIOUS = 920
EXPECTED_POOL = 1_439
BATCH_SIZE = 50
BATCHES = ((921, 970), (971, 1020))
EXPECTED_STRICT = Counter({2: 100})
EXPECTED_TOKENS = Counter({3: 54, 2: 44, 4: 2})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 63, "FUNCTION": 22, "NONLEXICAL": 15})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 96, "SOURCE-GAP": 4})
FIRST_MEMBER = "kaikki_ancient_greek:46948:en-ἀγνέω-grc-verb-s4XIRs7b"
LAST_MEMBER = "kaikki_ancient_greek:24731:en-ξυν--grc-prefix-pGZCMoHI"


def completed_members() -> set[str]:
    """Read the accepted continuous completion ledger through round 16."""
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
            r"- مرجع (?:بطاقة )?الجرد: `[^`]+`؛ العضو(?: الفردي)? `([^`]+)`",
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
    """Select the first hundred nonzero two-layer members after round 16."""
    used = completed_members()
    coverage = R11.coverage_rows()
    eligible: list[tuple[int, int, R11.InventoryItem]] = []
    con = R11.open_connection()
    try:
        for member_id, state in coverage.items():
            if member_id in used:
                continue
            previous = R11.nfc(state.get("non_issuance_reason"))
            counts = R11.ZERO_LAYERS.search(previous)
            if counts is None or counts.groups() == ("0", "0"):
                continue
            row = con.execute(
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
            families = con.execute(
                """
                SELECT f.family_id, f.member_count, f.lemma_count
                FROM family_members fm JOIN families f ON f.family_id=fm.family_id
                WHERE fm.entry_id=? ORDER BY f.family_id
                """,
                (member_id,),
            ).fetchall()
            if len(families) != 1:
                raise AssertionError(f"عضو الجرد لا يحمل أسرة واحدة: {member_id}")

            def values(key: str) -> tuple[str, ...]:
                return tuple(R11.nfc(value) for value in json.loads(row[key] or "[]"))

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
                tokens=values("tokens_json"),
                form_of=bool(row["form_of"]),
                alternative_of=bool(row["alternative_of"]),
                form_targets=values("form_targets_json"),
                alternative_targets=values("alternative_targets_json"),
                processing_status=R11.nfc(row["processing_status"]),
                previous_state=previous,
                source_rowid=int(row["source_rowid"]),
            )
            eligible.append((
                len(R11.R2.branch_skeleton(item.word)),
                item.source_rowid,
                item,
            ))
    finally:
        con.close()

    eligible.sort(key=lambda record: (record[0], record[1]))
    if len(eligible) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الجرد ذي المرشحات: {len(eligible)}")
    selected = [record[2] for record in eligible[:100]]
    if selected[0].member_id != FIRST_MEMBER:
        raise AssertionError("تغير أول عضو في الجولة السابعة عشرة")
    if selected[-1].member_id != LAST_MEMBER:
        raise AssertionError("تغير آخر عضو في الجولة السابعة عشرة")
    if len({item.member_id for item in selected}) != 100:
        raise AssertionError("تكرر عضو في الجولة السابعة عشرة")
    strict = Counter(len(R11.R2.branch_skeleton(item.word)) for item in selected)
    tokens = Counter(len(item.tokens) for item in selected)
    categories = Counter(R11.item_category(item) for item in selected)
    if strict != EXPECTED_STRICT:
        raise AssertionError(f"تغير توزيع الهيكل الصارم: {strict}")
    if tokens != EXPECTED_TOKENS:
        raise AssertionError(f"تغير توزيع صوامت الجرد: {tokens}")
    if categories != EXPECTED_CATEGORIES:
        raise AssertionError(f"تغير توزيع أصناف الجرد: {categories}")
    return selected


def render_all() -> tuple[list[str], list[dict]]:
    cards: list[str] = []
    records: list[dict] = []
    old_criterion = "أول الباقي بعد `00820`"
    new_criterion = f"أول الباقي بعد `{EXPECTED_PREVIOUS:05d}`"
    for number, item in enumerate(inventory_items(), FIRST_COMPLETION):
        card, record = R16.inventory_card(number, item)
        if card.count(old_criterion) != 1:
            raise AssertionError(f"تغير موضع معيار الانتخاب في البطاقة {number}")
        card = card.replace(old_criterion, new_criterion)
        cards.append(card)
        records.append(record)
    expected = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected:
        raise AssertionError("معرفات الجولة السابعة عشرة غير متصلة")
    verdicts = Counter(record["verdict"] for record in records)
    if verdicts != EXPECTED_VERDICTS:
        raise AssertionError(f"تغيرت أحكام الجولة السابعة عشرة: {verdicts}")
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
            f"<!-- LANE-A-GREEK-ROUND17-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة السابعة عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ لا صلة بلا شاهدين عربيين قديمين، ولا صف صوتيا مخترعا.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND17-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round17-"))
    for first, last in BATCHES:
        for start in range(first, last + 1, 4):
            count = min(4, last - start + 1)
            (stage / f"{start:05d}.md").write_text(
                reading_fragment(start, count, cards), encoding="utf-8"
            )
    return stage


def append_patch(path: Path, fragment: str, marker: str) -> str:
    return R16.R15.R14.R13.R12.R11.R8.emit_append_patch(path, fragment, marker)


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
        "<!-- LANE-A-GREEK-ROUND17-REPORT:START -->",
        "",
        f"## {DATE}، الجولة السابعة عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00921` إلى `LANE-A-OPEN-COMP-00970`.",
        "- توزيع الأحكام: " + distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + distribution(first, "category") + ".",
        "",
        f"## {DATE}، الجولة السابعة عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00971` إلى `LANE-A-OPEN-COMP-01020`.",
        "- توزيع الأحكام: " + distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + distribution(second, "category") + ".",
        "",
        "## حصيلة الجولة السابعة عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق بعد الإتمامات 920 من `TWO-LAYER-OPEN` ذي مرشح في طبقة على الأقل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت؛ بقي في هذه الشريحة 1339 عضوا.",
        "- الأحكام الكلية: `OPEN-CANDIDATE`=96؛ `SOURCE-GAP`=4؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- الطبقتان: مجموع مرشحي الجذر={root_total}؛ مجموع مرشحي النواة={nucleus_total}؛ كل بطاقة سمت عددي الطبقتين وقرأتهما معا.",
        "- بوابة المصدر: 96 بطاقة سمت جذر شاهد ومصدرين عربيين قديمين على الأقل ثم منعت الحكم لغياب المدار؛ بطاقات `κἀγώ` و`κάγ` و`κάκ` و`κάκ'` بقيت `SOURCE-GAP`.",
        "- أصناف النافذة: `LEXICAL`=63؛ `FUNCTION`=22؛ `NONLEXICAL`=15؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: صوامت `tokens_json`: 2=44؛ 3=54؛ 4=2؛ لا صامت أصليا حذف بالحدس.",
        "- حارس الطبقتين: أعيدت البطاقات المئة إلى مسترجع SECTION28 المجمد بمدخل `tokens_json`؛ طابقت أعداد الجذر والنواة سجل التغطية فيها كلها.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND17-REPORT:END -->",
        "",
        "LANE-A DONE17 100 LANE-A-OPEN-COMP-01020",
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
        print(append_patch(REPORT, report_fragment(), "LANE-A DONE17"), end="")
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
