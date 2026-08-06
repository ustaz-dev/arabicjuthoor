# -*- coding: utf-8 -*-
"""ابن طابور المسار ب من البطاقات التي أعادتها صفوف الساميات إلى الفحص.

المصدر الحاكم هو سجل إعادة الفرز، لكن التحقق يقع على حكم كل بطاقة في جسمها.
لا يعتمد هذا البناء على بقاء العنوان وحده، ولا يستعيد أي درجة موجبة.
"""
from __future__ import annotations

import argparse
import collections
import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent
SOURCE = ROOT / "data" / "semitic-row-retraction-rescreen.json"
DATA = ROOT / "data" / "semitic-row-reopened-lane-b-queue.json"
AUDIT = ROOT / "05-audits" / "2026-08-06-semitic-row-reopened-lane-b-queue.md"

EXPECTED = {
    "RET-REOPEN-SEM-001": {
        "queue_id": "LANE-B-SEM-REOPEN-001",
        "language": "aramaic",
        "language_ar": "الآرامية",
        "word": "עיבא",
        "romanization": "ʕēḇā",
        "sense": "rain cloud",
        "body_fragment": "עיבא `ʕēḇā`، noun، «rain cloud»",
        "remaining_work": "إعادة قراءة النواة دلاليًا، مع فصل وجهي العين والغين، من غير استعادة NUCLEUS-ECHO آليًا",
    },
    "RET-REOPEN-SEM-002": {
        "queue_id": "LANE-B-SEM-REOPEN-002",
        "language": "hebrew",
        "language_ar": "العبرية",
        "word": "רעב",
        "romanization": "ra'év، ra'áv",
        "sense": "hungry، hunger، to hunger",
        "body_fragment": "רעב `ra'év`، adj، «hungry (desirous of food)»",
        "remaining_work": "بناء مسار رغب داخل المروحة المرخصة نفسها، ثم اختبار مدار الجوع والرغبة من غير خلطه برعب",
    },
    "RET-REOPEN-SEM-003": {
        "queue_id": "LANE-B-SEM-REOPEN-003",
        "language": "hebrew",
        "language_ar": "العبرية",
        "word": "מערה",
        "romanization": "m'ará",
        "sense": "cave",
        "body_fragment": "`מערה` `m'ará`، noun، «cave»",
        "remaining_work": "استيفاء قراءة الجذر المجمدة لمغر أو إحالة نافذة إليها، ثم إعادة الحكم الدلالي",
    },
    "RET-REOPEN-SEM-004": {
        "queue_id": "LANE-B-SEM-REOPEN-004",
        "language": "hebrew",
        "language_ar": "العبرية",
        "word": "עץ",
        "romanization": "ʿēṣ",
        "sense": "tree",
        "body_fragment": "`עץ` ʿēṣ، noun، «tree»",
        "remaining_work": "استيفاء بنية الثنائي العبري بإزاء عضة العربية وهائها، ثم اختبار تخصيص الشجر الشائك",
    },
    "RET-REOPEN-SEM-005": {
        "queue_id": "LANE-B-SEM-REOPEN-005",
        "language": "hebrew",
        "language_ar": "العبرية",
        "word": "עול",
        "romanization": "ol",
        "sense": "yoke",
        "body_fragment": "עול `ol`، noun، «yoke»",
        "remaining_work": "تفسير الواو ومضاعفة اللام في עול بإزاء غلل، ثم إعادة قراءة مدار القيد",
    },
}


def extract_card(text: str, marker: str) -> tuple[str, str]:
    if text.count(marker) != 1:
        raise RuntimeError(f"اختل حضور معرّف النسخ في الجسم: {marker}={text.count(marker)}")
    marker_at = text.index(marker)
    start = text.rfind("\n### ", 0, marker_at)
    if start < 0:
        raise RuntimeError(f"لم يوجد رأس البطاقة السابقة للنسخ: {marker}")
    end = text.find("\n### ", marker_at)
    if end < 0:
        end = len(text)
    card = text[start + 1:end]
    heading = card.splitlines()[0]
    return heading, card


def card_id(record: dict) -> str:
    match = re.search(
        r"([a-z]+:family:[0-9a-f]{8,}|(?:kaikki|kellia)_[a-z_]+:\d+:[^`،]+)",
        record["heading"],
    )
    if not match:
        raise RuntimeError(f"لم يستخرج معرّف البطاقة: {record['copy_id']}")
    return match.group(1)


