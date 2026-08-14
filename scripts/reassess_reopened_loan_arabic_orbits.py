# -*- coding: utf-8 -*-
"""Append an Arabic-root-sense reassessment for open loan-harvest cards.

The earlier harvest cards remain untouched.  Every revision explicitly
supersedes its ``LH-*`` card, reads the full local Arabic root fan with the
equivalent of ``--max-chars 0``, and keeps OPEN-CANDIDATE when the branch
meaning, frozen event, and quoted Arabic witness still do not form one
convincing orbit.
"""
from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from collections import Counter
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "scripts"))

import harvest_reopened_loans as H  # noqa: E402


DATE = "2026-08-14"
LANGUAGE = "welsh"
BATCH = 2
BASE = ROOT / "data" / "reopened-loan-welsh-harvest-batch-002.json"
READING = ROOT / "04-cross-linguistic" / "readings" / "welsh.md"
MANIFEST = ROOT / "data" / "reopened-loan-welsh-arabic-root-sense-rereview-batch-002.json"
AUDIT = ROOT / "05-audits" / "2026-08-14-reopened-loan-welsh-arabic-root-sense-rereview-batch-002.md"
MARKER = "LOAN-ARABIC-ROOT-SENSE-REREVIEW-WELSH-BATCH-002"
SUPERSEDES_MARKER = "ARABIC-ROOT-SENSE-REREVIEW"
PREDECESSOR_PREFIX = "LH-WELSH-FAMILY"


def predecessor_id(index: int) -> str:
    """Return the active family-rereview card that this narrower pass replaces."""
    return f"{PREDECESSOR_PREFIX}-{index:05d}"


def quote_key(value: Any) -> str:
    value = unicodedata.normalize("NFKC", str(value or ""))
    value = H.AR.ARABIC_MARKS.sub("", value)
    value = value.replace("أ", "ا").replace("إ", "ا").replace("آ", "ا")
    value = value.replace("ى", "ي").replace("ة", "ه")
    return re.sub(r"[^ء-يA-Za-z0-9]+", "", value).casefold()


def verify_positive_witnesses(
    rows: list[dict[str, Any]],
    hits_by_root: dict[str, list[dict[str, Any]]],
) -> None:
    for row in rows:
        for positive in row["positives"]:
            root = str(positive["root"])
            definitions = [
                quote_key(match.get("definition"))
                for match in hits_by_root.get(root, [])
            ]
            if not definitions:
                raise AssertionError(f"الموجب {row['card_id']}:{root} بلا شاهد معجمي")
            for witness in positive["arabic_witnesses"]:
                quote = quote_key(witness["quote"])
                if not quote or not any(quote in definition for definition in definitions):
                    raise AssertionError(
                        f"اقتباس غير متحقق حرفيًا بعد التطبيع: "
                        f"{row['card_id']}:{root}:{witness['source']}"
                    )


