#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 24; emit patches only, never commit or ship."""

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

import harvest_ancient_greek_round23 as R23  # noqa: E402


R21 = R23.R21
R2 = R23.R2
SWEEP, READING, PROPOSAL, REPORT = R23.SWEEP, R23.READING, R23.PROPOSAL, R23.REPORT
DATE = "2026-08-24"
EXPECTED_POOL = 1_098
SCAN_FROM = 997
EXPECTED_ROWS = 102
EXPECTED_MEMORY_REPEATS = 36
EXPECTED_FRESH = 66
EXPECTED_SOURCE_DUPLICATES = 0
EXPECTED_FIRST_RANK = 997
EXPECTED_LAST_RANK = 1_098
EXPECTED_FIRST_WORD = "ὅμως"
EXPECTED_LAST_WORD = "ποιήεις"
BATCH_SIZE = 51
CARD_COUNT = 102
Outcome = R23.Outcome


# Every non-open outcome is hand-read against the complete branch homograph
# set and the complete Arabic-root result set. Retrieval weight is not proof.
OUTCOMES: dict[int, Outcome] = {
}


def load_and_select() -> tuple[list[tuple[int, int, dict]], dict, set[str]]:
    """Select the complete 997..1098 tail and memory-check every exact form."""
    reading_text = R21.nfc(READING.read_text(encoding="utf-8"))
    if "<!-- LANE-A-GREEK-ROUND23-CHUNK-10:END -->" not in reading_text:
        raise AssertionError("الجولة الثالثة والعشرون غير مثبتة")
    if "<!-- LANE-A-GREEK-ROUND24-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الرابعة والعشرين موجودة")
    if "LANE-A DONE23 100 996" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE23 غير مثبتة")

    payload = json.loads(SWEEP.read_text(encoding="utf-8"))
    if payload.get("language") != "ancient_greek":
        raise AssertionError("اختلط لسان الحوض")
    rows = payload.get("both", [])
    if len(rows) != EXPECTED_POOL:
        raise AssertionError(f"تغير مقام الحوض: {len(rows)}")
    ordered = sorted(
        enumerate(rows, 1),
        key=lambda item: (-int(item[1].get("overlap") or 0), item[0]),
    )
    selected = [
        (expanded_rank, source_rank, row)
        for expanded_rank, (source_rank, row) in enumerate(ordered, 1)
        if expanded_rank >= SCAN_FROM
    ]
    words = [R21.nfc(item[2].get("branch")) for item in selected]
    if any(not word for word in words):
        raise AssertionError("صف بلا صورة في ذيل الحوض")
    source_duplicates = len(words) - len(set(words))
    memory_words = {word for word in words if word in reading_text}
    first = selected[0]
    last = selected[-1]
    actual = (
        len(selected), len(memory_words), len(selected) - len(memory_words),
        source_duplicates, first[0], last[0], first[2]["branch"], last[2]["branch"],
    )
    expected = (
        EXPECTED_ROWS, EXPECTED_MEMORY_REPEATS, EXPECTED_FRESH,
        EXPECTED_SOURCE_DUPLICATES, EXPECTED_FIRST_RANK, EXPECTED_LAST_RANK,
        EXPECTED_FIRST_WORD, EXPECTED_LAST_WORD,
    )
    if actual != expected:
        raise AssertionError(f"تغير ذيل الحوض أو ذاكرته: {actual!r}")
    return selected, {
        "pool": len(rows), "scan_from": SCAN_FROM, "rows": len(selected),
        "memory_repeats": len(memory_words), "fresh_rows": len(selected) - len(memory_words),
        "source_duplicates": source_duplicates, "first_rank": first[0], "last_rank": last[0],
    }, memory_words


def gather_hits(selected: list[tuple[int, int, dict]]) -> dict[str, list[dict]]:
    R23.OUTCOMES = OUTCOMES
    return R23.gather_hits(selected)


def build_card(
    expanded_rank: int,
    source_rank: int,
    row: dict,
    hits: dict[str, list[dict]],
    memory_words: set[str],
) -> tuple[str, dict]:
    R23.OUTCOMES = OUTCOMES
    card, record = R23.build_card(expanded_rank, source_rank, row, hits)
    card = card.replace("LANE-A-R23-", "LANE-A-R24-")
    word = R21.nfc(row["branch"])
    memory_line = (
        "- فحص التكرار في الذاكرة: الصورة حاضرة قبل الجولة في سجل القراءة؛ "
        "أعيد فحص صف الرتبة مستقلا، ولم يرث حكم متحد الرسم."
        if word in memory_words else
        "- فحص التكرار في الذاكرة: لا حضور سابق مطابق للصورة قبل الجولة؛ الصف طازج الصورة."
    )
    card, substitutions = re.subn(
        r"(?m)^(- الكلمة في الفرع:.*)$",
        rf"\1\n{memory_line}",
        card,
        count=1,
    )
    if substitutions != 1:
        raise AssertionError(f"تعذر وسم فحص الذاكرة: {expanded_rank}")
    card, size = R21.R6.compact_to_limit(card, f"R24-{expanded_rank}")
    record["bytes"] = size
    record["memory_repeat"] = word in memory_words
    return card, record


