# -*- coding: utf-8 -*-
"""اجمع دفعات مسح المروحة الثلاث وتحقق من تغطية 851 بطاقة مرة واحدة."""
from __future__ import annotations

import argparse
import json
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
DATA = ROOT / "data" / "blocked-northern-fan-rescreen.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-blocked-northern-fan-rescreen.md"
BATCHES = tuple(
    ROOT / "data" / f"blocked-northern-fan-rescreen-batch-{batch:02d}.json"
    for batch in (1, 2, 3)
)
TOTAL = 851
NOTABLE = (
    ("קַיִץ", "قيظ"),
    ("עצם", "عظم"),
    ("צבע", "صبغ"),
    ("עפרא", "عفر"),
    ("עסק", "عشق"),
)


def collect() -> tuple[dict, list[dict]]:
    payloads = [json.loads(path.read_text(encoding="utf-8")) for path in BATCHES]
    records = [record for payload in payloads for record in payload["records"]]
    indexes = [record["global_index"] for record in records]
    if indexes != list(range(1, TOTAL + 1)):
        raise RuntimeError("دفعات المروحة لا تغطي المجال 1 إلى 851 مرة واحدة وبالترتيب")
    ranges = [payload["range"] for payload in payloads]
    if ranges != [[1, 284], [285, 568], [569, 851]]:
        raise RuntimeError(f"اختلت مجالات الدفعات: {ranges}")
    fans = [payload["fan"] for payload in payloads]
    if not all(fan == fans[0] for fan in fans[1:]):
        raise RuntimeError("تغيرت المروحة بين الدفعات")

    notable_records = []
    for form, root in NOTABLE:
        hits = []
        for record in records:
            for form_record in record["northern_forms"]:
                roots = [candidate["root"] for candidate in form_record["candidates"]]
                if form_record["form"] == form and root in roots:
                    hits.append({
                        "global_index": record["global_index"],
                        "source": record["source"],
                        "source_line": record["source_line"],
                        "head": record["head"],
                        "form": form,
                        "root": root,
                    })
        if not hits:
            raise RuntimeError(f"غاب المثال الضابط: {form} ← {root}")
        notable_records.extend(hits)

    payload = {
        "schema_version": "1.0",
        "date": "2026-08-06",
        "population": TOTAL,
        "coverage": {
            "first_global_index": indexes[0],
            "last_global_index": indexes[-1],
            "missing_global_indexes": [],
            "duplicate_global_indexes": [],
        },
        "summary": {
            "cards": len(records),
            "cards_with_northern_forms": sum(bool(r["northern_forms"]) for r in records),
            "cards_with_lexicon_candidates": sum(bool(r["candidate_roots"]) for r in records),
            "card_candidate_roots": sum(r["candidate_count"] for r in records),
        },
        "fan": fans[0],
        "batches": [
            {
                "batch": payload["batch"],
                "range": payload["range"],
                "data_file": BATCHES[index].relative_to(ROOT).as_posix(),
                "summary": payload["summary"],
            }
            for index, payload in enumerate(payloads)
        ],
        "notable_witnesses": notable_records,
        "fan_expansion": {
            "added_reflections": [],
            "reason": "لم يثبت في الدفعات الثلاث انعكاس مسمى بمصدر خارج جدول FAN الجاري؛ لم يضف شيء بلا شاهد.",
        },
    }
    return payload, records


def render_audit(payload: dict) -> str:
    summary = payload["summary"]
    lines = [
        "# محضر اكتمال إعادة مسح بطاقات العائق بالمروحة",
        "",
        "## التغطية",
        "",
        f"غُطيت البطاقات من 1 إلى {TOTAL} مرة واحدة في ثلاث دفعات متجاورة. "
        "لا رقم مفقود ولا مكرر.",
        "",
        f"- البطاقات: {summary['cards']}.",
        f"- البطاقات ذات رسم شمالي صالح: {summary['cards_with_northern_forms']}.",
        f"- البطاقات ذات مرشح موجود في المعاجم: {summary['cards_with_lexicon_candidates']}.",
        f"- الجذور المميزة داخل بطاقاتها: {summary['card_candidate_roots']}.",
        "- كل شاهد معجمي لكل مرشح محفوظ في ملفات JSON الثلاثة، ولا يصدر وجوده حكم صلة.",
        "",
        "## أمثلة الضبط",
        "",
        "| الرسم الشمالي | المرشح العربي الموجود | موضع البطاقة |",
        "|---|---|---|",
    ]
    seen = set()
    for item in payload["notable_witnesses"]:
        key = (item["form"], item["root"])
        if key in seen:
            continue
        seen.add(key)
        lines.append(
            f"| `{item['form']}` | `{item['root']}` | "
            f"`{item['source']}:{item['source_line']}` |"
        )
    lines += [
        "",
        "## توسيع المروحة",
        "",
        "لم يثبت في الدفعات الثلاث انعكاس مسمى بمصدر خارج جدول `FAN` الجاري، "
        "فلم يضف شيء بلا شاهد. بقيت خريطة المروحة نفسها مسجلة حرفيًا في البيان.",
        "",
        "## حد الحكم",
        "",
        "هذا اكتمال مسح معجمي لا اكتمال تحكيم دلالي. المرشح المذكور سابقًا "
        "مفصول في البيانات عن المرشح غير المفحوص، وإعادة الفتح تحتاج سطر نسخ مستقل.",
        "",
    ]
    text = "\n".join(lines)
    if "—" in text or "–" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    payload, _ = collect()
    data_text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    audit_text = render_audit(payload) + "\n"
    if args.check:
        if not DATA.is_file() or DATA.read_text(encoding="utf-8") != data_text:
            raise RuntimeError("بيان اكتمال المروحة بائت أو مفقود")
        if not AUDIT.is_file() or AUDIT.read_text(encoding="utf-8") != audit_text:
            raise RuntimeError("محضر اكتمال المروحة بائت أو مفقود")
    else:
        DATA.write_text(data_text, encoding="utf-8", newline="\n")
        AUDIT.write_text(audit_text, encoding="utf-8", newline="\n")
    print(json.dumps(payload["summary"], ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
