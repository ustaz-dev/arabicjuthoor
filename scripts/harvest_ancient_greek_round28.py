#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 28; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative inventory after OPEN-COMP-01620
with two fixed batches of fifty cards. Each card either carries all three
proof legs or records an honourable, reason-named non-positive verdict. Only
the repository's closed closure vocabulary is permitted.
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

import check_closure_vocabulary as CV  # noqa: E402
import harvest_ancient_greek_round27 as R27  # noqa: E402


R26, R25 = R27.R26, R27.R25
R20, R19, R18, R17, R16 = R27.R20, R27.R19, R27.R18, R27.R17, R27.R16
READING, REPORT = R27.READING, R27.REPORT
DATE = "2026-08-26"
FIRST_COMPLETION, LAST_COMPLETION = 1621, 1720
EXPECTED_PREVIOUS = 1620
EXPECTED_POOL = 739
REMAINING_AFTER = 639
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
BATCHES = ((1621, 1670), (1671, 1720))
EXPECTED_STRICT = Counter({3: 100})
EXPECTED_TOKENS = Counter({3: 93, 4: 7})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 82, "NONLEXICAL": 11, "FUNCTION": 7})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:11272:en-νύττω-grc-verb-oFKay8rK"
LAST_MEMBER = "kaikki_ancient_greek:42138:en-εἰαρινός-grc-adj-avx3JbPg"
EXPECTED_SURFACE_GROUPS = {"παρέξ": 2, "πάροιθε": 2, "πάροιθ'": 2}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:f8c3140f1c687a02ade21ab4": 3,
    "ancient_greek:family:cd8e161732087298f0414c6f": 2,
    "ancient_greek:family:66bbe842742f77dfe866251d": 2,
    "ancient_greek:family:ed603b45a5225eb967c1997f": 2,
    "ancient_greek:family:1be97555129f3d5fe1d3bb8f": 2,
    "ancient_greek:family:a797dcb982f5bcf67266006a": 2,
    "ancient_greek:family:efe0c7d58d6db0491a34e6df": 3,
    "ancient_greek:family:779a42449795098b1e4408b3": 3,
    "ancient_greek:family:13e587835ce3d15bca1f9706": 3,
    "ancient_greek:family:5b690fa0ab3460d450a28e0e": 2,
    "ancient_greek:family:0113474e4392686641e3e8ac": 2,
    "ancient_greek:family:4d65b1f6363d3a3fd140dbc2": 2,
    "ancient_greek:family:a9cc5759482e799f05e25065": 2,
    "ancient_greek:family:73f24eef403c7aa56cead68f": 2,
}


