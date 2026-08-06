# -*- coding: utf-8 -*-
"""ابن طابور المسار ب من بطاقات العائق التي فتحتها مروحة الشمال.

تُرتب البطاقات تنازليا بعدد الجذور العربية الموجودة في المعاجم، ثم تُقسم
إلى ثلاث دفعات متجاورة في ترتيب الطابور. تحفظ البيانات الرسم الشمالي وكل
شاهد معجمي وعلامة الجذر القرآني. وجود المرشح لا يصدر حكم صلة، والجذر
القرآني عربي محض لا يجوز أن يعكس اتجاه الحكم إلى اقتراض العربية من الفرع.

الاستعمال:
    python scripts/build_blocked_northern_fan_lane_b_queue.py --batch 1
    python scripts/build_blocked_northern_fan_lane_b_queue.py --batch 1 --check
    python scripts/build_blocked_northern_fan_lane_b_queue.py --aggregate
    python scripts/build_blocked_northern_fan_lane_b_queue.py --aggregate --check
"""
from __future__ import annotations

import argparse
import collections
import hashlib
import json
import unicodedata
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent.parent
DATE = "2026-08-06"
CORE = ROOT / "data" / "juthoor-core-levels.json"
CORE_SHA256 = "98d31b01a811ea44706d2ecc82c6f0423014982d1ad65eed3ad39ace3715cfcb"
QURANIC = ROOT / "data" / "quranic-roots.json"
SOURCE_MANIFEST = ROOT / "data" / "blocked-northern-fan-rescreen.json"
SOURCE_BATCHES = tuple(
    ROOT / "data" / f"blocked-northern-fan-rescreen-batch-{batch:02d}.json"
    for batch in (1, 2, 3)
)
DATA = ROOT / "data" / "blocked-northern-fan-lane-b-queue.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-blocked-northern-fan-lane-b-queue.md"
TOTAL_SOURCE = 851
TOTAL_QUEUE = 258
TOTAL_CANDIDATE_MEMBERSHIPS = 951
QURANIC_ROOTS = 1651
BATCH_RANGES = {
    1: (1, 86),
    2: (87, 172),
    3: (173, 258),
}
LONG_DASHES = {chr(0x2013), chr(0x2014)}
ARABIC_NORMALIZE = str.maketrans({
    "أ": "ء",
    "إ": "ء",
    "ؤ": "ء",
    "ئ": "ء",
    "ى": "ي",
})
LANGUAGE_AR = {
    "akkadian": "الأكادية",
    "aramaic": "الآرامية",
    "hebrew": "العبرية",
    "nucleus-echoes-week17": "أصداء النوى في الأسبوع 17",
    "old-latin": "اللاتينية القديمة",
    "phoenician-punic-scout": "استطلاع الفينيقية والبونية",
}
GENERIC_WORDS = {
    "أكّادية",
    "آرامية",
    "عبرية",
    "فينيقية",
    "بونية",
}


def nfc(value: object) -> str:
    return unicodedata.normalize("NFC", str(value or ""))


def normalize_arabic(value: object) -> str:
    return nfc(value).translate(ARABIC_NORMALIZE)


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def source_batch_for(global_index: int) -> int:
    if global_index <= 284:
        return 1
    if global_index <= 568:
        return 2
    return 3


def load_quranic() -> dict[str, int]:
    payload = json.loads(QURANIC.read_text(encoding="utf-8"))
    by_root = {
        normalize_arabic(root): int(count)
        for root, count in payload["by_root"].items()
    }
    if payload.get("roots") != QURANIC_ROOTS or len(by_root) != QURANIC_ROOTS:
        raise RuntimeError(
            f"تغير جرد الجذور القرآنية: {payload.get('roots')}، {len(by_root)}"
        )
    return by_root


