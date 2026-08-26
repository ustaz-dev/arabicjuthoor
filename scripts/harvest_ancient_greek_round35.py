#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 35; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative ledger after OPEN-COMP-02320.
The fixed window first exhausts the thirty-nine remaining TWO-LAYER-OPEN
members, then advances to the first sixty-one untouched OPEN-CANDIDATE
members. Every card reads both retrieval layers, keeps retrieval separate
from judgment, and uses only the repository's closed closure vocabulary.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import replace
import argparse
import json
from pathlib import Path
import re
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))

import check_closure_vocabulary as CV  # noqa: E402
import harvest_ancient_greek_round34 as R34  # noqa: E402


R33 = R34.R33
R17 = R33.R32.R31.R30.R29.R28.R27.R26.R25.R20.R19.R18.R17
R16, R11 = R17.R16, R17.R11
READING, REPORT = R34.READING, R34.REPORT
DATE = "2026-08-26"
FIRST_COMPLETION, LAST_COMPLETION = 2321, 2420
EXPECTED_PREVIOUS = 2320
TAIL_COUNT, NEXT_POOL_COUNT = 39, 61
EXPECTED_TAIL_POOL = 39
EXPECTED_NEXT_POOL = 14_391
REMAINING_NEXT_POOL = 14_330
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
BATCHES = ((2321, 2370), (2371, 2420))
EXPECTED_STRICT = Counter({1: 51, 6: 18, 7: 16, 0: 10, 8: 4, 9: 1})
EXPECTED_TOKENS = Counter({2: 47, 6: 16, 7: 16, 3: 10, 8: 5, 4: 3, 9: 2, 5: 1})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 90, "NONLEXICAL": 8, "FUNCTION": 2})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 99, "SOURCE-GAP": 1})
FIRST_MEMBER = "kaikki_ancient_greek:30969:en-ἐπιγλωττίς-grc-noun-h6ZVQMVZ"
TAIL_LAST_MEMBER = (
    "kaikki_ancient_greek:29117:en-εἰς_τοὺς_αἰῶνας_τῶν_αἰώνων-grc-phrase-HIT14Ckr"
)
NEXT_FIRST_MEMBER = "kaikki_ancient_greek:47432:en-𐠍𐠦𐠚-grc-noun-IP-M5FnT"
LAST_MEMBER = "kaikki_ancient_greek:460:en-υἱός-grc-noun-mKpmdUgl"
EXPECTED_SURFACE_GROUPS = {
    "προπάροιθεν": 2,
    "ἅμα": 2,
}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:050b232e73b392b949e5a32a": 2,
    "ancient_greek:family:efe0c7d58d6db0491a34e6df": 2,
    "ancient_greek:family:ffc9f62a2561430747a49929": 2,
    "ancient_greek:family:db46c4323c8fcc1223fa0fbe": 4,
    "ancient_greek:family:32509db05e25c952cbf81562": 2,
    "ancient_greek:family:88bf45370190be0ad758222c": 2,
    "ancient_greek:family:f242506e2e553faab95efb2d": 2,
    "ancient_greek:family:c71959cc250756a279d58822": 2,
    "ancient_greek:family:016882764bfc835f0f8f512a": 4,
    "ancient_greek:family:8791d77c9b52d42df7e23ddd": 2,
}


R16.DATE = DATE


def _values(row: object, key: str) -> tuple[str, ...]:
    return tuple(R11.nfc(value) for value in json.loads(row[key] or "[]"))


def _inventory_item(row: object, previous: str, family: object) -> R11.InventoryItem:
    return R11.InventoryItem(
        family_id=R11.nfc(family["family_id"]),
        family_members=int(family["member_count"]),
        family_lemmas=int(family["lemma_count"]),
        member_id=R11.nfc(row["entry_id"]),
        word=R11.nfc(row["headword"]),
        read=R11.nfc(row["romanization"]),
        pos=R11.nfc(row["pos"]),
        meaning=R11.nfc(row["gloss"]),
        etym=R11.nfc(row["etymology"]),
        source_stratum=R11.nfc(row["source_stratum"]),
        selected_input=R11.nfc(row["selected_input"]),
        skeleton=R11.nfc(row["skeleton"]),
        tokens=_values(row, "tokens_json"),
        form_of=bool(row["form_of"]),
        alternative_of=bool(row["alternative_of"]),
        form_targets=_values(row, "form_targets_json"),
        alternative_targets=_values(row, "alternative_targets_json"),
        processing_status=R11.nfc(row["processing_status"]),
        previous_state=previous,
        source_rowid=int(row["source_rowid"]),
    )


