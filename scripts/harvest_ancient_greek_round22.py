#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 22 from the expanded Ancient Greek both-pool.

The scan resumes at expanded rank 453.  The reading ledger is normalized and
kept in memory, and an in-memory seen set also suppresses duplicate source
surfaces.  The first one hundred fresh forms are rendered as two batches of
fifty.  This module only emits apply-patch inputs; it never commits or ships.
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

import harvest_ancient_greek_round21 as R21  # noqa: E402


SWEEP = R21.SWEEP
READING = R21.READING
PROPOSAL = R21.PROPOSAL
REPORT = R21.REPORT
DATE = "2026-08-18"
EXPECTED_POOL = 1_098
SCAN_FROM = 453
EXPECTED_FRESH = 266
EXPECTED_EXISTING = 378
EXPECTED_SOURCE_DUPLICATES = 2
EXPECTED_FIRST_RANK = 455
EXPECTED_LAST_RANK = 653
EXPECTED_FIRST_WORD = "ἄχρι"
EXPECTED_LAST_WORD = "ὁποῖος"
BATCH_SIZE = 50
CARD_COUNT = 100
BT = chr(96)


Outcome = R21.Outcome


def q(value: object) -> str:
    return BT + str(value) + BT


# Every non-open outcome below was hand-read against the complete Arabic-root
# result set.  Retrieval weight alone never enters this mapping.
OUTCOMES: dict[int, Outcome] = {
    462: Outcome(
        "root", "صحح", "الصحة خلاف السقم؛ وصحاح الطريق شدته",
        "physically strong في الفرع يلتقي صحة البدن وشدة الطريق في العربية؛ المدار سلامة البنية وثبات قوتها.",
        1,
    ),
    471: Outcome(
        "root", "وسم", "وسم الشيء: أثر فيه بسمة؛ والموسوم يعرف بعلامته",
        "military standard وensign علامتان تميزان الجماعة، وهو وسم العربية: أثر ظاهر يعرف به صاحبه.",
        1,
    ),
    480: Outcome(
        "root", "مز", "التمزز المص؛ والمزة المصة",
        "to suck هو المص نفسه الذي تسميه العربية تمززا؛ المدار أخذ السائل بالمص قليلا قليلا.",
        2,
    ),
    496: Outcome(
        "law", "وفد", "وفد إليه: قدم؛ وأوفده: أرسله",
        "to go to or visit repeatedly يلتقي الوفود إلى الشخص أو المكان؛ المدار قصد الموضع والقدوم عليه، لكن τ إلى د بلا صف يوناني مسمى.",
        1, "τ ↔ د",
    ),
    499: Outcome(
        "law", "حوت", "الحوت السمك معروف",
        "dried fish-skin وfishery مقيدان بالسمك الذي تسميه العربية حوتا؛ المدار الحيوان ومادته، لكن θ إلى ت بلا صف يوناني مسمى.",
        1, "θ ↔ ت",
    ),
    500: Outcome(
        "law", "حوت", "الحوت السمك معروف",
        "to fish وto sport of fish فعلان مشتقان من السمك نفسه الذي تسميه العربية حوتا؛ لكن θ إلى ت بلا صف يوناني مسمى.",
        1, "θ ↔ ت",
    ),
    515: Outcome(
        "root", "وسم", "وسم الشيء: أثر فيه بسمة يعرف بها",
        "to mark وstamp وseal هي إحداث وسم ظاهر في الشيء؛ المدار العلامة المثبتة التي يعرف بها الموسوم.",
        1,
    ),
    540: Outcome(
        "law", "نفي", "نفاه: طرده وأبعده؛ والسيل ينفي الغثاء يدفعه",
        "to drive back يطابق نفي الشيء ودفعه عن الحيز؛ المعنى والحدث مباشران، لكن π إلى ف بلا صف يوناني مسمى.",
        1, "π ↔ ف",
    ),
    545: Outcome(
        "root", "جلو", "جلا الشيء: كشفه وأظهره؛ وتجلي الشمس انكشافها",
        "radiance وgleam هما ظهور الضوء بعد انكشافه؛ المدار جلاء الشمس وانكشافها للناظر.",
        1,
    ),
    574: Outcome(
        "root", "بيت", "البيت مأوى الإنسان؛ والخِباء بيت من صوف أو شعر",
        "tent or shelter made of skins هو بيت العربية وخباؤها؛ المدار حيز محيط مصنوع للسكن والاحتماء.",
        1,
    ),
    599: Outcome(
        "law", "لفف", "لف الشيء في ثوبه وتلفف به؛ واللفافة ما يلف",
        "covering وrobe وmantle أشياء يلتف بها البدن؛ المدار غطاء يلوى على ظاهر الشيء، لكن π إلى ف بلا صف يوناني مسمى.",
        1, "π ↔ ف",
    ),
    602: Outcome(
        "law", "فري", "فرى الشيء بالسيف والشفرة: قطعه وشقه",
        "to saw هو قطع المادة وشقها بأداة ذات حد؛ المدار فعل الفصل بالشفرة، لكن π إلى ف بلا صف يوناني مسمى.",
        3, "π ↔ ف",
    ),
    624: Outcome(
        "law", "وفد", "أوفدته إلى الأمير: أرسلته",
        "to send forth يطابق أوفدته أي أرسلته؛ المدار إخراج المرسل ودفعه إلى وجهته، لكن π إلى ف وτ إلى د بلا صفين يونانيين مسميين.",
        1, "π ↔ ف",
    ),
    626: Outcome(
        "root", "فم", "الفم معروف؛ وهو فتحة الفم وما يملؤها",
        "muzzle أداة تغلق الفم، وto muzzle إغلاقه ومنع الكلام منه؛ المدار العضو الذي يقع عليه الإغلاق.",
        2,
    ),
    627: Outcome(
        "law", "قفو", "القفا مؤخر العنق؛ واستقفاه أتاه من خلفه",
        "back door هو الباب الواقع في خلف البناء؛ المدار الجهة الخلفية المسماة بالقفا، لكن π إلى ف بلا صف يوناني مسمى.",
        1, "π ↔ ف",
    ),
    636: Outcome(
        "root", "غش", "غشه: لم يمحضه النصيحة وعامله بغير صفاء",
        "cheat في الفرع هو الغاش في العربية؛ المدار إظهار غير الحقيقة وإخفاء الخلل عن المخدوع.",
        2,
    ),
    640: Outcome(
        "law", "فر", "الفرار الهرب والانكشاف عن الموضع",
        "to dart away هو الفرار السريع عن الموضع؛ المدار انفصال متحرك إلى خارج، لكن π إلى ف بلا صف يوناني مسمى.",
        2, "π ↔ ف",
    ),
    641: Outcome(
        "root", "طوح", "طاح: سقط أو هلك أو ذهب",
        "fail وmiscarry في الفرع يلتقيان طاح في العربية: سقط الأمر وذهب قبل بلوغ غايته.",
        3,
    ),
    646: Outcome(
        "root", "روس", "رُوس: بلد، وقيل طائفة من الناس",
        "Rus وthe Russes هما الروس في العربية اسما للبلد والطائفة؛ الاسم والمسمى واحدان، وحاشية الأصل غير السامي لا تصير شرطا رابعا.",
        3,
    ),
}


