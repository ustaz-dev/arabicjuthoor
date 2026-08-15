#!/usr/bin/env python3
"""ألحق سجل الإصدار المعياري لموجبات دفعات المسح اللاتيني الثلاث."""

from __future__ import annotations

import hashlib
import json
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
import harvest_reopened_loans as H  # noqa: E402


DATE = "2026-08-15"
READING = ROOT / "04-cross-linguistic" / "readings" / "old-latin.md"
MARKER = "PHONETIC-SWEEP-LATIN-ISSUANCE-001"
MANIFEST = ROOT / "data" / "phonetic-sweep-latin-issuance-register-001.json"
AUDIT = ROOT / "05-audits" / f"{DATE}-phonetic-sweep-latin-issuance-register-001.md"


def marker_in_tail() -> bool:
    size = READING.stat().st_size
    with READING.open("rb") as handle:
        handle.seek(max(0, size - 4 * 1024 * 1024))
        return MARKER.encode("ascii") in handle.read()


def clean(value: object) -> str:
    return H.clean(value)


def main() -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if MANIFEST.exists() or AUDIT.exists() or marker_in_tail():
        raise AssertionError("سجل الإصدار موجود من قبل")
    batches = [
        json.loads(
            (ROOT / "data" / f"phonetic-sweep-latin-harvest-batch-{batch:03d}.json").read_text(
                encoding="utf-8"
            )
        )
        for batch in (1, 2, 3)
    ]
    positives = [
        row for payload in batches for row in payload["rows"] if row["positive_roots"]
    ]
    if len(positives) != 7:
        raise AssertionError(f"انتظر سجل الإصدار سبعة موجبات، وجد {len(positives)}")
    controls = H.control_run()
    if any(item["a_minus_b"] for item in controls):
        raise AssertionError("a-b غير فارغة؛ توقف الإصدار")
    original_stat = READING.stat()
    lines = [
        f"<!-- {MARKER}:START -->", "",
        f"## سجل إصدار موجبات المسح اللاتيني ({DATE})", "",
        "هذه بطاقات إصدار معيارية تحيل إلى بطاقات الأدلة الكاملة؛ لا تعيد بناء المدار ولا تغيره.", "",
    ]
    issued_rows = []
    for row in positives:
        word = str(row["word"])
        root = str(row["positive_roots"][0])
        closure = str(row["closure"])
        family = hashlib.sha1(f"latin:{word}:{root}".encode("utf-8")).hexdigest()[:12]
        issue_id = f"PS-LATIN-ISSUE-{int(row['sweep_rank']):05d}"
        lines.extend([
            f"### بطاقة: `{clean(word)}` «{clean(root)}»؛ {issue_id}", "",
            f"- الرومنة: /{clean(row['say'])}/.",
            "- الخط: `latin` صريحًا.",
            f"- الأسرة: `latin-sweep:family:{family}`.",
            f"- بطاقة الدليل والمدار اليدوي: `{row['id']}`؛ وفيها قراءة الشواهد كاملة بـ`--max-chars 0`.",
            f"- الجذر العربي: `{clean(root)}`.",
            f"- الحكم: {closure}.", "",
        ])
        issued_rows.append({
            "id": issue_id, "evidence_card": row["id"], "word": word,
            "say": row["say"], "script": "latin", "root": root,
            "closure": closure, "family": f"latin-sweep:family:{family}",
        })
    lines.extend([f"<!-- {MARKER}:END -->", ""])
    latest_stat = READING.stat()
    if latest_stat.st_size != original_stat.st_size or latest_stat.st_mtime_ns != original_stat.st_mtime_ns:
        raise AssertionError("تغيّر ملف القراءة أثناء بناء سجل الإصدار")
    with READING.open("a", encoding="utf-8", newline="\n") as handle:
        handle.write("\n\n" + "\n".join(lines))
    payload = {
        "schema": "phonetic-sweep-issuance-register-v1", "date": DATE,
        "language": "latin", "script": "latin", "controls": controls,
        "a_minus_b_nonempty": 0, "issued_cards": len(issued_rows), "rows": issued_rows,
    }
    MANIFEST.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8", newline="\n",
    )
    audit_lines = [
        "# محضر إصدار موجبات المسح اللاتيني", "",
        f"- التاريخ: {DATE}.",
        "- العلة: تعريف الصلة في `count_links.py` يقرأ الحقل القياسي غير المزخرف؛ بطاقات الأدلة أبقت الحكم داخل عريض Markdown فلم تدخل العد.",
        "- الإجراء: سبع بطاقات إصدار صغيرة تحيل إلى بطاقات الأدلة والمدارات اليدوية، من غير نسخ شاهد أو تغيير حكم.",
        "- الضابط: ست بطاقات صادرة، وجميع `a-b` فارغة قبل الإلحاق.",
        "- الخط: `latin` صريحًا، والرومنة مطبوعة في كل بطاقة.", "",
    ]
    audit_lines.extend(
        f"- `{item['id']}`: `{item['word']}` /{item['say']}/ → `{item['root']}`؛ `{item['closure']}`."
        for item in issued_rows
    )
    AUDIT.write_text("\n".join(audit_lines) + "\n", encoding="utf-8", newline="\n")
    print(json.dumps({"issued_cards": len(issued_rows), "a_minus_b_nonempty": 0}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
