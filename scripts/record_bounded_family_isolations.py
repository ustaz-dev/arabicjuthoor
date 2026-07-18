#!/usr/bin/env python3
"""Record two-lens source isolations for the bounded Phoenician/Punic scout."""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from recovery_pipeline.families import FAMILY_REVIEW_STATE, load_family_review_states


ROOT = Path(__file__).resolve().parents[1]
SCOPE_FILE = ROOT / "data" / "phoenician-punic-family-scope.json"
DATE = "2026-07-18"
ISOLATIONS = {
    "nonlexical-isolated": {
        "result": "عزل عنصر غير معجمي؛ الحكم غير صادر.",
        "blocker": "عنصر غير معجمي معزول؛ لا يدخل أحكام النسب.",
        "notes": "صنفته اللقطة حرفًا أو عنصرًا غير معجمي، فحفظ للعرض وأخرج من مسح اللمات.",
    },
    "proper-name-isolated": {
        "result": "عزل علم؛ الحكم غير صادر.",
        "blocker": "علم معزول؛ لا يدخل المعجم العام، ويحتاج بطاقة أسماء مستقلة إن أعيد فتحه.",
        "notes": "وسم المصدر الأسرة علمًا، ففصلت عن المعجم العام من غير إنكار اشتقاق اسم محتمل.",
    },
    "reconstruction-isolated": {
        "result": "عزل تعمير؛ الحكم غير صادر.",
        "blocker": "تعمير معزول حتى يثبت شاهد منشور مسمى للصورة.",
        "notes": "وسم المصدر الصورة تعميرًا، فحفظت ولم تعامل كشاهد منقول.",
    },
}


def expected_states() -> dict[str, dict]:
    scope = json.loads(SCOPE_FILE.read_text(encoding="utf-8"))
    expected: dict[str, dict] = {}
    for language in ("phoenician", "punic"):
        for family in scope["languages"][language]["families"]:
            disposition = family["scope_disposition"]
            if disposition not in ISOLATIONS:
                continue
            contract = ISOLATIONS[disposition]
            expected[family["family_id"]] = {
                "status": "suspended",
                "blocker": contract["blocker"],
                "recovery_review": {
                    "reviewer": "ممر الاسترداد البنيوي",
                    "date": DATE,
                    "result": contract["result"],
                    "notes": contract["notes"],
                },
                "skeptical_review": {
                    "reviewer": "ممر التشكيك البنيوي",
                    "date": DATE,
                    "result": contract["result"],
                    "notes": contract["notes"],
                    "loan_screen": "unknown",
                    "homonym_screen": "unknown",
                    "source_check": "clear",
                },
            }
    return expected


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    expected = expected_states()
    payload = load_family_review_states()
    problems = []
    for family_id, state in expected.items():
        actual = payload["families"].get(family_id)
        if actual is not None and actual != state:
            problems.append(f"existing review differs for {family_id}")
        elif args.check and actual is None:
            problems.append(f"missing isolation review for {family_id}")
    if problems:
        for problem in problems:
            print(f"FAIL: {problem}")
        return 1
    if args.check:
        print(f"bounded family isolations: CLEAN ({len(expected)} families)")
        return 0
    for family_id, state in expected.items():
        payload["families"].setdefault(family_id, state)
    temporary = FAMILY_REVIEW_STATE.with_suffix(FAMILY_REVIEW_STATE.suffix + ".tmp")
    temporary.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    temporary.replace(FAMILY_REVIEW_STATE)
    load_family_review_states()
    print(f"recorded {len(expected)} bounded family isolations")
    return 0


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    raise SystemExit(main())
