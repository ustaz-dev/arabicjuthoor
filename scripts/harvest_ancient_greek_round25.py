#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 25; emit patches only, never commit, ship, or use git.

The ranked ``both`` pool ended at rank 1098 in round 24.  Rank 1099 is
therefore the transition sentinel: this round resumes the still-open Ancient
Greek inventory after OPEN-COMP-01320 and renders two batches of fifty cards.
Every selected member and every repeated surface/family is checked explicitly.
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

import harvest_ancient_greek_round20 as R20  # noqa: E402


R19 = R20.R19
R18 = R19.R18
R17 = R18.R17
R16 = R17.R16
READING, REPORT = R20.READING, R20.REPORT
DATE = "2026-08-25"
FIRST_COMPLETION, LAST_COMPLETION = 1321, 1420
EXPECTED_PREVIOUS = 1320
EXPECTED_POOL = 1_039
REMAINING_AFTER = 939
BATCH_SIZE = 50
CARD_COUNT = 100
BATCHES = ((1321, 1370), (1371, 1420))
EXPECTED_STRICT = Counter({2: 80, 3: 20})
EXPECTED_TOKENS = Counter({2: 76, 3: 23, 4: 1})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 50, "NONLEXICAL": 44, "FUNCTION": 6})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 95, "SOURCE-GAP": 5})
FIRST_MEMBER = "kaikki_ancient_greek:11110:en-αὐτίκ'-grc-adv-A3PdpTCE"
LAST_MEMBER = "kaikki_ancient_greek:34363:en-δέμνι'-grc-noun-muRyaJ69"
EXPECTED_SURFACE_GROUPS = {"-της": 2, "τεός": 2, "-τας": 2}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:3311cba893578746d2dd14a4": 2,
    "ancient_greek:family:36c9c69aaa30e74f19debdab": 3,
    "ancient_greek:family:5ece169afadf2b7ecdbfb926": 2,
    "ancient_greek:family:b188b7c6564b8ddfd1902f5d": 2,
}


# Bind every delegating layer to the new fixed window.  Historical scripts are
# unchanged on disk; only this process receives round-25 invariants.
for module in (R20, R19, R18, R17):
    module.FIRST_COMPLETION = FIRST_COMPLETION
    module.LAST_COMPLETION = LAST_COMPLETION
    module.EXPECTED_PREVIOUS = EXPECTED_PREVIOUS
    module.EXPECTED_POOL = EXPECTED_POOL
    module.BATCH_SIZE = BATCH_SIZE
    module.BATCHES = BATCHES
    module.EXPECTED_STRICT = EXPECTED_STRICT
    module.EXPECTED_TOKENS = EXPECTED_TOKENS
    module.EXPECTED_CATEGORIES = EXPECTED_CATEGORIES
    module.EXPECTED_VERDICTS = EXPECTED_VERDICTS
    module.FIRST_MEMBER = FIRST_MEMBER
    module.LAST_MEMBER = LAST_MEMBER