def load_and_select() -> tuple[list[tuple[int, int, dict]], dict]:
    """Select one hundred fresh exact surfaces after rank 452."""
    reading_text = R21.nfc(READING.read_text(encoding="utf-8"))
    if "<!-- LANE-A-GREEK-ROUND21-BATCH-2:END -->" not in reading_text:
        raise AssertionError("الجولة الحادية والعشرون غير مثبتة في سجل القراءة")
    if "<!-- LANE-A-GREEK-ROUND22-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الثانية والعشرين موجودة")
    report_text = REPORT.read_text(encoding="utf-8")
    if "LANE-A DONE21 100 452" not in report_text:
        raise AssertionError("خاتمة الجولة الحادية والعشرين غير مثبتة")

    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    if payload.get("language") != "ancient_greek":
        raise AssertionError("اختلط لسان حوض المسح")
    source_rows = payload.get("both", [])
    if len(source_rows) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الحوض المضاعف: {len(source_rows)}")
    ordered = sorted(
        enumerate(source_rows, 1),
        key=lambda item: (-int(item[1].get("overlap") or 0), item[0]),
    )

    fresh: list[tuple[int, int, dict]] = []
    seen: set[str] = set()
    existing = 0
    source_duplicates = 0
    for expanded_rank, (source_rank, row) in enumerate(ordered, 1):
        if expanded_rank < SCAN_FROM:
            continue
        word = R21.nfc(row.get("branch"))
        if not word:
            raise AssertionError(f"صف بلا صورة عند الرتبة الموسعة {expanded_rank}")
        if word in reading_text:
            existing += 1
            continue
        if word in seen:
            source_duplicates += 1
            continue
        seen.add(word)
        fresh.append((expanded_rank, source_rank, row))

    if len(fresh) != EXPECTED_FRESH:
        raise AssertionError(f"تغير عدد الطازج بعد الرتبة 452: {len(fresh)}")
    if existing != EXPECTED_EXISTING or source_duplicates != EXPECTED_SOURCE_DUPLICATES:
        raise AssertionError(
            f"تغير فحص التكرار: الموجود={existing}؛ تكرار المصدر={source_duplicates}"
        )
    selected = fresh[:CARD_COUNT]
    if len(selected) != CARD_COUNT:
        raise AssertionError(f"الطازج أقل من نافذة الجولة: {len(selected)}")
    if selected[0][0] != EXPECTED_FIRST_RANK or selected[-1][0] != EXPECTED_LAST_RANK:
        raise AssertionError("تغير مدى نافذة الجولة الثانية والعشرين")
    if selected[0][2]["branch"] != EXPECTED_FIRST_WORD:
        raise AssertionError("تغير أول عضو طازج")
    if selected[-1][2]["branch"] != EXPECTED_LAST_WORD:
        raise AssertionError("تغير آخر عضو طازج")
    if len({R21.nfc(row[2]["branch"]) for row in selected}) != CARD_COUNT:
        raise AssertionError("تكررت صورة داخل نافذة الطازج")
    return selected, {
        "pool": len(source_rows),
        "scan_from": SCAN_FROM,
        "existing_rows": existing,
        "source_duplicates": source_duplicates,
        "fresh_rows": len(fresh),
        "first_rank": selected[0][0],
        "last_rank": selected[-1][0],
    }


