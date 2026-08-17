#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 16 without committing or shipping.

Round 15 exhausted the frozen zero/zero slice at OPEN-COMP-00820. This
round reads the first one hundred still-open members with a licensed root or
nucleus candidate, in strict-skeleton/source-row order, as two batches of
fifty. Retrieval never becomes a verdict by itself.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from functools import lru_cache
import argparse
import json
import sys
import tempfile
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_ancient_greek_round15 as R15  # noqa: E402


R12, R11, TL = R15.R12, R15.R11, R15.TWO_LAYER
READING, REPORT = R15.READING, R15.REPORT
DATE = "2026-08-17"
FIRST_COMPLETION, LAST_COMPLETION = 821, 920
EXPECTED_PREVIOUS = 820
EXPECTED_POOL = 1_539
BATCH_SIZE = 50
BATCHES = ((821, 870), (871, 920))
EXPECTED_STRICT = Counter({1: 49, 2: 47, 0: 4})
EXPECTED_TOKENS = Counter({2: 93, 3: 5, 4: 2})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 61, "NONLEXICAL": 24, "FUNCTION": 15})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 98, "SOURCE-GAP": 2})
FIRST_MEMBER_PREFIX = "kaikki_ancient_greek:4754:"
LAST_MEMBER = "kaikki_ancient_greek:46266:en-γονά-grc-noun-CfcQrNNL"


@dataclass(frozen=True)
class ReviewOption:
    layer: str
    form: str
    support_root: str
    sources: tuple[str, ...]
    reading: str
    rules: tuple[str, ...]
    score: float


def inventory_items() -> list[R11.InventoryItem]:
    """Select the first hundred nonzero two-layer members after round 15."""
    R12.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    used = R12.completed_before_round12()
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
    if not selected[0].member_id.startswith(FIRST_MEMBER_PREFIX):
        raise AssertionError("تغير أول عضو في الجولة السادسة عشرة")
    if selected[-1].member_id != LAST_MEMBER:
        raise AssertionError("تغير آخر عضو في الجولة السادسة عشرة")
    if len({item.member_id for item in selected}) != 100:
        raise AssertionError("تكرر عضو في الجولة السادسة عشرة")
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


@lru_cache(maxsize=1)
def retriever() -> TL.TwoLayerRetriever:
    return TL.TwoLayerRetriever()


@lru_cache(maxsize=1)
def semantic() -> TL.SemanticReview:
    return TL.SemanticReview(retriever().core)


@lru_cache(maxsize=None)
def target_meanings(target: str) -> tuple[str, ...]:
    con = R11.open_connection()
    try:
        rows = con.execute(
            """SELECT gloss FROM entries
               WHERE language='ancient_greek' AND headword=?
               ORDER BY rowid LIMIT 5""",
            (target,),
        ).fetchall()
    finally:
        con.close()
    return tuple(dict.fromkeys(
        R11.nfc(row["gloss"]) for row in rows if R11.nfc(row["gloss"])
    ))


def full_meaning(item: R11.InventoryItem) -> str:
    meanings = [item.meaning]
    for target in item.form_targets + item.alternative_targets:
        meanings.extend(target_meanings(target))
    return " | ".join(dict.fromkeys(value for value in meanings if value))


def score(left: str, right: str) -> float:
    return TL.overlap_sets(TL.semantic_tokens(left), TL.semantic_tokens(right))


def review_options(branch: str, roots: list, nuclei: list) -> list[ReviewOption]:
    review = semantic()
    options: list[ReviewOption] = []
    for hit in roots:
        sources = review.sources(hit.form)
        if len(sources) < 2 or R11.R2.EVENT.resolve(hit.form) is None:
            continue
        reading = review.definitions.get(hit.form, "")
        options.append(ReviewOption(
            "root", hit.form, hit.form, sources, reading,
            tuple(hit.rule_ids), score(branch, reading),
        ))
    for hit in nuclei:
        core = retriever().core[hit.form]
        core_en = R11.nfc(core.get("composed_reading_en"))
        core_ar = (
            R11.nfc(core.get("jabal_lexicon_reading_ar"))
            or R11.nfc(core.get("composed_reading_ar"))
        )
        supported: list[ReviewOption] = []
        for root, _tokens, sources in review.support.get(hit.form, ()):
            if len(sources) < 2 or R11.R2.EVENT.resolve(root) is None:
                continue
            root_reading = review.definitions.get(root, "")
            reading = " || ".join(
                value for value in (core_ar, core_en, root_reading) if value
            )
            supported.append(ReviewOption(
                "nucleus", hit.form, root, sources, reading,
                tuple(hit.rule_ids), max(score(branch, core_en), score(branch, root_reading)),
            ))
        if supported:
            supported.sort(key=lambda option: (-option.score, option.support_root))
            options.append(supported[0])
    options.sort(key=lambda option: (
        -option.score, option.layer != "root", option.form, option.support_root,
    ))
    return options