def review_stats(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_root: dict[str, dict[str, Any]] = {}
    candidate_reviews = 0
    for row in rows:
        ready = [
            candidate for candidate in row["fan_candidates"]
            if candidate["sound"] and candidate["event_tier"]
        ]
        if not ready:
            raise AssertionError(f"دخلت بطاقة بلا صوت وحدث في نطاق المدار: {row['card_id']}")
        for candidate in ready:
            review = candidate.get("arabic_lexicon_review") or {}
            if review.get("max_chars") != 0 or review.get("truncated"):
                raise AssertionError(
                    f"قراءة مقتطعة أو غير مسجلة: {row['card_id']}:{candidate['root']}"
                )
            candidate_reviews += 1
            by_root.setdefault(str(candidate["root"]), review)
    return {
        "cards": len(rows),
        "candidate_reviews": candidate_reviews,
        "unique_roots": len(by_root),
        "unique_root_witnesses": sum(
            int(review["witness_count"]) for review in by_root.values()
        ),
        "roots_with_witnesses": sum(
            int(review["witness_count"]) > 0 for review in by_root.values()
        ),
        "roots_without_witnesses": sum(
            int(review["witness_count"]) == 0 for review in by_root.values()
        ),
        "truncated": 0,
        "max_chars": 0,
    }


def audit_text(rows: list[dict[str, Any]], stats: dict[str, Any]) -> str:
    converted = [row for row in rows if row["closure"] != "OPEN-CANDIDATE"]
    opened = [row for row in rows if row["closure"] == "OPEN-CANDIDATE"]
    reasons = Counter(row["open_reason"] for row in opened)
    pairs = [
        f"`{row['form']}` ↔ `{positive['root']}` ({positive['closure']})"
        for row in converted for positive in row["positives"]
    ]
    lines = [
        "# إعادة الـ123 المفتوحة بالشواهد المعجمية العربية: الويلزية، الدفعة 002 (2026-08-14)",
        "",
        "## نطاق الإعادة",
        "",
        "أعيدت البطاقات التي كان سبب فتحها الحصري في محضر الحصاد السابق «اكتمل الصوت والحدث ولم يقنع مدار يدوي». لم تُمس بطاقات نقص المروحة أو المسار الصوتي، وبقيت البطاقات السابقة في ملف القراءة كما هي؛ كل بطاقة هنا ناسخة لها بمعرّف صريح.",
        "",
        f"- البطاقات المعادة: {len(rows)}.",
        f"- مقابلات الجذور المكتملة صوتًا وحدثًا التي قُرئت: {stats['candidate_reviews']}.",
        f"- الجذور الفريدة التي شُغلت عليها أداة عائلات اللسان: {stats['unique_roots']}.",
        f"- الشواهد الكاملة المقروءة في هذه الجذور: {stats['unique_root_witnesses']}.",
        f"- جذور لها شاهد واحد على الأقل: {stats['roots_with_witnesses']}؛ بلا شاهد: {stats['roots_without_witnesses']}.",
        "- حد العرض: `--max-chars 0` في كل قراءة؛ الشواهد المقتطعة: 0.",
        "",
        "## قانون الحكم",
        "",
        "لم يُجعل الشاهد المعجمي حكمًا مستقلًا. الموجب وحده ما اجتمع فيه مسار الصوت المسمى، وحدث السجل المجمد كما هو، ومعنى قاموس الفرع، ثم مدار كتبه القارئ يصل الطرفين واستشهد داخله بنص المعجم واسمه. وما لم يقنع بعد قراءة المروحة العربية الكاملة بقي OPEN-CANDIDATE.",
        "",
        "## الحصيلة",
        "",
        f"- تحوّل من الـ123 المفتوحة: {len(converted)} بطاقات.",
        f"- بقي OPEN-CANDIDATE بعد استيفاء الطرفين: {len(opened)} بطاقة.",
        f"- بقي سبب الفتح «لا مدار مقنع بعد قراءة الشواهد الكاملة»: {reasons['orbit_not_convincing']} بطاقة.",
        "",
        "## الأزواج التي تحولت",
        "",
    ]
    lines.extend(f"{number}. {pair}" for number, pair in enumerate(pairs, 1))
    if not pairs:
        lines.append("لم تتحول بطاقة.")
    lines.extend([
        "",
        "## ضبط الاقتباس",
        "",
        "كل موجب يحمل نص الشاهد واسم معجمه ورابط مادته حيث وفره الفهرس. وتحقق المولد من وجود نص الاقتباس داخل أحد الشواهد الكاملة للجذر بعد تطبيع الرسم والحركات، ولم يقبل ملخصًا منشأً بدل النص.",
        "",
    ])
    return "\n".join(lines)


def repair_existing_predecessors() -> int:
    """Repair an interrupted append whose predecessor snapshot became stale.

    The correction is limited to this script's own marked section and manifest.
    It does not alter any historical harvest or family-rereview card.
    """
    if not MANIFEST.exists() or not AUDIT.exists():
        raise AssertionError("لا توجد مخرجات مكتملة تصلح لإصلاح مراجع السلف")
    text = READING.read_text(encoding="utf-8")
    start_tag = f"<!-- {MARKER}:START -->"
    end_tag = f"<!-- {MARKER}:END -->"
    if text.count(start_tag) != 1 or text.count(end_tag) != 1:
        raise AssertionError("تعذر عزل مقطع إعادة الشواهد العربية عزلًا وحيدًا")
    start = text.index(start_tag)
    end = text.index(end_tag, start) + len(end_tag)
    section = text[start:end]

    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    rows = payload.get("rows", [])
    if len(rows) != 123:
        raise AssertionError(f"بيان الإصلاح يحوي {len(rows)} بطاقة بدل 123")
    updated = 0
    for row in rows:
        index = int(row["original_index"])
        old = f"LH-WELSH-{index:05d}"
        new = predecessor_id(index)
        if new not in text[:start]:
            raise AssertionError(f"بطاقة السلف النافذة غير موجودة قبل المقطع: {new}")
        old_marker = f"<!-- {SUPERSEDES_MARKER}:{old} -->"
        new_marker = f"<!-- {SUPERSEDES_MARKER}:{new} -->"
        if section.count(old_marker) or section.count(new_marker) != 1:
            raise AssertionError(f"لم يطبق التصحيح الموضعي لعلامة السلف: {old}")
        old_line = f"- ناسخ البطاقة السابقة: `{old}` ←"
        new_line = f"- ناسخ البطاقة السابقة: `{new}` ←"
        if section.count(old_line) or section.count(new_line) != 1:
            raise AssertionError(f"لم يطبق التصحيح الموضعي لسطر السلف: {old}")
        if row.get("supersedes") == old:
            row["supersedes"] = new
            updated += 1
        elif row.get("supersedes") != new:
            raise AssertionError(f"مرجع البيان غير المتوقع: {row['card_id']}")

    if updated:
        MANIFEST.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    audit = AUDIT.read_text(encoding="utf-8").replace(
        "# إعادة الـ123 المفتوحة بعائلات اللسان:",
        "# إعادة الـ123 المفتوحة بالشواهد المعجمية العربية:",
        1,
    )
    AUDIT.write_text(audit, encoding="utf-8", newline="\n")
    print(json.dumps({
        "repaired_cards": updated,
        "predecessor_prefix": PREDECESSOR_PREFIX,
    }, ensure_ascii=False))
    return 0


def sync_existing_orbits() -> int:
    """Synchronize the five issued orbit fields with the quoted rendering rule."""
    if not MANIFEST.exists():
        raise AssertionError("بيان إعادة الشواهد العربية غير موجود")
    payload = json.loads(MANIFEST.read_text(encoding="utf-8"))
    changed = 0
    for row in payload.get("rows", []):
        for positive in row.get("positives", []):
            specs = H.MANUAL_SPECS.get((LANGUAGE, int(row["original_index"])), [])
            spec = next(
                (item for item in specs if item["root"] == positive["root"]),
                None,
            )
            if not spec:
                raise AssertionError(f"لا مواصفة يدوية للموجب {row['card_id']}")
            expected = H.orbit_with_witnesses(
                str(spec["orbit"]),
                H.manual_witnesses(spec),
            )
            if positive.get("orbit") != expected:
                positive["orbit"] = expected
                changed += 1
    if changed not in {0, 5}:
        raise AssertionError(f"توقع مزامنة صفر أو خمسة مدارات، فكانت {changed}")
    if changed:
        MANIFEST.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
            newline="\n",
        )
    print(json.dumps({"synced_orbits": changed}, ensure_ascii=False))
    return 0


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser()
    repairs = parser.add_mutually_exclusive_group()
    repairs.add_argument("--repair-existing-predecessors", action="store_true")
    repairs.add_argument("--sync-existing-orbits", action="store_true")
    args = parser.parse_args()
    if args.repair_existing_predecessors:
        return repair_existing_predecessors()
    if args.sync_existing_orbits:
        return sync_existing_orbits()
    if MANIFEST.exists() or AUDIT.exists():
        raise AssertionError("مخرجات إعادة عائلات اللسان موجودة من قبل")
    original_text = READING.read_text(encoding="utf-8")
    if f"<!-- {MARKER}:START -->" in original_text:
        raise AssertionError("مقطع إعادة عائلات اللسان موجود في ملف القراءة")

    base = json.loads(BASE.read_text(encoding="utf-8"))
    target_rows = [
        row for row in base["rows"]
        if row.get("open_reason") == "orbit_not_convincing"
    ]
    if len(target_rows) != 123:
        raise AssertionError(f"نطاق الإعادة {len(target_rows)} لا يساوي 123")
    target_indices = {int(row["original_index"]) for row in target_rows}
    source_cards = {
        int(card["index"]): card for card in H.original_cards(LANGUAGE)
        if int(card["index"]) in target_indices
    }
    if set(source_cards) != target_indices:
        raise AssertionError("تعذر استرداد بطاقات المصدر الـ123 كاملة")

    ordered_cards = [source_cards[index] for index in sorted(target_indices)]
    hits_by_root = H.arabic_hits_for_cards(LANGUAGE, ordered_cards)
    rows: list[dict[str, Any]] = []
    rendered_cards: list[str] = []
    for card in ordered_cards:
        index = int(card["index"])
        card_lines, row, _ = H.build_card(
            LANGUAGE,
            card,
            hits_by_root,
            orbit_reassessment=True,
            revision_id=f"ALR-WELSH-{index:05d}",
            supersedes_id=predecessor_id(index),
            supersedes_marker=SUPERSEDES_MARKER,
        )
        rendered_cards.extend(card_lines)
        rows.append(row)

    verify_positive_witnesses(rows, hits_by_root)
    stats = review_stats(rows)
    converted = [row for row in rows if row["closure"] != "OPEN-CANDIDATE"]
    expected_new = {194, 195, 214, 217, 244}
    actual_new = {int(row["original_index"]) for row in converted}
    if actual_new != expected_new:
        raise AssertionError(f"تحولات غير متوقعة: {sorted(actual_new)}")

    section = "\n".join([
        f"<!-- {MARKER}:START -->",
        "",
        "## إعادة بطاقات المدار بالشواهد المعجمية العربية، الدفعة الويلزية 002 (2026-08-14)",
        "",
        *rendered_cards,
        f"<!-- {MARKER}:END -->",
        "",
    ])
    if READING.read_text(encoding="utf-8") != original_text:
        raise AssertionError("تغيّر ملف القراءة أثناء البناء؛ أوقف الإلحاق")
    READING.write_text(
        original_text.rstrip() + "\n\n" + section,
        encoding="utf-8",
        newline="\n",
    )

    reasons = Counter(
        row["open_reason"] for row in rows
        if row["closure"] == "OPEN-CANDIDATE"
    )
    payload = {
        "schema": "reopened-loan-arabic-root-sense-rereview-v1",
        "date": DATE,
        "language": LANGUAGE,
        "base_manifest": str(BASE.relative_to(ROOT)).replace("\\", "/"),
        "base_open_reason": "orbit_not_convincing",
        "reassessed_cards": len(rows),
        "transformed_cards": len(converted),
        "positive_traces": sum(len(row["positives"]) for row in converted),
        "remaining_open_cards": sum(
            row["closure"] == "OPEN-CANDIDATE" for row in rows
        ),
        "remaining_open_reasons": dict(reasons),
        "arabic_root_sense_review": stats,
        "rows": rows,
    }
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
        newline="\n",
    )
    AUDIT.write_text(
        audit_text(rows, stats),
        encoding="utf-8",
        newline="\n",
    )
    print(json.dumps({key: value for key, value in payload.items() if key != "rows"}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