def gather_hits(selected: list[tuple[int, int, dict]]) -> dict[str, list[dict]]:
    R21.OUTCOMES = OUTCOMES
    return R21.gather_hits(selected)


def build_card(
    expanded_rank: int,
    source_rank: int,
    row: dict,
    hits: dict[str, list[dict]],
) -> tuple[str, dict]:
    R21.OUTCOMES = OUTCOMES
    card, record = R21.build_card(expanded_rank, source_rank, row, hits)
    card = card.replace("LANE-A-R21-", "LANE-A-R22-")
    if expanded_rank == 624:
        old = (
            "- عائق: النوع=LAW-GAP؛ يتطلب=صفا مجمدا مسمى يرخص "
            + q("π ↔ ف")
            + "؛ فُتشت الشبكة بالحرفين وبـ«اليونانية/Greek» في عمود الشاهد."
        )
        new = (
            "- عائق: النوع=LAW-GAP؛ يتطلب=صفين مجمدين مسميين يرخصان "
            + q("π ↔ ف")
            + " و"
            + q("τ ↔ د")
            + "؛ فُتشت الشبكة بكل زوج وبـ«اليونانية/Greek» في عمود الشاهد."
        )
        if old not in card:
            raise AssertionError("تعذر توسيع عائق البطاقة 624")
        card = card.replace(old, new)
        card, size = R21.R6.compact_to_limit(card, "R22-624")
        record["bytes"] = size
    return card, record


def render_all() -> tuple[str, list[dict], dict]:
    selected, selection = load_and_select()
    hits = gather_hits(selected)
    sections: list[str] = []
    records: list[dict] = []
    for batch in (1, 2):
        batch_rows = selected[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND22-BATCH-{batch}:START -->",
            "",
            f"## اليونانية، الجولة الثانية والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})",
            "",
            f"- النموذج {q('WO-B-PROBE-001')}؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {batch_rows[0][0]} إلى {batch_rows[-1][0]} بعد بدء المسح من 453 وتجاوز الصور الموجودة والمكررة في الذاكرة.",
            "- الترتيب " + q("overlap") + " نازل ثابت ثم موضع المصدر؛ قُرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.",
            "",
        ]
        for expanded_rank, source_rank, row in batch_rows:
            card, record = build_card(expanded_rank, source_rank, row, hits)
            sections += [card, ""]
            records.append(record)
        sections.append(f"<!-- LANE-A-GREEK-ROUND22-BATCH-{batch}:END -->")
        if batch == 1:
            sections.append("")
    if len(records) != CARD_COUNT:
        raise AssertionError(f"عدد بطاقات الجولة {len(records)}")
    return "\n".join(sections).rstrip(), records, selection