def inventory_items() -> list[tuple[str, R11.InventoryItem]]:
    """Return the fixed tail-first transition window."""
    R17.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    used = R17.completed_members()
    coverage = R11.coverage_rows()
    tail: list[tuple[int, int, object, str]] = []
    next_pool: list[tuple[int, int, object, str]] = []
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
            strict_length = len(R11.R2.branch_skeleton(R11.nfc(row["headword"])))
            record = (strict_length, int(row["source_rowid"]), row, previous)
            counts = R11.ZERO_LAYERS.search(previous)
            if counts is not None and counts.groups() != ("0", "0"):
                tail.append(record)
            elif previous == "OPEN-CANDIDATE":
                next_pool.append(record)

        tail.sort(key=lambda record: (record[0], record[1]))
        next_pool.sort(key=lambda record: (record[0], record[1]))
        if len(tail) != EXPECTED_TAIL_POOL:
            raise AssertionError(f"تغير ذيل TWO-LAYER-OPEN: {len(tail)}")
        if len(next_pool) != EXPECTED_NEXT_POOL:
            raise AssertionError(f"تغير حوض OPEN-CANDIDATE: {len(next_pool)}")
        chosen = [
            *(('TWO-LAYER-OPEN', record) for record in tail),
            *(('OPEN-CANDIDATE', record) for record in next_pool[:NEXT_POOL_COUNT]),
        ]
        items: list[tuple[str, R11.InventoryItem]] = []
        for subpool, (_strict, _rowid, row, previous) in chosen:
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
            items.append((subpool, _inventory_item(row, previous, families[0])))
    finally:
        con.close()

    if len(items) != CARD_COUNT or len({item.member_id for _pool, item in items}) != CARD_COUNT:
        raise AssertionError("تغير عد نافذة الجولة الخامسة والثلاثين أو تكرر عضو")
    if items[0][1].member_id != FIRST_MEMBER:
        raise AssertionError("تغير أول عضو في الجولة الخامسة والثلاثين")
    if items[TAIL_COUNT - 1][1].member_id != TAIL_LAST_MEMBER:
        raise AssertionError("تغير آخر عضو في ذيل TWO-LAYER-OPEN")
    if items[TAIL_COUNT][1].member_id != NEXT_FIRST_MEMBER:
        raise AssertionError("تغير أول عضو في حوض OPEN-CANDIDATE")
    if items[-1][1].member_id != LAST_MEMBER:
        raise AssertionError("تغير آخر عضو في الجولة الخامسة والثلاثين")

    strict = Counter(len(R11.R2.branch_skeleton(item.word)) for _pool, item in items)
    tokens = Counter(len(item.tokens) for _pool, item in items)
    categories = Counter(R11.item_category(item) for _pool, item in items)
    if strict != EXPECTED_STRICT:
        raise AssertionError(f"تغير توزيع الهيكل الصارم: {strict}")
    if tokens != EXPECTED_TOKENS:
        raise AssertionError(f"تغير توزيع صوامت الجرد: {tokens}")
    if categories != EXPECTED_CATEGORIES:
        raise AssertionError(f"تغير توزيع أصناف الجرد: {categories}")
    return items


def _groups(records: list[dict], field: str) -> dict[str, list[str]]:
    grouped: dict[str, list[str]] = {}
    for record in records:
        grouped.setdefault(str(record[field]), []).append(record["completion_id"])
    return grouped


def _previous_words() -> set[str]:
    text = READING.read_text(encoding="utf-8")
    found = [
        (int(number), word)
        for number, word in re.findall(
            r"^### LANE-A-OPEN-COMP-(\d{5}):[^\n]*، `([^`]+)` /",
            text,
            re.MULTILINE,
        )
        if int(number) <= EXPECTED_PREVIOUS
    ]
    if len(found) != EXPECTED_PREVIOUS:
        raise AssertionError(f"تغير عد بطاقات الإتمام السابقة: {len(found)}")
    return {word for _number, word in found}


def _leg_disposition(record: dict) -> str:
    if record["verdict"] == "OPEN-CANDIDATE":
        if record["source_options"] < 1:
            raise AssertionError(f"حكم مفتوح بلا شاهد مصدري: {record['completion_id']}")
        return "HONOURABLE-REASONED-OPEN"
    if record["verdict"] == "SOURCE-GAP":
        return "HONOURABLE-REASONED-SOURCE-GAP"
    raise AssertionError(f"حكم غير معالج: {record['verdict']}")