R16.DATE = DATE


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


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed window and add an explicit duplicate audit per card."""
    if "LANE-A DONE24 102 1098" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE24 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND24-CHUNK-12:END -->" not in reading_text:
        raise AssertionError("الجولة الرابعة والعشرون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND25-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الخامسة والعشرين موجودة")

    cards, records = R20.render_all()
    expected_ids = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if len(cards) != CARD_COUNT or [record["completion_id"] for record in records] != expected_ids:
        raise AssertionError("تغير اتصال نافذة الجولة الخامسة والعشرين")
    if len({record["member_id"] for record in records}) != CARD_COUNT:
        raise AssertionError("تكرر معرّف عضو داخل النافذة")

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

    rendered_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        same_surface = surfaces[record["word"]]
        same_family = families[record["family_id"]]
        surface_note = (
            "لا تكرار رسم داخل النافذة ولا في الإتمامات 00001–01320"
            if len(same_surface) == 1 else
            "تكرر الرسم في النافذة عند " + "، ".join(f"`{item}`" for item in same_surface)
        )
        family_note = (
            "الأسرة منفردة في النافذة"
            if len(same_family) == 1 else
            "تكررت الأسرة عند " + "، ".join(f"`{item}`" for item in same_family)
        )
        repeat_line = (
            f"- فحص التكرار: معرّف العضو فريد؛ {surface_note}؛ {family_note}؛ "
            "أُبقي كل صف لأنه عضو جرد مستقل بموضع مصدر مثبت."
        )
        card, substitutions = re.subn(
            r"(?m)^(- مرجع (?:بطاقة )?الجرد:.*)$",
            rf"\1\n{repeat_line}",
            card,
            count=1,
        )
        if substitutions != 1:
            raise AssertionError(f"تعذر وسم فحص التكرار: {record['completion_id']}")
        card, size = R16.R11.R6.compact_to_limit(card, record["completion_id"])
        if repeat_line not in card:
            raise AssertionError(f"سقط سطر فحص التكرار: {record['completion_id']}")
        record["bytes"] = size
        record["surface_window_count"] = len(same_surface)
        record["family_window_count"] = len(same_family)
        record["surface_seen_before"] = False
        rendered_cards.append(card)

    meta = {
        "both_pool": 1_098,
        "requested_rank": 1_099,
        "transitioned": True,
        "open_previous": EXPECTED_PREVIOUS,
        "eligible_before": EXPECTED_POOL,
        "remaining_after": REMAINING_AFTER,
        "unique_members": len({record["member_id"] for record in records}),
        "prior_surface_rows": prior_surface_rows,
        "surface_duplicate_rows": sum(len(value) - 1 for value in surfaces.values()),
        "surface_duplicate_groups": surface_groups,
        "family_duplicate_rows": sum(len(value) - 1 for value in families.values()),
        "family_duplicate_groups": family_groups,
    }
    return rendered_cards, records, meta


def _distribution(rows: list[dict], field: str) -> str:
    counts = Counter(row[field] for row in rows)
    return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))


def batch_header(batch: int, records: list[dict]) -> list[str]:
    first, last = records[0]["completion_id"], records[-1]["completion_id"]
    lines = [
        f"<!-- LANE-A-GREEK-ROUND25-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة الخامسة والعشرون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
        "",
    ]
    if batch == 1:
        lines += [
            "- انتقال الجولة: انتهى حوض `both` ذو 1098 صفا عند الرتبة 1098 في الجولة الرابعة والعشرين؛ الرتبة المطلوبة 1099 خارج الحوض، فانتقل العمل إلى الجرد المفتوح من آخر موضع مثبت `LANE-A-OPEN-COMP-01320`.",
        ]
    lines += [
        f"- المواصلة متصلة من `{first}` إلى `{last}`؛ 50 بطاقة؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        "- فُحص تكرار معرّف العضو والرسم والأسرة في الذاكرة وفي النافذة؛ لم يسقط صف مستقل لمجرد اتحاد الرسم أو الأسرة.",
        "- قرئت طبقتا الجذر والنواة في عرض واحد لكل عضو؛ لا صلة بلا شاهدين عربيين قديمين، ولا صف صوتيا مخترعا.",
        "",
    ]
    return lines


def report_addition(records: list[dict], meta: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])
    source_gap_words = "، ".join(
        f"`{record['word']}`" for record in records if record["verdict"] == "SOURCE-GAP"
    )
    surface_groups = "؛ ".join(
        f"`{word}`={count}" for word, count in meta["surface_duplicate_groups"].items()
    )
    family_groups = "؛ ".join(
        f"`{family}`={count}" for family, count in meta["family_duplicate_groups"].items()
    )
    root_total = sum(record["roots"] for record in records)
    nucleus_total = sum(record["nuclei"] for record in records)
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND25-REPORT:START -->", "",
        f"## {DATE}، الجولة الخامسة والعشرون، إتمام الجرد المفتوح، الدفعة 1", "",
        f"- البطاقات: 50؛ المدى: `{first[0]['completion_id']}` إلى `{first[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(first, "category") + ".", "",
        f"## {DATE}، الجولة الخامسة والعشرون، إتمام الجرد المفتوح، الدفعة 2", "",
        f"- البطاقات: 50؛ المدى: `{second[0]['completion_id']}` إلى `{second[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(second, "category") + ".", "",
        "## حصيلة الجولة الخامسة والعشرين", "",
        "- الانتقال: حوض `both` ذو 1098 صفا منته عند الرتبة 1098؛ لا صف للرتبة 1099، لذلك انتقلت الجولة مباشرة من `LANE-A DONE24 102 1098` إلى الجرد المفتوح بعد `LANE-A-OPEN-COMP-01320`.",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        f"- معيار الجرد: أول 100 عضو باق بعد الإتمامات {EXPECTED_PREVIOUS} من `TWO-LAYER-OPEN` ذي مرشح في طبقة على الأقل؛ كان الحوض المفتوح المؤهل {EXPECTED_POOL} عضوا وبقي بعد النافذة {REMAINING_AFTER}.",
        f"- فحص التكرار: معرّفات الأعضاء الفريدة={meta['unique_members']}؛ صورة سبق إتمامها={meta['prior_surface_rows']}؛ تكرار الرسم الزائد داخل النافذة={meta['surface_duplicate_rows']} في المجموعات {surface_groups}.",
        f"- فحص الأسرة: تكرار الصفوف الزائد={meta['family_duplicate_rows']} في المجموعات {family_groups}؛ حفظت الصفوف لأنها أعضاء مستقلة بمواضع مصدر مختلفة.",
        "- الأحكام الكلية: " + _distribution(records, "verdict") + "؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- الطبقتان: مجموع مرشحي الجذر={root_total}؛ مجموع مرشحي النواة={nucleus_total}؛ كل بطاقة سمت عددي الطبقتين وقرأتهما معا.",
        f"- بوابة المصدر: بطاقات `SOURCE-GAP` الخمس هي {source_gap_words}؛ بقيت مفتوحة ولم يصنع غياب المصدر صلة.",
        "- أصناف النافذة: " + _distribution(records, "category") + ".",
        "- ضبط الهيكل الصارم: " + _distribution(records, "strict_length") + "؛ صوامت `tokens_json`: " + _distribution(records, "token_length") + ".",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: اتصال المعرفات؛ مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ فحص التكرار، من غير تشغيل git.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.", "",
        "<!-- LANE-A-GREEK-ROUND25-REPORT:END -->", "",
        f"LANE-A DONE25 {len(records)} {records[-1]['completion_id']}",
    ])


def _add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def _anchored_patch(path: Path, fragment: str, anchor: str) -> str:
    """Build a bounded patch after an existing (or earlier staged) anchor."""
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {path.relative_to(ROOT).as_posix()}",
        "@@",
        f" {anchor}",
        "+",
        _add_lines(fragment.rstrip()),
        "*** End Patch",
        "",
    ])


def stage_patches() -> Path:
    cards, records, meta = render_all()
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round25-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND24-CHUNK-12:END -->"
    chunk_number = 0
    for batch in (1, 2):
        batch_cards = cards[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        batch_records = records[(batch - 1) * BATCH_SIZE:batch * BATCH_SIZE]
        for offset in range(0, BATCH_SIZE, 10):
            chunk_number += 1
            lines: list[str] = []
            if offset == 0:
                lines += batch_header(batch, batch_records)
            for card in batch_cards[offset:offset + 10]:
                lines += [card, ""]
            if offset + 10 == BATCH_SIZE:
                lines += [f"<!-- LANE-A-GREEK-ROUND25-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND25-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = _anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker

    report_patch = _anchored_patch(
        REPORT,
        report_addition(records, meta),
        "LANE-A DONE24 102 1098",
    )
    (stage / "report.patch").write_text(report_patch, encoding="utf-8", newline="\n")
    return stage


def _remove_patch(path: Path, block: str) -> str:
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {path.relative_to(ROOT).as_posix()}",
        "@@",
        *("-" + line for line in block.rstrip("\n").splitlines()),
        "*** End Patch",
        "",
    ])


def _before_line_patch(path: Path, fragment: str, next_line: str) -> str:
    return "\n".join([
        "*** Begin Patch",
        f"*** Update File: {path.relative_to(ROOT).as_posix()}",
        "@@",
        _add_lines(fragment.rstrip()),
        "+",
        " " + next_line,
        "*** End Patch",
        "",
    ])


def stage_repair_patches() -> Path:
    """Replace any transport-truncated card spans with small canonical patches."""
    cards, records, _meta = render_all(allow_installed=True)
    canonical = {
        int(record["completion_id"].rsplit("-", 1)[1]): card
        for card, record in zip(cards, records, strict=True)
    }
    spans = (
        (1324, 1326, 1327),
        (1335, 1336, 1337),
        (1345, 1346, 1347),
        (1355, 1356, 1357),
        (1365, 1366, 1367),
        (1374, 1376, 1377),
        (1385, 1386, 1387),
        (1395, 1396, 1397),
        (1405, 1406, 1407),
        (1415, 1416, 1417),
    )
    current = READING.read_text(encoding="utf-8")
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round25-repair-"))
    for index, (first, last, next_id) in enumerate(spans, 1):
        start_pattern = rf"^### LANE-A-OPEN-COMP-{first:05d}:.*$"
        next_pattern = rf"^### LANE-A-OPEN-COMP-{next_id:05d}:.*$"
        start_match = re.search(start_pattern, current, re.MULTILINE)
        next_match = re.search(next_pattern, current, re.MULTILINE)
        if start_match is None or next_match is None or start_match.start() >= next_match.start():
            raise AssertionError(f"تعذر تحديد span الإصلاح {first}..{last}")
        block = current[start_match.start():next_match.start()]
        if not re.search(r"tokens truncated|chars truncated|lines truncated", block):
            raise AssertionError(f"span الإصلاح بلا اقتطاع: {first}..{last}")
        (stage / f"remove-{index:02d}.patch").write_text(
            _remove_patch(READING, block), encoding="utf-8", newline="\n"
        )
        next_line = next_match.group(0)
        for number in range(first, last + 1):
            (stage / f"insert-{number:05d}.patch").write_text(
                _before_line_patch(READING, canonical[number], next_line),
                encoding="utf-8",
                newline="\n",
            )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND25-BATCH-1:START -->" not in reading:
        raise AssertionError("الجولة الخامسة والعشرون غير مثبتة")
    first_marker = "<!-- LANE-A-GREEK-ROUND25-BATCH-1:START -->"
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND25-CHUNK-10:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND25-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND25-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND25-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, _expected_records, _expected_meta = render_all(allow_installed=True)
    exact_cards = 0
    for number, expected_card in zip(
        range(FIRST_COMPLETION, LAST_COMPLETION + 1), expected_cards, strict=True
    ):
        completion_id = f"LANE-A-OPEN-COMP-{number:05d}"
        match = re.search(
            rf"(?ms)^### {re.escape(completion_id)}:.*?"
            rf"^- سطر الإتمام \([^\n]*{re.escape(completion_id)}\):[^\n]*\n"
            rf"^- ملاحظات:[^\n]*$",
            section,
        )
        if match is not None and match.group(0).rstrip() == expected_card.rstrip():
            exact_cards += 1
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND25-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: معرّف العضو فريد؛")
    transition_lines = section.count("- انتقال الجولة: انتهى حوض `both` ذو 1098 صفا")
    truncation_markers = len(re.findall(r"tokens truncated|chars truncated|lines truncated", section))
    done = f"LANE-A DONE25 {CARD_COUNT} LANE-A-OPEN-COMP-{LAST_COMPLETION:05d}"
    expected_ids = list(range(FIRST_COMPLETION, LAST_COMPLETION + 1))
    report = REPORT.read_text(encoding="utf-8")
    if (
        ids != expected_ids
        or batch_counts != [BATCH_SIZE, BATCH_SIZE]
        or len(cards) != CARD_COUNT
        or exact_cards != CARD_COUNT
        or len(markers) != 10
        or max_bytes > 5_120
        or repeat_lines != CARD_COUNT
        or transition_lines != 1
        or truncation_markers
        or done not in report
        or report.count("<!-- LANE-A-GREEK-ROUND25-REPORT:START -->") != 1
    ):
        raise AssertionError(
            f"فشل التحقق: ids={len(ids)} batches={batch_counts} cards={len(cards)} "
            f"exact={exact_cards} chunks={len(markers)} max={max_bytes} repeats={repeat_lines} "
            f"transition={transition_lines} truncation={truncation_markers} done={done in report}"
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
        "transition_lines": transition_lines,
        "truncation_markers": truncation_markers,
        "done": done,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--stage", action="store_true")
    parser.add_argument("--repair-stage", action="store_true")
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
    if args.repair_stage:
        print(stage_repair_patches())
        return 0
    _cards, records, meta = render_all()
    print(json.dumps({
        **meta,
        "cards": len(records),
        "closures": dict(Counter(record["closure"] for record in records)),
        "verdicts": dict(Counter(record["verdict"] for record in records)),
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