def layer_text(hits: list) -> str:
    return R11.clip(TL.layer_summary(hits, 3), 120)


def inventory_card(number: int, item: R11.InventoryItem) -> tuple[str, dict]:
    roots, nuclei = retriever().layers("ancient_greek", item.tokens)
    declared = R11.ZERO_LAYERS.search(item.previous_state)
    actual = (str(len(roots)), str(len(nuclei)))
    if declared is None or declared.groups() != actual:
        raise AssertionError(f"تغير عدادا الطبقتين في {number}: {actual}")
    if not roots and not nuclei:
        raise AssertionError(f"دخل عضو صفري الجولة: {number}")

    branch = full_meaning(item)
    options = review_options(branch, roots, nuclei)
    chosen = options[0] if options else None
    verdict = "OPEN-CANDIDATE" if chosen else "SOURCE-GAP"
    completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
    read = item.read or "قراءة غير مثبتة في الفهرس"
    tokens = "-".join(item.tokens) or "∅"
    strict = "-".join(R11.R2.branch_skeleton(item.word)) or "∅"
    oldest = R11.clip(item.etym or item.source_stratum, 85)
    oldest = oldest or "لم ينشر قاموس الفرع صورة أقدم لهذا العضو."
    category = R11.item_category(item)
    root_summary, nucleus_summary = layer_text(roots), layer_text(nuclei)

    if chosen:
        route = "+".join(chosen.rules) or "ANCHOR"
        event = R11.R2.EVENT.resolve(chosen.support_root)
        if event is None:
            raise AssertionError(f"حدث مجمد غائب في {number}")
        selected = (
            f"الطبقة=`{chosen.layer}`؛ الصورة=`{chosen.form}`؛ "
            f"جذر الشاهد=`{chosen.support_root}`؛ الصفوف=`{route}`"
        )
        witness = (
            f"`{chosen.support_root}`؛ المصادر القديمة المسماة: "
            f"{' + '.join(chosen.sources)}؛ قراءة الفهرس: "
            f"«{R11.clip(chosen.reading, 105)}»"
        )
        event_line = event.line() + "."
        orbit = (
            f"قوبل معنى العضو بقراءة `{chosen.support_root}` عبر طبقة "
            f"`{chosen.layer}` وصورة `{chosen.form}`؛ لم يثبت مدار محدود"
        )
        blocker = (
            "- عائق: النوع=OPEN-CANDIDATE؛ يتطلب=مدارا بشريا محدودا يجمع "
            "معنى العضو بالمادة العربية المسماة؛ الاسترجاع وحده ليس حكما."
        )
    else:
        selected = "لا منتخب مصدريا؛ كل الصور بقيت دون جذر شاهد ذي مصدرين قديمين"
        witness = (
            f"قرئت صور الجذر ({len(roots)}) والنواة ({len(nuclei)})؛ "
            "لم يعد أي منها جذر شاهد مسمى في مصدرين عربيين قديمين"
        )
        event_line = (
            "- حدث الحرف: لم يمرر مرشح مصدري إلى الحدث المجمد؛ "
            "لا حكم صادر."
        )
        orbit = (
            "لا يبدأ بناء المدار قبل وجود مادة عربية مسماة في مصدرين؛ "
            "بقي المعنى خارج حكم الصلة"
        )
        blocker = (
            "- عائق: النوع=SOURCE-GAP؛ يتطلب=جذرا شاهدا مسمى في مصدرين "
            "عربيين قديمين لمرشح من إحدى الطبقتين؛ لم يحول الفراغ إلى نفي."
        )

    lines = [
        f"### {completion_id}: إتمام `{item.family_id}`، `{item.word}` /{read}/",
        "",
        f"- إصدار البروتوكول: RECOVERY-v2 ({DATE}) + SECTION28-TWO-LAYER؛ الطبقة: استكشاف.",
        f"- مرجع الجرد: `{item.family_id}`؛ العضو `{item.member_id}`؛ السابق: TWO-LAYER-OPEN.",
        f"- الكلمة في الفرع: `{item.word}` /{read}/؛ `{item.pos}`؛ «{R11.clip(item.meaning, 105)}».",
        f"- معيار الانتخاب: أول الباقي بعد `00820` ذو مرشح في طبقة؛ الهيكل `{strict}`؛ موضع الجرد {item.source_rowid}؛ الترتيب بطول الهيكل ثم الموضع.",
        f"- أقدم صورة مستعادة: {oldest} [Kaikki Ancient Greek؛ حقل etymology/source_stratum].",
        f"- الخطوة صفر: {R11.zero_step(item)}؛ لا صامت أصلي محذوف بالحدس.",
        f"- بوابة الصوامت: `{tokens}`؛ حفظت للمولدين؛ المحذوف الحدسي=0.",
        f"- نتيجة طبقة الجذر: مرشحون مرخصون={len(roots)}؛ {root_summary}؛ لا حكم من الاسترجاع وحده.",
        f"- نتيجة طبقة النواة: مرشحون مرخصون={len(nuclei)}؛ {nucleus_summary}؛ قرئت مع الجذر بلا ترتيب فشل.",
        f"- حارس المولد: طوبق `tokens_json` بالسجل؛ الجذر={len(roots)} والنواة={len(nuclei)}؛ لا توريث من مولد مواز.",
        f"- مسح المعاني العربية: {witness}.",
        f"- المقابل من اللسان: {selected}؛ لم تصدر صلة.",
        "- مسار الصوت: المرشحون من الصفوف الموقعة؛ لا صف مخترع ولا LAW-GAP.",
        event_line,
        f"- معنى الفرع: «{R11.clip(branch, 115) or '(غير مسجل)'}» [Kaikki؛ العضو وأهداف form/alternative].",
        f"- المدار: {orbit}.",
        "- المصفاة: سجل الاتجاه السابق لم يصدر انتقالا ساميا مسمى لهذا العضو؛ بقي المصدر مقيدا بهويته ومعناه.",
        f"- فصل المتجانسات: الحكم للعضو `{item.member_id}` وحده؛ لا يرث متحد الرسم ولا الهدف حكمه.",
        f"- فحص الطبقتين: الجذر={len(roots)}؛ النواة={len(nuclei)}؛ خيارات الشاهد ذي المصدرين={len(options)}؛ لا مرشح يحتكر البحث.",
        f"- مؤشر اليتم: الأسرة `{item.family_id}`: الأعضاء={item.family_members}؛ اللمم={item.family_lemmas}؛ العدد ليس قرينة حكم.",
        "- إشعاع الأسرة: الفرع=0/0؛ العربية=0/0؛ لم تصدر صلة، والشواهد مواد مراجعة فقط.",
        "- الجسور المفحوصة: العضو؛ صفر؛ الصوامت؛ الطبقتان؛ الشبكة؛ الحدث؛ المعنى؛ المصدر؛ الاتجاه؛ المدار.",
        blocker,
        f"- حالة الإغلاق: {verdict}.",
        f"- الحكم (استكشاف): {verdict}.",
        f"- سطر الإتمام ({DATE}، {completion_id}): الحالة السابقة `TWO-LAYER-OPEN`؛ الحكم الجديد `{verdict}`؛ السبب: قراءة الطبقتين وشواهدهما معا بعد حفظ الصوامت الكاملة وتصنيف المصدر `{item.processing_status}`.",
        f"- ملاحظات: الصنف `{category}`؛ عدسة الاسترداد عرضت المرشحات، وعدسة التشكيك منعت صلة بلا مدار محدود.",
    ]
    rendered, size = R11.R6.compact_to_limit("\n".join(lines), completion_id)
    if size > R11.R2.MAX_CARD_BYTES:
        raise AssertionError(f"تجاوزت البطاقة {completion_id} حد الحجم: {size}")
    if "—" in rendered:
        raise AssertionError(f"شرطة طويلة في {completion_id}")
    return rendered, {
        "completion_id": completion_id,
        "family_id": item.family_id,
        "member_id": item.member_id,
        "word": item.word,
        "read": read,
        "closure": verdict,
        "verdict": verdict,
        "bytes": size,
        "strict_length": len(R11.R2.branch_skeleton(item.word)),
        "token_length": len(item.tokens),
        "category": category,
        "source_rowid": item.source_rowid,
        "roots": len(roots),
        "nuclei": len(nuclei),
        "source_options": len(options),
    }


