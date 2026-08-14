#!/usr/bin/env python3
"""ألحق إعادة قراءة عائلات اللسان لدفعة حصاد سابقة."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from pathlib import Path

import harvest_reopened_loans as H


ROOT = Path(__file__).resolve().parents[1]
LANGUAGE = "welsh"
BATCH_SIZE = 150
CORRECTED = {214, 217, 244, 454, 455, 603, 700, 1163, 1166, 1475}


def control_table(controls: list[dict]) -> str:
    return "\n".join(
        f"| `{row['word']}` | `{row['root']}` | {row['closure']} | "
        f"{row['current_verdict']} | {'ثابت' if row['unchanged'] else 'تغيّر'} |"
        for row in controls
    )


def audit_text(
    batch: int,
    rows: list[dict],
    controls: list[dict],
    old_closures: dict[int, str],
) -> str:
    reasons = Counter(row["open_reason"] for row in rows if row["open_reason"])
    reason_ar = {
        "branch_lexicon_context_unresolved": "لم تتعين مدخلة من قاموس الفرع توافق سياق الصف",
        "orbit_not_convincing": "اكتمل الصوت والحدث، وقُرئت شواهد الجذور كاملة، ولم يقنع مدار يدوي",
        "event_unresolved": "اكتمل الصوت ولم يحل السجل حدث المرشح",
        "no_named_sound": "لم يكتمل مسار صوتي مسمى بعد البحث بالحرفين واللسان",
        "fan_empty": "لم تولد المروحة مرشحًا من الهيكل",
    }
    changed = [
        row for row in rows
        if old_closures[int(row["original_index"])] != row["closure"]
    ]
    positives = [row for row in rows if row["positives"]]
    named = [row for row in rows if row["closure"] == "SEMITIC-SOURCE-TRANSMISSION"]
    changes = "\n".join(
        f"{number}. `{row['form']}`: {old_closures[int(row['original_index'])]} ← {row['closure']}"
        for number, row in enumerate(changed, 1)
    ) or "لم يتغير حكم بطاقة."
    pairs = "\n".join(
        f"{number}. `{row['form']}` ↔ `{positive['root']}` ({positive['closure']})"
        for number, (row, positive) in enumerate(
            ((row, positive) for row in positives for positive in row["positives"]),
            1,
        )
    ) or "لم تدخل صلة في هذه الإعادة."
    named_lines = "\n".join(
        f"- `{row['form']}`: {row['closure']}؛ {row['named_closure']['donor']}؛ "
        f"{row['named_closure']['evidence']}."
        for row in named
    ) or "لا إغلاق بمانح سامي في هذه الإعادة."
    reason_lines = "\n".join(
        f"- سبب الفتح: {count} بطاقة، {reason_ar.get(reason, reason)}."
        for reason, count in reasons.items()
    )
    return (
        f"# إعادة قراءة عائلات اللسان للحصاد الويلزي، الدفعة {batch:03d} ({H.DATE})\n\n"
        "## الضابط الإلزامي\n\n"
        "أعيد حساب البطاقات الست الصادرة بالمروحة الحالية وبـ`frozen_event.resolve` وحده، "
        "ولم يتغير حكم واحدة.\n\n"
        "| الصورة | المقابل | السابق | الحالي | النتيجة |\n"
        "|---|---|---|---|---|\n"
        f"{control_table(controls)}\n\n"
        "## سبب الإعادة\n\n"
        "ألحقت 150 بطاقة ناسخة لأن النسخة السابقة سبقت إلزام المسار بطباعة قراءة "
        "عائلات اللسان لكل مرشح اكتمل فيه الصوت والحدث. شُغّل منطق "
        "`search_arabic_root_senses.py` بلا قطع للعرض، وبقي المدار حكمًا يدويًا.\n\n"
        "## الحصيلة\n\n"
        f"- فُحص وكُتب: {len(rows)} بطاقة ناسخة.\n"
        f"- تغير الحكم: {len(changed)} بطاقة.\n"
        f"- موجب بالأرجل الثلاث: {len(positives)} بطاقة.\n"
        f"- أغلق بمانح سامي مسمى: {len(named)} بطاقة.\n"
        f"- بقي OPEN-CANDIDATE: {sum(row['closure'] == 'OPEN-CANDIDATE' for row in rows)} بطاقة.\n"
        f"{reason_lines}\n\n"
        "## تغييرات الحكم\n\n"
        f"{changes}\n\n"
        "## الصلات المثبتة\n\n"
        f"{pairs}\n\n"
        "## الإغلاقات غير النسبية\n\n"
        f"{named_lines}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--batch", type=int, choices=range(1, 9), required=True)
    args = parser.parse_args()
    batch = args.batch
    marker = f"LOAN-HARVEST-WELSH-FAMILY-REREVIEW-BATCH-{batch:03d}"
    reading = ROOT / "04-cross-linguistic" / "readings" / "welsh.md"
    audit = ROOT / "05-audits" / f"{H.DATE}-reopened-loan-welsh-family-rereview-batch-{batch:03d}.md"
    manifest = ROOT / "data" / f"reopened-loan-welsh-family-rereview-batch-{batch:03d}.json"
    text = reading.read_text(encoding="utf-8")
    if f"<!-- {marker}:START -->" in text or audit.exists() or manifest.exists():
        raise AssertionError(f"مخرجات إعادة القراءة {batch} موجودة من قبل")

    all_cards = H.original_cards(LANGUAGE)
    start = (batch - 1) * BATCH_SIZE
    cards = all_cards[start:start + BATCH_SIZE]
    if len(cards) != BATCH_SIZE:
        raise AssertionError(f"دفعة إعادة القراءة ناقصة: {len(cards)}")
    old_manifest = json.loads(
        (ROOT / "data" / f"reopened-loan-welsh-harvest-batch-{batch:03d}.json")
        .read_text(encoding="utf-8")
    )
    old_closures = {
        int(row["original_index"]): str(row["closure"])
        for row in old_manifest["rows"]
    }
    for correction_path in sorted(
        (ROOT / "data").glob("reopened-loan-welsh-harvest-corrections-*.json")
    ):
        correction = json.loads(correction_path.read_text(encoding="utf-8"))
        for row in correction["rows"]:
            old_closures[int(row["original_index"])] = str(row["closure"])

    controls = H.control_run()
    arabic_hits_by_root = H.arabic_hits_for_cards(LANGUAGE, cards)
    rows: list[dict] = []
    blocks: list[str] = []
    for card in cards:
        index = int(card["index"])
        supersedes = (
            f"LH-WELSH-CORR-{index:05d}" if index in CORRECTED
            else f"LH-WELSH-{index:05d}"
        )
        revision = f"LH-WELSH-FAMILY-{index:05d}"
        lines, row, _ = H.build_card(
            LANGUAGE,
            card,
            arabic_hits_by_root,
            orbit_reassessment=True,
            revision_id=revision,
            supersedes_id=supersedes,
            supersedes_marker="LOAN-HARVEST-FAMILY-REREVIEW",
        )
        row["supersedes"] = supersedes
        rows.append(row)
        blocks.extend(lines)

    section = "\n".join([
        f"<!-- {marker}:START -->",
        "",
        f"## إعادة قراءة عائلات اللسان، الدفعة {batch:03d} ({H.DATE})",
        "",
        *blocks,
        f"<!-- {marker}:END -->",
        "",
    ])
    if reading.read_text(encoding="utf-8") != text:
        raise AssertionError("تغير ملف القراءة أثناء إعادة القراءة؛ أوقف الحفظ")
    reading.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8", newline="\n")
    payload = {
        "schema": "reopened-loan-family-rereview-v1",
        "date": H.DATE,
        "language": LANGUAGE,
        "batch": batch,
        "batch_size": len(rows),
        "controls": controls,
        "changed_cards": sum(
            old_closures[int(row["original_index"])] != row["closure"] for row in rows
        ),
        "positive_cards": sum(bool(row["positives"]) for row in rows),
        "named_semantic_closures": sum(
            row["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for row in rows
        ),
        "open_cards": sum(row["closure"] == "OPEN-CANDIDATE" for row in rows),
        "rows": rows,
    }
    manifest.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(
        audit_text(batch, rows, controls, old_closures),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
