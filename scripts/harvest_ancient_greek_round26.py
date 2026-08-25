#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Render lane A round 26; emit patches only, never commit, ship, or use git.

Continue the Ancient Greek open comparative inventory after OPEN-COMP-01420
with two fixed batches of fifty cards.  Each card either carries all three
proof legs or records an honourable, reason-named non-positive verdict.  Only
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
import harvest_ancient_greek_round25 as R25  # noqa: E402


R20, R19, R18, R17, R16 = R25.R20, R25.R19, R25.R18, R25.R17, R25.R16
READING, REPORT = R25.READING, R25.REPORT
DATE = "2026-08-25"
FIRST_COMPLETION, LAST_COMPLETION = 1421, 1520
EXPECTED_PREVIOUS = 1420
EXPECTED_POOL = 939
REMAINING_AFTER = 839
BATCH_SIZE = 50
CARD_COUNT = 100
CHUNK_SIZE = 2
BATCHES = ((1421, 1470), (1471, 1520))
EXPECTED_STRICT = Counter({3: 100})
EXPECTED_TOKENS = Counter({3: 58, 4: 42})
EXPECTED_CATEGORIES = Counter({"LEXICAL": 91, "NONLEXICAL": 4, "FUNCTION": 5})
EXPECTED_VERDICTS = Counter({"OPEN-CANDIDATE": 100})
FIRST_MEMBER = "kaikki_ancient_greek:9076:en-δᾶμος-grc-noun-VfAgB4-4"
LAST_MEMBER = "kaikki_ancient_greek:39113:en-ἀκούσιος-grc-noun-gnmEcBUh"
EXPECTED_SURFACE_GROUPS = {"ὅππως": 2, "κλαίουσ'": 2, "ξεῖνος": 2}
EXPECTED_FAMILY_GROUPS = {
    "ancient_greek:family:4dd471ea55270e2cdcdbba55": 2,
    "ancient_greek:family:70413a23a4f96fc4b585d44d": 3,
    "ancient_greek:family:4757689d7bc11a97bc39bee0": 2,
    "ancient_greek:family:21934f5a7e61fea658ce2910": 2,
    "ancient_greek:family:18d48f33f8f85f48571704e0": 2,
    "ancient_greek:family:7b38ba58b1f3fdb45059849f": 2,
    "ancient_greek:family:916e4124d9cd953dd9ced0de": 2,
    "ancient_greek:family:a3404872d656cc6c4cf9be5f": 3,
    "ancient_greek:family:83eb39967d46e8c7dac4213d": 2,
    "ancient_greek:family:aa15e9b76b22faf52113831e": 4,
}


# Rebind the historical delegating chain to the fixed round-26 window.  No
# historical script is changed on disk; only this process receives the new
# invariants.
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


def _leg_disposition(record: dict) -> str:
    verdict = record["verdict"]
    if verdict == "OPEN-CANDIDATE":
        if record["source_options"] < 1:
            raise AssertionError(f"حكم مفتوح بلا شاهد مصدري: {record['completion_id']}")
        return "HONOURABLE-REASONED-OPEN"
    if verdict == "SOURCE-GAP":
        return "HONOURABLE-REASONED-SOURCE-GAP"
    raise AssertionError(f"حكم غير معالج في ضبط الأرجل: {verdict}")


