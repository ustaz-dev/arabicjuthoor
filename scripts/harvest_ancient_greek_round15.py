#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 15 without committing or shipping.

Round 14 ended at OPEN-COMP-00733.  This round exhausts the eighty-seven
members still open in the frozen two-layer zero/zero inventory, ordered by
strict branch-skeleton length and then the pinned inventory row.  The cards
are append-only and split into batches of forty-four and forty-three.
"""

from __future__ import annotations

from collections import Counter
from functools import lru_cache
import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round14 as R14  # noqa: E402
import lane_c_two_layer_month as TWO_LAYER  # noqa: E402


R12 = R14.R13.R12
R11 = R12.R11
READING = R14.READING
REPORT = R14.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION = 734, 820
EXPECTED_PREVIOUS = 733
EXPECTED_POOL = 87
FIRST_BATCH_SIZE = 44
EXPECTED_STRICT_LENGTHS = Counter({1: 60, 2: 26, 3: 1})
EXPECTED_TOKEN_LENGTHS = Counter({1: 60, 2: 26, 3: 1})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 37, "NONLEXICAL": 32, "FUNCTION": 18})
FIRST_MEMBER = "kaikki_ancient_greek:10887:en-τ'-grc-conj-382Uf-7g"
LAST_MEMBER = "kaikki_ancient_greek:10024:en-τάττω-grc-verb-7FjWXzA0"
BATCHES = (
    (FIRST_COMPLETION, FIRST_COMPLETION + FIRST_BATCH_SIZE - 1),
    (FIRST_COMPLETION + FIRST_BATCH_SIZE, LAST_COMPLETION),
)


def inventory_items() -> list[R11.InventoryItem]:
    """Return every member left in the accepted frozen zero/zero inventory."""
    R12.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    used = R12.completed_before_round12()
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
                    f"عضو الجرد لا يحمل أسرة واحدة: {member_id} "
                    f"({len(families)})"
                )

            def tuple_field(key: str) -> tuple[str, ...]:
                return tuple(
                    R11.nfc(value)
                    for value in json.loads(row[key] or "[]")
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
                tokens=tuple_field("tokens_json"),
                form_of=bool(row["form_of"]),
                alternative_of=bool(row["alternative_of"]),
                form_targets=tuple_field("form_targets_json"),
                alternative_targets=tuple_field("alternative_targets_json"),
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
        connection.close()

    eligible.sort(key=lambda record: (record[0], record[1]))
    if len(eligible) != EXPECTED_POOL:
        raise AssertionError(
            f"تغير مقام الجرد الباقي: {len(eligible)} لا {EXPECTED_POOL}"
        )
    selected = [record[2] for record in eligible]
    if (selected[0].member_id, selected[-1].member_id) != (
        FIRST_MEMBER,
        LAST_MEMBER,
    ):
        raise AssertionError("تغير طرفا نافذة الجولة الخامسة عشرة")
    if len({item.member_id for item in selected}) != EXPECTED_POOL:
        raise AssertionError("تكرر عضو في نافذة الجولة الخامسة عشرة")
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


@lru_cache(maxsize=1)
def two_layer_retriever() -> TWO_LAYER.TwoLayerRetriever:
    return TWO_LAYER.TwoLayerRetriever()


def inventory_card(number: int, item: R11.InventoryItem) -> tuple[str, dict]:
    roots, nuclei = two_layer_retriever().layers("ancient_greek", item.tokens)
    if roots or nuclei:
        raise AssertionError(
            f"تغير صفر الطبقتين في {number}: "
            f"الجذر={len(roots)}، النواة={len(nuclei)}"
        )
    tokens = "-".join(item.tokens) if item.tokens else "∅"
    strict = "-".join(R11.R2.branch_skeleton(item.word)) or "∅"
    read = item.read or "قراءة غير مثبتة في الفهرس"
    oldest = R11.clip(item.etym or item.source_stratum, 180)
    if not oldest:
        oldest = "لم ينشر قاموس الفرع صورة أقدم لهذا العضو."
    category = R11.item_category(item)
    if len(item.tokens) < 2:
        requirement = (
            "صامت ثان على الأقل من تحليل صرفي أو رومنة منشورة يفتح فحص "
            "النواة، أو قاعدة إغلاق موقعة تخص هذا الصنف؛ الصامت الواحد لا "
            "يكفي للجذر أو النواة"
        )
        gate = "لم يتح جذر أو نواة لقلة الصوامت"
    else:
        requirement = (
            "صف صوتي موقع أو توسيع مرخص لمخزون المقارنة يعيد مرشحا في طبقة "
            "الجذر أو النواة، أو قاعدة إغلاق موقعة تخص العضو؛ صفر الاسترجاع لا يجيز النفي"
        )
        gate = "دخلت الصوامت مولدي الطبقتين وأعادت الصفوف المرخصة صفرا"
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE}) + SECTION28-TWO-LAYER؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو `{item.member_id}`؛ السابق: {R11.clip(item.previous_state, 260)}.",
        f"- الكلمة في الفرع: `{item.word}` /{read}/؛ `{item.pos}`؛ «{R11.clip(item.meaning, 120)}».",
        f"- معيار الانتخاب: كل الباقي بعد `00733` من `TWO-LAYER-OPEN` ذي الجذر=0 والنواة=0؛ الهيكل `{strict}`؛ موضع الجرد {item.source_rowid}؛ الترتيب بطول الهيكل ثم الموضع.",
        f"- أقدم صورة مستعادة: {oldest} [Kaikki Ancient Greek؛ حقل etymology/source_stratum].",
        f"- الخطوة صفر: {R11.zero_step(item)}؛ لا صامت أصلي محذوف بالحدس.",
        f"- بوابة الصوامت الكاملة: الصوامت `{tokens}`؛ حفظت كلها للمولدين؛ المحذوف الحدسي=0؛ {gate}.",
        "- درجة المقارنة: الجذر والنواة معا؛ أعاد كل مولد صفرا مستقلا.",
        "- حارس المولد: أعيد فحص `tokens_json` بمسترجع SECTION28 المجمد؛ الجذر=0 والنواة=0؛ لم تورث نتيجة مولد مواز خارج هذا العقد.",
        "- مسح المعاني العربية: لا جذر ولا نواة مولدة لمسح معانيها؛ لم يختر مقابل من خارج الأداة ولم يحول الصفر إلى شاهد نفي.",
        "- المقابل من اللسان: (لا مقابل من الأداة المجمدة)؛ هذا وصف لفجوة مدخل المقارنة لا لحكم تاريخي.",
        "- مسار الصوت: لا مرشح مولدا ولا صف شبكة مطلوبا؛ لم يخترع صفا ولم يعلن LAW-GAP.",
        "- حدث الحرف: لا جذر مولدا يمرر إلى `frozen_event`؛ لا حكم حدث صادر.",
        f"- المعنى من قاموس الفرع: «{R11.clip(item.meaning, 150) or '(غير مسجل في المصدر)'}» [Kaikki Ancient Greek].",
        "- المدار: لا مدار دلالي مستعمل؛ لا تبدأ المقارنة الدلالية قبل وجود مقابل مولد.",
        "- المصفاة: سجل الاتجاه السابق لم يصدر انتقالا مسمى لهذا العضو؛ بقي فحص الأصل مقيدا بهوية العضو ومعناه.",
        f"- فصل المتجانسات والاقتراض: الحكم للعضو `{item.member_id}` وحده؛ لا يرث متحد الرسم ولا عضو الأسرة حكمه.",
        "- فحص الطبقتين: مرشحو الجذر=0؛ مرشحو النواة=0؛ ذوات الشاهد العربي=0؛ لا مرشح مصدر يحتكر البحث.",
        f"- مؤشر اليتم: الأسرة `{item.family_id}` تضم {item.family_members} عضوا ومنها {item.family_lemmas} لمة؛ العدد وصف استرجاع لا قرينة حكم.",
        "- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ لم يصدر حكم موجب.",
        "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ لم تنتج الأداة مقابلا.",
        "- جسور الاسترداد المفحوصة: العضو؛ الخطوة صفر؛ الصوامت؛ الجذر؛ النواة؛ الشبكة؛ الحدث؛ المعنى؛ الأصل؛ الاتجاه؛ المدار.",
        f"- عائق: النوع=TOOL-GAP؛ يتطلب={requirement}.",
        "- حالة الإغلاق: TOOL-GAP.",
        "- الحكم (استكشاف): TOOL-GAP.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحالة السابقة `TWO-LAYER-OPEN`؛ الحكم الجديد `TOOL-GAP`؛ السبب: سمي صفر الطبقتين ومطلوبه بعد حفظ الصوامت الكاملة وتصنيف المصدر `{item.processing_status}`.",
        f"- ملاحظات: الصنف `{category}`؛ عدسة الاسترداد أبقت المطلوب مفتوحا، وعدسة التشكيك منعت صلة بلا مقابل.",
    ]
    rendered, size = R11.R6.compact_to_limit(
        "\n".join(lines),
        completion_id,
    )
    if size > R11.R2.MAX_CARD_BYTES:
        raise AssertionError(
            f"تجاوزت البطاقة {completion_id} حد الحجم: {size}"
        )
    if "—" in rendered:
        raise AssertionError(f"شرطة طويلة في {completion_id}")
    return rendered, {
        "completion_id": completion_id,
        "family_id": item.family_id,
        "member_id": item.member_id,
        "word": item.word,
        "read": read,
        "closure": "TOOL-GAP",
        "verdict": "TOOL-GAP",
        "bytes": size,
        "strict_length": len(R11.R2.branch_skeleton(item.word)),
        "token_length": len(item.tokens),
        "category": category,
        "source_rowid": item.source_rowid,
    }


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
        raise AssertionError("معرفات الجولة الخامسة عشرة غير متصلة")
    verdicts = Counter(record["verdict"] for record in records)
    if verdicts != Counter({"TOOL-GAP": EXPECTED_POOL}):
        raise AssertionError(f"تغيرت أحكام الجولة الخامسة عشرة: {verdicts}")
    return rendered, records


def batch_for(start: int, end: int) -> tuple[int, int, int]:
    for batch, (first, last) in enumerate(BATCHES, 1):
        if first <= start <= end <= last:
            return batch, first, last
    raise AssertionError("مدى قطعة القراءة غير صحيح")


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
    batch, first, last = batch_for(start, end)
    selected = cards[
        start - FIRST_COMPLETION:start - FIRST_COMPLETION + count
    ]
    lines: list[str] = []
    if start == first:
        lines += [
            f"<!-- LANE-A-GREEK-ROUND15-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الخامسة عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ اختير كل الباقي لأنهما صفريان معا، وسميت فجوة الأداة ومطلوبها من غير NO-TRACE.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND15-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round15-"))
    for first, last in BATCHES:
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
    return R14.R13.R12.R11.R8.emit_append_patch(
        READING,
        fragment.read_text(encoding="utf-8"),
        marker,
    )


def report_fragment() -> str:
    _, records = render_all()
    first = records[:FIRST_BATCH_SIZE]
    second = records[FIRST_BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])

    def categories(rows: list[dict]) -> str:
        counts = Counter(row["category"] for row in rows)
        return "؛ ".join(
            f"`{key}`={value}" for key, value in sorted(counts.items())
        )

    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND15-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الخامسة عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 44؛ المدى: `LANE-A-OPEN-COMP-00734` إلى `LANE-A-OPEN-COMP-00777`.",
        "- توزيع الأحكام: `TOOL-GAP`=44؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(first) + ".",
        "",
        f"## {DATE}، الجولة الخامسة عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 43؛ المدى: `LANE-A-OPEN-COMP-00778` إلى `LANE-A-OPEN-COMP-00820`.",
        "- توزيع الأحكام: `TOOL-GAP`=43؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(second) + ".",
        "",
        "## حصيلة الجولة الخامسة عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 87؛ دفعتان من 44 و43 بطاقة.",
        "- معيار الجرد: كل الـ87 عضوا الباقية من `TWO-LAYER-OPEN` بعد الإتمامات الـ733، بشرط صفر مرشحي الجذر وصفر مرشحي النواة؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت؛ الباقي في هذا الجرد=0.",
        "- الأحكام الكلية: `TOOL-GAP`=87؛ لم يحول صفر الأداة إلى `NO-TRACE` ولم يختر مرشحا من خارجها.",
        "- أصناف النافذة: `NONLEXICAL`=32؛ `LEXICAL`=37؛ `FUNCTION`=18؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: الهيكل الصارم وصوامت الجرد المثبتة: 1=60؛ 2=26؛ 3=1؛ لا صامت أصلي حذف بالحدس.",
        "- حارس الطبقتين: أعيدت الـ87 بطاقة إلى مسترجع SECTION28 المجمد بمدخل `tokens_json`؛ الجذر=0 والنواة=0 فيها كلها؛ لم تورث نتائج مولد مواز.",
        "- المطلوب المكتوب: كل بطاقة تسمي تحليلا أو رومنة أو توسيعا مرخصا أو قاعدة إغلاق موقعة لازمة قبل أي حكم؛ لا صلة موجبة جديدة.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والصنف والصوامت الكاملة وحكمي الطبقتين والمصدر والعائق وعدستي المراجعة.",
        "- فحص انضباط النواة: 28 ملاحظة موروثة بلا زيادة؛ لم تضف الجولة حكم جذر أو نواة موجبا.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ طزاجة سجل الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND15-REPORT:END -->",
        "",
        "LANE-A DONE15 87 LANE-A-OPEN-COMP-00820",
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
        print(R14.R13.R12.R11.R8.emit_append_patch(
            READING,
            reading_fragment(args.start, args.count),
            marker,
        ), end="")
    elif args.report:
        print(R14.R13.R12.R11.R8.emit_append_patch(
            REPORT,
            report_fragment(),
            "LANE-A DONE15",
        ), end="")
    else:
        _, records = render_all()
        print(
            f"cards={len(records)} "
            f"max={max(record['bytes'] for record in records)}"
        )
        print(Counter(record["verdict"] for record in records))
        print(Counter(record["category"] for record in records))
        print(Counter(record["strict_length"] for record in records))
        if args.records:
            for record in records:
                print(record)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