def proposal_addition(records: list[dict]) -> str:
    law = [record for record in records if record["closure"] == "LAW-GAP"]
    grouped: dict[str, list[dict]] = {}
    for record in law:
        _licensed, _route, gaps = R21.R2.sound_route(record["word"], record["root"])
        if not gaps:
            raise AssertionError(f"بطاقة LAW-GAP بلا ساق غائبة: {record['expanded_rank']}")
        for gap in dict.fromkeys(gaps):
            grouped.setdefault(gap, []).append(record)
    lines = [
        "## إلحاق شواهد الجولة الثانية والعشرين، الحوض المضاعف",
        "",
        "هذه شواهد " + q("LAW-GAP") + " الطازجة وحدها من دفعتين؛ لا توصية بإضافة صف، ولا تعديل للشبكة النافذة.",
        "",
        "| الساق الغائبة | الشواهد الجديدة | أمثلة بأسمائها | الحكم النافذ |",
        "|---|---:|---|---|",
    ]
    for gap, rows in grouped.items():
        examples = "؛ ".join(
            q(row["word"]) + "→" + q(row["root"]) + " «"
            + OUTCOMES[row["expanded_rank"]].counterpart + "»"
            for row in rows
        )
        lines.append(
            "| " + q(gap) + f" | {len(rows)} | {examples} | لا صف مجمد مسمى؛ تبقى البطاقات "
            + q("LAW-GAP") + " |"
        )
    lines += [
        "",
        "تبقى هذه البطاقات في " + q("LAW-GAP") + " إلى قرار المؤلف؛ الإلحاق شاهد فقط.",
    ]
    return "\n".join(lines)


def report_addition(records: list[dict], selection: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]

    def counts(rows: list[dict], field: str) -> str:
        return "؛ ".join(
            q(key) + f"={value}"
            for key, value in sorted(Counter(row[field] for row in rows).items())
        )

    law = [record for record in records if record["closure"] == "LAW-GAP"]
    lines = [
        "<!-- LANE-A-GREEK-ROUND22-REPORT:START -->",
        "",
        f"## {DATE}، الجولة الثانية والعشرون، الحوض المضاعف، الدفعة 1",
        "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {first[0]['expanded_rank']} إلى {first[-1]['expanded_rank']}؛ آخر {q('overlap')}={first[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(first, "verdict") + ".",
        "- توزيع الإغلاق: " + counts(first, "closure") + ".",
        "",
        f"## {DATE}، الجولة الثانية والعشرون، الحوض المضاعف، الدفعة 2",
        "",
        f"- البطاقات: 50؛ الرتبة الموسعة: {second[0]['expanded_rank']} إلى {second[-1]['expanded_rank']}؛ آخر {q('overlap')}={second[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(second, "verdict") + ".",
        "- توزيع الإغلاق: " + counts(second, "closure") + ".",
        "",
        "## حصيلة الجولة الثانية والعشرين",
        "",
        f"- استؤنف المسح من الرتبة {selection['scan_from']}؛ الرتبتان 453 و454 متجاوزتان لوجود صورتيهما في سجل القراءة؛ أول بطاقة طازجة={selection['first_rank']}.",
        f"- من الرتبة 453 إلى آخر الحوض: الموجود في السجل={selection['existing_rows']}؛ تكرار المصدر المضبوط في الذاكرة={selection['source_duplicates']}؛ الطازج غير المكرر={selection['fresh_rows']}.",
        "- مجموع البطاقات: 100؛ دفعتان من 50 بطاقة بنموذج " + q("WO-B-PROBE-001") + ".",
        "- الترتيب: " + q("overlap") + " نازل ثابت ثم موضع المصدر؛ لا صف مكرر الصورة دخل النافذة.",
        "- الإغلاق الكلي: " + counts(records, "closure") + ".",
        "- الحكم الكلي: " + counts(records, "verdict") + ".",
        f"- فجوات القانون الطازجة: {len(law)}؛ ألحقت شواهدها في {q('proposed-shift-rows-greek.md')} بلا توصية ولا تعديل للشبكة.",
        f"- حد الحجم: أكبر بطاقة {max(record['bytes'] for record in records)} بايت؛ لا بطاقة تجاوزت 5 كيلوبايت.",
        "- الإيداع والشحن: لم يشغل " + q("scripts/ship.py") + "، ولم ينشأ إيداع، ولم يجر شحن.",
        "",
        "<!-- LANE-A-GREEK-ROUND22-REPORT:END -->",
        "",
        f"LANE-A DONE22 {len(records)} {records[-1]['expanded_rank']}",
    ]
    return "\n".join(lines)


def add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def append_patch(path: Path, fragment: str, anchor: str) -> str:
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {path.relative_to(ROOT).as_posix()}",
        "@@",
        f" {anchor}",
        "+",
        add_lines(fragment.rstrip()),
        "*** End Patch",
        "",
    ])