def load_source_records() -> list[dict[str, Any]]:
    manifest = json.loads(SOURCE_MANIFEST.read_text(encoding="utf-8"))
    expected_summary = {
        "cards": TOTAL_SOURCE,
        "cards_with_northern_forms": 312,
        "cards_with_lexicon_candidates": TOTAL_QUEUE,
        "card_candidate_roots": TOTAL_CANDIDATE_MEMBERSHIPS,
    }
    if manifest.get("summary") != expected_summary:
        raise RuntimeError(f"تغيرت حصيلة مسح المروحة: {manifest.get('summary')}")
    if manifest.get("fan_expansion", {}).get("added_reflections") != []:
        raise RuntimeError("تغيرت المروحة بعد بناء بيان المسح، فأوقف بناء الطابور")

    records: list[dict[str, Any]] = []
    for batch, path in enumerate(SOURCE_BATCHES, start=1):
        payload = json.loads(path.read_text(encoding="utf-8"))
        if payload.get("batch") != batch:
            raise RuntimeError(f"اختل رقم دفعة المصدر: {path.relative_to(ROOT)}")
        records.extend(payload["records"])
    indexes = [int(row["global_index"]) for row in records]
    if indexes != list(range(1, TOTAL_SOURCE + 1)):
        raise RuntimeError("مصادر المسح لا تغطي 1 إلى 851 مرة واحدة وبالترتيب")
    return records


def candidate_details(
    record: dict[str, Any], quranic: dict[str, int]
) -> list[dict[str, Any]]:
    details: dict[str, dict[str, Any]] = {}
    for form_record in record["northern_forms"]:
        form_ref = {
            "form": nfc(form_record["form"]),
            "skeleton": nfc(form_record["skeleton"]),
        }
        for candidate in form_record["candidates"]:
            root = nfc(candidate["root"])
            normalized = normalize_arabic(root)
            is_quranic = normalized in quranic
            occurrences = quranic.get(normalized, 0)
            if bool(candidate["quranic"]) != is_quranic:
                raise RuntimeError(
                    f"بليت علامة القرآن في البطاقة {record['global_index']} للجذر {root}"
                )
            if int(candidate["quranic_occurrences"]) != occurrences:
                raise RuntimeError(
                    f"بلي عدد الشواهد القرآنية في البطاقة {record['global_index']} للجذر {root}"
                )
            if candidate["evidence_kind"] != "named-lexicon-witnesses":
                raise RuntimeError(
                    f"دخل الطابور مرشح بلا شاهد معجمي مسمى: {root}"
                )
            if not candidate["witnesses"]:
                raise RuntimeError(f"دخل الطابور مرشح بلا شاهد محفوظ: {root}")

            item = details.setdefault(
                root,
                {
                    "root": root,
                    "source_forms": [],
                    "mentioned_in_card": False,
                    "quranic": is_quranic,
                    "quranic_occurrences": occurrences,
                    "quranic_direction_rule": (
                        "ARABIC-PURE; NO-BORROWING-INTO-ARABIC; "
                        "ARABIC-TO-BRANCH-OR-COMMON-ORIGIN-ONLY"
                        if is_quranic
                        else "NOT-TRIGGERED"
                    ),
                    "evidence_kind": "named-lexicon-witnesses",
                    "witnesses": [],
                },
            )
            if form_ref not in item["source_forms"]:
                item["source_forms"].append(form_ref)
            item["mentioned_in_card"] = bool(
                item["mentioned_in_card"] or candidate["mentioned_in_card"]
            )
            for witness in candidate["witnesses"]:
                normalized_witness = {
                    "source": nfc(witness["source"]),
                    "definition": nfc(witness["definition"]),
                }
                if normalized_witness not in item["witnesses"]:
                    item["witnesses"].append(normalized_witness)

    output = [details[root] for root in sorted(details)]
    if [item["root"] for item in output] != sorted(record["candidate_roots"]):
        raise RuntimeError(
            f"اختل جمع مرشحات البطاقة {record['global_index']}"
        )
    if len(output) != int(record["candidate_count"]):
        raise RuntimeError(
            f"اختل عدد مرشحات البطاقة {record['global_index']}"
        )
    return output


def display_name(record: dict[str, Any], forms: list[dict[str, str]]) -> str:
    word = nfc(record.get("word")).strip()
    if word and word not in GENERIC_WORDS:
        return word
    if forms:
        return " · ".join(item["form"] for item in forms)
    return nfc(record["head"])


