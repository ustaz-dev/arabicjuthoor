#!/usr/bin/env python3
"""ألحق بطاقات تصحيح ناسخة من غير إعادة كتابة بطاقات الحصاد السابقة."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import harvest_reopened_loans as H


ROOT = Path(__file__).resolve().parents[1]
LANGUAGE = "welsh"
ROUNDS = {
    1: (214, 217, 244, 454, 455),
    2: (603, 700, 1163, 1166, 1475),
    3: (1616,),
    4: (2353,),
}


def correction_lines(lines: list[str], old_id: str, new_id: str) -> list[str]:
    corrected: list[str] = []
    old_reopen_marker_seen = False
    for line in lines:
        if line.startswith("### بطاقة حصاد القرض المعاد فتحه:"):
            corrected.append(line.replace(old_id, new_id))
        elif line.startswith("<!-- LOAN-HARVEST-REREVIEW:"):
            corrected.extend([
                f"<!-- LOAN-HARVEST-CARD:{new_id} -->",
                f"<!-- LOAN-HARVEST-CORRECTION:{old_id} -->",
            ])
            old_reopen_marker_seen = True
        elif line.startswith("- ناسخ البطاقة التاريخية:"):
            corrected.append(
                f"- ناسخ بطاقة الحصاد: `{old_id}` ← `{new_id}`؛ بقي النص السابق كاملًا، "
                f"وهذا الحكم هو النافذ بتاريخ {H.DATE}."
            )
        else:
            corrected.append(line)
    if not old_reopen_marker_seen:
        raise AssertionError(f"لم يوجد وسم البطاقة الأصلية في {old_id}")
    return corrected


def audit_text(correction: int, rows: list[dict], controls: list[dict]) -> str:
    positives = [row for row in rows if row["positives"]]
    named = [row for row in rows if row["closure"] == "SEMITIC-SOURCE-TRANSMISSION"]
    control_rows = "\n".join(
        f"| `{row['word']}` | `{row['root']}` | {row['closure']} | "
        f"{row['current_verdict']} | {'ثابت' if row['unchanged'] else 'تغيّر'} |"
        for row in controls
    )
    positive_rows = "\n".join(
        f"{number}. `{row['form']}` ↔ `{row['positives'][0]['root']}` "
        f"({row['closure']})"
        for number, row in enumerate(positives, 1)
    )
    named_rows = "\n".join(
        f"- `{row['form']}`: {row['closure']}؛ {row['named_closure']['donor']}؛ "
        f"{row['named_closure']['evidence']}."
        for row in named
    )
    reasons = {
        1: (
            "ألحقت خمس بطاقات ناسخة ولم أعد كتابة بطاقة سابقة: ثلاث صلات ظهر لها شاهد "
            "عربي مباشر بعد قراءة شواهد الجذر كاملة، وإغلاقان للعضو `oren` بعد تسمية العربية "
            "`نارنج` مانحًا في سلسلة النقل. بقي `prostitute ↔ فتن` و`paste ↔ بسط` "
            "مفتوحين لأن المدار المقترح علاقة فاعل أو أداة لا معنى مباشرًا."
        ),
        2: (
            "ألحقت خمس بطاقات ناسخة ولم أعد كتابة بطاقة سابقة. سمت المراجع العربية "
            "`قهوة` مانحًا في `caffi` و`caffîn`، والعربية `سكر` في `siwgr`، والعربية "
            "`مومياء` في `mymi`، والعبرية `bōśem` في `bawm`."
        ),
        3: (
            "ألحقت بطاقة ناسخة واحدة ولم أعد كتابة بطاقة سابقة. بعد قراءة شواهد "
            "`وجس` كاملة، وافق معنى `gès` في قاموس الفرع `guess, idea, estimate` "
            "تعريف الواجس بالهاجس والخاطر، واتصل بحدث السجل في تحصّل الشيء دقيق "
            "الوقع في الباطن. بقي `siâp ↔ صوب` مفتوحًا لأن الانتقال من الهيئة أو "
            "الحال الجيدة إلى حدث الوقوع الموافق لا يبلغ درجة المدار المقنع."
        ),
        4: (
            "ألحقت بطاقة ناسخة واحدة ولم أعد كتابة بطاقة سابقة. مدخلة الفرع تحلل "
            "`ansero` بمعنى `nonzero` إلى `an- + sero`، ومعجم Merriam-Webster يرد "
            "`zero` عبر اللاتينية الوسيطة والإيطالية إلى العربية `ṣifr`؛ فسمي "
            "المانح العربي وأغلق العضو بنقل سامي مسمى. بقي `tiwna` مفتوحًا لأن "
            "العربية ناقل وسيط لمادة لاتينية يونانية، وبقي `Arabia` مفتوحًا لعدم "
            "تعيّن مانح سامي واحد في أصل الاسم القديم."
        ),
    }
    reason = reasons[correction]
    return (
        f"# تصحيح ناسخ لحصاد القرض الويلزي المعاد فتحه، الجولة {correction:03d} ({H.DATE})\n\n"
        "## الضابط\n\n"
        "أعيد حساب البطاقات الست الصادرة بالمروحة الحالية وبـ`frozen_event.resolve` وحده، "
        "ولم يتغير حكم واحدة.\n\n"
        "| الصورة | المقابل | السابق | الحالي | النتيجة |\n"
        "|---|---|---|---|---|\n"
        f"{control_rows}\n\n"
        "## سبب التصحيح\n\n"
        f"{reason}\n\n"
        "## الحصيلة\n\n"
        f"- فُحص وصُحح: {len(rows)} بطاقات.\n"
        f"- موجب بالأرجل الثلاث: {len(positives)} بطاقات.\n"
        f"- أعيد إغلاقه بمانح سامي مسمى: {len(named)} بطاقات.\n"
        "- بقي مفتوحًا من البطاقات المصححة: 0.\n\n"
        "## الصلات الداخلة\n\n"
        f"{positive_rows}\n\n"
        "## الإغلاقات غير النسبية\n\n"
        f"{named_rows}\n"
    )


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--round", type=int, choices=tuple(ROUNDS), required=True)
    args = parser.parse_args()
    correction = args.round
    indices = ROUNDS[correction]
    marker = f"LOAN-HARVEST-WELSH-CORRECTIONS-{correction:03d}"
    reading = ROOT / "04-cross-linguistic" / "readings" / "welsh.md"
    audit = ROOT / "05-audits" / f"{H.DATE}-reopened-loan-welsh-harvest-corrections-{correction:03d}.md"
    manifest = ROOT / "data" / f"reopened-loan-welsh-harvest-corrections-{correction:03d}.json"
    text = reading.read_text(encoding="utf-8")
    if f"<!-- {marker}:START -->" in text or audit.exists() or manifest.exists():
        raise AssertionError("مخرجات جولة التصحيح موجودة من قبل")

    cards = {int(card["index"]): card for card in H.original_cards(LANGUAGE)}
    controls = H.control_run()
    selected_cards = [cards[index] for index in indices]
    arabic_hits_by_root = H.arabic_hits_for_cards(LANGUAGE, selected_cards)
    rows: list[dict] = []
    blocks: list[str] = []
    for index in indices:
        old_id = f"LH-WELSH-{index:05d}"
        new_id = f"LH-WELSH-CORR-{index:05d}"
        lines, row, reason = H.build_card(
            LANGUAGE,
            cards[index],
            arabic_hits_by_root,
            orbit_reassessment=True,
            revision_id=new_id,
            supersedes_id=old_id,
            supersedes_marker="LOAN-HARVEST-CORRECTION",
        )
        if reason or row["closure"] == "OPEN-CANDIDATE":
            raise AssertionError(f"التصحيح {index} لم يستوف الحكم: {reason}")
        row["supersedes"] = old_id
        rows.append(row)
        blocks.extend(lines)

    section = "\n".join([
        f"<!-- {marker}:START -->",
        "",
        f"## تصحيح ناسخ لحصاد القرض المعاد فتحه، الجولة {correction:03d} ({H.DATE})",
        "",
        *blocks,
        f"<!-- {marker}:END -->",
        "",
    ])
    if reading.read_text(encoding="utf-8") != text:
        raise AssertionError("تغير ملف القراءة أثناء بناء التصحيح؛ أوقف الحفظ")
    reading.write_text(text.rstrip() + "\n\n" + section, encoding="utf-8", newline="\n")
    manifest.write_text(
        json.dumps({
            "schema": "reopened-loan-harvest-correction-v1",
            "date": H.DATE,
            "language": LANGUAGE,
            "correction": correction,
            "controls": controls,
            "corrected_cards": len(rows),
            "positive_cards": sum(bool(row["positives"]) for row in rows),
            "named_semantic_closures": sum(
                row["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for row in rows
            ),
            "rows": rows,
        }, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    audit.write_text(audit_text(correction, rows, controls), encoding="utf-8", newline="\n")
    print(json.dumps({
        "corrected_cards": len(rows),
        "positive_cards": sum(bool(row["positives"]) for row in rows),
        "named_semantic_closures": sum(
            row["closure"] == "SEMITIC-SOURCE-TRANSMISSION" for row in rows
        ),
    }, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