def stage_patches() -> Path:
    """Render once and stage bounded apply-patch inputs in system temp."""
    rendered, records, selection = render_all()
    cards = [match.group(0).rstrip() for match in re.finditer(
        r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND22-BATCH-[12]:END -->)",
        rendered,
    )]
    if len(cards) != CARD_COUNT:
        raise AssertionError(f"تعذر تفكيك البطاقات المرحلية: {len(cards)}")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round22-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND21-CHUNK-10:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            lines: list[str] = []
            if offset == 0:
                lines += [
                    f"<!-- LANE-A-GREEK-ROUND22-BATCH-{batch}:START -->",
                    "",
                    f"## اليونانية، الجولة الثانية والعشرون: الحوض المضاعف، الدفعة {batch} ({DATE})",
                    "",
                    f"- النموذج {q('WO-B-PROBE-001')}؛ 50 بطاقة طازجة؛ الرتبة الموسعة من {batch_records[0]['expanded_rank']} إلى {batch_records[-1]['expanded_rank']} بعد بدء المسح من 453 وتجاوز الصور الموجودة والمكررة في الذاكرة.",
                    "- الترتيب " + q("overlap") + " نازل ثابت ثم موضع المصدر؛ قُرئت المروحة كاملة، ولم يتحول وزن الاسترجاع إلى حكم.",
                    "",
                ]
            for card in batch_cards[offset:offset + 10]:
                lines += [card, ""]
            if offset + 10 == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND22-BATCH-{batch}:END -->", ""]
            chunk_marker = f"<!-- LANE-A-GREEK-ROUND22-CHUNK-{chunk_number:02d}:END -->"
            lines.append(chunk_marker)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                append_patch(READING, "\n".join(lines), previous_anchor),
                encoding="utf-8",
                newline="\n",
            )
            previous_anchor = chunk_marker

    proposal = proposal_addition(records)
    report = report_addition(records, selection)
    proposal_anchor = (
        "تبقى هذه البطاقات في " + q("LAW-GAP")
        + " إلى قرار المؤلف؛ الإلحاق شاهد فقط."
    )
    tail_patch = [
        "*** Begin Patch",
        "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md",
        "@@",
        " " + proposal_anchor,
        "+",
        add_lines(proposal),
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md",
        "@@",
        " LANE-A DONE21 100 452",
        "+",
        add_lines(report),
        "*** End Patch",
        "",
    ]
    (stage / "proposal-report.patch").write_text(
        "\n".join(tail_patch), encoding="utf-8", newline="\n"
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    report = REPORT.read_text(encoding="utf-8")
    ids = re.findall(r"^### بطاقة:.*LANE-A-R22-(\d+)$", reading, re.MULTILINE)
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND22-CHUNK-\d{2}:END -->", reading)
    if len(ids) != CARD_COUNT or len(set(ids)) != CARD_COUNT:
        raise AssertionError(f"عدد بطاقات الجولة المثبتة غير صحيح: {len(ids)}")
    if len(markers) != 10:
        raise AssertionError(f"عدد قطع الجولة المثبتة غير صحيح: {len(markers)}")
    expected_done = f"LANE-A DONE22 {CARD_COUNT} {EXPECTED_LAST_RANK}"
    if expected_done not in report:
        raise AssertionError("خاتمة الجولة الثانية والعشرين مفقودة")
    return {
        "cards": len(ids),
        "chunks": len(markers),
        "first_id": int(ids[0]),
        "last_id": int(ids[-1]),
        "done": expected_done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--selection", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2))
        return 0
    if args.selection:
        selected, meta = load_and_select()
        print(json.dumps(meta, ensure_ascii=False, sort_keys=True))
        for fresh_number, (expanded_rank, source_rank, row) in enumerate(selected, 1):
            print(json.dumps({
                "fresh": fresh_number,
                "expanded_rank": expanded_rank,
                "source_rank": source_rank,
                "branch": row.get("branch"),
                "say": row.get("say"),
                "gloss": row.get("gloss"),
                "best": row.get("best"),
                "overlap": row.get("overlap"),
            }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.stage:
        print(stage_patches())
        return 0
    _cards, records, selection = render_all()
    print(json.dumps({
        **selection,
        "cards": len(records),
        "closures": dict(Counter(record["closure"] for record in records)),
        "verdicts": dict(Counter(record["verdict"] for record in records)),
        "max_bytes": max(record["bytes"] for record in records),
    }, ensure_ascii=False, indent=2))
    if args.records:
        for record in records:
            print(json.dumps(record, ensure_ascii=False, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