def _render_base(number: int, subpool: str, item: R11.InventoryItem) -> tuple[str, dict]:
    rendered_item = item
    if subpool == "OPEN-CANDIDATE":
        roots, nuclei = R16.retriever().layers("ancient_greek", item.tokens)
        rendered_item = replace(
            item,
            previous_state=(
                f"TWO-LAYER-OPEN؛ الجذر=مرشحون مرخصون {len(roots)}؛ "
                f"النواة=مرشحون مرخصون {len(nuclei)} من الفهرس المجمد؛ "
                "قُرئا معًا لا على ترتيب الفشل؛ الحكم غير صادر"
            ),
        )
    card, record = R16.inventory_card(number, rendered_item)
    old_criterion = "أول الباقي بعد `00820` ذو مرشح في طبقة"
    if subpool == "TWO-LAYER-OPEN":
        criterion = "ذيل `TWO-LAYER-OPEN` بعد `02320` ذو مرشح في طبقة"
        previous = "TWO-LAYER-OPEN"
    else:
        criterion = (
            "أول الباقي من حوض `OPEN-CANDIDATE` غير المستعمل بعد استنفاد "
            "`TWO-LAYER-OPEN`"
        )
        previous = "OPEN-CANDIDATE"
    if card.count(old_criterion) != 1:
        raise AssertionError(f"تغير موضع معيار الانتخاب في البطاقة {number}")
    card = card.replace(old_criterion, criterion)
    if previous == "OPEN-CANDIDATE":
        card = card.replace("السابق: TWO-LAYER-OPEN.", "السابق: OPEN-CANDIDATE.", 1)
        card = card.replace(
            "الحالة السابقة `TWO-LAYER-OPEN`؛",
            "الحالة السابقة `OPEN-CANDIDATE`؛",
            1,
        )
    record["previous_state"] = previous
    record["subpool"] = subpool
    return card, record


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed transition window and enforce all audit gates."""
    if "LANE-A DONE34 100 LANE-A-OPEN-COMP-02320" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE34 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND34-CHUNK-50:END -->" not in reading_text:
        raise AssertionError("الجولة الرابعة والثلاثون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND35-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الخامسة والثلاثين موجودة")

    pairs = inventory_items()
    raw_cards: list[str] = []
    records: list[dict] = []
    for number, (subpool, item) in enumerate(pairs, FIRST_COMPLETION):
        card, record = _render_base(number, subpool, item)
        raw_cards.append(card)
        records.append(record)

    expected_ids = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if [record["completion_id"] for record in records] != expected_ids:
        raise AssertionError("تغير اتصال نافذة الجولة الخامسة والثلاثين")
    closures = Counter(record["closure"] for record in records)
    if not set(closures) <= CV.LEGAL or closures != EXPECTED_VERDICTS:
        raise AssertionError(f"خرج حكم عن قاموس الإغلاق المغلق: {closures}")
    if Counter(record["subpool"] for record in records) != Counter({
        "TWO-LAYER-OPEN": TAIL_COUNT,
        "OPEN-CANDIDATE": NEXT_POOL_COUNT,
    }):
        raise AssertionError("تغير توزيع حوضي الانتقال")

    prior_words = _previous_words()
    prior_surface_rows = sum(record["word"] in prior_words for record in records)
    if prior_surface_rows:
        raise AssertionError(f"دخلت صورة من الإتمامات السابقة: {prior_surface_rows}")
    surfaces = _groups(records, "word")
    families = _groups(records, "family_id")
    surface_groups = {key: len(value) for key, value in surfaces.items() if len(value) > 1}
    family_groups = {key: len(value) for key, value in families.items() if len(value) > 1}
    if surface_groups != EXPECTED_SURFACE_GROUPS:
        raise AssertionError(f"تغير تكرار الرسم: {surface_groups!r}")
    if family_groups != EXPECTED_FAMILY_GROUPS:
        raise AssertionError(f"تغير تكرار الأسرة: {family_groups!r}")

    cards: list[str] = []
    for card, record in zip(raw_cards, records, strict=True):
        same_surface = surfaces[record["word"]]
        same_family = families[record["family_id"]]
        surface_note = (
            "الرسم جديد إلى 02320"
            if len(same_surface) == 1 else
            f"الرسم مكرر في النافذة={len(same_surface)}"
        )
        family_note = (
            "الأسرة منفردة"
            if len(same_family) == 1 else
            f"الأسرة مكررة في النافذة={len(same_family)}"
        )
        repeat_line = (
            f"- فحص التكرار: العضو فريد؛ {surface_note}؛ {family_note}؛ "
            "الصف مستقل بمصدره."
        )
        card, substitutions = re.subn(
            r"(?m)^(- مرجع (?:بطاقة )?الجرد:.*)$",
            rf"\1\n{repeat_line}",
            card,
            count=1,
        )
        if substitutions != 1:
            raise AssertionError(f"تعذر وسم فحص البطاقة: {record['completion_id']}")
        disposition = _leg_disposition(record)
        if len((card + "\n").encode("utf-8")) > R11.R2.MAX_CARD_BYTES:
            card, compacted = re.subn(
                r"(?m)^- ملاحظات:.*$",
                f"- ملاحظات: الصنف `{record['category']}`؛ لا حكم من الاسترجاع وحده.",
                card,
                count=1,
            )
            if compacted != 1:
                raise AssertionError(f"تعذر ضغط البطاقة: {record['completion_id']}")
        card, size = R11.R6.compact_to_limit(card, record["completion_id"])
        if (
            repeat_line not in card
            or f"- عائق: النوع={record['verdict']}؛" not in card
            or f"- حالة الإغلاق: {record['closure']}." not in card
        ):
            raise AssertionError(f"سقط ضبط البطاقة: {record['completion_id']}")
        if "—" in card:
            raise AssertionError(f"شرطة طويلة في {record['completion_id']}")
        record["bytes"] = size
        record["surface_window_count"] = len(same_surface)
        record["family_window_count"] = len(same_family)
        record["surface_seen_before"] = False
        record["leg_disposition"] = disposition
        cards.append(card)

    meta = {
        "open_previous": EXPECTED_PREVIOUS,
        "tail_before": EXPECTED_TAIL_POOL,
        "tail_remaining": 0,
        "next_pool_before": EXPECTED_NEXT_POOL,
        "next_pool_remaining": REMAINING_NEXT_POOL,
        "unique_members": len({record["member_id"] for record in records}),
        "prior_surface_rows": prior_surface_rows,
        "surface_duplicate_rows": sum(len(value) - 1 for value in surfaces.values()),
        "surface_duplicate_groups": surface_groups,
        "family_duplicate_rows": sum(len(value) - 1 for value in families.values()),
        "family_duplicate_groups": family_groups,
        "honourable_reasoned": sum(
            record["leg_disposition"].startswith("HONOURABLE-REASONED-")
            for record in records
        ),
    }
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
        f"<!-- LANE-A-GREEK-ROUND35-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة الخامسة والثلاثون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
        "",
        f"- المواصلة متصلة من `{first}` إلى `{last}`؛ 50 بطاقة؛ المصدر سجل التغطية الشامل؛ الترتيب بحسب أولوية الحوض ثم طول الهيكل الصارم ثم موضع الجرد المثبت.",
        f"- توزيع الأحواض: {_distribution(records, 'subpool')}.",
        "- فُحص تكرار معرّف العضو والرسم والأسرة في الذاكرة وفي النافذة؛ لم يسقط صف مستقل لمجرد اتحاد الرسم أو الأسرة.",
        "- لا موجب إلا بأرجل الصوت والحدث والمعنى كاملة؛ وما لم يكتمل حمل حكما شريفا مسمى السبب من قاموس الإغلاق المغلق.",
        "",
    ]


def report_addition(records: list[dict], meta: dict) -> str:
    first_batch, second_batch = records[:BATCH_SIZE], records[BATCH_SIZE:]
    verdicts = Counter(record["verdict"] for record in records)
    categories = Counter(record["category"] for record in records)
    strict = Counter(record["strict_length"] for record in records)
    tokens = Counter(record["token_length"] for record in records)
    largest = max(records, key=lambda record: record["bytes"])
    source_gaps = [record for record in records if record["verdict"] == "SOURCE-GAP"]
    source_gap_text = "؛ ".join(
        f"`{record['word']}` ({record['completion_id']})" for record in source_gaps
    )
    lines = [
        "",
        "<!-- LANE-A-GREEK-ROUND35-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الخامسة والثلاثون، إتمام الجرد المفتوح، الدفعة 1",
        "",
        f"- البطاقات: 50؛ المدى: `{first_batch[0]['completion_id']}` إلى `{first_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(first_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(first_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(first_batch, 'category')}.",
        "",
        f"## {DATE}، الجولة الخامسة والثلاثون، إتمام الجرد المفتوح، الدفعة 2",
        "",
        f"- البطاقات: 50؛ المدى: `{second_batch[0]['completion_id']}` إلى `{second_batch[-1]['completion_id']}`.",
        f"- توزيع الأحواض: {_distribution(second_batch, 'subpool')}.",
        f"- توزيع الأحكام: {_distribution(second_batch, 'verdict')}.",
        f"- أصناف الجرد: {_distribution(second_batch, 'category')}.",
        "",
        "## حصيلة الجولة الخامسة والثلاثين",
        "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        f"- انتقال الرتل: استُنفدت البطاقات {meta['tail_before']} الباقية من `TWO-LAYER-OPEN` أولا، ثم أُخذت أول {NEXT_POOL_COUNT} بطاقة من حوض `OPEN-CANDIDATE` غير المستعمل؛ بقي من الحوض التالي {meta['next_pool_remaining']} عضوا.",
        f"- فحص التكرار: معرّفات الأعضاء الفريدة={meta['unique_members']}؛ صورة سبق إتمامها={meta['prior_surface_rows']}؛ تكرار الرسم الزائد داخل النافذة={meta['surface_duplicate_rows']} في المجموعات {_groups_text(meta['surface_duplicate_groups'])}.",
        f"- فحص الأسرة: تكرار الصفوف الزائد={meta['family_duplicate_rows']} في المجموعات {_groups_text(meta['family_duplicate_groups'])}؛ حفظت الصفوف لأنها أعضاء مستقلة بمواضع مصدر مختلفة.",
        f"- الأحكام الكلية: {_distribution(records, 'verdict')}؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- ضبط الأرجل الثلاث: موجب مكتمل=0؛ حكم شريف مسمى السبب={meta['honourable_reasoned']}؛ حملت {verdicts['OPEN-CANDIDATE']} بطاقة حكما مفتوحا لغياب مدار بشري محدود، وحملت {verdicts['SOURCE-GAP']} بطاقة `SOURCE-GAP` لغياب شاهد مصدري صالح.",
        f"- بوابة المصدر: بطاقة `SOURCE-GAP` هي {source_gap_text}؛ بقيت مفتوحة ولم يصنع غياب المصدر صلة.",
        f"- الطبقتان: مجموع مرشحي الجذر={sum(record['roots'] for record in records)}؛ مجموع مرشحي النواة={sum(record['nuclei'] for record in records)}؛ خيارات الشاهد ذي المصدرين={sum(record['source_options'] for record in records)}؛ كل بطاقة قرأت الطبقتين معا.",
        f"- قاموس الإغلاق: استعمل {_distribution(records, 'closure')}، وكلها من القاموس المغلق المقرر؛ لم يولد وسم جديد.",
        f"- أصناف النافذة: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(categories.items())) + ".",
        f"- ضبط الهيكل الصارم: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(strict.items())) + "؛ صوامت `tokens_json`: " + "؛ ".join(f"`{key}`={value}" for key, value in sorted(tokens.items())) + ".",
        f"- حد الحجم: أكبر بطاقة {largest['bytes']} بايت، `{largest['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: اتصال المعرفات؛ مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ الأرجل؛ التكرار، من غير تشغيل git.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.",
        "",
        "<!-- LANE-A-GREEK-ROUND35-REPORT:END -->",
        "",
        "LANE-A DONE35 100 LANE-A-OPEN-COMP-02420",
    ]
    report = "\n".join(lines)
    if "—" in report:
        raise AssertionError("شرطة طويلة في تقرير الجولة الخامسة والثلاثين")
    return report


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round35-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND34-CHUNK-50:END -->"
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
                lines += [f"<!-- LANE-A-GREEK-ROUND35-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND35-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R34.R33.R30._anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        R34.R33.R30._anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE34 100 LANE-A-OPEN-COMP-02320",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND35-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة الخامسة والثلاثون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND35-CHUNK-50:END -->", 1)[0]
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
            section.split(f"<!-- LANE-A-GREEK-ROUND35-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND35-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND35-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, records, meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND35-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(
        r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE
    ))
    previous_states = Counter(record["previous_state"] for record in records)
    truncation_markers = len(re.findall(
        r"tokens truncated|chars truncated|lines truncated", section
    ))
    done = "LANE-A DONE35 100 LANE-A-OPEN-COMP-02420"
    report = REPORT.read_text(encoding="utf-8")
    report_marker = "<!-- LANE-A-GREEK-ROUND35-REPORT:START -->"
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
        or previous_states != Counter({
            "TWO-LAYER-OPEN": TAIL_COUNT,
            "OPEN-CANDIDATE": NEXT_POOL_COUNT,
        })
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