def build_queue() -> list[dict[str, Any]]:
    if sha256(CORE) != CORE_SHA256:
        raise RuntimeError("تغير data/juthoor-core-levels.json؛ أوقف بناء الطابور")
    quranic = load_quranic()
    source = load_source_records()
    selected = [row for row in source if row["candidate_roots"]]
    selected.sort(key=lambda row: (-int(row["candidate_count"]), int(row["global_index"])))
    if len(selected) != TOTAL_QUEUE:
        raise RuntimeError(f"تغير مقام الطابور: {len(selected)}")
    if sum(int(row["candidate_count"]) for row in selected) != TOTAL_CANDIDATE_MEMBERSHIPS:
        raise RuntimeError("تغير عدد المرشحات داخل بطاقات الطابور")

    queue: list[dict[str, Any]] = []
    for rank, record in enumerate(selected, start=1):
        language = nfc(record["language"])
        if language not in LANGUAGE_AR:
            raise RuntimeError(f"لسان بلا تسمية عربية في الطابور: {language}")
        details = candidate_details(record, quranic)
        forms = []
        for form_record in record["northern_forms"]:
            if form_record["candidates"]:
                item = {
                    "form": nfc(form_record["form"]),
                    "skeleton": nfc(form_record["skeleton"]),
                }
                if item not in forms:
                    forms.append(item)
        quranic_candidates = [
            {
                "root": item["root"],
                "occurrences": item["quranic_occurrences"],
                "direction_rule": item["quranic_direction_rule"],
            }
            for item in details
            if item["quranic"]
        ]
        batch = 1 if rank <= 86 else 2 if rank <= 172 else 3
        queue.append({
            "schema_version": "1.0",
            "queue_id": f"LANE-B-NORTHERN-FAN-{rank:03d}",
            "rank": rank,
            "batch": batch,
            "source_global_index": int(record["global_index"]),
            "language": language,
            "language_ar": LANGUAGE_AR[language],
            "card_name": display_name(record, forms),
            "head": nfc(record["head"]),
            "word": nfc(record.get("word")),
            "northern_forms": forms,
            "candidate_count": len(details),
            "candidate_roots": [item["root"] for item in details],
            "quranic_candidate_count": len(quranic_candidates),
            "quranic_candidates": quranic_candidates,
            "candidate_details": details,
            "source_rescreen_batch": source_batch_for(int(record["global_index"])),
            "source_file": nfc(record["source"]),
            "source_line": int(record["source_line"]),
            "snapshot_blocker": nfc(record["snapshot_blocker"]),
            "snapshot_last_verdict": nfc(record["snapshot_last_verdict"]),
            "lane": "lane-b",
            "state": "LEXICON-CANDIDATE-QUEUED; ORGANIC-REVIEW-REQUIRED",
            "remaining_work": (
                "قراءة المعنى والصوت والصرف والقرض والمتجانسات، ثم إصدار حكم مستقل"
            ),
            "verdict_issued": False,
            "relation_created": False,
            "direction_policy": (
                "في المرشح القرآني يمتنع اقتراض العربية من الفرع، والاتجاه الممكن "
                "من العربية إلى الفرع أو من الأصل المشترك إلى كليهما؛ وفي سائر "
                "المرشحات لا اتجاه صادر من الفحص المعجمي"
            ),
        })
    return queue


def batch_paths(batch: int) -> tuple[Path, Path]:
    suffix = f"{batch:02d}"
    return (
        ROOT / "data" / f"blocked-northern-fan-lane-b-queue-batch-{suffix}.json",
        ROOT / "05-audits" / f"2026-08-06-blocked-northern-fan-lane-b-queue-batch-{suffix}.md",
    )


def summary(rows: list[dict[str, Any]]) -> dict[str, Any]:
    languages = collections.Counter(row["language"] for row in rows)
    roots = {root for row in rows for root in row["candidate_roots"]}
    quranic_roots = {
        item["root"]
        for row in rows
        for item in row["quranic_candidates"]
    }
    return {
        "cards": len(rows),
        "candidate_memberships": sum(row["candidate_count"] for row in rows),
        "distinct_candidate_roots": len(roots),
        "cards_with_quranic_candidates": sum(
            bool(row["quranic_candidates"]) for row in rows
        ),
        "quranic_candidate_memberships": sum(
            row["quranic_candidate_count"] for row in rows
        ),
        "distinct_quranic_candidate_roots": len(quranic_roots),
        "by_language": dict(sorted(languages.items())),
    }


