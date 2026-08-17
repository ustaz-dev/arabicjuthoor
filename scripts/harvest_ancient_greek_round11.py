#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 11 without committing or shipping.

The accepted explicit Greek inventory ended at OPEN-COMP-00333.  This round
continues into the complete two-layer coverage ledger.  It selects the first
one hundred still-open members for which both frozen layers returned zero,
ordered by the strict branch skeleton and then the pinned inventory row.
Cards are append-only and split into two batches of fifty.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
import argparse
import json
import re
import sqlite3
import sys
import tempfile
import unicodedata
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round10 as R10  # noqa: E402


R8, R6, R2 = R10.R8, R10.R6, R10.R2
READING = ROOT / "04-cross-linguistic" / "readings" / "ancient-greek.md"
REPORT = ROOT / "_inbox" / "lane-reports" / "2026-08-16-A.md"
COVERAGE = ROOT / "04-cross-linguistic" / "data" / "lane_c_coverage.jsonl"
DB = ROOT / "cache" / "recovery_pipeline" / "inventory-v5.sqlite"
SOURCE = (
    ROOT / "Resources" / "ancient_greek"
    / "kaikki.org-dictionary-AncientGreek.jsonl"
)
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION, BATCH_SIZE = 334, 433, 50
EXPECTED_DB_BYTES = 4_377_219_072
EXPECTED_SOURCE_BYTES = 266_670_872
EXPECTED_POOL = 487
EXPECTED_TOKEN_LENGTHS = Counter({0: 94, 1: 6})
FIRST_MEMBER = "kaikki_ancient_greek:30:en-;-grc-punct-hGURBDSd"
LAST_MEMBER = "kaikki_ancient_greek:8793:en-◌̔-grc-character-LJ-o5Bp8"
ZERO_LAYERS = re.compile(
    r"الجذر=مرشحون مرخصون (\d+)؛ النواة=مرشحون مرخصون (\d+)"
)


@dataclass(frozen=True)
class InventoryItem:
    family_id: str
    family_members: int
    family_lemmas: int
    member_id: str
    word: str
    read: str
    pos: str
    meaning: str
    etym: str
    source_stratum: str
    selected_input: str
    skeleton: str
    tokens: tuple[str, ...]
    form_of: bool
    alternative_of: bool
    form_targets: tuple[str, ...]
    alternative_targets: tuple[str, ...]
    processing_status: str
    previous_state: str
    source_rowid: int


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or "")).strip()


def clip(value: object, limit: int) -> str:
    return R2.clip(nfc(value).replace("—", "-"), limit)


def completed_before_round11() -> set[str]:
    text = READING.read_text(encoding="utf-8")
    used: set[str] = set()
    starts = list(re.finditer(
        r"^### LANE-A-OPEN-COMP-(?P<number>\d{5}):[^\n]*$",
        text,
        re.MULTILINE,
    ))
    for index, match in enumerate(starts):
        number = int(match.group("number"))
        if number > 333:
            continue
        end = starts[index + 1].start() if index + 1 < len(starts) else len(text)
        block = text[match.start():end]
        member = re.search(r"- مرجع بطاقة الجرد: `[^`]+`؛ العضو الفردي `([^`]+)`", block)
        if member is None:
            raise AssertionError(f"بطاقة إتمام بلا عضو: {number}")
        used.add(member.group(1))
    if len(used) != 333:
        raise AssertionError(f"تغير مقام الإتمام السابق: {len(used)} لا 333")
    return used


def coverage_rows() -> dict[str, dict]:
    latest: dict[str, dict] = {}
    with COVERAGE.open(encoding="utf-8") as handle:
        for line in handle:
            if '"language":"ancient_greek"' not in line:
                continue
            row = json.loads(line)
            latest[nfc(row["member_id"])] = row
    return latest


def open_connection() -> sqlite3.Connection:
    if DB.stat().st_size != EXPECTED_DB_BYTES:
        raise AssertionError("تغيرت قاعدة الجرد اليوناني المثبتة")
    if SOURCE.stat().st_size != EXPECTED_SOURCE_BYTES:
        raise AssertionError("تغيرت لقطة Kaikki Ancient Greek المثبتة")
    connection = sqlite3.connect(
        f"file:{DB.as_posix()}?mode=ro", uri=True,
    )
    connection.row_factory = sqlite3.Row
    return connection


