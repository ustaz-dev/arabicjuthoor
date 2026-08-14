# -*- coding: utf-8 -*-
"""أعد حصاد صفوف «البرهان» المستردة وحدها، بدفعات ثابتة من 150.

يستعمل هذا المسار بطاقة خشيم المصرية نفسها بعد تصحيح بوابتها إلى الأرجل
الثلاث: مسار الصوت المسمى، و``frozen_event.resolve``، ومعنى بدج مع مدار
مكتوب يدويًا. المروحة أداة بحث داخل مسار الصوت وليست رجلًا رابعة. ولا ينشئ
هذا السكربت مدارًا؛ يأخذ المدارات المسماة حرفيًا من ``HUMAN_ORBITS`` فقط.
"""
from __future__ import annotations

import argparse
import json
import pathlib
import re
import sys
from collections import Counter
from typing import Any

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import build_khashim_egyptian_cards as B  # noqa: E402
import frozen_event as FE  # noqa: E402

SOURCE = ROOT / "data" / "khashim-pairs.json"
RECOVERIES = ROOT / "data" / "khashim-egyptian-ocr-recoveries.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "egyptian.md"
REPORTS = [ROOT / "data" / f"khashim-egyptian-batch-{n:03d}.json"
           for n in range(1, 5)]
BATCH_SIZE = 150