def render_data(rows: list[dict[str, Any]], batch: int | None) -> str:
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "date": DATE,
        "scope": (
            "Cards with one or more named-lexicon Arabic candidates in the "
            "2026-08-06 blocked northern-fan rescreen."
        ),
        "order": "candidate_count descending, then source_global_index ascending",
        "frozen_core_sha256": CORE_SHA256,
        "quranic_inventory_roots": QURANIC_ROOTS,
        "summary": summary(rows),
    }
    if batch is not None:
        payload["batch"] = batch
        payload["rank_range"] = list(BATCH_RANGES[batch])
    else:
        payload["population"] = TOTAL_QUEUE
        payload["batch_ranges"] = {
            str(key): list(value) for key, value in BATCH_RANGES.items()
        }
    payload["queue"] = rows
    text = json.dumps(payload, ensure_ascii=False, indent=2) + "\n"
    if any(dash in text for dash in LONG_DASHES):
        raise RuntimeError("تسربت شرطة طويلة إلى بيانات الطابور")
    return nfc(text)


def safe_cell(value: object) -> str:
    return nfc(value).replace("|", "¦").replace("\n", " ").strip()


def render_audit(rows: list[dict[str, Any]], batch: int | None) -> str:
    report = summary(rows)
    if batch is None:
        title = "# محضر طابور المسار ب من بطاقات المروحة ذات المرشح المعجمي"
        range_line = (
            "يجمع هذا المحضر الدفعات 01 و02 و03، ويغطي رتب الطابور من 1 إلى 258 مرة واحدة."
        )
    else:
        start, end = BATCH_RANGES[batch]
        title = f"# محضر طابور المسار ب من بطاقات المروحة، الدفعة {batch:02d}"
        range_line = f"تغطي هذه الدفعة رتب الطابور من {start} إلى {end}."
    lines = [
        title,
        "",
        "## النطاق والترتيب",
        "",
        "دخل الطابور كل سطر من إعادة المسح له جذر عربي واحد على الأقل بشاهد "
        "معجمي مسمى. رتبت البطاقات تنازليا بعدد المرشحات، ثم برقمها العام في "
        "المسح عند التعادل. وجود المرشح لا يصدر حكم صلة ولا يعيد حكما منسوخا.",
        "",
        range_line,
        "",
        f"- البطاقات: {report['cards']}.",
        f"- مواضع المرشحات داخل البطاقات: {report['candidate_memberships']}.",
        f"- الجذور المرشحة المميزة: {report['distinct_candidate_roots']}.",
        f"- البطاقات ذات مرشح قرآني: {report['cards_with_quranic_candidates']}.",
        f"- مواضع المرشحات القرآنية: {report['quranic_candidate_memberships']}.",
        "- كل شاهد معجمي محفوظ في ملف JSON المرافق تحت المرشح نفسه.",
        "",
        "## البطاقات بألسنتها",
        "",
        "| الرتبة | رقم الطابور | اللسان | اسم البطاقة | الرسم الشمالي المفتاح | عدد المرشحات | المرشحات العربية | الجذور القرآنية | موضع الأصل |",
        "|---:|---|---|---|---|---:|---|---|---|",
    ]
    for row in rows:
        forms = " · ".join(
            f"`{safe_cell(item['form'])}`" for item in row["northern_forms"]
        ) or "لا رسم منفصل"
        roots = " · ".join(f"`{root}`" for root in row["candidate_roots"])
        quranic = " · ".join(
            f"`{item['root']}` ({item['occurrences']})"
            for item in row["quranic_candidates"]
        ) or "لا جذر قرآني"
        locator = f"`{row['source_file']}:{row['source_line']}`"
        lines.append(
            f"| {row['rank']} | `{row['queue_id']}` | {row['language_ar']} | "
            f"{safe_cell(row['card_name'])} | {forms} | {row['candidate_count']} | "
            f"{roots} | {quranic} | {locator} |"
        )
    lines += [
        "",
        "## قاعدة القرآن",
        "",
        "قوبلت علامات الجذور بملف `data/quranic-roots.json` ذي 1651 جذرا. كل "
        "جذر قرآني في الجدول عربي محض، فلا يجوز للمسار ب أن يحكم باقتراضه من "
        "الفرع. الاتجاه الممكن عند ثبوت الصلة هو من العربية إلى الفرع أو من الأصل "
        "المشترك إلى كليهما. هذه القاعدة تقيد الاتجاه ولا تصدر الصلة.",
        "",
        "## حد الإدخال إلى المسار ب",
        "",
        "حالة كل بطاقة `LEXICON-CANDIDATE-QUEUED; ORGANIC-REVIEW-REQUIRED`. "
        "يبدأ القارئ من رسم الفرع ومعناه، ثم يفصل المرشحات بالصوت والصرف والقرض "
        "والمتجانسات والمدار الدلالي. لا تحمل البطاقة من هذا الطابور درجة موجبة.",
        "",
        "## الحراس",
        "",
        f"- تجزئة الفهرس المجمّد المقروء فقط: `{CORE_SHA256}`.",
        "- ترتيب الطابور حتمي ومثبت بعدد المرشحات.",
        "- لا حكم صادر ولا صلة منشأة في أي سطر.",
        "",
    ]
    text = "\n".join(lines)
    if any(dash in text for dash in LONG_DASHES):
        raise RuntimeError("تسربت شرطة طويلة إلى محضر الطابور")
    return nfc(text)