def inventory_items() -> list[InventoryItem]:
    used = completed_before_round11()
    coverage = coverage_rows()
    eligible: list[tuple[int, int, InventoryItem]] = []
    connection = open_connection()
    try:
        for member_id, state in coverage.items():
            if member_id in used:
                continue
            previous = nfc(state.get("non_issuance_reason"))
            counts = ZERO_LAYERS.search(previous)
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
            tokens = tuple(nfc(token) for token in json.loads(row["tokens_json"] or "[]"))
            form_targets = tuple(
                nfc(target) for target in json.loads(row["form_targets_json"] or "[]")
            )
            alternative_targets = tuple(
                nfc(target)
                for target in json.loads(row["alternative_targets_json"] or "[]")
            )
            family = families[0]
            item = InventoryItem(
                family_id=nfc(family["family_id"]),
                family_members=int(family["member_count"]),
                family_lemmas=int(family["lemma_count"]),
                member_id=member_id,
                word=nfc(row["headword"]),
                read=nfc(row["romanization"]),
                pos=nfc(row["pos"]),
                meaning=nfc(row["gloss"]),
                etym=nfc(row["etymology"]),
                source_stratum=nfc(row["source_stratum"]),
                selected_input=nfc(row["selected_input"]),
                skeleton=nfc(row["skeleton"]),
                tokens=tokens,
                form_of=bool(row["form_of"]),
                alternative_of=bool(row["alternative_of"]),
                form_targets=form_targets,
                alternative_targets=alternative_targets,
                processing_status=nfc(row["processing_status"]),
                previous_state=previous,
                source_rowid=int(row["source_rowid"]),
            )
            strict_length = len(R2.branch_skeleton(item.word))
            eligible.append((strict_length, item.source_rowid, item))
    finally:
        connection.close()
    eligible.sort(key=lambda record: (record[0], record[1]))
    if len(eligible) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الجرد ذي الطبقتين الصفريتين: {len(eligible)}")
    selected = [record[2] for record in eligible[:100]]
    if (selected[0].member_id, selected[-1].member_id) != (
        FIRST_MEMBER,
        LAST_MEMBER,
    ):
        raise AssertionError("تغير طرفا نافذة الجولة الحادية عشرة")
    if len({item.member_id for item in selected}) != 100:
        raise AssertionError("تكرر عضو في نافذة الجولة الحادية عشرة")
    strict_lengths = Counter(len(R2.branch_skeleton(item.word)) for item in selected)
    if strict_lengths != Counter({0: 100}):
        raise AssertionError(f"تغير توزيع الهيكل الصارم: {strict_lengths}")
    token_lengths = Counter(len(item.tokens) for item in selected)
    if token_lengths != EXPECTED_TOKEN_LENGTHS:
        raise AssertionError(f"تغير توزيع صوامت الجرد: {token_lengths}")
    return selected


def item_category(item: InventoryItem) -> str:
    if "SECTION26-NONLEXICAL-INCLUDED" in item.previous_state:
        return "NONLEXICAL"
    if "SECTION26-FUNCTION-PRIORITY" in item.previous_state:
        return "FUNCTION"
    return "LEXICAL"


def zero_step(item: InventoryItem) -> str:
    parts: list[str] = []
    if item.form_of:
        parts.append(
            "form_of=" + ("، ".join(item.form_targets) or "هدف غير مسمى")
        )
    if item.alternative_of:
        parts.append(
            "alt_of="
            + ("، ".join(item.alternative_targets) or "هدف غير مسمى")
        )
    if not parts:
        parts.append("لا نزع صرفي حدسي؛ حُفظ تصنيف المصدر كما هو")
    tokens = "-".join(item.tokens) if item.tokens else "∅"
    selected = item.selected_input or item.skeleton or "∅"
    return (
        "؛ ".join(parts)
        + f"؛ مدخل التطبيع `{selected}`؛ الصوامت الكاملة `{tokens}`"
    )