def render_all() -> tuple[str, list[dict], dict]:
    selected, selection, memory_words = load_and_select()
    hits = gather_hits(selected)
    sections: list[str] = []
    records: list[dict] = []
    for batch in (1, 2):
        batch_rows = selected[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        sections += [
            f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:START -->", "",
            f"## اليونانية، الجولة الرابعة والعشرون: ذيل الحوض المضاعف، الدفعة {batch} ({DATE})", "",
            f"- النموذج `WO-B-PROBE-001`؛ 51 بطاقة؛ الرتبة الموسعة من {batch_rows[0][0]} إلى {batch_rows[-1][0]}؛ فُحص حضور كل صورة في ذاكرة السجل قبل الجولة.",
            "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع ولا حكم متحد الرسم إلى حكم الصف.", "",
        ]
        for expanded_rank, source_rank, row in batch_rows:
            card, record = build_card(expanded_rank, source_rank, row, hits, memory_words)
            sections += [card, ""]
            records.append(record)
        sections.append(f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:END -->")
        if batch == 1:
            sections.append("")
    if len(records) != CARD_COUNT:
        raise AssertionError(f"عدد بطاقات الجولة: {len(records)}")
    return "\n".join(sections).rstrip(), records, selection


def proposal_addition(records: list[dict]) -> str:
    law = [record for record in records if record["closure"] == "LAW-GAP"]
    if not law:
        return ""
    grouped: dict[str, list[dict]] = {}
    for record in law:
        _licensed, _route, gaps = R2.sound_route(record["word"], record["root"])
        if not gaps:
            raise AssertionError(f"بطاقة LAW-GAP بلا ساق غائبة: {record['expanded_rank']}")
        for gap in dict.fromkeys(gaps):
            grouped.setdefault(gap, []).append(record)
    lines = [
        "## إلحاق شواهد الجولة الرابعة والعشرين، ذيل الحوض المضاعف", "",
        "فُتشت الشبكة النافذة بكل زوج حرفي وبتسميات الحرف اليوناني وبـ«اليونانية/Greek»؛ وحُسبت `BR-GREC-02..06` صفوفا مرخصة. هذه شواهد `LAW-GAP` وحدها؛ لا توصية بإضافة صف.", "",
        "| الساق الغائبة | الشواهد | الشاهد ومقابله | الحكم النافذ |", "|---|---:|---|---|",
    ]
    for gap, rows in grouped.items():
        examples = "؛ ".join(
            f"`{row['word']}`→`{row['root']}` «{OUTCOMES[row['expanded_rank']].counterpart}»"
            for row in rows
        )
        lines.append(f"| `{gap}` | {len(rows)} | {examples} | لا صف مجمد مسمى؛ تبقى البطاقات `LAW-GAP` |")
    lines += ["", "تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط."]
    return "\n".join(lines)


def report_addition(records: list[dict], selection: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]

    def counts(rows: list[dict], field: str) -> str:
        return "؛ ".join(f"`{key}`={value}" for key, value in sorted(Counter(row[field] for row in rows).items()))

    law = [record for record in records if record["closure"] == "LAW-GAP"]
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND24-REPORT:START -->", "",
        f"## {DATE}، الجولة الرابعة والعشرون، ذيل الحوض المضاعف، الدفعة 1", "",
        f"- البطاقات: 51؛ الرتبة الموسعة: {first[0]['expanded_rank']} إلى {first[-1]['expanded_rank']}؛ آخر `overlap`={first[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(first, "verdict") + ".", "- توزيع الإغلاق: " + counts(first, "closure") + ".", "",
        f"## {DATE}، الجولة الرابعة والعشرون، ذيل الحوض المضاعف، الدفعة 2", "",
        f"- البطاقات: 51؛ الرتبة الموسعة: {second[0]['expanded_rank']} إلى {second[-1]['expanded_rank']}؛ آخر `overlap`={second[-1]['overlap']}.",
        "- توزيع الأحكام: " + counts(second, "verdict") + ".", "- توزيع الإغلاق: " + counts(second, "closure") + ".", "",
        "## حصيلة الجولة الرابعة والعشرين", "",
        f"- استؤنف الذيل من الرتبة {selection['scan_from']} إلى {selection['last_rank']} واستُنفد الحوض المضاعف كله.",
        f"- فحص الذاكرة قبل الجولة: حاضر الصورة={selection['memory_repeats']}؛ طازج الصورة={selection['fresh_rows']}؛ تكرار داخل الذيل={selection['source_duplicates']}.",
        "- مجموع البطاقات: 102؛ دفعتان من 51 بطاقة بنموذج `WO-B-PROBE-001`.",
        "- كل صف حاضر الصورة في الذاكرة أعيد فحصه مستقلا ولم يرث حكم متحد الرسم.",
        "- الإغلاق الكلي: " + counts(records, "closure") + ".", "- الحكم الكلي: " + counts(records, "verdict") + ".",
        f"- فجوات القانون: {len(law)}؛ ألحقت شواهدها في `proposed-shift-rows-greek.md` بعد احتساب `BR-GREC-02..06` صفوفا نافذة.",
        f"- حد الحجم: أكبر بطاقة {max(record['bytes'] for record in records)} بايت؛ لا بطاقة تجاوزت 5 كيلوبايت.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.", "",
        "<!-- LANE-A-GREEK-ROUND24-REPORT:END -->", "", f"LANE-A DONE24 {len(records)} {records[-1]['expanded_rank']}",
    ])