def collect() -> list[dict]:
    payload = json.loads(SOURCE.read_text(encoding="utf-8"))
    records = payload["records"]
    if payload["summary"] != {
        "screened": 146,
        "reopened": 5,
        "positive_verdicts_restored": 0,
        "aramaic_ayin_to_arabic_dad_retractions": 0,
    }:
        raise RuntimeError(f"تغيرت حصيلة إعادة الفرز: {payload['summary']}")
    by_copy = {record["copy_id"]: record for record in records}
    if set(by_copy) != set(EXPECTED):
        raise RuntimeError(
            f"تغير نطاق الطابور: حاضر={sorted(by_copy)}، مطلوب={sorted(EXPECTED)}"
        )

    source_cache: dict[str, str] = {}
    queue: list[dict] = []
    verdict = "- الحكم (إعادة فرز الصفوف السامية، 2026-08-06): OPEN-CANDIDATE؛"
    for copy_id, spec in EXPECTED.items():
        record = by_copy[copy_id]
        if record["language"] != spec["language"] or record["decision"] != "OPEN-CANDIDATE":
            raise RuntimeError(f"اختل لسان البطاقة أو حكمها في السجل: {copy_id}")
        source_file = record["source_file"]
        if source_file not in source_cache:
            source_cache[source_file] = (ROOT / source_file).read_text(encoding="utf-8")
        heading, body = extract_card(source_cache[source_file], copy_id)
        if heading != record["heading"]:
            raise RuntimeError(f"اختل رأس جسم البطاقة: {copy_id}")
        if spec["body_fragment"] not in body:
            raise RuntimeError(f"لم يثبت اسم البطاقة من جسمها: {copy_id}")
        after_copy = body[body.index(copy_id):]
        if verdict not in after_copy:
            raise RuntimeError(f"لم يثبت حكم OPEN-CANDIDATE بعد النسخ: {copy_id}")

        queue.append({
            "queue_id": spec["queue_id"],
            "copy_id": copy_id,
            "retraction_id": record["audit_id"],
            "language": spec["language"],
            "language_ar": spec["language_ar"],
            "word": spec["word"],
            "romanization": spec["romanization"],
            "sense": spec["sense"],
            "layer": record["layer"],
            "licensed_rows": record["rows"],
            "correspondence": record["correspondence"],
            "state": "OPEN-CANDIDATE",
            "card_id": card_id(record),
            "source_file": source_file,
            "heading": heading,
            "remaining_work": spec["remaining_work"],
        })
    return queue


def render_data(queue: list[dict]) -> str:
    counts = collections.Counter(item["language"] for item in queue)
    payload = {
        "schema_version": "1.0",
        "date": "2026-08-06",
        "scope": "Cards reopened only by the 2026-08-06 Semitic-row retraction rescreen.",
        "summary": {
            "total": len(queue),
            "by_language": dict(sorted(counts.items())),
            "positive_verdicts_restored": 0,
        },
        "queue": queue,
    }
    return json.dumps(payload, ensure_ascii=False, indent=2) + "\n"


def render_audit(queue: list[dict]) -> str:
    counts = collections.Counter(item["language_ar"] for item in queue)
    lines = [
        "# محضر طابور المسار ب بعد رفع علّة غياب الصف، 2026-08-06",
        "",
        "## النطاق",
        "",
        "يحصي هذا المحضر البطاقات التي أعادها فحص صفوف الساميات في 2026-08-06 إلى "
        "`OPEN-CANDIDATE` بعد نسخ علّة غياب الصف الصوتي. لا يدخل فيه طابور إعادة فرز "
        "القروض، فذلك نطاق مستقل.",
        "",
        f"الحصيلة {len(queue)} بطاقات: {counts['الآرامية']} آرامية و{counts['العبرية']} عبرية. "
        "لم تستعد أي بطاقة درجة موجبة، وهذه الخمس هي طابور العمل الجديد للمسار ب.",
        "",
        "## البطاقات بألسنتها",
        "",
        "| رقم الطابور | اللسان | الكلمة | الرومنة | المعنى | الطبقة | النقض المنسوخ | الصف المرخّص | ما بقي للمسار ب |",
        "|---|---|---|---|---|---|---|---|---|",
    ]
    for item in queue:
        rows = "، ".join(f"`{row}`" for row in item["licensed_rows"])
        lines.append(
            f"| `{item['queue_id']}` | {item['language_ar']} | `{item['word']}` | "
            f"`{item['romanization']}` | {item['sense']} | {item['layer']} | "
            f"`{item['retraction_id']}` | {rows} | {item['remaining_work']} |"
        )
    lines += [
        "",
        "## ضابط الإدخال إلى المسار ب",
        "",
        "الصف الجديد يرخص التقابل الصوتي وحده. لذلك يبدأ المسار ب من الحكم "
        "`OPEN-CANDIDATE` في كل سطر أعلاه، ويعيد القراءة العضوية وفصل المعنى والقرض "
        "والمتجانسات والبنية الصرفية. لا يرث أي سطر درجته التاريخية المنسوخة.",
        "",
        "## التحقق الجسدي",
        "",
        "قوبل كل معرّف نسخ بجسم بطاقته، وثبت بعده حكم حي واحد يعيدها إلى "
        "`OPEN-CANDIDATE`. كما ثبت الرسم الأصلي والرومنة والمعنى من حقل الكلمة أو العضو "
        "داخل الجسم، لا من بقاء العنوان وحده.",
        "",
    ]
    text = "\n".join(lines)
    if chr(0x2014) in text:
        raise RuntimeError("تسربت شرطة طويلة إلى المحضر")
    return text


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    queue = collect()
    data_text = render_data(queue)
    audit_text = render_audit(queue)
    if args.check:
        if not DATA.exists() or DATA.read_text(encoding="utf-8") != data_text:
            raise RuntimeError("بيانات طابور المسار ب بائتة أو مفقودة")
        if not AUDIT.exists() or AUDIT.read_text(encoding="utf-8") != audit_text:
            raise RuntimeError("محضر طابور المسار ب بائت أو مفقود")
    else:
        DATA.write_text(data_text, encoding="utf-8", newline="\n")
        AUDIT.write_text(audit_text, encoding="utf-8", newline="\n")
    print(json.dumps({"queue": len(queue), "aramaic": 1, "hebrew": 4}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