# Rebind the historical delegating chain to the fixed round-28 window. No
# historical script is changed on disk; only this process receives the new
# invariants.
for module in (R27, R26, R25, R20, R19, R18, R17):
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
R27.REMAINING_AFTER = REMAINING_AFTER
R27.EXPECTED_SURFACE_GROUPS = EXPECTED_SURFACE_GROUPS
R27.EXPECTED_FAMILY_GROUPS = EXPECTED_FAMILY_GROUPS
R26.REMAINING_AFTER = REMAINING_AFTER
R26.EXPECTED_SURFACE_GROUPS = EXPECTED_SURFACE_GROUPS
R26.EXPECTED_FAMILY_GROUPS = EXPECTED_FAMILY_GROUPS
R16.DATE = DATE


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed window and enforce legs, duplicates, and closures."""
    if "LANE-A DONE27 100 LANE-A-OPEN-COMP-01620" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE27 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND27-CHUNK-50:END -->" not in reading_text:
        raise AssertionError("الجولة السابعة والعشرون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND28-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة الثامنة والعشرين موجودة")

    cards, records, meta = R27.render_all(allow_installed=True)
    rendered_cards: list[str] = []
    for card, record in zip(cards, records, strict=True):
        card = card.replace("الرسم جديد إلى 01520", "الرسم جديد إلى 01620")
        if "الرسم جديد إلى 01520" in card:
            raise AssertionError(f"بقي مرجع نافذة قديم: {record['completion_id']}")
        rendered_cards.append(card)
    closures = Counter(record["closure"] for record in records)
    if not set(closures) <= CV.LEGAL or closures != EXPECTED_VERDICTS:
        raise AssertionError(f"خرج حكم عن قاموس الإغلاق المغلق: {closures}")
    return rendered_cards, records, meta


def _distribution(rows: list[dict], field: str) -> str:
    counts = Counter(row[field] for row in rows)
    return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))


def batch_header(batch: int, records: list[dict]) -> list[str]:
    first, last = records[0]["completion_id"], records[-1]["completion_id"]
    return [
        f"<!-- LANE-A-GREEK-ROUND28-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة الثامنة والعشرون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
        "",
        f"- المواصلة متصلة من `{first}` إلى `{last}`؛ 50 بطاقة؛ المصدر سجل التغطية الشامل؛ الترتيب بطول الهيكل الصارم ثم موضع الجرد المثبت.",
        "- فُحص تكرار معرّف العضو والرسم والأسرة في الذاكرة وفي النافذة؛ لم يسقط صف مستقل لمجرد اتحاد الرسم أو الأسرة.",
        "- لا موجب إلا بأرجل الصوت والحدث والمعنى كاملة؛ وما لم يكتمل حمل حكما شريفا مسمى السبب من قاموس الإغلاق المغلق.",
        "",
    ]


def report_addition(records: list[dict], meta: dict) -> str:
    first, second = records[:BATCH_SIZE], records[BATCH_SIZE:]
    maximum = max(records, key=lambda record: record["bytes"])
    surface_groups = "؛ ".join(
        f"`{word}`={count}" for word, count in meta["surface_duplicate_groups"].items()
    )
    family_groups = "؛ ".join(
        f"`{family}`={count}" for family, count in meta["family_duplicate_groups"].items()
    )
    root_total = sum(record["roots"] for record in records)
    nucleus_total = sum(record["nuclei"] for record in records)
    option_total = sum(record["source_options"] for record in records)
    return "\n".join([
        "<!-- LANE-A-GREEK-ROUND28-REPORT:START -->", "",
        f"## {DATE}، الجولة الثامنة والعشرون، إتمام الجرد المفتوح، الدفعة 1", "",
        f"- البطاقات: 50؛ المدى: `{first[0]['completion_id']}` إلى `{first[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(first, "category") + ".", "",
        f"## {DATE}، الجولة الثامنة والعشرون، إتمام الجرد المفتوح، الدفعة 2", "",
        f"- البطاقات: 50؛ المدى: `{second[0]['completion_id']}` إلى `{second[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(second, "category") + ".", "",
        "## حصيلة الجولة الثامنة والعشرين", "",
        "- مجموع البطاقات المكتوبة: 100؛ دفعتان من 50 بطاقة.",
        f"- معيار الجرد: أول 100 عضو باق بعد الإتمامات {EXPECTED_PREVIOUS} من `TWO-LAYER-OPEN` ذي مرشح في طبقة على الأقل؛ كان الحوض المفتوح المؤهل {EXPECTED_POOL} عضوا وبقي بعد النافذة {REMAINING_AFTER}.",
        f"- فحص التكرار: معرّفات الأعضاء الفريدة={meta['unique_members']}؛ صورة سبق إتمامها={meta['prior_surface_rows']}؛ تكرار الرسم الزائد داخل النافذة={meta['surface_duplicate_rows']} في المجموعات {surface_groups}.",
        f"- فحص الأسرة: تكرار الصفوف الزائد={meta['family_duplicate_rows']} في المجموعات {family_groups}؛ حفظت الصفوف لأنها أعضاء مستقلة بمواضع مصدر مختلفة.",
        "- الأحكام الكلية: " + _distribution(records, "verdict") + "؛ لا صلة موجبة جديدة ولا نفي من ترتيب الاسترداد.",
        f"- ضبط الأرجل الثلاث: موجب مكتمل=0؛ حكم شريف مسمى السبب={meta['honourable_reasoned']}؛ جميعها `OPEN-CANDIDATE` لغياب مدار بشري محدود، لا لوسم مخترع.",
        f"- الطبقتان: مجموع مرشحي الجذر={root_total}؛ مجموع مرشحي النواة={nucleus_total}؛ خيارات الشاهد ذي المصدرين={option_total}؛ كل بطاقة قرأت الطبقتين معا.",
        "- قاموس الإغلاق: استعمل `OPEN-CANDIDATE` وحده، وهو من القاموس المغلق المقرر؛ لم يولد وسم جديد.",
        "- أصناف النافذة: " + _distribution(records, "category") + ".",
        "- ضبط الهيكل الصارم: " + _distribution(records, "strict_length") + "؛ صوامت `tokens_json`: " + _distribution(records, "token_length") + ".",
        f"- حد الحجم: أكبر بطاقة {maximum['bytes']} بايت، `{maximum['completion_id']}`؛ لا بطاقة تتجاوز 5 كيلوبايت.",
        "- فحص انضباط النواة: بقي الاسترجاع والحكم مفصولين؛ لم تضف الجولة ROOT-TRACE أو NUCLEUS-TRACE ولم تغير مخزون النوى المجمد.",
        "- الفحوص النظيفة: اتصال المعرفات؛ مطابقة النص المولد؛ نقاء الشحنة؛ قاموس الإغلاق؛ خط الاسترداد؛ الأرجل؛ التكرار، من غير تشغيل git.",
        "- الإيداع والشحن: لم يشغل `scripts/ship.py`، ولم يستعمل git إطلاقا.",
        f"- آخر موضع: `{records[-1]['completion_id']}`، `{records[-1]['word']}` /{records[-1]['read']}/.", "",
        "<!-- LANE-A-GREEK-ROUND28-REPORT:END -->", "",
        f"LANE-A DONE28 {len(records)} {records[-1]['completion_id']}",
    ])


def _add_lines(value: str) -> str:
    return "\n".join("+" + line for line in value.splitlines())


def _anchored_patch(path: Path, fragment: str, anchor: str) -> str:
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
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round28-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND27-CHUNK-50:END -->"
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
                lines += [f"<!-- LANE-A-GREEK-ROUND28-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND28-CHUNK-{chunk_number:02d}:END -->"
            lines.append(marker)
            patch = _anchored_patch(READING, "\n".join(lines), previous_anchor)
            (stage / f"reading-{chunk_number:02d}.patch").write_text(
                patch, encoding="utf-8", newline="\n"
            )
            previous_anchor = marker
    (stage / "report.patch").write_text(
        _anchored_patch(
            REPORT,
            report_addition(records, meta),
            "LANE-A DONE27 100 LANE-A-OPEN-COMP-01620",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND28-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة الثامنة والعشرون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND28-CHUNK-50:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND28-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND28-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND28-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, _records, _meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND28-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE))
    truncation_markers = len(re.findall(r"tokens truncated|chars truncated|lines truncated", section))
    done = "LANE-A DONE28 100 LANE-A-OPEN-COMP-01720"
    report = REPORT.read_text(encoding="utf-8")
    if (
        ids != list(range(FIRST_COMPLETION, LAST_COMPLETION + 1))
        or batch_counts != [BATCH_SIZE, BATCH_SIZE]
        or len(cards) != CARD_COUNT
        or exact_cards != CARD_COUNT
        or len(markers) != 50
        or max_bytes > 5_120
        or repeat_lines != CARD_COUNT
        or leg_lines != CARD_COUNT
        or truncation_markers
        or report.count(done) != 1
        or report.count("<!-- LANE-A-GREEK-ROUND28-REPORT:START -->") != 1
    ):
        raise AssertionError(
            f"فشل التحقق: ids={len(ids)} batches={batch_counts} cards={len(cards)} "
            f"exact={exact_cards} chunks={len(markers)} max={max_bytes} repeats={repeat_lines} "
            f"legs={leg_lines} truncation={truncation_markers} done={report.count(done)}"
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
        "truncation_markers": truncation_markers,
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