def atomic_write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(text, encoding="utf-8", newline="\n")
    temporary.replace(path)


def verify_queue(rows: list[dict[str, Any]]) -> None:
    if len(rows) != TOTAL_QUEUE:
        raise RuntimeError(f"اختل مقام الطابور: {len(rows)}")
    if [row["rank"] for row in rows] != list(range(1, TOTAL_QUEUE + 1)):
        raise RuntimeError("رتب الطابور مفقودة أو مكررة")
    expected_order = sorted(
        rows,
        key=lambda row: (-int(row["candidate_count"]), int(row["source_global_index"])),
    )
    if rows != expected_order:
        raise RuntimeError("اختل ترتيب الطابور بعدد المرشحات")
    if sum(row["candidate_count"] for row in rows) != TOTAL_CANDIDATE_MEMBERSHIPS:
        raise RuntimeError("اختل مجموع المرشحات في الطابور")
    if any(row["verdict_issued"] or row["relation_created"] for row in rows):
        raise RuntimeError("تسرب حكم أو صلة إلى طابور القراءة")


def select_batch(queue: list[dict[str, Any]], batch: int) -> list[dict[str, Any]]:
    start, end = BATCH_RANGES[batch]
    rows = queue[start - 1:end]
    if [row["rank"] for row in rows] != list(range(start, end + 1)):
        raise RuntimeError(f"اختل مجال الدفعة {batch}")
    return rows


def write_or_check(path: Path, text: str, check: bool) -> None:
    if check:
        if not path.is_file() or path.read_text(encoding="utf-8") != text:
            raise RuntimeError(f"مخرج بائت أو مفقود: {path.relative_to(ROOT)}")
    else:
        atomic_write(path, text)


def process_batch(queue: list[dict[str, Any]], batch: int, check: bool) -> dict[str, Any]:
    rows = select_batch(queue, batch)
    data_path, audit_path = batch_paths(batch)
    write_or_check(data_path, render_data(rows, batch), check)
    write_or_check(audit_path, render_audit(rows, batch), check)
    return summary(rows)


def process_aggregate(queue: list[dict[str, Any]], check: bool) -> dict[str, Any]:
    for batch in sorted(BATCH_RANGES):
        rows = select_batch(queue, batch)
        data_path, audit_path = batch_paths(batch)
        expected_data = render_data(rows, batch)
        expected_audit = render_audit(rows, batch)
        if not data_path.is_file() or data_path.read_text(encoding="utf-8") != expected_data:
            raise RuntimeError(f"دفعة البيانات {batch} بائتة أو مفقودة")
        if not audit_path.is_file() or audit_path.read_text(encoding="utf-8") != expected_audit:
            raise RuntimeError(f"محضر الدفعة {batch} بائت أو مفقود")
    write_or_check(DATA, render_data(queue, None), check)
    write_or_check(AUDIT, render_audit(queue, None), check)
    return summary(queue)


def main() -> int:
    parser = argparse.ArgumentParser()
    target = parser.add_mutually_exclusive_group(required=True)
    target.add_argument("--batch", type=int, choices=sorted(BATCH_RANGES))
    target.add_argument("--aggregate", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    if hasattr(__import__("sys").stdout, "reconfigure"):
        __import__("sys").stdout.reconfigure(encoding="utf-8")

    queue = build_queue()
    verify_queue(queue)
    if args.aggregate:
        report = process_aggregate(queue, args.check)
        label = "aggregate"
    else:
        report = process_batch(queue, int(args.batch), args.check)
        label = f"batch-{int(args.batch):02d}"
    print(json.dumps({"target": label, **report}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