def inventory_card(number: int, item: InventoryItem) -> tuple[str, dict]:
    ranked = R2.FAN.rank(item.word, R2.FAN.fan(item.word, "greek"), "greek")
    if ranked:
        raise AssertionError(f"المروحة الجذرية لم تعد صفرا في {number}")
    tokens = "-".join(item.tokens) if item.tokens else "∅"
    strict = "-".join(R2.branch_skeleton(item.word)) or "∅"
    read = item.read or "قراءة غير مثبتة في الفهرس"
    oldest = clip(item.etym or item.source_stratum, 180)
    if not oldest:
        oldest = "لم ينشر قاموس الفرع صورة أقدم لهذا العضو."
    category = item_category(item)
    if item.tokens:
        requirement = (
            "صامت ثان على الأقل من تحليل صرفي أو رومنة منشورة يفتح فحص "
            "النواة، أو قاعدة إغلاق موقعة تخص هذا الصنف؛ الصامت الواحد لا "
            "يكفي للجذر أو النواة"
        )
    else:
        requirement = (
            "تحليل صرفي أو رومنة منشورة ينتج صامتين على الأقل لعضو معجمي، "
            "أو قاعدة إغلاق موقعة تخص الصنف غير المعجمي؛ الفراغ لا يجيز النفي"
        )
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE}) + SECTION28-TWO-LAYER؛ الطبقة: استكشاف.",
        f"- مرجع بطاقة الجرد: `{item.family_id}`؛ العضو `{item.member_id}`؛ السابق: {clip(item.previous_state, 260)}.",
        f"- الكلمة في الفرع: `{item.word}` /{read}/؛ `{item.pos}`؛ «{clip(item.meaning, 120)}».",
        f"- معيار الانتخاب: أول الباقي بعد `00333` من `TWO-LAYER-OPEN` ذي الجذر=0 والنواة=0؛ الهيكل `{strict}`؛ موضع الجرد {item.source_rowid}؛ الترتيب بطول الهيكل ثم الموضع.",
        f"- أقدم صورة مستعادة: {oldest} [Kaikki Ancient Greek؛ حقل etymology/source_stratum].",
        f"- الخطوة صفر: {zero_step(item)}؛ لا صامت أصلي محذوف بالحدس.",
        f"- بوابة الصوامت الكاملة: الصوامت `{tokens}`؛ حُفظت كلها للمولدين؛ المحذوف الحدسي=0؛ لم يتاح جذر أو نواة لقلة الصوامت.",
        "- درجة المقارنة: الجذر والنواة معًا؛ أعاد كل مولد صفرا مستقلًا.",
        "- مسح المعاني العربية: لا جذر ولا نواة مولدة لمسح معانيها؛ لم يختر مقابل من خارج الأداة ولم يحول الصفر إلى شاهد نفي.",
        "- المقابل من اللسان: (لا مقابل من الأداة المجمدة)؛ هذا وصف لفجوة مدخل المقارنة لا لحكم تاريخي.",
        "- مسار الصوت: لا مرشح مولدا ولا صف شبكة مطلوبا؛ لم يخترع صف ولم يعلن LAW-GAP.",
        "- حدث الحرف: لم يمرر رمز منفرد أو فراغ إلى `frozen_event` بوصفه جذرًا؛ لا حكم حدث صادر.",
        f"- المعنى من قاموس الفرع: «{clip(item.meaning, 150) or '(غير مسجل في المصدر)'}» [Kaikki Ancient Greek].",
        "- المدار: لا مدار دلالي مستعمل؛ لا تبدأ المقارنة الدلالية قبل وجود مقابل مولد.",
        "- المصفاة: سجل الاتجاه السابق لم يصدر انتقالا مسمى لهذا العضو؛ بقي فحص الأصل مقيدا بهوية العضو ومعناه.",
        f"- فصل المتجانسات والاقتراض: الحكم للعضو `{item.member_id}` وحده؛ لا يرث متحد الرسم ولا عضو الأسرة حكمه.",
        "- فحص الطبقتين: مرشحو الجذر=0؛ مرشحو النواة=0؛ ذوات الشاهد العربي=0؛ لا مرشح مصدر يحتكر البحث.",
        f"- مؤشر اليتم: الأسرة `{item.family_id}` تضم {item.family_members} عضوًا ومنها {item.family_lemmas} لمّة؛ العدد وصف استرجاع لا قرينة حكم.",
        "- إشعاع الأسرة في الفرع: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ لم يصدر حكم موجب.",
        "- إشعاع الأسرة في العربية: الأعضاء المعجمية المدعومة=0؛ سلاسل المعنى المدعومة=0؛ لم تنتج الأداة مقابلا.",
        "- جسور الاسترداد المفحوصة: العضو؛ الخطوة صفر؛ الصوامت؛ الجذر؛ النواة؛ الشبكة؛ الحدث؛ المعنى؛ الأصل؛ الاتجاه؛ المدار.",
        f"- عائق: النوع=TOOL-GAP؛ يتطلب={requirement}.",
        "- حالة الإغلاق: TOOL-GAP.",
        "- الحكم (استكشاف): TOOL-GAP.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحالة السابقة `TWO-LAYER-OPEN`؛ الحكم الجديد `TOOL-GAP`؛ السبب: سُمّي صفر الطبقتين ومطلوبه بعد حفظ الصوامت الكاملة وتصنيف المصدر `{item.processing_status}`.",
        f"- ملاحظات: الصنف `{category}`؛ عدسة الاسترداد أبقت المطلوب مفتوحا، وعدسة التشكيك منعت صلة بلا مقابل.",
    ]
    rendered, size = R6.compact_to_limit("\n".join(lines), completion_id)
    if size > R2.MAX_CARD_BYTES:
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
        "strict_length": len(R2.branch_skeleton(item.word)),
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
        raise AssertionError("معرفات الجولة الحادية عشرة غير متصلة")
    if Counter(record["verdict"] for record in records) != Counter({"TOOL-GAP": 100}):
        raise AssertionError("تغيرت أحكام الجولة الحادية عشرة")
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
            f"<!-- LANE-A-GREEK-ROUND11-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الحادية عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قُرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ اختيرت هذه النافذة لأنهما صفريان معًا، وسميت فجوة الأداة ومطلوبها من غير NO-TRACE.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND11-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round11-"))
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
    return R8.emit_append_patch(
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
        "<!-- LANE-A-GREEK-ROUND11-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الحادية عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00334` إلى `LANE-A-OPEN-COMP-00383`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(first) + ".",
        "",
        f"## {DATE}، الجولة الحادية عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00384` إلى `LANE-A-OPEN-COMP-00433`.",
        "- توزيع الأحكام: `TOOL-GAP`=50؛ الجذر=0 والنواة=0 في كل بطاقة.",
        "- أصناف الجرد: " + categories(second) + ".",
        "",
        "## حصيلة الجولة الحادية عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق من `TWO-LAYER-OPEN` بعد الإتمامات الـ333، بشرط صفر مرشحي الجذر وصفر مرشحي النواة؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        "- الأحكام الكلية: `TOOL-GAP`=100؛ لم يحول صفر الأداة إلى `NO-TRACE` ولم يختر مرشحا من خارجها.",
        "- أصناف النافذة: `NONLEXICAL`=79؛ `FUNCTION`=13؛ `LEXICAL`=8؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: الهيكل الصارم=0 في البطاقات كلها؛ صوامت الجرد المثبتة 0=94 و1=6؛ لا صامت أصلي حُذف بالحدس.",
        "- المطلوب المكتوب: كل بطاقة تسمي التحليل أو الرومنة أو قاعدة الإغلاق الموقعة اللازمة قبل أي حكم؛ لا صلة موجبة جديدة.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- سلامة القراءة: كل بطاقة تسمي الأسرة والعضو والصنف والصوامت الكاملة وحكمي الطبقتين والمصدر والعائق وعدستي المراجعة.",
        "- فحص انضباط النواة: 28 ملاحظة موروثة بلا زيادة؛ لم تضف الجولة حكم جذر أو نواة موجبًا.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ طزاجة سجل الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND11-REPORT:END -->",
        "",
        "LANE-A DONE11 100 LANE-A-OPEN-COMP-00433",
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
        print(R8.emit_append_patch(
            READING,
            reading_fragment(args.start, args.count),
            marker,
        ), end="")
    elif args.report:
        print(R8.emit_append_patch(
            REPORT,
            report_fragment(),
            "LANE-A DONE11",
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
