# -*- coding: utf-8 -*-
"""ابن طابورًا واحدًا لكل بطاقة فتحها فحص ولم يصدر فيها حكم جديد.

كل صف يحمل لسانه وتعيين قارئ المسار ب. لا يصدر هذا البناء حكم نسب، ولا
يغير أجسام البطاقات، ولا يحول المرشح المعجمي وحده إلى صلة.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Any, Iterable


ROOT = Path(__file__).resolve().parent.parent
LOAN = ROOT / "data" / "loanword-rescreen.json"
QURANIC = ROOT / "data" / "quranic-loan-retraction-rescreen.json"
DELEGATED = ROOT / "04-cross-linguistic" / "data" / "delegated_ruling_card_reviews.jsonl"
FAN_MANIFEST = ROOT / "data" / "blocked-northern-fan-rescreen.json"
AKKADIAN = ROOT / "04-cross-linguistic" / "readings" / "akkadian.md"

QUEUE = ROOT / "data" / "lane-b-open-review-queue.jsonl"
MANIFEST = ROOT / "data" / "lane-b-open-review-queue-manifest.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-lane-b-open-review-queue-periodic-001.md"

DATE = "2026-08-06"
CYCLE = 1
READER = "lane-b"

LANGUAGE_AR = {
    "akkadian": "الأكّادية",
    "ancient-greek": "اليونانية القديمة",
    "aramaic": "الآرامية",
    "coptic": "القبطية",
    "egyptian": "المصرية القديمة",
    "gothic": "القوطية",
    "hebrew": "العبرية",
    "latin": "اللاتينية",
    "old-english": "الإنجليزية القديمة",
    "old-irish": "الأيرلندية القديمة",
    "old-latin": "اللاتينية القديمة",
    "old-norse": "النوردية القديمة",
    "persian": "الفارسية",
    "phoenician": "الفينيقية",
    "phoenician-punic": "الفينيقية والبونية",
    "punic": "البونية",
    "welsh": "الويلزية",
}

LIVE_QURANIC = (
    {
        "opening_id": "LIVE-REOPEN-QUR-001",
        "heading": "بطاقة: šaṭāru «يكتب ويسطر» ↔ سطر",
        "root": "سطر",
        "remaining_review": "فحص الأصل المشترك ومسار الصوت والمدار",
    },
    {
        "opening_id": "LIVE-REOPEN-QUR-002",
        "heading": "بطاقة: أسرة eperum «الغبار» وبقية أعضاء p-r",
        "root": "فيل",
        "remaining_review": "قراءة عضو pīru أو pīlu وحده مع إبقاء قرض pūru وعوائق الأسرة الأخرى",
    },
)

SOURCE_ORDER = {
    "quranic-retraction": 0,
    "quranic-live-closure": 1,
    "northern-fan": 2,
    "proposed-nuclei": 3,
    "loan-rescreen": 4,
}


def clean(value: object) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    return text.replace("\u2013", "-").replace("\u2014", "-")


def normalized_language(value: object, *, word: object = "") -> str:
    language = clean(value).replace("_", "-")
    if language == "nucleus-echoes-week17":
        if "العبرية" in clean(word):
            return "hebrew"
        raise RuntimeError("تعذر تعيين لسان بطاقة أصداء النوى")
    if language == "phoenician-punic-scout":
        return "phoenician-punic"
    return language


def language_fields(value: object, *, word: object = "") -> dict[str, str]:
    language = normalized_language(value, word=word)
    if language not in LANGUAGE_AR:
        raise RuntimeError(f"لسان بلا وسم عربي: {language}")
    return {"language": language, "language_ar": LANGUAGE_AR[language]}


def base_record(
    *,
    queue_id: str,
    opening_source: str,
    opening_id: str,
    language: object,
    word: object = "",
) -> dict[str, Any]:
    return {
        "schema": "lane-b-open-review-v1",
        "date": DATE,
        "cycle": CYCLE,
        "queue_id": queue_id,
        "opening_source": opening_source,
        "opening_id": clean(opening_id),
        **language_fields(language, word=word),
        "reader": READER,
        "reader_role_ar": "قارئ المسار ب",
        "reader_state": "QUEUED",
        "verdict_issued_by_queue": False,
        "relation_created_by_queue": False,
    }


def loan_records() -> list[dict[str, Any]]:
    payload = json.loads(LOAN.read_text(encoding="utf-8"))
    rows = [row for row in payload["records"] if row["decision"] == "reopen"]
    if len(rows) != int(payload["summary"]["reopened"]):
        raise RuntimeError("اختل عد المفتوح في سجل إعادة فرز القرض")
    output = []
    for row in rows:
        record = base_record(
            queue_id=f"LANE-B/LOAN/{row['migration_id']}",
            opening_source="loan-rescreen",
            opening_id=row["migration_id"],
            language=row["language"],
        )
        record.update({
            "review_state": "OPEN-CANDIDATE",
            "card_id": clean(row.get("card_id")),
            "source_file": clean(row["file"]),
            "heading": clean(row["heading"]),
            "opening_reason": clean(row["reason"]),
        })
        output.append(record)
    return output


def quranic_retraction_records() -> list[dict[str, Any]]:
    payload = json.loads(QURANIC.read_text(encoding="utf-8"))
    rows = payload["records"]
    if len(rows) != int(payload["summary"]["reopened"]):
        raise RuntimeError("اختل عد المفتوح في إعادة فرز النقوض القرآنية")
    output = []
    for row in rows:
        if row["decision"] != "OPEN-CANDIDATE" or not row["copy_line_present"]:
            raise RuntimeError(f"نقض قرآني غير مفتوح جسديًا: {row['copy_id']}")
        record = base_record(
            queue_id=f"LANE-B/QURANIC-RETRACTION/{row['copy_id']}",
            opening_source="quranic-retraction",
            opening_id=row["copy_id"],
            language=row["language"],
        )
        record.update({
            "review_state": "OPEN-CANDIDATE",
            "retraction_id": clean(row["audit_id"]),
            "source_file": clean(row["source_file"]),
            "heading": clean(row["heading"]),
            "quranic_root": clean(row["quranic_root"]),
            "quranic_occurrences": int(row["quranic_occurrences"]),
            "remaining_review": clean(row["remaining_review"]),
        })
        output.append(record)
    return output


def quranic_live_records() -> list[dict[str, Any]]:
    text = AKKADIAN.read_text(encoding="utf-8")
    output = []
    for row in LIVE_QURANIC:
        marker = row["opening_id"]
        if text.count(marker) != 1:
            raise RuntimeError(f"اختل حضور فتح قرآني حي: {marker}={text.count(marker)}")
        marker_at = text.index(marker)
        heading_at = text.rfind("\n### ", 0, marker_at)
        heading_end = text.find("\n", heading_at + 1)
        heading = clean(text[heading_at + 5:heading_end])
        if heading != row["heading"]:
            raise RuntimeError(f"اختل رأس الفتح القرآني الحي: {marker}")
        record = base_record(
            queue_id=f"LANE-B/QURANIC-LIVE/{marker}",
            opening_source="quranic-live-closure",
            opening_id=marker,
            language="akkadian",
        )
        record.update({
            "review_state": "OPEN-CANDIDATE",
            "source_file": "04-cross-linguistic/readings/akkadian.md",
            "heading": heading,
            "quranic_root": row["root"],
            "remaining_review": row["remaining_review"],
        })
        output.append(record)
    return output


def delegated_records() -> list[dict[str, Any]]:
    rows = []
    with DELEGATED.open(encoding="utf-8") as handle:
        for line in handle:
            if line.strip():
                row = json.loads(line)
                if row.get("lane") == "proposed-nuclei":
                    rows.append(row)
    ranks = [int(row["rank"]) for row in rows]
    if ranks != list(range(1, len(rows) + 1)):
        raise RuntimeError("اختل ترتيب بطاقات النوى المقترحة")
    output = []
    for row in rows:
        record = base_record(
            queue_id=f"LANE-B/PROPOSED-NUCLEI/{row['rank']:05d}",
            opening_source="proposed-nuclei",
            opening_id=row["entry_id"],
            language=row["language"],
        )
        record.update({
            "review_state": clean(row["review_state"]),
            "entry_id": clean(row["entry_id"]),
            "family_id": clean(row.get("family_id")),
            "headword": clean(row.get("headword")),
            "romanization": clean(row.get("romanization")),
            "branch_gloss": clean(row.get("branch_gloss")),
            "approved_proposed_nuclei": [clean(item) for item in row.get("approved_proposed_nuclei", [])],
            "tri_root_precedence": clean(row.get("tri_root_precedence")),
        })
        output.append(record)
    return output


def fan_records() -> list[dict[str, Any]]:
    manifest = json.loads(FAN_MANIFEST.read_text(encoding="utf-8"))
    output = []
    for batch in manifest["batches"]:
        path = ROOT / batch["data_file"]
        payload = json.loads(path.read_text(encoding="utf-8"))
        for row in payload["records"]:
            if int(row["candidate_count"]) < 1:
                continue
            word = row.get("word") or row.get("head")
            record = base_record(
                queue_id=f"LANE-B/NORTHERN-FAN/{int(row['global_index']):05d}",
                opening_source="northern-fan",
                opening_id=str(row["global_index"]),
                language=row["language"],
                word=word,
            )
            record.update({
                "review_state": "FAN-CANDIDATE-READING",
                "source_file": f"04-cross-linguistic/exploration/{row['source']}",
                "source_line": int(row["source_line"]),
                "heading": clean(row["head"]),
                "word": clean(row.get("word")),
                "candidate_roots": [clean(root) for root in row["candidate_roots"]],
                "candidate_count": int(row["candidate_count"]),
                "fan_decision": clean(row["decision"]),
            })
            output.append(record)
    expected = int(manifest["summary"]["cards_with_lexicon_candidates"])
    if len(output) != expected:
        raise RuntimeError(f"اختل عد بطاقات المروحة: {len(output)} من {expected}")
    return output


def collect() -> list[dict[str, Any]]:
    rows = (
        quranic_retraction_records()
        + quranic_live_records()
        + fan_records()
        + delegated_records()
        + loan_records()
    )
    ids = [row["queue_id"] for row in rows]
    if len(ids) != len(set(ids)):
        raise RuntimeError("تكرر معرف في طابور المسار ب")
    rows.sort(key=lambda row: (SOURCE_ORDER[row["opening_source"]], row["queue_id"]))
    for row in rows:
        if row["reader"] != READER or row["reader_state"] != "QUEUED":
            raise RuntimeError(f"صف بلا قارئ: {row['queue_id']}")
        if not row["language"] or not row["language_ar"]:
            raise RuntimeError(f"صف بلا وسم لسان: {row['queue_id']}")
    return rows


def jsonl_text(rows: Iterable[dict[str, Any]]) -> str:
    return "".join(
        json.dumps(row, ensure_ascii=False, separators=(",", ":")) + "\n"
        for row in rows
    )


def manifest_payload(rows: list[dict[str, Any]]) -> dict[str, Any]:
    by_source = collections.Counter(row["opening_source"] for row in rows)
    by_language = collections.Counter(row["language"] for row in rows)
    by_source_language: dict[str, collections.Counter[str]] = collections.defaultdict(collections.Counter)
    for row in rows:
        by_source_language[row["opening_source"]][row["language"]] += 1
    return {
        "schema_version": "1.0",
        "date": DATE,
        "cycle": CYCLE,
        "scope": "Every still-open card or candidate-reading opened by the named rescreens.",
        "reader": READER,
        "summary": {
            "queue_rows": len(rows),
            "rows_with_reader": sum(row["reader"] == READER for row in rows),
            "rows_with_language": sum(bool(row["language"]) for row in rows),
            "historical_admissions_without_live_card": 1,
            "by_source": dict(sorted(by_source.items())),
            "by_language": dict(sorted(by_language.items())),
            "by_source_language": {
                source: dict(sorted(counts.items()))
                for source, counts in sorted(by_source_language.items())
            },
        },
        "priority": [
            "quranic-retraction",
            "quranic-live-closure",
            "northern-fan",
            "proposed-nuclei",
            "loan-rescreen",
        ],
        "queue_file": "data/lane-b-open-review-queue.jsonl",
    }


def manifest_text(rows: list[dict[str, Any]]) -> str:
    return json.dumps(manifest_payload(rows), ensure_ascii=False, indent=2) + "\n"


def audit_text(rows: list[dict[str, Any]]) -> str:
    manifest = manifest_payload(rows)
    summary = manifest["summary"]
    source_ar = {
        "quranic-retraction": "النقوض القرآنية",
        "quranic-live-closure": "الإغلاقات القرآنية الحية",
        "northern-fan": "مرشحو المروحة الشمالية",
        "proposed-nuclei": "بطاقات النوى المقترحة",
        "loan-rescreen": "إعادة فرز القرض",
    }
    lines = [
        "# المحضر الدوري لطابور المسار ب المفتوح، الدورة 001",
        "",
        f"التاريخ: {DATE}",
        "",
        "## الحصيلة",
        "",
        f"جُمعت {summary['queue_rows']} حالة قراءة مفتوحة في طابور واحد. "
        f"حملت {summary['rows_with_language']} حالة وسم اللسان، وعُيّنت "
        f"{summary['rows_with_reader']} حالة إلى قارئ المسار ب. لا صف مفتوح بلا قارئ.",
        "",
        "| مصدر الفتح | البطاقات أو حالات القراءة |",
        "|---|---:|",
    ]
    for source in manifest["priority"]:
        lines.append(f"| {source_ar[source]} | {summary['by_source'][source]} |")
    lines += [
        "",
        "الإقرار القرآني التاريخي الثالث محفوظ في محضره، لكنه لم يدخل الطابور لأنه بلا بطاقة حية مستقلة.",
        "",
        "## التوزيع بألسنته",
        "",
        "| اللسان | العدد |",
        "|---|---:|",
    ]
    for language, count in summary["by_language"].items():
        lines.append(f"| {LANGUAGE_AR[language]} (`{language}`) | {count} |")
    lines += [
        "",
        "## ترتيب القراءة",
        "",
        "تقدم النقوض والإغلاقات القرآنية، ثم مرشحو المروحة، ثم بطاقات النوى المقترحة، ثم بقية ما فتحته إعادة فرز القرض. هذا ترتيب قراءة فقط، ولا يستعيد حكمًا موجبًا ولا ينشئ صلة.",
        "",
        "## حارس الوصول إلى القارئ",
        "",
        "كل صف في `data/lane-b-open-review-queue.jsonl` يحمل `reader=lane-b` و`reader_state=QUEUED` ووسمي اللسان بالإنجليزية والعربية. يعيد المولد بناء المحضر والبيان من المصادر الحاكمة، ويفشل فحص النشر إذا بقي صف بلا قارئ أو بلا لسان أو إذا بلي أحد المشتقين.",
        "",
    ]
    text = "\n".join(lines)
    if "\u2013" in text or "\u2014" in text:
        raise RuntimeError("تسربت شرطة طويلة إلى محضر الطابور")
    return text


def write_atomic(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")

    rows = collect()
    outputs = {
        QUEUE: jsonl_text(rows),
        MANIFEST: manifest_text(rows),
        AUDIT: audit_text(rows),
    }
    for path, text in outputs.items():
        if "\u2013" in text or "\u2014" in text:
            raise RuntimeError(f"تسربت شرطة طويلة إلى {path.relative_to(ROOT)}")
    if args.check:
        for path, expected in outputs.items():
            if not path.exists() or path.read_text(encoding="utf-8") != expected:
                raise RuntimeError(f"مشتق طابور المسار ب بائت: {path.relative_to(ROOT)}")
        print(f"CLEAN: lane-b queue {len(rows)} rows, all assigned and language-tagged")
        return 0

    for path, text in outputs.items():
        write_atomic(path, text)
    print(f"WROTE: lane-b queue {len(rows)} rows, all assigned and language-tagged")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