def stage_patches() -> Path:
    rendered, records, selection = render_all()
    cards = [
        match.group(0).rstrip()
        for match in re.finditer(
            r"(?ms)^### بطاقة:.*?(?=^### بطاقة:|^<!-- LANE-A-GREEK-ROUND24-BATCH-[12]:END -->)",
            rendered,
        )
    ]
    if len(cards) != CARD_COUNT:
        raise AssertionError(f"تعذر تفكيك البطاقات: {len(cards)}")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round24-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND23-CHUNK-10:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            chunk_cards = batch_cards[offset:offset + 10]
            lines: list[str] = []
            if offset == 0:
                lines += [
                    f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:START -->", "",
                    f"## اليونانية، الجولة الرابعة والعشرون: ذيل الحوض المضاعف، الدفعة {batch} ({DATE})", "",
                    f"- النموذج `WO-B-PROBE-001`؛ 51 بطاقة؛ الرتبة الموسعة من {batch_records[0]['expanded_rank']} إلى {batch_records[-1]['expanded_rank']}؛ فُحص حضور كل صورة في ذاكرة السجل قبل الجولة.",
                    "- الترتيب `overlap` نازل ثابت ثم موضع المصدر؛ قرئت المروحة كاملة، ولم يتحول وزن الاسترجاع ولا حكم متحد الرسم إلى حكم الصف.", "",
                ]
            for card in chunk_cards:
                lines += [card, ""]
            if offset + len(chunk_cards) == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND24-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND24-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = R23.R22.append_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(patch, encoding="utf-8", newline="\n")
            previous_anchor = marker

    proposal = proposal_addition(records)
    tail = ["*** Begin Patch"]
    if proposal:
        tail += [
            "*** Update File: 04-cross-linguistic/proposed-shift-rows-greek.md", "@@",
            " تبقى هذه البطاقات في `LAW-GAP` إلى قرار المؤلف؛ الإلحاق شاهد فقط.", "+",
            R23.R22.add_lines(proposal),
        ]
    tail += [
        "*** Update File: _inbox/lane-reports/2026-08-16-A.md", "@@", " LANE-A DONE23 100 996", "+",
        R23.R22.add_lines(report_addition(records, selection)), "*** End Patch", "",
    ]
    (stage / "proposal-report.patch").write_text("\n".join(tail), encoding="utf-8", newline="\n")
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    ids = [int(value) for value in re.findall(r"^### بطاقة:.*LANE-A-R24-(\d+)$", reading, re.MULTILINE)]
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND24-CHUNK-\d{2}:END -->", reading)
    section = reading.split("<!-- LANE-A-GREEK-ROUND24-BATCH-1:START -->", 1)[-1]
    section = section.split("<!-- LANE-A-GREEK-ROUND24-CHUNK-12:END -->", 1)[0]
    present = section.count("فحص التكرار في الذاكرة: الصورة حاضرة قبل الجولة")
    fresh = section.count("فحص التكرار في الذاكرة: لا حضور سابق مطابق للصورة")
    done = f"LANE-A DONE24 {CARD_COUNT} {EXPECTED_LAST_RANK}"
    expected_ids = list(range(EXPECTED_FIRST_RANK, EXPECTED_LAST_RANK + 1))
    if ids != expected_ids or len(markers) != 12 or present != EXPECTED_MEMORY_REPEATS or fresh != EXPECTED_FRESH or done not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError(
            f"التحقق فشل: بطاقات={len(ids)} قطع={len(markers)} حاضر={present} طازج={fresh}"
        )
    return {
        "cards": len(ids), "chunks": len(markers), "first_id": ids[0], "last_id": ids[-1],
        "memory_repeats": present, "fresh": fresh, "done": done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--verify-installed", action="store_true")
    parser.add_argument("--records", action="store_true")
    parser.add_argument("--selection", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if args.verify_installed:
        print(json.dumps(verify_installed(), ensure_ascii=False, indent=2)); return 0
    if args.selection:
        selected, meta, memory_words = load_and_select()
        print(json.dumps(meta, ensure_ascii=False, indent=2))
        for expanded_rank, source_rank, row in selected:
            print(json.dumps({
                "expanded_rank": expanded_rank, "source_rank": source_rank,
                "branch": row.get("branch"), "say": row.get("say"), "gloss": row.get("gloss"),
                "best": row.get("best"), "overlap": row.get("overlap"),
                "memory_repeat": R21.nfc(row.get("branch")) in memory_words,
                "candidates": list(row.get("candidates_found") or []),
            }, ensure_ascii=False, separators=(",", ":")))
        return 0
    if args.stage:
        print(stage_patches()); return 0
    _rendered, records, selection = render_all()
    print(json.dumps({
        **selection, "cards": len(records),
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