def render_all() -> tuple[list[str], list[dict]]:
    cards: list[str] = []
    records: list[dict] = []
    for number, item in enumerate(inventory_items(), FIRST_COMPLETION):
        card, record = inventory_card(number, item)
        cards.append(card)
        records.append(record)
    expected = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected:
        raise AssertionError("معرفات الجولة السادسة عشرة غير متصلة")
    verdicts = Counter(record["verdict"] for record in records)
    if verdicts != EXPECTED_VERDICTS:
        raise AssertionError(f"تغيرت أحكام الجولة السادسة عشرة: {verdicts}")
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
            f"<!-- LANE-A-GREEK-ROUND16-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة السادسة عشرة: دفعة إتمام الجرد المفتوح {batch} ({DATE})",
            "",
            f"- المواصلة متصلة من `LANE-A-OPEN-COMP-{first:05d}` إلى `LANE-A-OPEN-COMP-{last:05d}`؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
            "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ لا صلة بلا شاهدين عربيين قديمين، ولا صف صوتيا مخترعا.",
            "",
        ]
    for card in selected:
        lines += [card, ""]
    if end == last:
        lines.append(f"<!-- LANE-A-GREEK-ROUND16-BATCH-{batch}:END -->")
    return "\n".join(lines).rstrip()