def render_all(*, allow_installed: bool = False) -> tuple[list[str], list[dict], dict]:
    """Render the fixed window and enforce legs, duplicates, and closures."""
    if "LANE-A DONE25 100 LANE-A-OPEN-COMP-01420" not in REPORT.read_text(encoding="utf-8"):
        raise AssertionError("خاتمة DONE25 غير مثبتة")
    reading_text = READING.read_text(encoding="utf-8")
    if "<!-- LANE-A-GREEK-ROUND25-CHUNK-10:END -->" not in reading_text:
        raise AssertionError("الجولة الخامسة والعشرون غير مثبتة")
    if not allow_installed and "<!-- LANE-A-GREEK-ROUND26-BATCH-1:START -->" in reading_text:
        raise AssertionError("بطاقات الجولة السادسة والعشرين موجودة")

    cards, records = R20.render_all()
    expected_ids = [
        f"LANE-A-OPEN-COMP-{number:05d}"
        for number in range(FIRST_COMPLETION, LAST_COMPLETION + 1)
    ]
    if len(cards) != CARD_COUNT or [record["completion_id"] for record in records] != expected_ids:
        raise AssertionError("تغير اتصال نافذة الجولة السادسة والعشرين")
    if len({record["member_id"] for record in records}) != CARD_COUNT:
        raise AssertionError("تكرر معرّف عضو داخل النافذة")
    closures = Counter(record["closure"] for record in records)
    if not set(closures) <= CV.LEGAL or closures != EXPECTED_VERDICTS:
        raise AssertionError(f"خرج حكم عن قاموس الإغلاق المغلق: {closures}")

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
            "الرسم جديد إلى 01420"
            if len(same_surface) == 1 else
            "الرسم في النافذة: " + "، ".join(f"`{item}`" for item in same_surface)
        )
        family_note = (
            "الأسرة منفردة"
            if len(same_family) == 1 else
            "الأسرة في النافذة: " + "، ".join(f"`{item}`" for item in same_family)
        )
        repeat_line = (
            f"- فحص التكرار: العضو فريد؛ {surface_note}؛ {family_note}؛ الصف مستقل بمصدره."
        )
        leg_disposition = _leg_disposition(record)
        card, substitutions = re.subn(
            r"(?m)^(- مرجع (?:بطاقة )?الجرد:.*)$",
            rf"\1\n{repeat_line}",
            card,
            count=1,
        )
        if substitutions != 1:
            raise AssertionError(f"تعذر وسم فحوص البطاقة: {record['completion_id']}")
        card, size = R16.R11.R6.compact_to_limit(card, record["completion_id"])
        if (
            repeat_line not in card
            or f"- عائق: النوع={record['verdict']}؛" not in card
            or f"- حالة الإغلاق: {record['closure']}." not in card
        ):
            raise AssertionError(f"سقط ضبط البطاقة: {record['completion_id']}")
        record["bytes"] = size
        record["surface_window_count"] = len(same_surface)
        record["family_window_count"] = len(same_family)
        record["surface_seen_before"] = False
        record["leg_disposition"] = leg_disposition
        rendered_cards.append(card)

    meta = {
        "open_previous": EXPECTED_PREVIOUS,
        "eligible_before": EXPECTED_POOL,
        "remaining_after": REMAINING_AFTER,
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
    return rendered_cards, records, meta


def _distribution(rows: list[dict], field: str) -> str:
    counts = Counter(row[field] for row in rows)
    return "؛ ".join(f"`{key}`={value}" for key, value in sorted(counts.items()))


def batch_header(batch: int, records: list[dict]) -> list[str]:
    first, last = records[0]["completion_id"], records[-1]["completion_id"]
    return [
        f"<!-- LANE-A-GREEK-ROUND26-BATCH-{batch}:START -->",
        "",
        f"## اليونانية، الجولة السادسة والعشرون: إتمام الجرد المفتوح، الدفعة {batch} ({DATE})",
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
        "<!-- LANE-A-GREEK-ROUND26-REPORT:START -->", "",
        f"## {DATE}، الجولة السادسة والعشرون، إتمام الجرد المفتوح، الدفعة 1", "",
        f"- البطاقات: 50؛ المدى: `{first[0]['completion_id']}` إلى `{first[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(first, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(first, "category") + ".", "",
        f"## {DATE}، الجولة السادسة والعشرون، إتمام الجرد المفتوح، الدفعة 2", "",
        f"- البطاقات: 50؛ المدى: `{second[0]['completion_id']}` إلى `{second[-1]['completion_id']}`.",
        "- توزيع الأحكام: " + _distribution(second, "verdict") + ".",
        "- أصناف الجرد: " + _distribution(second, "category") + ".", "",
        "## حصيلة الجولة السادسة والعشرين", "",
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
        "<!-- LANE-A-GREEK-ROUND26-REPORT:END -->", "",
        f"LANE-A DONE26 {len(records)} {records[-1]['completion_id']}",
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
    stage = Path(tempfile.mkdtemp(prefix="lane-a-round26-"))
    previous_anchor = "<!-- LANE-A-GREEK-ROUND25-CHUNK-10:END -->"
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
                lines += [f"<!-- LANE-A-GREEK-ROUND26-BATCH-{batch}:END -->", ""]
            marker = f"<!-- LANE-A-GREEK-ROUND26-CHUNK-{chunk_number:02d}:END -->"
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
            "LANE-A DONE25 100 LANE-A-OPEN-COMP-01420",
        ),
        encoding="utf-8",
        newline="\n",
    )
    return stage


def verify_installed() -> dict:
    reading = READING.read_text(encoding="utf-8")
    first_marker = "<!-- LANE-A-GREEK-ROUND26-BATCH-1:START -->"
    if first_marker not in reading:
        raise AssertionError("الجولة السادسة والعشرون غير مثبتة")
    section = first_marker + reading.split(first_marker, 1)[1]
    section = section.split("<!-- LANE-A-GREEK-ROUND26-CHUNK-50:END -->", 1)[0]
    ids = [
        int(value)
        for value in re.findall(r"^### LANE-A-OPEN-COMP-(\d{5}):", section, re.MULTILINE)
    ]
    batch_counts = [
        len(re.findall(
            r"^### LANE-A-OPEN-COMP-",
            section.split(f"<!-- LANE-A-GREEK-ROUND26-BATCH-{batch}:START -->", 1)[1]
                   .split(f"<!-- LANE-A-GREEK-ROUND26-BATCH-{batch}:END -->", 1)[0],
            re.MULTILINE,
        ))
        for batch in (1, 2)
    ]
    cards = re.findall(
        r"(?ms)^### LANE-A-OPEN-COMP-.*?(?=^### LANE-A-OPEN-COMP-|^<!-- LANE-A-GREEK-ROUND26-(?:BATCH|CHUNK)-)",
        section,
    )
    expected_cards, _records, _meta = render_all(allow_installed=True)
    exact_cards = sum(
        installed.rstrip() == expected.rstrip()
        for installed, expected in zip(cards, expected_cards, strict=True)
    ) if len(cards) == CARD_COUNT else 0
    markers = re.findall(r"<!-- LANE-A-GREEK-ROUND26-CHUNK-\d{2}:END -->", reading)
    max_bytes = max(len(card.rstrip().encode("utf-8")) + 1 for card in cards)
    repeat_lines = section.count("- فحص التكرار: العضو فريد؛")
    leg_lines = len(re.findall(r"^- عائق: النوع=(?:OPEN-CANDIDATE|SOURCE-GAP)؛", section, re.MULTILINE))
    truncation_markers = len(re.findall(r"tokens truncated|chars truncated|lines truncated", section))
    done = "LANE-A DONE26 100 LANE-A-OPEN-COMP-01520"
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
        or report.count("<!-- LANE-A-GREEK-ROUND26-REPORT:START -->") != 1
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