def replace_card(text: str, marker: str, replacement: str, batch_no: int) -> str:
    end_marker = f"<!-- KHASHIM-EGYPTIAN-BATCH-{batch_no:03d}:END -->"
    pattern = re.compile(
        rf"^### بطاقة:[^\n]*\n{re.escape(marker)}\n.*?"
        rf"(?=^### بطاقة:|^{re.escape(end_marker)})",
        re.MULTILINE | re.DOTALL,
    )
    updated, count = pattern.subn(replacement.rstrip() + "\n\n", text, count=1)
    if count != 1:
        raise SystemExit(f"لم يوجد موضع بطاقة وحيد للعلامة {marker}: {count}")
    return updated


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, required=True)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    sys.stdout.reconfigure(encoding="utf-8")
    if args.batch < 1:
        raise SystemExit("رقم الدفعة يبدأ من 1")

    recovery_payload = json.loads(RECOVERIES.read_text(encoding="utf-8"))
    recovery_by_index = {
        int(row["index"]): row for row in recovery_payload["recoveries"]
    }
    indices = sorted(recovery_by_index)
    total_batches = (len(indices) + BATCH_SIZE - 1) // BATCH_SIZE
    if args.batch > total_batches:
        raise SystemExit(
            f"لا دفعة {args.batch}؛ الصفوف المستردة {len(indices)} في {total_batches} دفعات"
        )
    start = (args.batch - 1) * BATCH_SIZE
    selected_indices = indices[start:start + BATCH_SIZE]

    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    rows = [
        row for row in payload["rows"]
        if row.get("source") == "ocr-egyptian2"
    ]
    if len(rows) != 938:
        raise SystemExit(f"تغير مقام المصرية: {len(rows)}")
    rows, manual_stats = B.apply_ocr_head_recoveries(rows)
    first, second, third, fourth, defects, pool = B.choose_batches(rows)
    pool_by_index = {int(item["index"]): item for item in pool}
    membership: dict[int, int] = {}
    for batch_no, group in enumerate((first, second, third, fourth), start=1):
        for item in group:
            membership[int(item["index"])] = batch_no
    if set(membership) != set(range(938)):
        raise SystemExit("اختلت عضوية الدفعات المصرية الأربع")

    report_payloads = {
        number: json.loads(path.read_text(encoding="utf-8"))
        for number, path in enumerate(REPORTS, start=1)
    }
    reading = READING.read_text(encoding="utf-8")
    rendered_rows: list[dict[str, Any]] = []
    table_rows: list[dict[str, Any]] = []
    tier_counts: Counter[str] = Counter()
    field_counts: Counter[str] = Counter()
    for index in selected_indices:
        item = pool_by_index[index]
        batch_no = membership[index]
        card_text, summary = B.card(item, batch_no)
        marker = f"<!-- khashim-egyptian-batch-{batch_no:03d}:{index} -->"
        reading = replace_card(reading, marker, card_text, batch_no)

        report_rows = report_payloads[batch_no]["rows"]
        positions = [pos for pos, row in enumerate(report_rows)
                     if int(row["index"]) == index]
        if len(positions) != 1:
            raise SystemExit(f"الفهرس {index} ليس صفًا وحيدًا في تقرير {batch_no:03d}")
        report_rows[positions[0]] = summary

        event = FE.resolve(summary["root"])
        tier = str(event.tier) if event else "0"
        tier_counts[tier] += 1
        fields = sorted(recovery_by_index[index]["fields"])
        field_counts.update(fields)
        rendered_rows.append(summary)
        table_rows.append({
            "index": index,
            "book_batch": batch_no,
            "foreign": summary["foreign"],
            "root": summary["root"],
            "restored_fields": fields,
            "frozen_event_tier": int(tier),
            "sound_leg": bool(summary["sound_ready"]),
            "manual_orbit": bool(summary["human_orbit"]),
            "verdict": summary["verdict"],
            "open_reasons": summary["open_reasons"],
        })

    global_scan_reasons: Counter[str] = Counter()
    for item in defects:
        global_scan_reasons.update(item["reasons"])
    for report in report_payloads.values():
        report_rows = report["rows"]
        selection_scan_reasons: Counter[str] = Counter()
        open_reasons: Counter[str] = Counter()
        for row in report_rows:
            selection_scan_reasons.update(row["scan_reasons"])
            open_reasons.update(row["open_reasons"])
        report["ocr_recovery"] = {
            "overlay_rows": len(recovery_by_index),
            "overlay_fields": sum(
                len(recovery["fields"]) for recovery in recovery_by_index.values()
            ),
            "reharvested_through_batch": args.batch,
            "manual_head_recovery_baseline": manual_stats,
        }
        report["scan_defects_union"] = len(defects)
        report["scan_defects_by_reason"] = dict(sorted(global_scan_reasons.items()))
        report["selection_scan_reasons"] = dict(sorted(selection_scan_reasons.items()))
        report["cards_written"] = len(report_rows)
        report["chosen_in_corrected_fan"] = sum(
            row["root_in_raw_fan"] or row["root_in_stem_fan"] for row in report_rows
        )
        report["positive"] = sum(bool(row["verdict"]) for row in report_rows)
        report["open_candidate"] = sum(
            row["closure"] == "OPEN-CANDIDATE" for row in report_rows
        )
        report["open_reasons_overlapping"] = dict(sorted(open_reasons.items()))

    positives = sum(bool(row["verdict"]) for row in rendered_rows)
    sound_ready = sum(bool(row["sound_ready"]) for row in rendered_rows)
    event_ready = sum(bool(row["frozen_event"]) for row in rendered_rows)
    manual_orbits = sum(bool(row["human_orbit"]) for row in rendered_rows)
    batch_payload = {
        "schema": "khashim-egyptian-ocr-recovery-batch-v1",
        "generated_by": "scripts/build_khashim_egyptian_ocr_recovery_batches.py",
        "batch": args.batch,
        "batch_size": BATCH_SIZE,
        "total_recovered_rows": len(indices),
        "total_batches": total_batches,
        "slice": [start, start + len(selected_indices) - 1],
        "rows": table_rows,
        "counts": {
            "rows": len(rendered_rows),
            "restored_fields": dict(sorted(field_counts.items())),
            "frozen_event_tiers": dict(sorted(tier_counts.items())),
            "sound_leg_ready": sound_ready,
            "frozen_event_leg_ready": event_ready,
            "manual_orbit_present": manual_orbits,
            "positive_verdicts": positives,
            "open_verdicts": len(rendered_rows) - positives,
        },
        "manual_head_recovery_baseline": manual_stats,
        "contract": (
            "ثلاث أرجل فقط: مسار الصوت المسمى؛ frozen_event.resolve؛ معنى بدج "
            "مع مدار يدوي. لا يولد السكربت مدارًا"
        ),
    }
    out = ROOT / "data" / f"khashim-egyptian-ocr-recovery-batch-{args.batch:03d}.json"
    audit = ROOT / "05-audits" / (
        f"2026-08-14-khashim-proof-ocr-recovery-harvest-batch-{args.batch:03d}.md"
    )
    audit_lines = [
        f"# محضر إعادة حصاد «البرهان»، دفعة الاسترداد {args.batch:03d}",
        "",
        "**التاريخ:** 2026-08-14  ",
        f"**المقام:** {len(rendered_rows)} صفًا مستردًا وحده من أصل {len(indices)}؛ "
        f"الحجم الثابت 150، وهذه الدفعة {args.batch} من {total_batches}.",
        "",
        "## العقد",
        "",
        "الأرجل ثلاث لا رابعة لها: مسار صوت مسمى، ثم حدث من "
        "`frozen_event.resolve`، ثم معنى بدج مع مدار كتبه القارئ بيده. المروحة "
        "تعين البحث الصوتي ولا تنشئ رجلًا. لم يولد السكربت مدارًا واحدًا؛ المدار "
        "إما عضو مسمى سابق في `HUMAN_ORBITS` وإما غائب والحكم مفتوح.",
        "",
        "## الحصيلة",
        "",
        f"- الصفوف: **{len(rendered_rows)}**.",
        f"- حقول legacy المستردة: **{sum(field_counts.values())}**: "
        + "، ".join(f"{key}={value}" for key, value in sorted(field_counts.items())) + ".",
        f"- الرجل الصوتية مكتملة: **{sound_ready}**.",
        f"- حدث frozen_event موجود: **{event_ready}**.",
        f"- مدار يدوي موجود: **{manual_orbits}**.",
        f"- الأحكام الموجبة: **{positives}**؛ المفتوحة: **{len(rendered_rows) - positives}**.",
        f"- درجات الحدث: " + "، ".join(
            f"{key}={value}" for key, value in sorted(tier_counts.items())) + ".",
        "",
        "## الصفوف",
        "",
        "| الفهرس | دفعة الكتاب | الرأس | الجذر | الحقول المستردة | درجة الحدث | الصوت | المدار | الحكم |",
        "|---:|---:|---|---|---|---:|---|---|---|",
    ]
    for row in table_rows:
        audit_lines.append(
            f"| {row['index']} | {row['book_batch']:03d} | `{row['foreign']}` | "
            f"`{row['root']}` | {', '.join(row['restored_fields'])} | "
            f"{row['frozen_event_tier']} | "
            f"{'مكتمل' if row['sound_leg'] else 'مفتوح'} | "
            f"{'مكتوب' if row['manual_orbit'] else 'غير مكتوب'} | "
            f"{row['verdict'] or 'غير صادر'} |"
        )

    print(json.dumps(batch_payload["counts"], ensure_ascii=False, indent=1))
    if args.dry_run:
        return 0
    READING.write_text(reading, encoding="utf-8", newline="\n")
    for number, path in enumerate(REPORTS, start=1):
        path.write_text(json.dumps(report_payloads[number], ensure_ascii=False, indent=1),
                        encoding="utf-8", newline="\n")
    out.write_text(json.dumps(batch_payload, ensure_ascii=False, indent=1),
                   encoding="utf-8", newline="\n")
    audit.write_text("\n".join(audit_lines) + "\n", encoding="utf-8", newline="\n")
    print(f"كتب: {out}")
    print(f"كتب: {audit}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