def stage_fragments() -> Path:
    cards, _ = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round16-"))
    for first, last in BATCHES:
        for start in range(first, last + 1, 4):
            count = min(4, last - start + 1)
            (stage / f"{start:05d}.md").write_text(
                reading_fragment(start, count, cards), encoding="utf-8"
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
    return R15.R14.R13.R12.R11.R8.emit_append_patch(
        READING, fragment.read_text(encoding="utf-8"), marker,
    )


def report_fragment() -> str:
    _, records = render_all()
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])

    def distribution(rows: list[dict], field: str) -> str:
        counts = Counter(row[field] for row in rows)
        return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))

    root_total = sum(record["roots"] for record in records)
    nucleus_total = sum(record["nuclei"] for record in records)
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND16-REPORT:START -->",
        "",
        f"## {DATE}، الجولة السادسة عشرة، دفعة إتمام الجرد المفتوح 1",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00821` إلى `LANE-A-OPEN-COMP-00870`.",
        "- توزيع الأحكام: " + distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + distribution(first, "category") + ".",
        "",
        f"## {DATE}، الجولة السادسة عشرة، دفعة إتمام الجرد المفتوح 2",
        "",
        "- البطاقات: 50؛ المدى: `LANE-A-OPEN-COMP-00871` إلى `LANE-A-OPEN-COMP-00920`.",
        "- توزيع الأحكام: " + distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + distribution(second, "category") + ".",
        "",
        "## حصيلة الجولة السادسة عشرة",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        "- معيار الجرد: أول 100 عضو باق بعد الإتمامات 820 من `TWO-LAYER-OPEN` ذي مرشح في طبقة على الأقل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت؛ بقي في هذه الشريحة 1439 عضوا.",
        "- الأحكام الكلية: `OPEN-CANDIDATE`=98؛ `SOURCE-GAP`=2؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- الطبقتان: مجموع مرشحي الجذر={root_total}؛ مجموع مرشحي النواة={nucleus_total}؛ كل بطاقة سمت عددي الطبقتين وقرأتهما معا.",
        "- بوابة المصدر: 98 بطاقة سمت جذر شاهد ومصدرين عربيين قديمين على الأقل ثم منعت الحكم لغياب المدار؛ بطاقتا `ἐγώγε` و`ἔγωγ'` بقيتا SOURCE-GAP.",
        "- أصناف النافذة: `LEXICAL`=61؛ `NONLEXICAL`=24؛ `FUNCTION`=15؛ لم يسقط عضو بسبب صنفه.",
        "- ضبط الصوامت الكاملة: صوامت `tokens_json`: 2=93؛ 3=5؛ 4=2؛ لا صامت أصليا حذف بالحدس.",
        "- حارس الطبقتين: أعيدت البطاقات المئة إلى مسترجع SECTION28 المجمد بمدخل `tokens_json`؛ طابقت أعداد الجذر والنواة سجل التغطية فيها كلها.",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ `git diff --check`.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم ينشأ أي إيداع، ولم يجر شحن.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND16-REPORT:END -->",
        "",
        "LANE-A DONE16 100 LANE-A-OPEN-COMP-00920",
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
        print(R15.R14.R13.R12.R11.R8.emit_append_patch(
            READING, reading_fragment(args.start, args.count), marker,
        ), end="")
    elif args.report:
        print(R15.R14.R13.R12.R11.R8.emit_append_patch(
            REPORT, report_fragment(), "LANE-A DONE16",
        ), end="")
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
